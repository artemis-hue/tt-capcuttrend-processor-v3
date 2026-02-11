"""
update_dashboard.py — Push daily processed data to Google Sheets dashboard
v5.6.1: Added seed_historical_revenue() for one-time historical data import
"""

import os
import json
import base64
from datetime import datetime
import gspread


# ── Historical revenue data from TikTok_Dashboard_With_Revenue.xlsx ──
# Extracted 2026-02-11 — 28 templates, $10,754 total, 4 at cap
HISTORICAL_REVENUE = [
    {'url': 'https://www.tiktok.com/@7597126976427609366/video/7597126976427609366', 'account': 'Account 1 (smaller)', 'received': 2500, 'estimated': 2500, 'us_installs': 2184, 'row_installs': 3782, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7597399641776508163/video/7597399641776508163', 'account': 'Account 1 (smaller)', 'received': 2500, 'estimated': 2500, 'us_installs': 717, 'row_installs': 1984, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7597123284848610582/video/7597123284848610582', 'account': 'Account 1 (smaller)', 'received': 2500, 'estimated': 2500, 'us_installs': 1196, 'row_installs': 1554, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7597924302243007766/video/7597924302243007766', 'account': 'Account 1 (smaller)', 'received': 2500, 'estimated': 2500, 'us_installs': 671, 'row_installs': 1269, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7597114246433869078/video/7597114246433869078', 'account': 'Account 1 (smaller)', 'received': 324, 'estimated': 324, 'us_installs': 49, 'row_installs': 79, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7597805299315068182/video/7597805299315068182', 'account': 'Account 1 (smaller)', 'received': 106, 'estimated': 106, 'us_installs': 13, 'row_installs': 41, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7597084269701270806/video/7597084269701270806', 'account': 'Account 1 (smaller)', 'received': 314, 'estimated': 314, 'us_installs': 47, 'row_installs': 79, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7597064708012920067/video/7597064708012920067', 'account': 'Account 1 (smaller)', 'received': 2, 'estimated': 2, 'us_installs': 0, 'row_installs': 2, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7599032518100241686/video/7599032518100241686', 'account': 'Account 1 (smaller)', 'received': 3, 'estimated': 3, 'us_installs': 0, 'row_installs': 3, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7597362819398503702/video/7597362819398503702', 'account': 'Account 1 (smaller)', 'received': 5, 'estimated': 5, 'us_installs': 1, 'row_installs': 0, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7597795533490507030/video/7597795533490507030', 'account': 'Account 1 (smaller)', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7597363566458539286/video/7597363566458539286', 'account': 'Account 1 (smaller)', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7597171707987709206/video/7597171707987709206', 'account': 'Account 1 (smaller)', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7591292533720878358/video/7591292533720878358', 'account': 'Account 1 (smaller)', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7597796013792939286/video/7597796013792939286', 'account': 'Account 1 (smaller)', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7597800531087658262/video/7597800531087658262', 'account': 'Account 1 (smaller)', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7597080404323028246/video/7597080404323028246', 'account': 'Account 1 (smaller)', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7597108883814944022/video/7597108883814944022', 'account': 'Account 1 (smaller)', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7603100212176997654/video/7603100212176997654', 'account': 'Account 1 (smaller)', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7597012528090107158/video/7597012528090107158', 'account': 'Account 1 (smaller)', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7597801729450577174/video/7597801729450577174', 'account': 'Account 1 (smaller)', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7597364619035888899/video/7597364619035888899', 'account': 'Account 1 (smaller)', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7590877569394773270/video/7590877569394773270', 'account': 'Account 1 (smaller)', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7582151219729272086/video/7582151219729272086', 'account': 'Account 1 (smaller)', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7581890594608336150/video/7581890594608336150', 'account': 'Account 1 (smaller)', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7597928583667010819/video/7597928583667010819', 'account': 'Account 1 (smaller)', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7582190483133238550/video/7582190483133238550', 'account': 'Account 1 (smaller)', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7581937222518115606/video/7581937222518115606', 'account': 'Account 1 (smaller)', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-09'},
]


def get_gspread_client():
    """Get authenticated gspread client. Tries OAuth2 first, then service account."""
    
    # Method 1: OAuth2 refresh token (personal Gmail)
    client_id = os.environ.get('GOOGLE_CLIENT_ID', '')
    client_secret = os.environ.get('GOOGLE_CLIENT_SECRET', '')
    refresh_token = os.environ.get('GOOGLE_REFRESH_TOKEN', '')
    
    if all([client_id, client_secret, refresh_token]):
        from google.oauth2.credentials import Credentials
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=client_id,
            client_secret=client_secret,
            scopes=[
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive',
            ]
        )
        print("  Auth: OAuth2 refresh token (personal account)")
        return gspread.authorize(creds)
    
    # Method 2: Service account (Google Workspace)
    creds_b64 = os.environ.get('GOOGLE_CREDENTIALS', '')
    if creds_b64:
        from google.oauth2 import service_account
        creds_json = json.loads(base64.b64decode(creds_b64))
        creds = service_account.Credentials.from_service_account_info(
            creds_json,
            scopes=[
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive',
            ]
        )
        print("  Auth: Service account")
        return gspread.authorize(creds)
    
    raise ValueError('No Google credentials configured')


def safe_get_worksheet(sheet, tab_name):
    """Safely get a worksheet by name, return None if not found."""
    try:
        return sheet.worksheet(tab_name)
    except gspread.exceptions.WorksheetNotFound:
        print(f'  ⚠️ Tab "{tab_name}" not found in spreadsheet — skipping')
        return None


def seed_historical_revenue(sheet):
    """One-time seed of historical revenue data into REVENUE_TRACKER.
    
    Checks if data already exists (by URL) and only adds missing entries.
    Safe to call on every run — skips if all entries already present.
    """
    ws = safe_get_worksheet(sheet, 'REVENUE_TRACKER')
    if ws is None:
        return 0

    # Get existing URLs to avoid duplicates
    existing_urls = set()
    try:
        url_col = ws.col_values(1)
        existing_urls = set(url_col[1:])  # Skip header
    except Exception:
        pass

    # Filter to only entries not already in the sheet
    new_entries = [h for h in HISTORICAL_REVENUE if h['url'] not in existing_urls]

    if not new_entries:
        print('  REVENUE_SEED: All historical data already present — skipping')
        return 0

    # Build rows matching the 19-column REVENUE_TRACKER structure
    next_row = len(existing_urls) + 2  # +1 for header, +1 for next empty
    rows = []
    for i, entry in enumerate(new_entries):
        r = next_row + i

        rows.append([
            entry['url'],                    # Col 1: TikTok URL
            entry['account'],                # Col 2: Account
            '',                              # Col 3: Template Link
            entry['received'],               # Col 4: Received ($)
            entry['estimated'],              # Col 5: Estimated ($)
            entry['us_installs'],            # Col 6: US & EU3 Installs
            entry['row_installs'],           # Col 7: ROW Installs
            f'=F{r}+G{r}',                  # Col 8: Total Installs (formula)
            f'=IFERROR(E{r}/H{r},0)',        # Col 9: Rev/Install (formula)
            f'=IF(E{r}>=2500,"✅ CAP","")',  # Col 10: At Cap? (formula)
            '',                              # Col 11: Trend Description
            '',                              # Col 12: Momentum at Detection
            '',                              # Col 13: Trigger Level
            '',                              # Col 14: Action Window
            '',                              # Col 15: Market
            '',                              # Col 16: AI Category
            '',                              # Col 17: Age at Detection
            entry['date'],                   # Col 18: Date First Seen
            'Historical import',             # Col 19: Notes
        ])

    if rows:
        ws.append_rows(rows, value_input_option='USER_ENTERED')

    total_rev = sum(e['received'] for e in new_entries)
    cap_count = sum(1 for e in new_entries if e['received'] >= 2500)
    print(f'  REVENUE_SEED: {len(rows)} historical entries added (${total_rev:,} revenue, {cap_count} at cap)')
    return len(rows)


def update_opportunity_now(sheet, opportunity_data):
    ws = safe_get_worksheet(sheet, 'OPPORTUNITY_NOW')
    if ws is None:
        return 0
    if ws.row_count > 1:
        try:
            ws.delete_rows(2, ws.row_count)
        except Exception:
            pass
    if not opportunity_data:
        return 0
    rows = []
    for item in opportunity_data:
        rows.append([
            item.get('Priority', ''),
            item.get('Build Priority', item.get('build_priority', '')),
            item.get('Time Zone', item.get('time_zone', '')),
            item.get('Time Remaining', item.get('time_note', '')),
            str(item.get('Trend', ''))[:50],
            str(item.get('Creator', ''))[:20],
            item.get('Momentum', item.get('momentum_score', 0)),
            item.get('Opportunity Score', item.get('opportunity_score', 0)),
            item.get('Age', ''),
            item.get('Market', ''),
            item.get('seasonal_event', ''),
            '✅' if item.get('previously_actioned', False) else '',
            item.get('URL', item.get('webVideoUrl', '')),
        ])
    if rows:
        ws.append_rows(rows, value_input_option='USER_ENTERED')
    print(f'  OPPORTUNITY_NOW: {len(rows)} rows written')
    return len(rows)


def append_competitor_view(sheet, competitor_data, date_str):
    ws = safe_get_worksheet(sheet, 'COMPETITOR_VIEW')
    if ws is None:
        return 0
    rows = []
    for gap in competitor_data:
        rows.append([
            date_str,
            gap.get('competitor', ''),
            str(gap.get('trend_text', ''))[:60],
            gap.get('competitor_momentum', 0),
            gap.get('your_momentum', 0),
            gap.get('competitor_shares_h', 0),
            gap.get('market', ''),
            gap.get('gap_type', ''),
            gap.get('hours_difference', gap.get('hours_behind', '')),
            gap.get('estimated_missed_revenue', 0),
            gap.get('ai_category', ''),
            gap.get('trend_url', ''),
        ])
    if rows:
        ws.append_rows(rows, value_input_option='USER_ENTERED')
    print(f'  COMPETITOR_VIEW: {len(rows)} rows appended')
    return len(rows)


def append_prediction_log(sheet, model_summary, date_str):
    ws = safe_get_worksheet(sheet, 'PREDICTION_LOG')
    if ws is None:
        return 0
    if not model_summary or 'direction_accuracy_pct' not in model_summary:
        print('  PREDICTION_LOG: No accuracy data')
        return 0
    outcomes = model_summary.get('action_outcomes', {})
    suggestions = model_summary.get('tuning_suggestions', [])
    row = [
        date_str,
        model_summary.get('trends_tracked', 0),
        model_summary.get('direction_accuracy_pct', 0) / 100,
        model_summary.get('bias', 'N/A'),
        model_summary.get('mean_absolute_pct_error', 0),
        outcomes.get('CORRECT_BUILD', 0),
        outcomes.get('FALSE_POSITIVE', 0),
        outcomes.get('MISSED_OPPORTUNITY', 0),
        outcomes.get('CORRECT_SKIP', 0),
        suggestions[0][:100] if suggestions else '',
    ]
    ws.append_row(row, value_input_option='USER_ENTERED')
    print(f'  PREDICTION_LOG: 1 row appended')
    return 1


def append_data_feed(sheet, my_performance_data, date_str):
    ws = safe_get_worksheet(sheet, 'DATA_FEED')
    if ws is None:
        return 0
    rows = []
    for item in my_performance_data:
        rows.append([
            date_str,
            item.get('Account', ''),
            str(item.get('Trend', ''))[:60],
            item.get('Age', ''),
            item.get('Momentum', 0),
            item.get('Status', ''),
            item.get('Market', ''),
            item.get('Views/h', 0),
            item.get('Shares/h', 0),
            item.get('BUILD_NOW', ''),
            item.get('TikTok URL', ''),
            item.get('TUTORIAL_TRIGGER', ''),
            item.get('URGENCY', ''),
            item.get('Trigger Reason', ''),
            item.get('AI_CATEGORY', item.get('ai_category', '')),
            item.get('opportunity_score', ''),
            item.get('time_zone', ''),
            item.get('build_priority', ''),
            item.get('seasonal_event', ''),
        ])
    if rows:
        ws.append_rows(rows, value_input_option='USER_ENTERED')
    print(f'  DATA_FEED: {len(rows)} rows appended')
    return len(rows)


def update_seasonal_alerts(sheet, seasonal_alerts):
    ws = safe_get_worksheet(sheet, 'DASHBOARD')
    if ws is None:
        return
    alert_start_row = 18
    actionable = [a for a in seasonal_alerts
                  if a.get('priority', '') in ('🔴 CRITICAL', '🟠 HIGH', '🟡 PREP', '🟢 HEADS_UP')]
    for i in range(3):
        row = alert_start_row + i
        if i < len(actionable):
            alert = actionable[i]
            ws.update_cell(row, 1, alert.get('priority', ''))
            ws.update_cell(row, 2, alert.get('event', ''))
            ws.update_cell(row, 3, alert.get('message', ''))
        else:
            ws.update_cell(row, 1, '')
            ws.update_cell(row, 2, '')
            ws.update_cell(row, 3, '')
    print(f'  DASHBOARD: {min(len(actionable), 3)} seasonal alerts updated')


def update_revenue_tracker_metadata(sheet, new_templates):
    ws = safe_get_worksheet(sheet, 'REVENUE_TRACKER')
    if ws is None:
        return 0
    existing_urls = set()
    try:
        url_col = ws.col_values(1)
        existing_urls = set(url_col[1:])
    except Exception:
        pass
    new_rows = []
    for tpl in new_templates:
        url = tpl.get('TikTok URL', tpl.get('webVideoUrl', ''))
        if url and url not in existing_urls and url != 'nan':
            new_rows.append([
                url, tpl.get('Account', ''), '', 0, 0, 0, 0,
                '', '', '',
                str(tpl.get('Trend', ''))[:60],
                tpl.get('Momentum', 0),
                tpl.get('URGENCY', tpl.get('trigger_level', '')),
                tpl.get('action_window', ''),
                tpl.get('Market', ''),
                tpl.get('AI_CATEGORY', tpl.get('ai_category', '')),
                tpl.get('Age', ''),
                datetime.now().strftime('%Y-%m-%d'),
                '',
            ])
    if new_rows:
        next_row = len(existing_urls) + 2
        for i, row in enumerate(new_rows):
            r = next_row + i
            row[7] = f'=F{r}+G{r}'
            row[8] = f'=IFERROR(E{r}/H{r},0)'
            row[9] = f'=IF(E{r}>=2500,"✅ CAP","")'
        ws.append_rows(new_rows, value_input_option='USER_ENTERED')
    print(f'  REVENUE_TRACKER: {len(new_rows)} new templates pre-filled')
    return len(new_rows)


def main():
    sheet_id = os.environ.get('DASHBOARD_SHEET_ID', '')
    if not sheet_id:
        raise ValueError('DASHBOARD_SHEET_ID not set')

    client = get_gspread_client()
    
    try:
        sheet = client.open_by_key(sheet_id)
    except gspread.exceptions.SpreadsheetNotFound:
        print(f"  ❌ Spreadsheet not found. Check sharing and ID.")
        raise
    except Exception as e:
        print(f"  ❌ Cannot open spreadsheet: {e}")
        raise
    
    today = datetime.now().strftime('%Y-%m-%d')
    print(f'Updating dashboard for {today}...')
    
    tab_names = [ws.title for ws in sheet.worksheets()]
    print(f'  Available tabs: {tab_names}')

    # ── Seed historical revenue (runs once, skips if already done) ──
    seed_historical_revenue(sheet)

    cache_dir = os.environ.get('CACHE_DIR', 'data')
    payload_path = os.path.join(cache_dir, 'dashboard_payload.json')
    
    try:
        with open(payload_path, 'r') as f:
            payload = json.load(f)
    except FileNotFoundError:
        print(f'ERROR: {payload_path} not found.')
        return

    update_opportunity_now(sheet, payload.get('opportunity_matrix', []))
    append_competitor_view(sheet, payload.get('competitor_gaps', []), today)
    append_prediction_log(sheet, payload.get('model_summary', {}), today)
    append_data_feed(sheet, payload.get('my_performance', []), today)
    update_seasonal_alerts(sheet, payload.get('seasonal_alerts', []))
    update_revenue_tracker_metadata(sheet, payload.get('new_templates', []))

    print(f'\n✅ Dashboard updated successfully')


if __name__ == '__main__':
    main()
