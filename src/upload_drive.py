"""
upload_drive.py — Upload BUILD files to Google Drive
v6.0.0: OAuth2 ONLY (service accounts cannot upload to personal Drive)

Requires: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN
"""

import os
import json
import glob
from datetime import datetime
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


def get_credentials():
    """Get OAuth2 credentials using refresh token. No service account fallback."""
    client_id = os.environ.get('GOOGLE_CLIENT_ID', '')
    client_secret = os.environ.get('GOOGLE_CLIENT_SECRET', '')
    refresh_token = os.environ.get('GOOGLE_REFRESH_TOKEN', '')

    print(f"  OAuth2 secrets: CLIENT_ID={'set' if client_id else 'MISSING'}, "
          f"CLIENT_SECRET={'set' if client_secret else 'MISSING'}, "
          f"REFRESH_TOKEN={'set' if refresh_token else 'MISSING'}")

    if not all([client_id, client_secret, refresh_token]):
        raise ValueError(
            'Google Drive upload requires GOOGLE_CLIENT_ID, '
            'GOOGLE_CLIENT_SECRET, and GOOGLE_REFRESH_TOKEN. '
            'Run get_refresh_token.py to generate these.'
        )

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=client_id,
        client_secret=client_secret,
    )

    # Force token refresh now so we catch errors early
    print("  Refreshing OAuth2 token...")
    creds.refresh(Request())
    print(f"  ✅ OAuth2 token refreshed (expires: {creds.expiry})")

    return creds


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

    # Check if file already exists (for update instead of duplicate)
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
