"""
upload_drive.py — Upload BUILD files to Google Drive
v5.5.1 FIX: Uses 'drive' scope, supportsAllDrives, and
explicit folder parent to resolve storage quota errors.
"""

import os
import json
import base64
import glob
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


def get_credentials():
    """Decode service account credentials from environment variable."""
    creds_b64 = os.environ.get('GOOGLE_CREDENTIALS', '')
    if not creds_b64:
        raise ValueError('GOOGLE_CREDENTIALS not set')

    creds_json = json.loads(base64.b64decode(creds_b64))
    return service_account.Credentials.from_service_account_info(
        creds_json,
        scopes=[
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/spreadsheets',
        ]
    )


def test_access(service, folder_id):
    """Test that the service account can access the target folder."""
    try:
        folder = service.files().get(
            fileId=folder_id,
            fields='id, name, mimeType',
            supportsAllDrives=True
        ).execute()
        print(f"  ✅ Folder accessible: '{folder.get('name')}' ({folder_id})")
        return True
    except Exception as e:
        print(f"  ❌ Cannot access folder {folder_id}: {e}")
        return False


def upload_file(service, filepath, folder_id):
    """Upload a single file to Google Drive folder."""
    filename = os.path.basename(filepath)

    # Check if file already exists (same name) - update instead of duplicate
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

    # Test folder access first
    if not test_access(service, folder_id):
        print("  ❌ Cannot access folder. Check:")
        print("     1. Folder is shared with service account email as Editor")
        print("     2. DRIVE_FOLDER_ID is correct")
        print("     3. Google Drive API is enabled in Google Cloud Console")
        raise RuntimeError("Google Drive folder not accessible")

    today = datetime.now().strftime('%Y-%m-%d')
    output_dir = os.environ.get('OUTPUT_DIR', 'output')

    # Find all output files
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














