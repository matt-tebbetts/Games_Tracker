
# ****************************************************************************** #
# import
# ****************************************************************************** #

# connections and local python files
import os
import socket
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# custom functions and configurations
from bot_camera import df_to_img
import bot_functions
from bot_config import setup_logger
from bot_config import sql_addr, my_intents
from bot_config import game_names, game_emojis, game_prefixes

# discord stuff
import discord
from discord import app_commands
from discord.ext import commands

# data processing
import logging
import numpy as np
import pandas as pd
import pytz
import json

# timing and scheduling
from datetime import date, datetime, timedelta
import asyncio


# ****************************************************************************** #
# setup
# ****************************************************************************** #

# pick bot
bot_name = 'GAMES_TRACKER_BOT'
bot_host = socket.gethostname()
TOKEN = os.getenv(bot_name)

# create logger
logger = setup_logger(bot_name, bot_host)

# create bot
bot = commands.Bot(command_prefix="/", intents=my_intents)

# ****************************************************************************** #
# convenient functions
# (should move this to bot_functions)
# from bot_functions import get_now, write_json, get_connections, bot_print
# ****************************************************************************** #

# get now
def get_now():
    return datetime.now(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d %H:%M:%S")

# save to json
def write_json(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

# get connected discords
def get_connections():

    # check connections
    guilds = []
    channels = []
    users = []
    users_list = []

    # for each guild
    for guild in bot.guilds:
        
        # add guild
        guilds.append({"name": guild.name, "id": guild.id})

        # add channels
        channels.append({
            "guild_id": guild.id, 
            "guild_name": guild.name, 
            "channels": [{"name": channel.name, "id": channel.id} for channel in guild.channels if isinstance(channel, discord.TextChannel)]
        })

        # add users
        members = [{"name": member.name, "id": member.id, "joined": member.created_at.strftime("%Y-%m-%d")} for member in guild.members]
        users.append({
            "guild_id": guild.id, 
            "guild_name": guild.name, 
            "members": members
        })

        # keep separate users list for sql
        for member in members:
            users_list.append({
                "guild_id": str(guild.id),
                "user_id": str(member['id']),
                "guild_nm": guild.name,
                "user_nm": member['name'],
                "insert_ts": get_now()
            })

    # save to json
    data_dict = {"guilds": guilds, "users": users, "channels": channels}
    for name, data in data_dict.items():
        write_json(data, f"files/connections/{name}.json")

    # save to sql
    df_users = pd.DataFrame(users_list)
    df_users['user_id'] = df_users['user_id'].astype(str)
    df_users['guild_id'] = df_users['guild_id'].astype(str)
    df_users.to_sql('discord_users', create_engine(sql_addr), if_exists='replace', index=False)

    # count
    total_guilds = len(guilds)
    total_users = sum(len(guild['members']) for guild in users)
    total_channels = sum(len(guild['channels']) for guild in channels)

    # print
    msg = f"connected to {total_guilds} guilds, {total_channels} channels, and {total_users} users"
    bot_print(msg)

    return

# print and/or log
def bot_print(msg):
    print(f"{get_now()} - {bot_name}: {msg}")
    return

# ****************************************************************************** #
# connect
# ****************************************************************************** #

# connect
@bot.event
async def on_connect():
    bot_print(f"connected to {bot_host}")

# disconnect
@bot.event
async def on_disconnect():
    bot_print(f"disconnected from {bot_host}")

# startup
@bot.event
async def on_ready():

    # sync commands
    try:
        bot_print("attempting to sync commands...")
        synced = await bot.tree.sync()
        command_names = [command.name for command in synced]
        msg = f"synced {len(synced)} command(s): {', '.join(command_names)}"
    except Exception as e:
        msg = f"failed to sync commands: {e}"
    bot_print(msg)

    # get connections
    get_connections()

    bot_print("ready, awaiting input...")

# ****************************************************************************** #
# commands
# ****************************************************************************** #

# set default channel for reading game scores
@bot.tree.command(name="set_scores_channel", description="Set the default channel for reading game scores")
@commands.has_permissions(administrator=True)
async def set_scores_channel(interaction: discord.Interaction):

    # get details
    guild_id = interaction.guild.id

    # define the new scores channel
    new_scores_channel = {
        "guild_id": guild_id,
        "channel_id": interaction.channel.id,
        "guild_name": interaction.guild.name,
        "channel_name": interaction.channel.name,
        "updated_by": interaction.user.name,
        "updated_at": get_now()
    }

    # load existing data or create new
    try:
        with open('files/connections/score_channels.json', 'r') as f:
            score_channels = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        score_channels = {}

    # remove if exists
    if str(guild_id) in score_channels.keys():
        del score_channels[str(guild_id)]

    # add record and save
    score_channels[guild_id] = new_scores_channel
    write_json(score_channels, 'files/connections/score_channels.json')

    # confirm
    await interaction.response.send_message(f"The scores channel has been set to {interaction.channel.name}")

# context menu option
@bot.tree.context_menu(name="whothis")
async def whothis(interaction: discord.Interaction, member: discord.Member):
    embed=discord.Embed(title=f"{member.name}#{member.discriminator}", description=f"ID: {member.id}")
    embed.add_field(name="Joined Discord", value=member.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)
    embed.add_field(name="Roles", value=", ".join([role.mention for role in member.roles]), inline=False)
    embed.add_field(name="Activity", value=member.activity)
    embed.set_thumbnail(url=member.avatar.url)
    await interaction.response.send_message(embed=embed)

# mini leaderboard
@bot.tree.command(name="mini")
async def mini(interaction: discord.Interaction, time_frame: str = 'today'):

    # set game name equal to command name
    game_name = interaction.command.name

    # confirm command
    msg = f"""Fetching {time_frame}'s {game_name} leaderboard for you...
    """
    await interaction.response.send_message(msg)

    # create leaderboard image
    img = bot_functions.get_leaderboard(guild_id=interaction.guild.id,
                                        game_name=game_name,
                                        time_frame=time_frame,
                                        user_nm=interaction.user.name)
    
    # send image
    await interaction.followup.send(file=discord.File(img))

# other leaderboards?
@bot.tree.command(name="boxoffice")
async def boxoffice(interaction: discord.Interaction, time_frame: str = None):
    msg = f"this command is for 'boxoffice' leaderboard for time frame: {time_frame}"
    print(msg)
    await interaction.response.send_message(msg)

# run bot
bot.run(TOKEN)
