import discord
import requests
import json
import cassiopeia as kass
import config
import arrow
import random
import StoreMatches
import time
import pymysql
from cassiopeia import Summoner, Match, Patch, Champion
from cassiopeia.core import MatchHistory
from cassiopeia import Queue
from discord.ext import commands
from riotwatcher import RiotWatcher
from requests import HTTPError

bot = commands.Bot(
    command_prefix=("!", "@LeagueBot"),
    description='Bot for League of Legends')

champion_gg_api_key = config.championGGAPI
kass.set_riot_api_key(config.riotAPI)
watcher = RiotWatcher(config.riotAPI)

all_champions = kass.Champions(region="NA")

latestLeaguePatch = kass.get_versions(region="NA")


#StoreMatches.populateTables()

# Shows when bot is ready
@bot.event
async def on_ready():
    print('Logged in as ' + bot.user.name)

# Simple hello command
@bot.command()
async def hello():
    await bot.say('Hello!')


# Method that checks if there is a new patch, used for pulling match history
def newPatch():
    currLeaguePatch = kass.get_versions(region="NA")
    newPatch = False
    if currLeaguePatch[0] != latestLeaguePatch[0]:
        newPatch = True
    return newPatch

# Collect new matches if there's been a patch, check every 24 hours
@bot.event
async def checkLeaguePatch():
    if newPatch():
        StoreMatches.populateTables()
        print("New version of League, re-populating database")
    time.sleep(86400)
    checkLeaguePatch()

# This command will generate information on a given champion
@bot.command()
async def champ(champName):
    """Enter <champion> to get general info"""
    champName = champName.title()
    try:
        champID = all_champions[champName].id
        response = requests.get("http://api.champion.gg/v2/champions/%d?elo=SILVER&limit=200&"
                                "champData=averageGames,runes,firstitems,skills,finalitems,damage,summoners,masteries&"
                                "api_key=%s" % (champID, champion_gg_api_key), timeout=30)
        jsonData = json.loads(response.text)
    except Warning as err:
        champError(err)
    for entry in jsonData:
        await bot.say("As " + entry['role'] + " " + champName + " has the following stats:")
        await bot.say("Games Analyzed: " + str(entry['gamesPlayed']))
        await bot.say("Winrate: " + str(100 * round(entry['winRate'], 2)) + "%")
        await bot.say("Percentage of picks in this role: " + str(100 * round(entry['percentRolePlayed'], 2)) + "%")
        await bot.say("Average damage a round: " + str(100 * round(entry['damageComposition']['total'], 0)))
        await bot.say("Ban rate for this role: " + str(100 * round(entry['banRate'], 2)) + "%")
        await bot.say("---------------------------------------------------")

# Error catching for champ command
@champ.error
async def champError(error):
    await bot.say(error)


# This command will generate information on a given player
@bot.command()
async def player(playerName):
    """Enter <player name> to get player information"""
    solo = -1
    flex = -1
    playerID = {}
    playerStats = {}
    wins = " "
    losses = " "
    winrate = 0.0
    try:
        playerID = watcher.summoner.by_name('na1', playerName)
        playerStats = watcher.league.positions_by_summoner('na1', playerID['id'])
    except HTTPError as err:
        if err.response.status_code == 404:
            await bot.say("Could not find the user")
        else:
            await playerError(err)
    # Check here if the data returned from the API call is for solo/duo
    # or for 5v5 flex and keep track of that information
    if not playerStats:
        await bot.say("Player is currently placed in neither Solo nor Flex")
    elif playerStats[0]['queueType'] == "RANKED_SOLO_5x5" or playerStats[0]['queueType'] == "RANKED_SOLO_5X5":
        solo = 0
        flex = 1
    elif playerStats[0]['queueType'] == "RANKED_FLEX_SR":
        solo = 1
        flex = 0
    else:
        await bot.say("Player is currently placed in neither Solo nor Flex")
    if solo != -1 and flex != -1:
        await bot.say(playerName)
        # Print data for Solo
        try:
            if playerStats[solo]['tier']:
                await bot.say("Solo Rank: " + playerStats[solo]['tier'] + " " + playerStats[solo]['rank'])
                wins = playerStats[solo]['wins']
                losses = playerStats[solo]['losses']
                winrate = 100 * float((wins / (wins + losses)))
                await bot.say("Solo Winrate: " + str(round(winrate, 2)) + "%")
                try:
                    await bot.say("Promos Progress: " + playerStats[solo]['miniSeries']['progress'])
                except KeyError:
                    pass
        except Warning:
            await bot.say("Player is not ranked in Solo play")
        # Print data for flex
        try:
            if playerStats[flex]['tier']:
                await bot.say("Flex Rank: " + playerStats[flex]['tier'] + " " + playerStats[flex]['rank'])
                wins = playerStats[flex]['wins']
                losses = playerStats[flex]['losses']
                winrate = 100 * float((wins / (wins + losses)))
                await bot.say("Flex Winrate: " + str(round(winrate, 2)) + "%")
                try:
                    await bot.say("Promos Progress: " + playerStats[flex]['miniSeries']['progress'])
                except KeyError:
                    pass
        except Warning:
            await bot.say("Player is not ranked in Flex play")


# Error catching for player command
@player.error
async def playerError(error):
    await bot.say(error)


@bot.command()
async def guide(champName):
    """Enter <champion name> to get a guide for the champion"""
    champName = champName.title()
    try:
        conn = pymysql.connect(user=config.dbUsername, password=config.dbPassword, host=config.dbIP, database=config.dbName)
        cursor = conn.cursor(pymysql.cursors.DictCursor)
    except pymysql.Error as err:
        print(err)

    await bot.say(champName)

    query = "SELECT * FROM champions WHERE champName = '%s'"
    cursor.execute(query % champName)

    for row in cursor:
        await bot.say("ITEMS")
        await bot.say("------------------")
        for x in range (1, 8):
            await bot.say(row['item%s'%x])
        await bot.say("------------------")
        await bot.say("RUNES")
        await bot.say("------------------")
        for x in range (1, 8):
            await bot.say(row['rune%s'%x])
        await bot.say("------------------")
        await bot.say("SPELLS")
        await bot.say("------------------")
        for x in range (1, 3):
            await bot.say(row['spell%s'%x])

    if conn.open:
        conn.close()
    cursor.close()

bot.run(config.discordAPI)
