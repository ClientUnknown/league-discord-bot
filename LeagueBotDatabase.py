import mysql.connector
import config
import cassiopeia as kass
from cassiopeia import Summoner, Match, Patch
from cassiopeia.core import MatchHistory
from cassiopeia import Queue
from mysql.connector import errorcode

DB_NAME = 'league'


def storeMatches(matchHistory):
	try:
		conn = mysql.connector.connect(user=config.dbUsername, password=config.dbPassword, host=config.dbIP, database=DB_NAME)
		cursor = cnx.cursor()
	except mysql.connector.Error as err:
		if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
			print("Credentials Error")
		elif err.errno == errorcode.ER_BAD_DB_ERROR:
			print("Database does not exist, creating now...")
			createDatabase(cursor)	# Create database if it does not exist
		else:
			print(err)
	else:
		conn.close()

	# Dict of tables
	TABLES = {}
	TABLES['matches'] = (
		"CREATE TABLE 'champions' ("

		)

	# Create the tables from the dict of tables above
	for name, ddl in TABLES.iteritems():
		try:
			print("Creating table {}: ".format(name), end='')
			cursor.execute(ddl)
		except mysql.connector.Error as err:
			if err.errno == errorcode.ER_TABLE_EXISTS_ERROR:
				print("already exists")
			else:
				print(err.msg)
		else:
			print("OK")
	cursor.close()
	cnx.close()

# Function to create the database if it does not exist
def createDatabase(cursor):
	try:
		cursor.execute("CREATE DATABASE {} DEFAULT CHARACTER SET 'utf8'".format(DB_NAME))
	except mysql.connector.Error as err:
		print("Could not create database: {}".format(err))
		return
