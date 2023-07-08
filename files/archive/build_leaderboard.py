from datetime import datetime
import pytz
import numpy as np
import pandas as pd
from tabulate import tabulate
import bot_functions

def get_leaderboard(game_id):

    if str.lower(game_id) not in ['wordle', 'worldle', 'factle']:
        print('sorry, not set up yet')
        return

    # (should just build match dataframe or dictionary)
    # set proper case of game name (need to adjust for boxoffice)
    game_id = str.upper(game_id[0]) + str.lower(game_id[1:len(game_id)])

    # get date and time
    now = datetime.now(pytz.timezone('US/Eastern'))
    now_date = now.strftime("%Y-%m-%d")

    # pull game_history for this game
    raw_df = pd.read_csv('../game_history.csv')
    raw_df = raw_df[raw_df['game_name'] == game_id]
    user_df = pd.read_csv('../users.csv')[['player_id', 'player_name']]
    df = pd.merge(raw_df, user_df, how='left', on='player_id')[
        ['game_date', 'game_name', 'game_score', 'added_ts', 'game_dtl', 'player_name']]

    # for now...
    df = df[df['game_name'] != 'BoxOffice']

    # remove dupes and make some adjustments
    df['game_dtl'] = df['game_dtl'].str[0:19].mask(pd.isnull, 'None')
    df['x'] = df.groupby(['game_date', 'game_name', 'game_dtl', 'player_name'])['added_ts'].rank(method='first')
    df = df[df['x'] == 1]
    df['week_nbr'] = pd.to_datetime(df['game_date']).dt.strftime('%Y-%U')

    # calculate points and stuff (g = guesses)
    max_g = df['game_score'].str[2].astype(int)
    act_g = df['game_score'].str[0].replace('X', 0).astype(int)
    df['played'] = 1
    df['won'] = np.minimum(act_g, 1)
    df['guesses'] = np.where(act_g == 0, max_g + 1, act_g)
    df['points'] = np.where(act_g == 0, 0, pow((max_g + 1) - act_g, 2))
    df.rename(columns={'game_score': 'score', 'player_name': 'player'}, inplace=True)

    # build daily leaderboard
    df_day = df[(df['game_name'] == game_id) & (df['game_date'] == now_date)][['player', 'score', 'points']]
    rank = df_day['points'].rank(method='dense', ascending=False)
    df_day.insert(loc=0, column='rank', value=rank)
    df_day.set_index('rank', drop=True, inplace=True)
    df_day.sort_values(by='points', ascending=False, inplace=True)
    print('daily for ' + game_id)
    print('')

    # save image
    path_daily = 'files/daily/' + game_id + '.png'
    chart_title = f'{game_id}, {now_date}'
    fig = bot_functions.render_mpl_table(df_day, chart_title=chart_title).figure
    fig.savefig(path_daily, dpi=300, bbox_inches='tight', pad_inches=.5)
    print(f'ok, printed daily leaderboard image for {game_id} to {path_daily}')
    print('')

    # create weekly leaderboard
    current_week = np.max(df['week_nbr'])
    df_week = df[(df['game_name'] == game_id) & (df['week_nbr'] == current_week)]
    df_week = df_week \
        .groupby(['week_nbr', 'game_name', 'player'], as_index=False) \
        .agg({'played': 'sum',
              'won': 'sum',
              'points': 'sum',
              'guesses': 'mean'}) \
        .sort_values(by='points', ascending=False) \
        .rename(columns={'guesses': 'avg_guess'})
    rank = df_week.groupby(['game_name'])['points'].rank(method='dense', ascending=False).astype(int)
    df_week.insert(loc=0, column='rank', value=rank)
    df_week.drop(columns={'week_nbr', 'game_name'}, inplace=True)
    df_week.set_index('rank', drop=True, inplace=True)
    df_week['avg_guess'] = np.round(df_week['avg_guess'], 1)
    print('weekly for ' + game_id)
    print(tabulate(df_week, headers='keys', tablefmt='psql'))
    print('')

    # save image
    path_wkly = 'files/weekly/' + game_id + '.png'
    fig = bot_functions.render_mpl_table(df_week, chart_title=f'{game_id}, Week #{current_week}').figure
    fig.savefig(path_wkly, dpi=300, bbox_inches='tight', pad_inches=.5)
    print(f'ok, printed weekly leaderboard image for {game_id} to {path_wkly}')
    print('')
