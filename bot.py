
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
from bot_config import sql_addr, active_channel_ids, my_intents
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
# connect
# ****************************************************************************** #

# connect
@bot.event
async def on_connect():
    msg = f"{bot_name} connected to {bot_host}"
    logger.info(msg)
    print(msg)

# disconnect
@bot.event
async def on_disconnect():
    msg = f"{bot_name} disconnected from {bot_host}"
    logger.warning(msg)
    print(msg)

# startup
@bot.event
async def on_ready():

    # Fetch all global commands
    #global_commands = await bot.http.get_global_commands(bot.user.id)

    # Delete all global commands
    #for command in global_commands:
        #await bot.http.delete_global_command(bot.user.id, command['id'])

    # sync commands
    try:
        synced = await bot.tree.sync()
        print(f"{bot_name} synced {len(synced)} command(s)")
    except Exception as e:
        print(e)

# ****************************************************************************** #
# commands
# ****************************************************************************** #

# context menu option
@bot.tree.context_menu(name="whothis")
async def whothis(interaction: discord.Interaction, member: discord.Member):
    embed=discord.Embed(title=f"{member.name}#{member.discriminator}", description=f"ID: {member.id}")
    embed.add_field(name="Joined Discord", value=member.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)
    embed.add_field(name="Roles", value=", ".join([role.mention for role in member.roles]), inline=False)
    embed.add_field(name="Activity", value=member.activity)
    embed.set_thumbnail(url=member.avatar.url)
    await interaction.response.send_message(embed=embed)

# just a test
@bot.tree.command(name="hello")
async def hello(interaction: discord.Interaction):
    print(f"{interaction.user} aka {interaction.user.name} called the /hello command")
    await interaction.response.send_message(f"what up, {interaction.user.name}?")

# class for calling leaderboards
@bot.tree.command(name="mini")
async def mini(interaction: discord.Interaction, time_frame: str = None):
    msg = f"this command is for 'mini' leaderboard for time frame: {time_frame}"
    print(msg)
    await interaction.response.send_message(msg)

@bot.tree.command(name="boxoffice")
async def boxoffice(interaction: discord.Interaction, time_frame: str = None):
    msg = f"this command is for 'boxoffice' leaderboard for time frame: {time_frame}"
    print(msg)
    await interaction.response.send_message(msg)

# run bot
bot.run(TOKEN)
