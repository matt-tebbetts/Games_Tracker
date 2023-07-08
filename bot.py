
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

# startup
@bot.event
async def on_ready():

    # sync commands
    try:
        synced = await bot.tree.sync()
        print(f"synced {len(synced)} command(s)")
    except Exception as e:
        print(e)

    # get time
    now_txt = datetime.now(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d %H:%M:%S")

    # get latest user list
    all_users = pd.DataFrame(columns=["guild_id", "guild_nm", "member_id", "member_nm", "insert_ts"])
    for guild in bot.guilds:
        logger.debug(f"Connected to {guild.name}")
        members = guild.members
        member_data = []
        for member in members:
            guild_id = guild.id
            guild_nm = guild.name
            member_id = member.id
            member_nm = str(member)[:-2] if str(member).endswith("#0") else str(member)
            member_data.append([guild_id, guild_nm, member_id, member_nm, now_txt])
        guild_users = pd.DataFrame(member_data, columns=["guild_id", "guild_nm", "member_id", "member_nm", "insert_ts"])
        all_users = pd.concat([all_users, guild_users], ignore_index=True)
    engine = create_engine(sql_addr)
    all_users.to_sql('discord_users', con=engine, if_exists='replace', index=False)

    # confirm
    logger.debug(f"{bot_name} has been connected to {socket.gethostname()}")
    logger.debug(f"{bot.user.name} is ready!")

"""
# read channel messages
@bot.event
async def on_message(message):
    
    # Create the conditions list
    exit_conditions = [
        message.channel.id not in active_channel_ids,
        message.author == bot.user
    ]

    # Check if any condition is True
    if any(exit_conditions):
        return

    msg_text = str(message.content)

    # check for game score
    for game_prefix in game_prefixes:

        # find prefix
        if str.lower(msg_text).startswith(str.lower(game_prefix)):

            # get message detail
            game_date = datetime.now(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d")
            
            # get discord name
            author = message.author.name
            user_id = author[:-2] if author.endswith("#0") else author

            logger.debug(f"{user_id} posted a score for {game_prefix}")

            # send to score scraper
            response = bot_functions.add_score(game_prefix, game_date, user_id, msg_text)

            # react with proper emoji
            emoji = '❌' if not response[0] else emoji_map.get(game_prefix.lower(), '✅')         
            await message.add_reaction(emoji)
        
            # exit the loop since we found the prefix
            break

    # run the message check
    await bot.process_commands(message)
"""

# ****************************************************************************** #
# commands
# ****************************************************************************** #

# get leaderboards
@bot.tree.command(name='get')
async def get(interaction: discord.Interaction, time_frame=None):

    # set context
    ctx = await bot.get_context(interaction)
    print(interaction.message.author)
    print(interaction.message.author.name)
    print(interaction.message.author.discriminator)

    # clarify request
    if ctx.author.discriminator == "0":
        user_nm = ctx.author.name
    else:
        user_nm = ctx.author.name + "#" + ctx.author.discriminator
    
    guild_id = str(ctx.guild.id)
    guild_nm = ctx.guild.name
    game_name = ctx.invoked_with
    
    # default time_frame to 'today' if not provided
    if time_frame is None:
        time_frame = 'today'
    time_frame = str.lower(time_frame)

    # print
    logger.debug(f"{guild_nm} user {user_nm} requested {game_name} leaderboard for {time_frame}.")

    # get the min_date and max_date based on the user's input
    date_range = bot_functions.get_date_range(time_frame)
    if date_range is None:
        return await ctx.channel.send("Invalid date range or format. Please try again with a valid date range or keyword (e.g., 'yesterday', 'last week', 'this month', etc.).")
    min_date, max_date = date_range

    # get the data
    try:
        
        # run new mini before pulling leaderboard
        if game_name == 'mini':
            mini_response = bot_functions.get_mini()
            logger.debug(f"Got latest mini scores from NYT")
        
        await asyncio.sleep(1) # wait a second before running query

        # pull leaderboard
        img = bot_functions.get_leaderboard(guild_id, game_name, min_date, max_date, user_nm)
        
        # send it
        await ctx.channel.send(file=discord.File(img))

    except Exception as e:
        error_message = f"Error getting {game_name} leaderboard: {str(e)}"
        await ctx.channel.send(error_message)

# run bot
bot.run(TOKEN)
