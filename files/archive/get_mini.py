# set this to true to avoid bigquery during testing
import pandas as pd
import bot_functions
import pytz
from datetime import datetime, timedelta
from sys import exit

# get mini date
now = datetime.now(pytz.timezone('US/Eastern'))
now_ts = now.strftime("%Y-%m-%d %H:%M:%S")
cond1 = (now.weekday() >= 5 and now.hour >= 18)
cond2 = (now.weekday() <= 4 and now.hour >= 22)
if cond1 or cond2:
    mini_dt = (now + timedelta(days=1)).strftime("%Y-%m-%d")
else:
    mini_dt = now.strftime("%Y-%m-%d")

# get mini into df
df = bot_functions.get_nyt(mini_dt, now_ts)

# append to master csv
df.to_csv('files/mini_history.csv', mode='a', index=False, header=False)
print('saved to master file')

# set up for image creation
real_names = pd.read_csv('../users.csv')
img_df = pd.merge(df, real_names, how='inner', on='player_id')
img_df = img_df[img_df['give_rank'] == True][['player_name', 'game_time']].reset_index(drop=True)
game_rank = img_df['game_time'].rank(method='dense').astype(int)
img_df.insert(0, 'game_rank', game_rank)

# image creator
fig = bot_functions.render_mpl_table(img_df, chart_title=f'Mini: {mini_dt}').figure
fig.savefig('files/daily/Mini.png', dpi=300, bbox_inches='tight', pad_inches=.5)

# send to google bigquery (leaving this disabled as of 2022-12-16)
send_to_gbq = False
if send_to_gbq:
    my_project = 'angular-operand-300822'
    my_table = 'crossword.mini_history'
    df.to_gbq(destination_table=my_table, project_id=my_project, if_exists='append')  # , progress_bar=False)
