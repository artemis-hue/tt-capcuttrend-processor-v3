# TikTok Trend System

Automated TikTok trend detection and CapCut template monetization system.

## Version
- Standard processing: v3.3.0 (daily_processor.py v5.3.0)
- Enhanced analytics: v3.5.0 (v35_enhancements.py)
- Dashboard + Drive: v3.6.0 (upload_drive.py, update_dashboard.py)
- Orchestrator: main.py v5.6.1
- Seasonal calendar: 46 fixed + 20 variable events (seasonal_calendar.py)

## How It Works
1. GitHub Actions runs daily at 9:00 AM UTC
2. Fetches TikTok data from Apify API (US + UK markets)
3. Processes data: momentum scoring, AI detection, cross-market detection
4. Generates standard BUILD files (TOP20, TOP100) with 8 tabs each
5. Generates Enhanced files with velocity predictions + competitor analysis
6. Generates daily briefing with immediate actions + strategic insights
7. Uploads all files to Google Drive
8. Updates Google Sheets dashboard
9. Sends Discord notification with summary

## Repository Structure
```
.github/workflows/
  daily-process.yml         # GitHub Actions workflow (runs daily 9am UTC)
src/
  main.py                   # Orchestrator (v5.6.0) - runs everything
  daily_processor.py        # Core processing (v5.3.0) - standard BUILD files
  v35_enhancements.py       # Velocity predictions + competitor analysis
  apify_fetcher.py          # Apify API data fetcher
  discord_notify.py         # Discord webhook notifications
  upload_drive.py           # Google Drive file upload (OAuth2 + service account)
  update_dashboard.py       # Google Sheets dashboard sync (+ historical revenue seed)
  seasonal_calendar.py      # 66 seasonal events with 14-day advance alerts
  get_refresh_token.py      # One-time setup: get OAuth2 refresh token
```

## Required GitHub Secrets
| Secret | Description | Required |
|--------|-------------|----------|
| APIFY_TOKEN | Apify API key | Yes |
| US_VIDEO_TASK_ID | US scraper task ID | Yes |
| UK_VIDEO_TASK_ID | UK scraper task ID | Yes |
| DISCORD_WEBHOOK | Discord webhook URL | Yes |
| GOOGLE_CLIENT_ID | OAuth2 client ID | For Drive/Dashboard |
| GOOGLE_CLIENT_SECRET | OAuth2 client secret | For Drive/Dashboard |
| GOOGLE_REFRESH_TOKEN | OAuth2 refresh token | For Drive/Dashboard |
| DRIVE_FOLDER_ID | Google Drive folder ID | For Drive upload |
| DASHBOARD_SHEET_ID | Google Sheets spreadsheet ID | For Dashboard |
| US_MUSIC_TASK_ID | US music scraper task ID | Optional |
| UK_MUSIC_TASK_ID | UK music scraper task ID | Optional |
| GOOGLE_CREDENTIALS | Service account JSON (base64) | Alternative auth |

## Google Auth Setup
For personal Gmail accounts, use OAuth2 (recommended):
1. Create OAuth2 credentials in Google Cloud Console
2. Run `python src/get_refresh_token.py` locally
3. Add CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN as GitHub secrets

For Google Workspace, use service account (alternative):
1. Create service account in Google Cloud Console
2. Base64 encode the JSON key
3. Add as GOOGLE_CREDENTIALS secret

## Output Files (8 standard + 3 enhanced)
| File | Tabs | Description |
|------|------|-------------|
| BUILD_TODAY_TOP20 | 8 | Top 20 per category (validated) |
| BUILD_TODAY_TOP100 | 8 | Top 100 per category (validated) |
| TikTok_Trend_System_US | 1 | Full US data |
| TikTok_Trend_System_UK | 1 | Full UK data |
| SUMMARY_REPORT | text | Daily summary + briefing |
| BUILD_TODAY_US_ENHANCED | 5 | Velocity + competitor (US) |
| BUILD_TODAY_UK_ENHANCED | 5 | Velocity + competitor (UK) |
| BUILD_TODAY_COMBINED_ENHANCED | 5 | Both markets combined |

## Manual Trigger
Actions tab → TikTok Daily Processing → Run workflow
