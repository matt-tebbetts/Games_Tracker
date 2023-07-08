import os
import requests
import pandas as pd
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import pytz
from datetime import datetime, timedelta

# get cookie
load_dotenv()
COOKIE = os.getenv('NYT_COOKIE')

# get mini date
now = datetime.now(pytz.timezone('US/Eastern'))
now_ts = now.strftime("%Y-%m-%d %H:%M:%S")
cond1 = (now.weekday() >= 5 and now.hour >= 18)
cond2 = (now.weekday() <= 4 and now.hour >= 22)
if cond1 or cond2:
    mini_dt = (now + timedelta(days=1)).strftime("%Y-%m-%d")
else:
    mini_dt = now.strftime("%Y-%m-%d")

# get leaderboard html
leaderboard_url = 'https://www.nytimes.com/puzzles/leaderboards'
html = requests.get(leaderboard_url, cookies={'NYT-S': COOKIE})

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
df.insert(0, 'game_date', mini_dt)
df['added_ts'] = now_ts

if len(df) == 0:
    print('Nobody did the mini yet')
else:

    # append to master file
    df.to_csv('files/mini_history.csv', mode='a', index=False, header=False)
    print('mini: saved to master file')
    print('mini: attempting to send to BigQuery')

    # append to google bigquery (optional)
    try:
        my_project = 'angular-operand-300822'
        my_table = 'crossword.mini_history'
        df.to_gbq(destination_table=my_table, project_id=my_project, if_exists='append')
        print('mini: it worked! sent to BigQuery')
    except:
        print('mini: error - was unable to send to BigQuery')