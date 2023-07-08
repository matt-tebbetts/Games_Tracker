import pandas as pd
# connect to google drive
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# set credentials
api_key = 'bq_key.json'
credentials = service_account.Credentials.from_service_account_file(api_key)

# build the Drive API service
service = build('drive', 'v3', credentials=credentials)
folder_id = '1XagccMZRt7A83Po0ti0AUo3cP3cpAQjM'
filename = '../game_history.csv'

# Set the search query
query = f"'{folder_id}' in parents and name='{filename}'"

# Search for the file
results = service.files().list(q=query, fields='nextPageToken, files(id, name)').execute()
items = results.get('files', [])
my_fil = items[0]['id']


# add new data to the game_history.csv file
data_to_add = [['2022-12-29', 'test', '0/6', '2022-12-28 15:00:00', 'matt', 'just a test']]

service.files().update(fileId=my_fil, body=data_to_add).execute()
