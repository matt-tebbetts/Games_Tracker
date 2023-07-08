import os
import pandas as pd
import pytz
from datetime import datetime
import bot_functions

mydata = r'C:\Users\matt_\OneDrive\OneDrive Documents\Python Projects\Tebbetts_Bot\files\mini_test.csv'

df = pd.read_csv(mydata)

winner = df.loc[df['game_rank'] == 1]['player_name'].unique()

print(df)
print(f'there are {len(winner)} winners')
print(f'winner is {winner}')
