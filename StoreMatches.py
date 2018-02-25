import cassiopeia as kass
import config
import arrow
import random
import time
import LeagueBotDatabase as db
import pymysql
from sortedcontainers import SortedList
from cassiopeia import Summoner, Match, Patch, Champion, Queue
from cassiopeia.core import MatchHistory

kass.set_riot_api_key(config.riotAPI)
#champion_id_to_name_mapping = {champion.id: champion.name for champion in kass.get_champions(region="NA")}


# Pulls matches from the start of the most recent patch using a random SILVER player as starting point
def collectMatches():
    summoner = Summoner(name="Ung5r", region="NA")  # A default summoner to pull matches from
    patchNo = Patch.from_str('8.1', region="NA")

    # Create some sorted lists to store the IDs of players and matches being analyzed.
    # Match info can only be pulled on a player basis so we'll have to pull each player
    # from a match to then get further match info.
    unpulledSummonerIDS = SortedList([summoner.id])
    pulledSummonerIDS = SortedList()
    unpulledMatchIDS = SortedList()
    pulledMatchIDS = SortedList()

    matchesList = []

    while unpulledSummonerIDS and len(pulledMatchIDS) < 1000:
        newSummonerID = random.choice(unpulledSummonerIDS)
        newSummoner = Summoner(id=newSummonerID, region="NA")
        matches = filterHistory(newSummoner, patchNo)
        unpulledMatchIDS.update([match.id for match in matches if match.id not in unpulledMatchIDS])
        unpulledSummonerIDS.remove(newSummonerID)
        pulledSummonerIDS.add(newSummonerID)

        while unpulledMatchIDS:
            newMatchID = random.choice(unpulledMatchIDS)
            newMatch = Match(id=newMatchID, region="NA")
            for participant in newMatch.participants:
                if participant.summoner.id not in pulledSummonerIDS and participant.summoner.id not in unpulledSummonerIDS:
                    unpulledSummonerIDS.add(participant.summoner.id)
            unpulledMatchIDS.remove(newMatchID)
            if newMatchID not in pulledMatchIDS:
                pulledMatchIDS.add(newMatchID)

    # Populate the list of matches by match ID
    for entry in pulledMatchIDS:
        matchesList.append(kass.get_match(id=entry,region="NA"))
    
    return matchesList

# Filters the match history that will be pulled
def filterHistory(summoner, patch):
    # This is the timeframe we want to pull matches from, based on patch versions
    endTime = patch.end
    if endTime is None:
        endTime = arrow.now()   # If there is an issue with the most recent patch, we'll go until current time
    matchHistory = MatchHistory(summoner=summoner, queues={Queue.ranked_flex_fives}, begin_time=patch.start, end_time=endTime)
    return matchHistory

# Collect usage information on a champion-basis of items and summoner spells
def collectItemUsage():
    matchesList = collectMatches()
    # Start by creating dictionaries of every spell, item, rune, and champion names
    try:
        itemUsage = {champion.name: [{spell.name: 0 for spell in kass.get_summoner_spells(region="NA")},
                    {item.name: 0 for item in kass.get_items(region="NA")}, 
                    {rune.name: 0 for rune in kass.get_runes(region="NA")}] for champion in kass.get_champions(region="NA")}
    except Warning as err:
        print(err)
    for match in matchesList:
        for player in match.participants:
            currWin = player.stats.win
            if (currWin):   # Only care if there was a win for the champion
                currChamp = player.champion.name
                if player.summoner_spell_d.name in itemUsage[currChamp][0]:
                    itemUsage[currChamp][0][player.summoner_spell_d.name] += 1
                if player.summoner_spell_f.name in itemUsage[currChamp][0]:
                    itemUsage[currChamp][0][player.summoner_spell_f.name] += 1
                for item in player.stats.items:
                    if item is not None and item.name in itemUsage[currChamp][1]:
                        itemUsage[currChamp][1][item.name] += 1 
                for rune in player.runes:
                    if rune is not None and rune.name in itemUsage[currChamp][2]:
                        itemUsage[currChamp][2][rune.name] += 1 
    return itemUsage

# Populate the database with the collected information
def populateTables():
    allChampions = collectItemUsage()

    try:
        conn = pymysql.connect(user=config.dbUsername, password=config.dbPassword, host=config.dbIP, database=config.dbName)
        cursor = conn.cursor()
    except pymysql.Error as err:
        print(err)

    # Calculate the best set of items, spells, and runes for each champion
    # This is based on data only from winning matches as specified in collectItemUsage()
    # Determine the best of each based on whether or not there was a win and how often the item is used
    for champion, value in allChampions.items():
        bestItems = []
        bestSpells = []
        bestRunes = []
        
        # Get best spells for champion
        for spell in allChampions[champion][0].copy():
            if len(bestSpells) < 2:
                best = max(allChampions[champion][0], key=allChampions[champion][0].get)
                bestSpells.append(best)
                allChampions[champion][0].pop(best)

        # Get best items for champion
        for item in allChampions[champion][1].copy():
            if len(bestItems) < 7:
                best = max(allChampions[champion][1], key=allChampions[champion][1].get)
                bestItems.append(best)
                allChampions[champion][1].pop(best)

        # Get best runes for champion
        for rune in allChampions[champion][2].copy():
            if len(bestRunes) < 7:
                best = max(allChampions[champion][2], key=allChampions[champion][2].get)
                bestRunes.append(best)
                allChampions[champion][2].pop(best)

        # Insert the best spells into champion table
        cursor.execute('''UPDATE champions SET spell1 = %s, spell2 = %s 
                        WHERE champName = %s''', 
                        (bestSpells[0], bestSpells[1], champion))
        conn.commit()
        # Insert the best items into chmapion table
        cursor.execute('''UPDATE champions
                        SET item1=%s,item2=%s,item3=%s,item4=%s,item5=%s,item6=%s,item7=%s 
                        WHERE champName = %s''', 
                        (bestItems[0],bestItems[1],bestItems[2],bestItems[3],bestItems[4],bestItems[5],bestItems[6], champion))
        conn.commit()
        # Insert the best runes into champion table
        cursor.execute('''UPDATE champions
                        SET rune1=%s,rune2=%s,rune3=%s,rune4=%s,rune5=%s,rune6=%s,rune7=%s
                        WHERE champName = %s''', 
                        (bestRunes[0],bestRunes[1],bestRunes[2],bestRunes[3],bestRunes[4],bestRunes[5],bestRunes[6], champion))
        conn.commit()

    if conn.open:
        conn.close()
    cursor.close()
