"""
revenue_persistence.py — Revenue Data Persistence Layer
v1.0.0: Reads live revenue data from Google Sheets REVENUE_TRACKER,
         provides URL→revenue lookup for all output file generation.

PURPOSE:
  Your Google Sheet REVENUE_TRACKER is the source of truth for revenue.
  You manually enter revenue figures there. This module reads those
  figures BEFORE any files are generated, so every output file contains
  your real revenue data. Nothing you enter manually ever gets overwritten.

USAGE IN main.py:
  from revenue_persistence import fetch_live_revenue, get_revenue_lookup

  # Early in pipeline (before any file generation):
  live_revenue_df = fetch_live_revenue()   # reads from Google Sheet
  revenue_lookup = get_revenue_lookup(live_revenue_df)  # URL → dict

  # Pass to daily_processor for MY_PERFORMANCE col 18:
  process_data(..., revenue_lookup=revenue_lookup)

  # Pass to v35_enhancements for dashboard REVENUE_TRACKER tab:
  create_enhanced_dashboard(..., live_revenue_df=live_revenue_df)

  # update_dashboard.py ONLY appends new URLs, never overwrites existing rows

FALLBACK:
  If Google Sheet is unreachable, falls back to SEED_REVENUE_DATA
  embedded in v35_enhancements.py (143 real Pioneer Programme entries,
  merged from Pioneer_Revenue_Data.xlsx + original seed data).
"""

import os
import json
import pandas as pd


# =============================================================================
# FETCH LIVE REVENUE FROM GOOGLE SHEETS
# =============================================================================

def fetch_live_revenue():
    """
    Read the REVENUE_TRACKER tab from the live Google Sheet.
    Returns a DataFrame with all columns, or None if unavailable.
    
    This is called ONCE at the start of the pipeline, before any
    file generation. The returned data is then passed through the
    pipeline to populate revenue in all output files.
    """
    sheet_id = os.environ.get('DASHBOARD_SHEET_ID', '')
    if not sheet_id:
        print("  [RevPersist] DASHBOARD_SHEET_ID not set — using fallback")
        return _load_fallback_revenue()
    
    try:
        client = _get_gspread_client()
        if client is None:
            print("  [RevPersist] No Google credentials — using fallback")
            return _load_fallback_revenue()
        
        sheet = client.open_by_key(sheet_id)
        
        try:
            ws = sheet.worksheet('REVENUE_TRACKER')
        except Exception:
            print("  [RevPersist] REVENUE_TRACKER tab not found in Sheet — using fallback")
            return _load_fallback_revenue()
        
        # Get all data including headers
        all_data = ws.get_all_values()
        
        if len(all_data) < 2:
            print("  [RevPersist] REVENUE_TRACKER is empty — using fallback")
            return _load_fallback_revenue()
        
        headers = all_data[0]
        rows = all_data[1:]
        
        df = pd.DataFrame(rows, columns=headers)
        
        # Clean up: convert numeric columns
        for col in ['Received ($)', 'Estimated ($)', 'US & EU3 Installs', 'ROW Installs',
                     'Total Installs', 'Rev/Install', 'Momentum at Detection']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Filter out completely empty rows
        url_col = _find_url_column(df)
        if url_col:
            df = df[df[url_col].astype(str).str.strip() != '']
            df = df[df[url_col].astype(str) != 'nan']
        
        print(f"  [RevPersist] ✅ Loaded {len(df)} revenue entries from live Google Sheet")
        
        # Count entries with actual revenue
        rev_col = _find_revenue_column(df)
        if rev_col:
            has_revenue = df[rev_col].astype(float, errors='ignore')
            has_revenue = pd.to_numeric(df[rev_col], errors='coerce').fillna(0)
            with_rev = (has_revenue > 0).sum()
            total_rev = has_revenue.sum()
            at_cap = (has_revenue >= 2500).sum()
            print(f"  [RevPersist]   {with_rev} templates with revenue, ${total_rev:,.0f} total, {at_cap} at cap")
        
        return df
        
    except Exception as e:
        print(f"  [RevPersist] ❌ Could not read Google Sheet: {e}")
        return _load_fallback_revenue()


def _get_gspread_client():
    """Get authenticated gspread client. Reuses logic from update_dashboard.py."""
    try:
        import gspread
    except ImportError:
        print("  [RevPersist] gspread not installed")
        return None
    
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
        return gspread.authorize(creds)
    
    # Method 2: Service account
    import base64
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
        return gspread.authorize(creds)
    
    return None


def _find_url_column(df):
    """Find the URL column in the DataFrame (handles different header names)."""
    for candidate in ['TikTok URL', 'URL', 'url', 'tiktok_url', 'webVideoUrl']:
        if candidate in df.columns:
            return candidate
    # First column is usually URL
    if len(df.columns) > 0:
        return df.columns[0]
    return None


def _find_revenue_column(df):
    """Find the revenue/estimated column."""
    for candidate in ['Estimated ($)', 'Received ($)', 'Revenue', 'revenue', 'Estimated']:
        if candidate in df.columns:
            return candidate
    return None


def _load_fallback_revenue():
    """Load revenue from embedded seed data when Google Sheet is unavailable."""
    try:
        from v35_enhancements import SEED_REVENUE_DATA
        if SEED_REVENUE_DATA:
            df = pd.DataFrame(SEED_REVENUE_DATA)
            print(f"  [RevPersist] Using fallback seed data ({len(df)} entries)")
            return df
    except (ImportError, AttributeError):
        pass
    
    try:
        from update_dashboard import HISTORICAL_REVENUE
        if HISTORICAL_REVENUE:
            df = pd.DataFrame(HISTORICAL_REVENUE)
            print(f"  [RevPersist] Using fallback historical data ({len(df)} entries)")
            return df
    except (ImportError, AttributeError):
        pass
    
    print("  [RevPersist] No fallback revenue data available")
    return None


# =============================================================================
# REVENUE LOOKUP — URL → Revenue Data
# =============================================================================

def get_revenue_lookup(live_revenue_df):
    """
    Build a URL → revenue dict from the live revenue DataFrame.
    
    Returns dict like:
      {
        'https://tiktok.com/@user/video/123': {
            'received': 2500,
            'estimated': 2500,
            'us_installs': 2184,
            'row_installs': 3782,
            'total_installs': 5966,
            'at_cap': True,
            'account': 'capcuttemplates833',
            'template_link': 'https://...',
            'notes': 'Ma po po trend',
        },
        ...
      }
    
    Used by:
      - daily_processor.py → MY_PERFORMANCE col 18 (Revenue)
      - v35_enhancements.py → Dashboard REVENUE_TRACKER tab
      - summary report → revenue totals
    """
    if live_revenue_df is None or len(live_revenue_df) == 0:
        return {}
    
    lookup = {}
    url_col = _find_url_column(live_revenue_df)
    if not url_col:
        return {}
    
    for _, row in live_revenue_df.iterrows():
        url = str(row.get(url_col, '')).strip()
        if not url or url == 'nan' or not url.startswith('http'):
            continue
        
        # Normalize URL (remove trailing slashes, query params)
        url_clean = url.rstrip('/').split('?')[0]
        
        # Extract revenue fields — handle multiple possible column names
        received = _safe_numeric(row, ['Received ($)', 'received', 'Revenue'])
        estimated = _safe_numeric(row, ['Estimated ($)', 'estimated', 'Estimated'])
        us_installs = _safe_numeric(row, ['US & EU3 Installs', 'us_installs'])
        row_installs = _safe_numeric(row, ['ROW Installs', 'row_installs'])
        total_installs = _safe_numeric(row, ['Total Installs', 'total_installs'])
        
        if total_installs == 0 and (us_installs > 0 or row_installs > 0):
            total_installs = us_installs + row_installs
        
        # Use the higher of received/estimated as the "revenue" figure
        revenue = max(received, estimated)
        
        lookup[url_clean] = {
            'revenue': revenue,
            'received': received,
            'estimated': estimated,
            'us_installs': us_installs,
            'row_installs': row_installs,
            'total_installs': total_installs,
            'at_cap': estimated >= 2500,
            'account': str(row.get('Account', row.get('account', ''))),
            'template_link': str(row.get('Template Link', row.get('template_link', ''))),
            'notes': str(row.get('Notes', row.get('notes', ''))),
        }
    
    with_revenue = sum(1 for v in lookup.values() if v['revenue'] > 0)
    total = sum(v['revenue'] for v in lookup.values())
    print(f"  [RevPersist] Revenue lookup: {len(lookup)} URLs, {with_revenue} with revenue (${total:,.0f})")
    
    return lookup


def _safe_numeric(row, column_candidates):
    """Try multiple column names, return first valid numeric value."""
    for col in column_candidates:
        if col in row.index:
            try:
                val = float(row[col])
                if pd.notna(val):
                    return val
            except (ValueError, TypeError):
                pass
    return 0.0


def lookup_revenue_for_url(revenue_lookup, url):
    """
    Look up revenue for a specific TikTok URL.
    Returns the revenue amount (float), or 0 if not found.
    
    Used by daily_processor.py when writing MY_PERFORMANCE col 18.
    """
    if not revenue_lookup or not url:
        return 0.0
    
    url_clean = str(url).rstrip('/').split('?')[0]
    entry = revenue_lookup.get(url_clean, {})
    return entry.get('revenue', 0.0)


# =============================================================================
# CACHE REVENUE LOCALLY (backup in case Sheet is unreachable tomorrow)
# =============================================================================

def cache_revenue_locally(live_revenue_df, cache_dir):
    """
    Save a local copy of revenue data so it's available even if
    Google Sheets is unreachable on a future run.
    """
    if live_revenue_df is None or len(live_revenue_df) == 0:
        return
    
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, 'revenue_cache.json')
    
    try:
        records = live_revenue_df.to_dict('records')
        # Clean NaN values for JSON serialization
        clean_records = []
        for record in records:
            clean = {}
            for k, v in record.items():
                if pd.isna(v):
                    clean[k] = None
                elif isinstance(v, float) and v == int(v):
                    clean[k] = int(v)
                else:
                    clean[k] = v
            clean_records.append(clean)
        
        with open(cache_path, 'w') as f:
            json.dump({
                'cached_at': pd.Timestamp.now().isoformat(),
                'entries': clean_records,
            }, f, default=str)
        
        print(f"  [RevPersist] Revenue cached locally ({len(clean_records)} entries)")
    except Exception as e:
        print(f"  [RevPersist] Warning: Could not cache revenue: {e}")


def load_cached_revenue(cache_dir):
    """Load locally cached revenue as fallback."""
    cache_path = os.path.join(cache_dir, 'revenue_cache.json')
    if not os.path.exists(cache_path):
        return None
    
    try:
        with open(cache_path, 'r') as f:
            data = json.load(f)
        entries = data.get('entries', [])
        if entries:
            df = pd.DataFrame(entries)
            cached_at = data.get('cached_at', 'unknown')
            print(f"  [RevPersist] Loaded {len(df)} entries from local cache (cached: {cached_at})")
            return df
    except Exception as e:
        print(f"  [RevPersist] Could not load cache: {e}")
    
    return None
