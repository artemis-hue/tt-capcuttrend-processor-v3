"""
update_dashboard.py — Push daily processed data to Google Sheets dashboard
v5.5.1 FIX: Uses 'drive' scope (not 'drive.file'), safe tab access,
safe row deletion, handles missing tabs gracefully.

Tabs updated:
- OPPORTUNITY_NOW:  Overwrites with today's opportunity matrix
- COMPETITOR_VIEW:  Appends today's competitor gap analysis
- PREDICTION_LOG:   Appends today's prediction accuracy summary
- DATA_FEED:        Appends today's MY_PERFORMANCE data
- DASHBOARD:        Updates seasonal alerts section
- REVENUE_TRACKER:  Pre-fills new templates (doesn't touch user data)
"""

import os
import json
import base64
from datetime import datetime
from google.oauth2 import service_account
import gspread


def get_gspread_client():
    """Get authenticated gspread client from environment credentials."""
    creds_b64 = os.environ.get('GOOGLE_CREDENTIALS', '')
    if not creds_b64:
        raise ValueError('GOOGLE_CREDENTIALS not set')

    creds_json = json.loads(base64.b64decode(creds_b64))
    creds = service_account.Credentials.from_service_account_info(
        creds_json,
        scopes=[
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive',
        ]
    )
    return gspread.authorize(creds)


def safe_get_worksheet(sheet, tab_name):
    """Safely get a worksheet by name, return None if not found."""
    try:
        return sheet.worksheet(tab_name)
    except gspread.exceptions.WorksheetNotFound:
        print(f'  ⚠️ Tab "{tab_name}" not found in spreadsheet — skipping')
        return None


def update_opportunity_now(sheet, opportunity_data):
    """Overwrite OPPORTUNITY_NOW tab with today's build queue."""
    ws = safe_get_worksheet(sheet, 'OPPORTUNITY_NOW')
    if ws is None:
        return 0

    # Clear existing data (keep headers) — safe check
    if ws.row_count > 1:
        try:
            ws.delete_rows(2, ws.row_count)
        except Exception:
            # If delete fails (e.g. only header), that's OK
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
    """Append today's competitor gap analysis rows."""
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
    """Append one row to PREDICTION_LOG with today's model accuracy metrics."""
    ws = safe_get_worksheet(sheet, 'PREDICTION_LOG')
    if ws is None:
        return 0

    if not model_summary or 'direction_accuracy_pct' not in model_summary:
        print('  PREDICTION_LOG: No accuracy data (first run or no predictions)')
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
    print(f'  PREDICTION_LOG: 1 row appended (accuracy: {model_summary.get("direction_accuracy_pct")}%)')
    return 1


def append_data_feed(sheet, my_performance_data, date_str):
    """Append today's MY_PERFORMANCE data to DATA_FEED."""
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
    """Update seasonal alerts section on DASHBOARD tab."""
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
    """Pre-fill new templates in REVENUE_TRACKER (doesn't touch user data)."""
    ws = safe_get_worksheet(sheet, 'REVENUE_TRACKER')
    if ws is None:
        return 0

    # Get existing URLs
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
                url,
                tpl.get('Account', ''),
                '',
                0,
                0,
                0,
                0,
                '',  # placeholder - formula added below
                '',
                '',
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
        print(f"  ❌ Spreadsheet {sheet_id} not found. Check:")
        print("     1. Sheet is shared with service account email as Editor")
        print("     2. DASHBOARD_SHEET_ID is correct (not the full URL)")
        raise
    except Exception as e:
        print(f"  ❌ Cannot open spreadsheet: {e}")
        raise
    
    today = datetime.now().strftime('%Y-%m-%d')
    print(f'Updating dashboard for {today}...')
    
    # List available tabs for debugging
    tab_names = [ws.title for ws in sheet.worksheets()]
    print(f'  Available tabs: {tab_names}')

    # Load processed data
    cache_dir = os.environ.get('CACHE_DIR', 'data')
    payload_path = os.path.join(cache_dir, 'dashboard_payload.json')
    
    try:
        with open(payload_path, 'r') as f:
            payload = json.load(f)
    except FileNotFoundError:
        print(f'ERROR: {payload_path} not found. Run daily_processor first.')
        return

    # Update each tab (each function handles missing tabs gracefully)
    update_opportunity_now(sheet, payload.get('opportunity_matrix', []))
    append_competitor_view(sheet, payload.get('competitor_gaps', []), today)
    append_prediction_log(sheet, payload.get('model_summary', {}), today)
    append_data_feed(sheet, payload.get('my_performance', []), today)
    update_seasonal_alerts(sheet, payload.get('seasonal_alerts', []))
    update_revenue_tracker_metadata(sheet, payload.get('new_templates', []))

    print(f'\n✅ Dashboard updated successfully')


if __name__ == '__main__':
    main()














