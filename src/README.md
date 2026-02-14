# TikTok Trend System

Automated TikTok trend detection and CapCut template monetization system.

## Version
- Orchestrator: main.py v5.7.0 (added revenue persistence)
- Standard processing: v3.3.0 (daily_processor.py v5.3.1)
- Enhanced analytics: v3.5.0 (v35_enhancements.py)
- Dashboard + Drive: v3.6.0 (upload_drive.py, update_dashboard.py)
- Revenue persistence: v1.0.0 (revenue_persistence.py) — NEW
- Competitor intel: 7-day deep analysis (competitor_intel_patch.py)
- Seasonal calendar: 46 fixed + 20 variable events (seasonal_calendar.py)
- Micro-polling: 2-hour trend acceleration detection (micro_poller.py)

## How It Works
1. GitHub Actions runs daily at 9:00 AM UTC
2. Fetches TikTok data from Apify API (US + UK markets)
3. **Reads live revenue data from Google Sheets** (preserves manual entries)
4. Processes data: momentum scoring, AI detection, cross-market detection
5. Generates standard BUILD files (TOP20, TOP100) with 8 tabs each
6. Populates revenue column in MY_PERFORMANCE from live data
7. Generates Enhanced files with velocity predictions + competitor analysis
8. Generates daily briefing with immediate actions + strategic insights
9. Uploads all files to Google Drive
10. Updates Google Sheets dashboard (append-only, never overwrites revenue)
11. Sends Discord notification with summary
12. Caches revenue locally as backup

## Revenue Persistence (NEW)
Your Google Sheet REVENUE_TRACKER is the **source of truth** for revenue.
You manually enter revenue figures there. Every daily run reads those
figures before generating files, so your revenue data appears in:

- **BUILD_TODAY_TOP20/TOP100** → MY_PERFORMANCE tab, Column 18 (Revenue)
- **Enhanced dashboard files** → REVENUE_TRACKER tab
- **Summary report** → revenue totals

**Nothing you manually enter is ever overwritten.**

Fallback chain if Google Sheet is unreachable:
1. Local cache (data/revenue_cache.json) from last successful read
2. Embedded seed data (59 historical entries)

## Repository Structure
```
.github/workflows/
  daily-process.yml          # GitHub Actions workflow (runs daily 9am UTC)
  micro-poll.yml             # Micro-polling workflow (every 2 hours 8am-10pm)
src/
  main.py                    # Orchestrator (v5.7.0) - runs everything
  daily_processor.py         # Core processing (v5.3.1) - standard BUILD files
  v35_enhancements.py        # Velocity predictions + competitor analysis + dashboard
  revenue_persistence.py     # NEW: Reads live revenue from Google Sheet
  competitor_intel_patch.py   # 7-day competitor intelligence (9 sections)
  seasonal_calendar.py       # 66 seasonal events with 14-day advance alerts
  apify_fetcher.py           # Apify API data fetcher (with JSON flattening)
  discord_notify.py          # Discord webhook notifications
  upload_drive.py            # Google Drive file upload (OAuth2 + service account)
  update_dashboard.py        # Google Sheets dashboard sync (append-only)
  micro_poller.py            # 2-hour trend acceleration detection
  get_refresh_token.py       # One-time setup: get OAuth2 refresh token
  __init__.py                # Package init
```

## Required GitHub Secrets
| Secret | Description | Required |
|--------|-------------|----------|
| APIFY_TOKEN | Apify API key | Yes |
| US_VIDEO_TASK_ID | US scraper task ID | Yes |
| UK_VIDEO_TASK_ID | UK scraper task ID | Yes |
| DISCORD_WEBHOOK | Discord webhook URL | Yes |
| GOOGLE_CLIENT_ID | OAuth2 client ID | For Drive/Dashboard/Revenue |
| GOOGLE_CLIENT_SECRET | OAuth2 client secret | For Drive/Dashboard/Revenue |
| GOOGLE_REFRESH_TOKEN | OAuth2 refresh token | For Drive/Dashboard/Revenue |
| DRIVE_FOLDER_ID | Google Drive folder ID | For Drive upload |
| DASHBOARD_SHEET_ID | Google Sheets spreadsheet ID | For Dashboard + Revenue |
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
| BUILD_TODAY_US_ENHANCED | 8 | Velocity + competitor + dashboard (US) |
| BUILD_TODAY_UK_ENHANCED | 8 | Velocity + competitor + dashboard (UK) |
| BUILD_TODAY_COMBINED_ENHANCED | 8 | Both markets combined |

## Pipeline Steps
```
Step 1:  Fetch data from Apify (US/UK video + music)
Step 2:  Load yesterday's cache (for 24h tracking)
Step 2b: Fetch live revenue from Google Sheet (NEW)
Step 3:  Process data → standard BUILD files
Step 3b: Enhanced analytics → velocity + competitor files
Step 3c: Daily briefing → appended to summary report
Step 4:  Save today's cache for tomorrow
Step 4b: Cache revenue locally as backup (NEW)
Step 4c: Save competitor history for 7-day intel
Step 5:  Send Discord notification (with seasonal alerts)
Step 5b: Generate dashboard payload
Step 6:  Upload to Google Drive
Step 7:  Update Google Sheets dashboard (append-only)
```

## Manual Trigger
Actions tab → TikTok Daily Processing → Run workflow

## Micro-Polling
Runs every 2 hours (8am-10pm UK time) to detect accelerating trends.
Sends Discord alerts when momentum thresholds are exceeded.
Trigger manually: Actions tab → TikTok Micro-Polling → Run workflow

## Changelog
### v5.7.0 (2026-02-13)
- Added: revenue_persistence.py — reads live revenue from Google Sheet
- Added: Revenue populated in BUILD files MY_PERFORMANCE col 18
- Added: Live revenue used for Enhanced dashboard REVENUE_TRACKER tab
- Added: Local revenue cache as fallback (data/revenue_cache.json)
- Added: Revenue stats in processing summary output
- Changed: main.py Step 2b added for revenue fetch at pipeline start
- Changed: main.py Step 4b added for revenue cache backup
- Unchanged: update_dashboard.py remains append-only (safe)

### v5.6.0 (2026-02-11)
- Added: Google Drive upload for all output files
- Added: Google Sheets dashboard auto-update
- Added: Competitor intel 7-day deep analysis (9 sections)
- Added: Seasonal calendar (66 events)

### v5.4.0 (2026-02-06)
- Added: v3.5.0 velocity predictions + competitor analysis
- Added: Enhanced output files (US, UK, Combined)
- Added: Daily briefing system

### v5.3.0 (2026-01-30)
- Added: GitHub Actions automation
- Added: Apify API integration
- Added: Discord notifications
