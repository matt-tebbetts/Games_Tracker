import os
import requests
import pandas as pd
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import pytz
from datetime import date, datetime, timedelta
from sqlalchemy import create_engine, text
import logging
import bot_camera
import bot_queries
from bot_config import credentials, sql_addr
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
import re
import json

# set up logging?
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# get secrets
load_dotenv()
NYT_COOKIE = os.getenv('NYT_COOKIE')

# get variables

# custom swear words
with open("files/swears.txt", "r") as file:
    swear_words_list = [word.strip() for word in file.read().split(',')]


# get now
def get_now():
    return datetime.now(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d %H:%M:%S")

# print and/or log
def bot_print(msg):
    bot_name = 'GAMES_TRACKER_BOT'
    print(f"{get_now()} - {bot_name}: {msg}")
    return

# get main channel for each guild (improved)
def get_main_channel_for_guild(guild_id):
    engine = create_engine(sql_addr)
    connection = engine.connect()
    query = f"""
        SELECT channel_id
        FROM discord_connections
        WHERE guild_channel_category = 'main'
        AND guild_id = :guild_id
    """
    result = connection.execute(text(query), {"guild_id": guild_id})
    row = result.fetchone()
    connection.close()

    if row:
        return int(row[0])
    else:
        return None

# find main channel id for each guild (old)
def get_bot_channels():
    engine = create_engine(sql_addr)
    connection = engine.connect()
    query = f"""
        SELECT guild_id, channel_id, guild_channel_category
        FROM discord_connections
        WHERE guild_channel_category = 'main'
    """
    result = connection.execute(text(query))
    rows = result.fetchall()
    connection.close()

    bot_channels = {}
    for row in rows:
        row_dict = dict(zip(result.keys(), row)) # convert row to dict
        bot_channels[row_dict["guild_id"]] = {
            "channel_id": row_dict["channel_id"],
            "channel_id_int": int(row_dict["channel_id"]),
        }

    return bot_channels

# get mini date
def get_mini_date():
    now = datetime.now(pytz.timezone('US/Eastern'))
    cutoff_hour = 17 if now.weekday() in [5, 6] else 21
    if now.hour > cutoff_hour:
        return (now + timedelta(days=1)).date().strftime("%Y-%m-%d")
    else:
        return now.date().strftime("%Y-%m-%d")

# translate date range based on text
def get_date_range(user_input):
    today = datetime.now(pytz.timezone('US/Eastern')).date()

    # Helper function to parse date string and set year to current year if not provided
    def parse_date(date_str, default_year=today.year):
        date_obj = parse(date_str)
        if date_obj.year == 1900:  # dateutil's default year is 1900 when not provided
            date_obj = date_obj.replace(year=default_year)
        return date_obj.date()

    try:
        if user_input == 'today':
            min_date = max_date = today
        elif user_input == 'yesterday':
            min_date = max_date = today - timedelta(days=1)
        elif user_input == 'last week':
            min_date = today - timedelta(days=today.weekday(), weeks=1)
            max_date = min_date + timedelta(days=6)
        elif user_input == 'this week':
            min_date = today - timedelta(days=today.weekday())
            max_date = today - timedelta(days=1)
        elif user_input == 'this month':
            min_date = today.replace(day=1)
            max_date = today - timedelta(days=1)
        elif user_input == 'last month':
            min_date = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
            max_date = (min_date.replace(month=min_date.month % 12 + 1) - timedelta(days=1))
        elif user_input == 'this year':
            min_date = today.replace(month=1, day=1)
            max_date = today - timedelta(days=1)
        elif user_input == 'last year':
            min_date = today.replace(year=today.year - 1, month=1, day=1)
            max_date = today.replace(year=today.year - 1, month=12, day=31)
        elif user_input == 'all time':
            min_date = date.min
            max_date = date.max
        else:
            dates = [parse_date(d.strip()) for d in user_input.split(':')]
            min_date, max_date = (dates[0], dates[-1]) if len(dates) > 1 else (dates[0], dates[0])
            
        # set to strings
        min_date = min_date.strftime("%Y-%m-%d")
        max_date = max_date.strftime("%Y-%m-%d")

    except Exception as e:
        print(f"Error parsing date range: {e}")

# if you find this comment, you win a prize!
    except(ValueError, TypeError):
        return None
    
    return min_date, max_date

# returns image location of leaderboard
def get_leaderboard(guild_id, game_name, time_frame:str='today', user_nm=None):
    engine = create_engine(sql_addr)
    connection = engine.connect()
    logger.debug(f'Connected to database using {sql_addr}')
    today = datetime.now(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d")

    # set date range
    if game_name == 'mini' and time_frame == 'today':
        min_date = max_date = get_mini_date()
    else:
        min_date, max_date = get_date_range(time_frame)
    
    # format the title
    title_date = min_date if min_date == max_date else f"{min_date} through {max_date}"

    # determine leaderboard query to run
    cols, query = bot_queries.build_query(guild_id, game_name, min_date, max_date, user_nm)

    try:
        # run the query
        result = connection.execute(text(query),
                                                {"guild_id": guild_id,
                                                "game_name": game_name,
                                                "min_date": min_date,
                                                "max_date": max_date,
                                                "user_nm": user_nm})
        rows = result.fetchall()
        connection.close()
    except Exception as e:
        print(f"Error when trying to run SQL query: {e}")
        img = 'files/images/error.png'
        return img

    df = pd.DataFrame(rows, columns=cols)

    # clean some columns
    if 'Rank' in df.columns:
        df['Rank'] = df['Rank'].fillna('').astype(str).apply(lambda x: x.rstrip('.0') if '.' in x and x != '' else x)
    if 'Game' in df.columns:
        df['Game'] = df['Game'].str.capitalize()

    # create image
    img_title = game_name.capitalize() if game_name != 'my_scores' else user_nm
    img = bot_camera.df_to_img(df, img_title=img_title, img_subtitle=title_date)
    return img

# add discord scores to database when people paste them to discord chat
def add_score(game_prefix, game_date, discord_id, msg_txt):

    # get date and time
    now = datetime.now(pytz.timezone('US/Eastern'))
    added_ts = now.strftime("%Y-%m-%d %H:%M:%S")

    # set these up
    game_name = None
    game_score = None
    game_dtl = None
    metric_01 = None
    metric_02 = None # game completed yes/no
    metric_03 = None

    if game_prefix == "#Worldle":
        game_name = "worldle"
        game_score = msg_txt[14:17]

    if game_prefix == "Wordle":
        game_name = "wordle"

        # find position slash for the score
        found_score = msg_txt.find('/')
        if found_score == -1:
            msg_back = [False, 'Invalid format']
            return msg_back
        else:
            game_score = msg_txt[11:14]
            metric_02 = 1 if game_score[0] != 'X' else 0

    if game_prefix in ["#travle", "#travle_usa", "#travle_gbr"]:
        game_name = game_prefix[1:]

        # find position of opening and closing parentheses
        opening_paren = msg_txt.find('(')
        closing_paren = msg_txt.find(')')

        # get substring between parentheses
        game_score = msg_txt[opening_paren+1:closing_paren]

        # set metric_02 based on first character of game_score
        metric_02 = 1 if game_score[0] != '?' else 0

    if game_prefix == "Factle.app":
        game_name = "factle"
        game_score = msg_txt[14:17]
        game_dtl = msg_txt.splitlines()[1]
        lines = msg_txt.split('\n')

        # find green frogs
        g1, g2, g3, g4, g5 = 0, 0, 0, 0, 0
        for line in lines[2:]:
            if line[0] == '🐸':
                g1 = 1
            if line[1] == '🐸':
                g2 = 1
            if line[2] == '🐸':
                g3 = 1
            if line[3] == '🐸':
                g4 = 1
            if line[4] == '🐸':
                g5 = 1
        metric_03 = g1 + g2 + g3 + g4 + g5

        # get top X% denoting a win
        final_line = lines[-1]
        if "Top" in final_line:
            metric_01 = final_line[4:]
            metric_02 = 1
        else:
            game_score = 'X/5'
            metric_02 = 0

    if game_prefix == 'boxofficega.me':
        game_name = 'boxoffice'
        game_dtl = msg_txt.split('\n')[1]
        movies_guessed = 0
        trophy_symbol = u'\U0001f3c6'
        check_mark = u'\u2705'

        # check for overall score and movies_guessed
        for line in msg_txt.split('\n'):

            if line.find(trophy_symbol) >= 0:
                game_score = line.split(' ')[1]

            if line.find(check_mark) >= 0:
                movies_guessed += 1

        metric_01 = movies_guessed

    if game_prefix == 'Atlantic':
        game_name = 'atlantic'
        msg_txt = msg_txt.replace('[', '')

        # find position of colon for time, slash for date
        s = msg_txt.find(':')
        d = msg_txt.find('/')
        if s == -1 or d == -1:
            msg_back = [False, 'Invalid format']
            return msg_back

        # find score and date
        game_score = msg_txt[s - 2:s + 3].strip()
        r_month = msg_txt[d - 2:d].strip().zfill(2)
        r_day = msg_txt[d + 1:d + 3].strip().zfill(2)

        # find year (this is generally not working)
        if '202' in msg_txt:
            y = msg_txt.find('202')
            r_year = msg_txt[y:y + 4]
        else:
            r_year = game_date[0:4]

        game_date = f'{r_year}-{r_month}-{r_day}'

    if game_prefix == 'Connections':
        game_name = 'connections'
        
        # split the text by newlines
        lines = msg_txt.strip().split("\n")

        # only keep lines that contain at least one emoji square
        emoji_squares = ["🟨", "🟩", "🟦", "🟪"]
        lines = [line for line in lines if any(emoji in line for emoji in emoji_squares)]

        max_possible_guesses = 7
        guesses_taken = len(lines)
        completed_lines = 0

        for line in lines:
            # a line is considered completed if all emojis are the same
            if len(set(line)) == 1:
                completed_lines += 1

        metric_02 = int(completed_lines == 4) # did the user complete the puzzle?
        game_score = f"{guesses_taken}/{max_possible_guesses}" if metric_02 == 1 else f"X/{max_possible_guesses}"

    if game_prefix == '#Emovi':
        game_name = 'emovi'

        # split the string into lines
        lines = msg_txt.split('\n')

        # find the line with the score
        for line in lines:
            if '🟥' in line or '🟩' in line:
                score_line = line
                break
        else:
            raise ValueError('No score line found in game text')

        # count the total squares and the position of the green square
        total_squares = 3
        green_square_pos = None
        for i, char in enumerate(score_line):
            if char == '🟩':
                green_square_pos = i

        # if no green square was found, the score is 0
        if green_square_pos is None:
            game_score = f"X/{total_squares}"
            metric_02 = 0
        else:
            game_score = f"{green_square_pos+1}/{total_squares}"
            metric_02 = 1

    if game_prefix == 'Daily Crosswordle':
        game_name = 'crosswordle'
        match = re.search(r"(\d+)m\s*(\d+)s", msg_txt)
        metric_02 = 1
        if match:
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            seconds_str = str(seconds).zfill(2)
            game_score = f"{minutes}:{seconds_str}"

    # put into dataframe
    my_cols = ['game_date', 'game_name', 'game_score', 'added_ts', 'discord_id', 'game_dtl', 'metric_01', 'metric_02', 'metric_03']
    my_data = [[game_date, game_name, game_score, added_ts, discord_id, game_dtl, metric_01, metric_02, metric_03]]
    df = pd.DataFrame(data=my_data, columns=my_cols)

    # append to mySQL
    engine = create_engine(sql_addr)
    df.to_sql(name='game_history', con=engine, if_exists='append', index=False)

    msg_back = f"Added {game_name} for {discord_id} on {game_date} with score {game_score}"

    return msg_back

# check to see if there's a new mini leader
def mini_leader_changed(guild_id):
    query = """
        SELECT guild_id FROM mini_leader_changed
        WHERE guild_id = :guild_id
    """

    try:
        engine = create_engine(sql_addr)
        with engine.connect() as connection:
            result = connection.execute(text(query), {"guild_id": guild_id})
            row = result.fetchone()
            return bool(row)

    except Exception as e:
        logger.error(f"An error occurred while executing query: {e}")
        return None

# find swear words in a message
def find_swear_words_in_message(message_content, swears):
    lowercased_content = message_content.lower()
    found_swears = [swear for swear in swears if swear in lowercased_content]
    return found_swears

def save_message_detail(message, msg_type):
    
    # Find URLs
    urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', message.content)
    
    # Check for GIFs or other attachments
    attachments = [attachment.url for attachment in message.attachments]
    urls.extend(attachments)
    contains_gifs = any(url.endswith('.gif') for url in attachments)
    
    # check for swears
    found_swear_words = find_swear_words_in_message(message.content, swear_words_list)
    
    # Structure data
    message_data = {
        "id": message.id,
        "content": message.content,
        "create_ts": message.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        "edit_ts": message.edited_at.strftime('%Y-%m-%d %H:%M:%S') if message.edited_at else None,
        "length": len(message.content),
        "author_id": message.author.id,
        "author_nm": message.author.name,
        "channel_id": message.channel.id,
        "channel_nm": message.channel.name,
        "has_attachments": bool(message.attachments),
        "has_links": bool(urls),
        "has_gifs": bool(contains_gifs),
        "has_swears": bool(found_swear_words),
        "has_mentions": bool(message.mentions),
        "list_of_attachment_types": [attachment.content_type for attachment in message.attachments],
        "list_of_links": urls,
        "list_of_gifs": [url for url in urls if url.endswith('.gif')],
        "list_of_swears": found_swear_words,
        "list_of_mentioned": [str(user.id) for user in message.mentions]
    }

    # set directory to save file
    if msg_type == "edited":
        directory = f"files/{message.guild.id}/edits"
    else:
        directory = f"files/{message.guild.id}/messages"

    # create it if not exists
    if not os.path.exists(directory):
        os.makedirs(directory)

    # write to it
    with open(f"{directory}/messages.json", "a") as file:
        json.dump(message_data, file)
        file.write('\n')

    print('Message saved to file')

    return