"""
upload_drive.py — Upload BUILD files to Google Drive
v5.6.0: Uses OAuth2 refresh token (uploads as YOUR account with YOUR quota)

Supports TWO auth methods:
1. OAuth2 refresh token (preferred for personal Gmail) — needs GOOGLE_CLIENT_ID, 
   GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN
2. Service account (fallback for Workspace) — needs GOOGLE_CREDENTIALS
"""

import os
import json
import base64
import glob
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


def get_oauth2_credentials():
    """Get credentials using OAuth2 refresh token (personal Gmail)."""
    from google.oauth2.credentials import Credentials
    
    client_id = os.environ.get('GOOGLE_CLIENT_ID', '')
    client_secret = os.environ.get('GOOGLE_CLIENT_SECRET', '')
    refresh_token = os.environ.get('GOOGLE_REFRESH_TOKEN', '')
    
    if not all([client_id, client_secret, refresh_token]):
        return None
    
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=client_id,
        client_secret=client_secret,
        scopes=[
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/spreadsheets',
        ]
    )
    print("  Auth: OAuth2 refresh token (personal account)")
    return creds


def get_service_account_credentials():
    """Get credentials using service account (Google Workspace)."""
    from google.oauth2 import service_account
    
    creds_b64 = os.environ.get('GOOGLE_CREDENTIALS', '')
    if not creds_b64:
        return None
    
    creds_json = json.loads(base64.b64decode(creds_b64))
    creds = service_account.Credentials.from_service_account_info(
        creds_json,
        scopes=[
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/spreadsheets',
        ]
    )
    print("  Auth: Service account")
    return creds


def get_credentials():
    """Try OAuth2 first (works on personal Gmail), fall back to service account."""
    creds = get_oauth2_credentials()
    if creds:
        return creds
    
    creds = get_service_account_credentials()
    if creds:
        return creds
    
    raise ValueError('No Google credentials configured. Set either '
                     'GOOGLE_CLIENT_ID+GOOGLE_CLIENT_SECRET+GOOGLE_REFRESH_TOKEN '
                     'or GOOGLE_CREDENTIALS')


def test_access(service, folder_id):
    """Test that we can access the target folder."""
    try:
        folder = service.files().get(
            fileId=folder_id,
            fields='id, name, mimeType',
            supportsAllDrives=True
        ).execute()
        print(f"  ✅ Folder accessible: '{folder.get('name')}'")
        return True
    except Exception as e:
        print(f"  ❌ Cannot access folder {folder_id}: {e}")
        return False


def upload_file(service, filepath, folder_id):
    """Upload a single file to Google Drive folder."""
    filename = os.path.basename(filepath)

    try:
        results = service.files().list(
            q=f"name='{filename}' and '{folder_id}' in parents and trashed=false",
            fields='files(id, name)',
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        existing = results.get('files', [])
    except Exception as e:
        print(f"  Warning: Could not check for existing file: {e}")
        existing = []

    mime_map = {
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.txt': 'text/plain',
        '.json': 'application/json',
    }
    ext = os.path.splitext(filename)[1]
    mime = mime_map.get(ext, 'application/octet-stream')
    media = MediaFileUpload(filepath, mimetype=mime, resumable=True)

    if existing:
        file_id = existing[0]['id']
        file = service.files().update(
            fileId=file_id,
            media_body=media,
            supportsAllDrives=True,
        ).execute()
        print(f'  Updated: {filename} (id: {file_id})')
    else:
        metadata = {
            'name': filename,
            'parents': [folder_id],
        }
        file = service.files().create(
            body=metadata,
            media_body=media,
            fields='id',
            supportsAllDrives=True,
        ).execute()
        print(f'  Uploaded: {filename} (id: {file.get("id")})')

    return file.get('id')


def main():
    folder_id = os.environ.get('DRIVE_FOLDER_ID', '')
    if not folder_id:
        raise ValueError('DRIVE_FOLDER_ID not set')

    creds = get_credentials()
    service = build('drive', 'v3', credentials=creds)

    if not test_access(service, folder_id):
        raise RuntimeError("Google Drive folder not accessible")

    today = datetime.now().strftime('%Y-%m-%d')
    output_dir = os.environ.get('OUTPUT_DIR', 'output')

    patterns = [
        f'{output_dir}/BUILD_TODAY_TOP20_{today}.xlsx',
        f'{output_dir}/BUILD_TODAY_TOP100_{today}.xlsx',
        f'{output_dir}/TikTok_Trend_System_US_{today}.xlsx',
        f'{output_dir}/TikTok_Trend_System_UK_{today}.xlsx',
        f'{output_dir}/SUMMARY_REPORT_{today}.txt',
        f'{output_dir}/BUILD_TODAY_*_ENHANCED_{today}.xlsx',
    ]

    files_uploaded = 0
    for pattern in patterns:
        for filepath in glob.glob(pattern):
            try:
                upload_file(service, filepath, folder_id)
                files_uploaded += 1
            except Exception as e:
                print(f'  ❌ Failed to upload {os.path.basename(filepath)}: {e}')

    print(f'\n  ✅ {files_uploaded} files uploaded to Google Drive')

    os.makedirs('data', exist_ok=True)
    with open('data/drive_upload_status.json', 'w') as f:
        json.dump({
            'date': today,
            'files_uploaded': files_uploaded,
            'folder_url': f'https://drive.google.com/drive/folders/{folder_id}',
        }, f)


if __name__ == '__main__':
    main()
