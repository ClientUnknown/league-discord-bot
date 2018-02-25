import config
import cassiopeia as kass
import pymysql
from cassiopeia import Summoner, Match, Patch
from cassiopeia.core import MatchHistory
from cassiopeia import Queue


# This function will only be used if there is a new patch for League of Legends
# It will store all the matches pulled from LeagueDiscordBot.py in a cloud-hosted database
def storeMatches():
	try:
		conn = pymysql.connect(user=config.dbUsername, password=config.dbPassword, host=config.dbIP, database=config.dbName)
		cursor = conn.cursor()
	except pymysql.Error as err:
		print(err)

	# Dict of tables
	TABLES = {}
	TABLES['champions'] = '''
		CREATE TABLE champions (
			champID		int	NOT NULL,
			champName	varchar(25)	NOT NULL,
			item1		varchar(50),
			item2		varchar(50),
			item3		varchar(50),
			item4		varchar(50),
			item5		varchar(50),
			item6		varchar(50),
			item7		varchar(50),
			rune1		varchar(35),
			rune2		varchar(35),
			rune3		varchar(35),
			rune4		varchar(35),
			rune5		varchar(35),
			rune6		varchar(35),
			rune7		varchar(35),
			spell1		varchar(40),
			spell2		varchar(40),


			PRIMARY KEY(champName)
		)'''

	TABLES['items'] = '''
		CREATE TABLE items (
			itemID		int	NOT NULL,
			itemName	varchar(50)	NOT NULL,

			PRIMARY KEY(itemName)
		)'''

	TABLES['runes'] = '''
		CREATE TABLE runes (
			runeID		int	NOT NULL,
			runeName	varchar(35)	NOT NULL,

			PRIMARY KEY(runeName)
		)'''

	TABLES['spells'] = '''
		CREATE TABLE spells (
			spellID		int	NOT NULL,
			spellName	varchar(40)	NOT NULL,

			PRIMARY KEY(spellName)
		)'''

	# Create the tables from the dict of tables above
	for name, ddl in TABLES.items():
		try:
			print("Creating table {}: ".format(name), end='')
			cursor.execute(ddl)
			conn.commit()
		except pymysql.Error as err:
			print(err)
		else:
			print("OK")


	# Fill tables with all champions, items, spells, and runes
	allChamps = {champion.id: champion.name for champion in kass.get_champions(region="NA")}
	allItems = {item.id: item.name for item in kass.get_items(region="NA")}
	allRunes = {rune.id: rune.name for rune in kass.get_runes(region="NA")}
	allSpells = {spell.id: spell.name for spell in kass.get_summoner_spells(region="NA")}

	addChamp = ('''INSERT INTO champions
					(champID, champName)
					VALUES (%s, %s)
					ON DUPLICATE KEY UPDATE champName=champName''')
	addItem = ('''INSERT INTO items
					(itemID, itemName)
					VALUES (%s, %s)
					ON DUPLICATE KEY UPDATE itemName=itemName''')
	addRune = ('''INSERT INTO runes
					(runeID, runeName)
					VALUES (%s, %s)
					ON DUPLICATE KEY UPDATE runeName=runeName''')
	addSpell = ('''INSERT INTO spells
					(spellID, spellName)
					VALUES (%s, %s)
					ON DUPLICATE KEY UPDATE spellName=spellName''')
	try:
		for champ, name in allChamps.items():
			dataChamp = (champ, name)
			cursor.execute(addChamp, dataChamp)
			conn.commit()
		for item, name in allItems.items():
			dataItem = (item, name)
			cursor.execute(addItem, dataItem)
			conn.commit()
		for rune, name in allRunes.items():
			dataRune = (rune, name)
			cursor.execute(addRune, dataRune)
			conn.commit()
		for spell, name in allSpells.items():
			dataSpell = (spell, name)
			cursor.execute(addSpell, dataSpell)
			conn.commit()
	except pymysql.Error as err:
		print(err)
	else:
		print("Tables populated with default data")

	if conn.open:
		conn.close()
	cursor.close()

# Function to create the database if it does not exist
def createDatabase():
	try:
		conn = pymysql.connect(user=config.dbUsername, password=config.dbPassword, host=config.dbIP, database=config.dbName)
		cursor = conn.cursor()
	except pymysql.Error as err:
		print(err)
	else:
		conn.close()


	try:
		cursor.execute("CREATE DATABASE {} DEFAULT CHARACTER SET 'utf8'".format(DB_NAME))
	except pymysql.Error as err:
		print("Could not create database: {}".format(err))
		return

	cursor.close()
	conn.close()
