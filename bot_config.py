import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import logging
import discord

#####################
## 1. connections
#####################

# load environment
load_dotenv()

# loop through variables
def get_env_variable(var_name):
    """Retrieve the value of an environment variable."""
    value = os.getenv(var_name)
    if not value:
        raise ValueError(f"Environment variable '{var_name}' not found.")
    return value

# assign credentials
credentials = {
    'SQL_USER': get_env_variable('SQLUSER'),
    'SQL_PASS': get_env_variable('SQLPASS'),
    'SQL_HOST': get_env_variable('SQLHOST'),
    'SQL_PORT': get_env_variable('SQLPORT'),
    'SQL_DATA': get_env_variable('SQLDATA'),
    'NYT_COOKIE': get_env_variable('NYT_COOKIE')
}

# build sql connection string
sql_addr = f"mysql+pymysql://{credentials['SQL_USER']}:{credentials['SQL_PASS']}@{credentials['SQL_HOST']}:{credentials['SQL_PORT']}/{credentials['SQL_DATA']}"


#####################
## 2. logging
#####################

def setup_logger(bot_name, bot_host):
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    file_handler = logging.FileHandler(f"files/logs/{bot_name}_{bot_host}.log")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter("%(asctime)s ... %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(file_handler)
    return logger


#####################
## 3. general setup
#####################

# discord connection stuff
my_intents = discord.Intents.all()
my_intents.message_content = True
my_intents.reactions = True
my_intents.emojis_and_stickers = True


#####################
## 4. games
#####################

# editable csv of game configs
game_config_str = """
prefix,nickname,emoji
Mini,Mini,🌎
#Worldle,Worldle,🌎
#travle,Travle,🌍
#travle_usa,Travle USA,🇺🇸
#travle_gbr,Travle GBR,🇬🇧
Factle.app,Factle,📈
boxofficega.me,BoxOffice,🎥
Wordle,Wordle,📚
Atlantic,Atlantic,🌊
Connections,Connections,🔢
#Emovi,Emovi,🎬
Daily Crosswordle,Crosswordle,🧩
"""

# Convert the string to a list of lines
lines = game_config_str.strip().split('\n')

# Get the headers from the first line
headers = lines[0].split(',')

# Convert the rest of the lines into dictionaries
game_config = [dict(zip(headers, line.split(','))) for line in lines[1:]]

# Create dictionaries
game_names = {game['prefix']: game['nickname'] for game in game_config}
game_emojis = {game['prefix']: game['emoji'] for game in game_config}
game_prefixes = [game['prefix'] for game in game_config].sort(key=len, reverse=True)


