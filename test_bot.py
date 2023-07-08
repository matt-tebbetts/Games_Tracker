
# ****************************************************************************** #
# import packages
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
from bot_config import sql_addr, active_channel_ids
from bot_config import game_names, game_emojis, game_prefixes

# discord stuff
import discord
from discord import app_commands
from discord.ext import commands, tasks

# data processing
import logging
import numpy as np
import pandas as pd
import pytz
import json
import re

# timing and scheduling
from datetime import date, datetime, timedelta
import asyncio


# ****************************************************************************** #
# set-up
# ****************************************************************************** #

# pick bot
bot_name = 'GAMES_TRACKER_BOT'
TOKEN = os.getenv(bot_name)

# create logger
logger = setup_logger(bot_name)

# create bot
my_intents = discord.Intents.all()
my_intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=my_intents)

# ****************************************************************************** #
# connecting
# ****************************************************************************** #

# connect
@bot.event
async def on_connect():
    msg = f"{bot_name} has been connected to {socket.gethostname()}"
    logger.info(msg)
    print(msg)

# disconnect
@bot.event
async def on_disconnect():
    msg = f"{bot_name} has been disconnected from {socket.gethostname()}"
    logger.warning(msg)
    print(msg)

# Startup
@bot.event
async def on_ready():
    # Fetch guild and channel information
    for guild in bot.guilds:
        guild_id = str(guild.id)
        guild_nm = guild.name

        for channel in guild.channels:
            if isinstance(channel, discord.TextChannel):
                channel_id = str(channel.id)
                channel_nm = channel.name
                is_active = 1
                is_for_testing = 1 if "test" in channel_nm else 0

                try:
                    # Insert data into the discord_config table
                    insert_data(
                        guild_id=guild_id,
                        channel_id=channel_id,
                        guild_nm=guild_nm,
                        channel_nm=channel_nm,
                        is_active=is_active,
                        is_for_testing=is_for_testing
                    )

                except Exception as e:
                    print(e)

                # Send message if channel is active
                if channel.id in active_channel_ids:
                    await channel.send(f"Howdy! I'm {bot.user.name} and I'm ready to track your games! :video_game:")
                else:
                    print(f"Channel '{channel.name}' ({channel.id}) on guild {guild_nm} ({guild_id}) is not in the list of active channels, so it will be ignored")

    # Get time
    now_txt = datetime.now(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d %H:%M:%S")


def insert_data(guild_id, channel_id, guild_nm, channel_nm, is_active, is_for_testing):
    engine = create_engine(sql_addr)

    try:
        with engine.connect() as connection:
            statement = text(
                """
                INSERT INTO discord_config (guild_id, channel_id, guild_nm, channel_nm, is_active, is_for_testing)
                VALUES (:guild_id, :channel_id, :guild_nm, :channel_nm, :is_active, :is_for_testing)
                """
            )
            print(f"SQL statement is: {statement}")
            print("Now attempting to execute...")
            connection.execute(
                    statement,
                        {
                        "guild_id": guild_id,
                        "channel_id": channel_id,
                        "guild_nm": guild_nm,
                        "channel_nm": channel_nm,
                        "is_active": is_active,
                        "is_for_testing": is_for_testing
                    }
                )

    except Exception as e:
        print(e)

# read channel messages
@bot.event
async def on_message(message):

    # print details
    print(f"message received from {message.author.name} in {message.channel.name} which has id {message.channel.id}")

    # Create the conditions list
    conditions = [
        message.channel.id not in active_channel_ids,
        message.author == bot.user
    ]

    # Check if any condition is True
    if any(conditions):
        return

    # Extract the details from the message
    message_details = {
        "author": message.author.name,
        "author_id": message.author.id,
        "message_text": message.content,
        "emoji_reactions": [str(reaction.emoji) for reaction in message.reactions],
        "hyperlinks": re.findall(r'(https?://[^\s]+)', message.content),
        "message_time": message.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "guild_id": message.guild.id,
        "guild_name": message.guild.name,
        "channel_id": message.channel.id,
        "channel_name": message.channel.name,
        "attachments": [attachment.url for attachment in message.attachments],
        "embeds": [embed.to_dict() for embed in message.embeds]
    }

    # Convert the details to JSON and print it
    message_details_json = json.dumps(message_details, indent=4)

    await bot.process_commands(message)

# ****************************************************************************** #
# commands
# ****************************************************************************** #

# say hello
@bot.tree.command(name='hello')
async def hello(interaction: discord.Interaction):
    msg_to_send = f"""
    Hello, {interaction.user.name} aka {interaction.user.nick}.
    aka {interaction.user.id} aka {interaction.user.mention}.
    This is a slash command. And you are awesome!
    """
    await interaction.response.send_message(msg_to_send, ephemeral=True)

# ****************************************************************************** #
# execution
# ****************************************************************************** #

# run bot
bot.run(TOKEN)
