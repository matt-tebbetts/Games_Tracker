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
from bot_functions import bot_print, get_now

# get nyt cookie
load_dotenv()
NYT_COOKIE = os.getenv('NYT_COOKIE')

# determine mini date (since it changes at 6pm/10pm)
def get_mini_date():
    now = datetime.now(pytz.timezone('US/Eastern'))
    cutoff_hour = 17 if now.weekday() in [5, 6] else 21
    if now.hour > cutoff_hour:
        return (now + timedelta(days=1)).date().strftime("%Y-%m-%d")
    else:
        return now.date().strftime("%Y-%m-%d")

# get mini leaderboard into dataframe
def get_mini_as_dataframe():
    bot_print("Fetching NYT leaderboard...")

    # get leaderboard html
    leaderboard_url = 'https://www.nytimes.com/puzzles/leaderboards'
    html = requests.get(leaderboard_url, cookies={'NYT-S': NYT_COOKIE})

    # find scores in the html
    soup = BeautifulSoup(html.text, features='lxml')
    divs = soup.find_all("div", class_='lbd-score')
    scores = {}
    for div in divs:
        name = div.find("p", class_='lbd-score__name').getText().strip().replace(' (you)', '')
        time_div = div.find("p", class_='lbd-score__time')
        if time_div:
            time = time_div.getText()
            if time != '--':
                scores[name] = time

    # put scores into df
    df = pd.DataFrame(scores.items(), columns=['player_id', 'game_time'])
    df['player_id'] = df['player_id'].str.lower()
    df.insert(0, 'game_date', get_mini_date())
    df['added_ts'] = get_now()

    # return dataframe
    return df

# Function to update leaderboard data to CSV and database
def update_leaderboard_data(df):

    bot_print(f"Found {len(df)} records on your NYT leaderboard.")

    # set variables
    file_name = f"files/mini/{df['game_date'][0]}.csv"
    sql_cols = ['game_date', 'player_id', 'game_time', 'added_ts']
    csv_cols = sql_cols + ['sent_to_sql']

    # configure dataframes
    df['sent_to_sql'] = 0
    merged_df = pd.DataFrame(columns=csv_cols)

    # find new records, which have not been sent to SQL yet
    if os.path.isfile(file_name):
        csv_df = pd.read_csv(file_name)
        bot_print(f"Found {len(csv_df)} records in {file_name}.")

        # merge new and old, keeping oldest
        merged_df = pd.concat([csv_df, df])
        merged_df.sort_values('added_ts', inplace=True)
        merged_df.drop_duplicates(subset=['player_id'], keep='first', inplace=True)

        # separate new records to be sent to sql
        new_records = merged_df[merged_df['sent_to_sql']==0]

        # print message
        bot_print(f"{len(new_records)} record(s) have not been sent to sql yet.")
    
    # if first run of day, all records are new
    else: 
        new_records = df.copy()
        merged_df = df.copy()

    # nothing new?
    if new_records.empty:
        msg = "No new records to add."
        return msg
    
    try:
        # force an exception
        #raise ValueError("Test error - forcing an exception!")
    
        # send to sql
        engine = create_engine(sql_addr)
        new_records[sql_cols].to_sql(name='mini_history', con=engine, if_exists='append', index=False)

        # update the "sent_to_sql" column in the CSV
        new_records.loc[:, 'sent_to_sql'] = 1
        merged_df.loc[new_records.index, 'sent_to_sql'] = 1
        
        # confirm message back
        msg = f"Successfully added {len(new_records)} records to the database."

    except Exception as e:
        msg = f"Failed to add records to the database: {e}. Will try again next time."

    # save daily csv
    merged_df.to_csv(file_name, mode='w', header=True, index=False)

    # return confirmation message
    return msg

# run the script
df = get_mini_as_dataframe()
msg = update_leaderboard_data(df)

# send confirmation message
bot_print(msg)
