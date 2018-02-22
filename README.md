# league-discord-bot
A Discord bot for League of Legends that provides player and champion information

This bot is developed using the Riot API (https://developer.riotgames.com/),
the Cassiopeia wrapper for the Riot API (https://github.com/meraki-analytics/cassiopeia),
the Riot Watcher wrapper for the Riot API (https://github.com/pseudonym117/Riot-Watcher),
the Champion.gg wrapper for the Riot API (http://api.champion.gg),
and the Discord API (https://discordapp.com/developers/docs/intro)

The bot uses a MySQL database stored on a Google Cloud Platform VM. 

The bot may be used with any API keys by simply creating a file called "config.py" in the same directory as LeagueDiscordBot.py
and LeagueBotDatabase.py

Place the following information in the config.py file:
riotAPI = 
championGGAPI = 
discordAPI = 
dbPassword = 
dbUsername = 
dbIP = 

This is a WIP and mainly for use for me and my friends, but feel free to try it out.
