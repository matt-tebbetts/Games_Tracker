from google.cloud import bigquery
from google.oauth2 import service_account

path_to_json = 'gbq_key.json'
my_credentials = service_account.Credentials.from_service_account_file(path_to_json)

my_project = 'angular-operand-300822'
client = bigquery.Client(credentials=my_credentials, project=my_project)
print('connected')