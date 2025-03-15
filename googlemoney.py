from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Scopes for YouTube API
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

# Authenticate and get credentials
flow = InstalledAppFlow.from_client_secrets_file(
    'client_secrets.json', SCOPES)
credentials = flow.run_local_server(port=8080)

# Save credentials for later use
with open('token.json', 'w') as token_file:
    token_file.write(credentials.to_json())