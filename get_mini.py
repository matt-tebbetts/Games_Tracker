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
    df.insert(0, 'game_date', get_mini_date().strftime("%Y-%m-%d"))
    df['added_ts'] = datetime.now(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d %H:%M:%S")

    # return dataframe
    return df

# Function to update leaderboard data to CSV and database
def update_leaderboard_data(df):
    file_name = f"mini_{df['game_date'][0]}.csv"
    
    # determine new records
    if os.path.isfile(file_name):
        csv_df = pd.read_csv(file_name)
        merged_df = pd.concat([csv_df, df]).drop_duplicates(subset=['player_id'], keep='last')
        new_records = merged_df[merged_df['sent_to_sql']==0]
    else: 
        new_records = df

    # set sql confirmation
    new_records['sent_to_sql'] = 0

    # send to database
    if not new_records.empty:
        engine = create_engine(sql_addr)
        try:

            # attempt to send to sql
            new_records.to_sql(name='mini_history', con=engine, if_exists='append', index=False)

            # if it worked, update the "sent_to_sql" column in the CSV
            new_records['sent_to_sql'] = 1
            merged_df.update(new_records)
            merged_df.to_csv(file_name, mode='w', header=True, index=False)

            # confirm message back
            msg = [True, len(new_records)]
            logging.info(f"Successfully added {len(new_records)} records to the database.")

        except Exception as e:

            # confirm failure
            msg = [False, 0]
            logging.error(f"Failed to add records to the database: {e}. Will try again next time.")

    # return confirmation message
    return msg

# put it all together
df = get_mini_as_dataframe()
sql_msg = update_leaderboard_data(df)

# send confirmation message
print(sql_msg)
