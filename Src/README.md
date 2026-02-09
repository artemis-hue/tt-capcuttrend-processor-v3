# TikTok Trend System

Automated TikTok trend detection and CapCut template monetization system.

## Version
- Standard processing: v3.3.0
- Enhanced analytics: v3.5.0  
- Dashboard + Drive: v3.6.0

## How It Works
1. GitHub Actions runs daily at 9:00 AM UTC
2. Fetches TikTok data from Apify API (US + UK markets)
3. Processes data: momentum, triggers, cross-market detection
4. Generates BUILD files (TOP20, TOP100, Enhanced)
5. Uploads files to Google Drive
6. Updates Google Sheets dashboard
7. Sends Discord notification

## Repository Structure
```
.github/workflows/
  daily-process.yml       # GitHub Actions workflow (runs daily)
src/
  main.py                 # Orchestrator (v5.5.0)
  daily_processor.py      # Core processing (v5.3.0)
  v35_enhancements.py     # Velocity + competitor analysis
  apify_fetcher.py        # Apify API data fetcher
  discord_notify.py       # Discord webhook notifications
  upload_drive.py         # Google Drive file upload
  update_dashboard.py     # Google Sheets dashboard sync
```

## Required GitHub Secrets
| Secret | Description | Required |
|--------|-------------|----------|
| APIFY_TOKEN | Apify API key | Yes |
| US_VIDEO_TASK_ID | US scraper task ID | Yes |
| UK_VIDEO_TASK_ID | UK scraper task ID | Yes |
| DISCORD_WEBHOOK | Discord webhook URL | Yes |
| GOOGLE_CREDENTIALS | Service account JSON (base64) | For Drive/Dashboard |
| DRIVE_FOLDER_ID | Google Drive folder ID | For Drive upload |
| DASHBOARD_SHEET_ID | Google Sheets spreadsheet ID | For Dashboard |
| US_MUSIC_TASK_ID | US music scraper task ID | Optional |
| UK_MUSIC_TASK_ID | UK music scraper task ID | Optional |

## Manual Trigger
Actions tab → TikTok Daily Processing → Run workflow
