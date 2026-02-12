"""
ONE-TIME SETUP: Run this locally to get a refresh token for Google Drive.

This script:
1. Opens your browser for Google login
2. You authorize the app to access your Drive
3. Outputs a REFRESH_TOKEN to paste into GitHub Secrets

You only need to run this ONCE. The refresh token lasts indefinitely.

Prerequisites:
  pip install google-auth-oauthlib

Usage:
  python get_refresh_token.py
"""

import json
from google_auth_oauthlib.flow import InstalledAppFlow

# You need to create OAuth2 credentials (Desktop App) in Google Cloud Console
# and download the JSON file, OR just paste your client_id and client_secret below.

CLIENT_CONFIG = {
    "installed": {
        "client_id": "YOUR_CLIENT_ID_HERE",
        "client_secret": "YOUR_CLIENT_SECRET_HERE",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost"]
    }
}

SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
]

def main():
    print("=" * 50)
    print("Google Drive OAuth2 Token Generator")
    print("=" * 50)
    print()
    
    # Check if user has set their credentials
    if CLIENT_CONFIG['installed']['client_id'] == 'YOUR_CLIENT_ID_HERE':
        print("SETUP NEEDED:")
        print("1. Go to Google Cloud Console > APIs & Services > Credentials")
        print("2. Click '+ CREATE CREDENTIALS' > 'OAuth client ID'")
        print("3. Choose 'Desktop app' as application type")
        print("4. Download the JSON or copy Client ID and Client Secret")
        print("5. Paste them into this script (lines 26-27)")
        print()
        
        client_id = input("Or paste your Client ID here: ").strip()
        client_secret = input("Paste your Client Secret here: ").strip()
        
        if not client_id or not client_secret:
            print("Cannot continue without credentials.")
            return
        
        CLIENT_CONFIG['installed']['client_id'] = client_id
        CLIENT_CONFIG['installed']['client_secret'] = client_secret
    
    flow = InstalledAppFlow.from_client_config(CLIENT_CONFIG, SCOPES)
    
    print("\nOpening browser for authorization...")
    print("(If browser doesn't open, copy the URL from the terminal)")
    print()
    
    creds = flow.run_local_server(port=8080)
    
    print()
    print("=" * 50)
    print("SUCCESS! Copy these values to GitHub Secrets:")
    print("=" * 50)
    print()
    print(f"GOOGLE_CLIENT_ID={CLIENT_CONFIG['installed']['client_id']}")
    print()
    print(f"GOOGLE_CLIENT_SECRET={CLIENT_CONFIG['installed']['client_secret']}")
    print()
    print(f"GOOGLE_REFRESH_TOKEN={creds.refresh_token}")
    print()
    print("Add all three as GitHub Secrets in your repository.")
    print("You can now delete the service account if you want.")

if __name__ == '__main__':
    main()
