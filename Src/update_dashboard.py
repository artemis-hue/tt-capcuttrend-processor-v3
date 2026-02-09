"""
update_dashboard.py — Push daily processed data to Google Sheets dashboard
Runs as part of GitHub Actions daily workflow.

This script updates the following tabs in the live Google Sheet:
- OPPORTUNITY_NOW:  Overwrites with today's opportunity matrix
- COMPETITOR_VIEW:  Appends today's competitor gap analysis
- PREDICTION_LOG:   Appends today's prediction accuracy summary
- DATA_FEED:        Appends today's MY_PERFORMANCE data
- DASHBOARD:        Updates seasonal alerts section

It does NOT touch REVENUE_TRACKER or REVENUE_INSIGHTS —
those are maintained by you (revenue data) and by Sheets formulas.

Setup:
1. Create a Google Sheet from the template (import TikTok_Dashboard_Template.xlsx)
2. Share the Sheet with your service account email
3. Copy the spreadsheet ID from the URL
4. Add as GitHub secret: DASHBOARD_SHEET_ID
"""

import os
import json
import base64
import pandas as pd
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
            'https://www.googleapis.com/auth/drive.file',
        ]
    )
    return gspread.authorize(creds)


def update_opportunity_now(sheet, opportunity_data):
    """
    Overwrite OPPORTUNITY_NOW tab with today's build queue.
    This tab is completely refreshed daily.
    """
    ws = sheet.worksheet('OPPORTUNITY_NOW')

    # Clear existing data (keep headers)
    if ws.row_count > 1:
        ws.delete_rows(2, ws.row_count)

    if not opportunity_data:
        return 0

    # Write rows
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
    """
    Append today's competitor gap analysis rows to COMPETITOR_VIEW.
    This tab accumulates data over time for trend analysis.
    """
    ws = sheet.worksheet('COMPETITOR_VIEW')

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
    """
    Append one row to PREDICTION_LOG with today's model accuracy metrics.
    """
    ws = sheet.worksheet('PREDICTION_LOG')

    if not model_summary or 'direction_accuracy_pct' not in model_summary:
        print('  PREDICTION_LOG: No accuracy data (first run or no predictions)')
        return 0

    outcomes = model_summary.get('action_outcomes', {})
    suggestions = model_summary.get('tuning_suggestions', [])

    row = [
        date_str,
        model_summary.get('trends_tracked', 0),
        model_summary.get('direction_accuracy_pct', 0) / 100,  # As decimal for %
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
    """
    Append today's MY_PERFORMANCE + enhanced data to DATA_FEED.
    This is the raw data that DASHBOARD formulas reference.
    """
    ws = sheet.worksheet('DATA_FEED')

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
    """
    Update the seasonal alerts section on the DASHBOARD tab.
    Writes to fixed cells (rows 18-20, columns A-C based on template layout).
    """
    ws = sheet.worksheet('DASHBOARD')

    # Clear previous alerts (rows 18-20 in template — adjust if layout changes)
    # These correspond to the 3 placeholder rows in the dashboard
    alert_start_row = 18  # Adjust based on your actual template

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
    """
    For new templates detected in MY_PERFORMANCE that have URLs not yet in
    REVENUE_TRACKER, pre-fill the automation columns (K-R) so the user only
    needs to add revenue data when it comes in.
    
    Does NOT overwrite any existing rows (preserves user-entered revenue data).
    """
    ws = sheet.worksheet('REVENUE_TRACKER')

    # Get existing URLs
    existing_urls = set()
    try:
        url_col = ws.col_values(1)  # Column A = TikTok URL
        existing_urls = set(url_col[1:])  # Skip header
    except Exception:
        pass

    new_rows = []
    for tpl in new_templates:
        url = tpl.get('TikTok URL', tpl.get('webVideoUrl', ''))
        if url and url not in existing_urls and url != 'nan':
            new_rows.append([
                url,                                          # A: URL
                tpl.get('Account', ''),                       # B: Account
                '',                                           # C: Template Link (user fills)
                0,                                            # D: Received
                0,                                            # E: Estimated
                0,                                            # F: US/EU installs
                0,                                            # G: ROW installs
                '=F{r}+G{r}',                                # H: Total (formula)
                '=IFERROR(E{r}/H{r},0)',                     # I: Rev/Install (formula)
                '=IF(E{r}>=2500,"✅ CAP","")',                # J: At Cap (formula)
                str(tpl.get('Trend', ''))[:60],               # K: Trend
                tpl.get('Momentum', 0),                       # L: Momentum at detection
                tpl.get('URGENCY', tpl.get('trigger_level', '')),  # M: Trigger level
                tpl.get('action_window', ''),                 # N: Action window
                tpl.get('Market', ''),                        # O: Market
                tpl.get('AI_CATEGORY', tpl.get('ai_category', '')),  # P: AI Category
                tpl.get('Age', ''),                           # Q: Age at detection
                datetime.now().strftime('%Y-%m-%d'),           # R: Date first seen
                '',                                           # S: Notes
            ])

    if new_rows:
        # Fix formula row references
        next_row = len(existing_urls) + 2  # +1 for header, +1 for 1-indexed
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
    sheet = client.open_by_key(sheet_id)
    today = datetime.now().strftime('%Y-%m-%d')

    print(f'Updating dashboard for {today}...')

    # Load processed data from daily processor output
    try:
        with open('data/dashboard_payload.json', 'r') as f:
            payload = json.load(f)
    except FileNotFoundError:
        print('ERROR: data/dashboard_payload.json not found. Run daily_processor first.')
        return

    # Update each tab
    update_opportunity_now(sheet, payload.get('opportunity_matrix', []))
    append_competitor_view(sheet, payload.get('competitor_gaps', []), today)
    append_prediction_log(sheet, payload.get('model_summary', {}), today)
    append_data_feed(sheet, payload.get('my_performance', []), today)
    update_seasonal_alerts(sheet, payload.get('seasonal_alerts', []))
    update_revenue_tracker_metadata(sheet, payload.get('new_templates', []))

    print(f'\n✅ Dashboard updated successfully')


if __name__ == '__main__':
    main()
