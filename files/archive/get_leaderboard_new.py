import os
import socket
import requests
import pandas as pd
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import numpy as np
import matplotlib.pyplot as plt
import six
import pytz
from datetime import datetime, timedelta
from tabulate import tabulate

# this creates two images (daily + weekly) of the leaderboard into the folder
def get_leaderboard(game_name, time_frame='this week'):
    print(f'fetching {time_frame} for {game_name}')

    # get date and time
    now = datetime.now(pytz.timezone('US/Eastern'))
    now_date = now.strftime("%Y-%m-%d")

    if time_frame in ['this week', 'current week']:
        time_field = 'is_this_week'
    elif time_frame in ['last week', 'previous week']:
        time_field = 'is_last_week'

    # get weekly leaderboard
    my_query = """
        select *
        from `crossword.leaders_weekly`
        where game_name = '""" + game_name + """'
        and """ + time_field + """
    """

    df = pd.read_gbq(my_query, project_id=my_project)[
        ['game_week', 'week_rank', 'player_name', 'games', 'wins', 'tot_points']]

    # title should include the game week
    game_week = df['game_week'].unique()[0]
    df.drop(columns='game week')

    print(game_week)

    # save image
    chart_title = f'Week {game_week}: {game_name}'
    img_save_as = f'{img_loc}{game_name}_weekly_{game_week}.png'

    # create image
    fig = render_mpl_table(df, chart_title=chart_title).figure
    fig.savefig(img_save_as, dpi=300, bbox_inches='tight', pad_inches=.5)
    print(f'printed {time_frame} leaderboard image for {game_name} to {img_save_as}')
    exit_msg = [True, f'Got {game_name} for week {game_week}']
    return exit_msg



get_leaderboard('boxoffice', 'this week')