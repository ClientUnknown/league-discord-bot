import discord
import requests
import json
import cassiopeia as kass
import config
import arrow
import random
from sortedcontainers import SortedList
from cassiopeia import Summoner, Match, Patch
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
    ver = False
    realms = kass.get_realms(region="NA")
    print(realms.latest_versions)
    if realms.latest_versions['champion'] != "8.3.1":
        ver = True
    return ver

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


@bot.command()
async def vs(champ1, champ2, roleSelected):
    """Enter <champion> <champion> <middle, top, jungle, duo_carry, duo_support>
    to get information on two champions pitted against eachother"""
    champ1 = champ1.title()
    champ2 = champ2.title()
    roleSelected = roleSelected.upper()
    try:
        champ1ID = all_champions[champ1].id
        champ2ID = all_champions[champ2].id
        
    except Warning as err:
        vsError(err)

# Error catching for vs command
@vs.error
async def vsError(error):
    await bot.say(error)

# Filters the match history that will be pulled for vs command
def filterHistory(summoner, patch):
    endTime = patch.end
    if endTime is None:
        endTime = arrow.now()
    matchHistory = MatchHistory(summoner=summoner, queues={Queue.ranked_flex_fives}, begin_time=patch.start, end_time=endTime)
    return matchHistory

# Pulls matches from the start of the most recent patch using a random SILVER player as starting point
def collectMatches():
    summoner = Summoner(name="Ung5r", region="NA")  # A default summoner to pull matches from
    patchNo = Patch.from_str('8.1', region="NA")

    unpulledSummonerIDS = SortedList([summoner.id])
    pulledSummonerIDS = SortedList()

    unpulledMatchIDS = SortedList()
    pulledMatchIDS = SortedList()

    matchesList = []
    x = 0
    while unpulledSummonerIDS and x != 5:
        newSummonerID = random.choice(unpulledSummonerIDS)
        newSummoner = Summoner(id=newSummonerID, region="NA")
        matches = filterHistory(newSummoner, patchNo)
        unpulledMatchIDS.update([match.id for match in matches])
        unpulledSummonerIDS.remove(newSummonerID)
        pulledSummonerIDS.add(newSummonerID)

        while unpulledMatchIDS and x != 5:
            newMatchID = random.choice(unpulledMatchIDS)
            newMatch = Match(id=newMatchID, region="NA")
            for participant in newMatch.participants:
                if participant.summoner.id not in pulledSummonerIDS and participant.summoner.id not in unpulledSummonerIDS:
                    unpulledSummonerIDS.add(participant.summoner.id)
            unpulledMatchIDS.remove(newMatchID)
            pulledMatchIDS.add(newMatchID)
            x += 1
    x += 1
    champion_id_to_name_mapping = {champion.id: champion.name for champion in kass.get_champions(region="NA")}
    for entry in pulledMatchIDS:
        matchesList.append(kass.get_match(id=entry,region="NA"))
    testing = matchesList[0].participants[0].champion.recommended_itemsets[0].item_sets[0].items
    for item in testing:
        print(item.name)
    return matchesList
collectMatches()

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
        playerStats = watcher.league.positions_by_summoner(
            'na1', playerID['id'])
    except HTTPError as err:
        if err.response.status_code == 404:
            await bot.say("Could not find the user")
        else:
            playerError(err)
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


bot.run(config.discordAPI)
