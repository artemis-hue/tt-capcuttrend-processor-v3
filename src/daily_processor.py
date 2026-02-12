#!/usr/bin/env python3
"""
TIKTOK DAILY PROCESSOR
Version: 5.3.0 - All bugs fixed
Fixes:
  - BUG 1: YOUR posts from processed data (not fresh)
  - BUG 2: Competitor count from processed data (not fresh)
  - BUG 3: Trigger counts from ALL data (not YOUR posts)
  - BUG 4: MY_PERFORMANCE no deduplication across markets
  - BUG 5: AUDIO sheets properly populated
  - BUG 6: START_HERE full summary
  - BUG 7: Tab order fixed (UK together, US together)
  - BUG 8: Status diversity preserved
"""

import pandas as pd
import json
import os
import re
from datetime import datetime, timedelta
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE


def _safe_int(val, default=0):
    """Safely convert to int, returning default for NaN/None."""
    try:
        if pd.isna(val):
            return default
        return int(val)
    except (ValueError, TypeError):
        return default


def _safe_round(val, decimals=1, default=0):
    """Safely round a value, returning default for NaN/None."""
    try:
        if pd.isna(val):
            return default
        return round(float(val), decimals)
    except (ValueError, TypeError):
        return default


def _safe_text(val, max_len=80):
    """Safely convert to string, sanitizing illegal Excel chars."""
    if pd.isna(val) or val is None:
        return ''
    s = str(val)[:max_len]
    return ILLEGAL_CHARACTERS_RE.sub('', s)

# Configuration
YOUR_ACCOUNTS = [
    'capcuttemplates833',
    'capcuttrends02', 
    'capcuttemplatesai',
    'artemiscc_capcut',
    'capcutaistudio',
    'artemiscccapcut',
    'capcut.vorlagen101'
]

COMPETITOR_ACCOUNTS = [
    'capcutdailyuk', 'capcut__creations', 'jyoung101capcut',
    'capcut_templatetrends', 'capcut_core', 'capcut.trends.uk1'
]

AI_KEYWORDS = [
    'artificial intelligence', 'capcut ai', 'capcutai', 'ai filter', 'ai effect',
    'ai generated', 'ai video', 'ai photo', 'ai template', 'aifilter', 'aieffect',
    'filtro ki', 'filtro ia', 'ki filter', 'ia filter',  # International: German, Spanish/Portuguese
]

# These short terms need word boundary matching (not substring)
AI_KEYWORDS_WORD_BOUNDARY = ['#ia', '#ki', 'ia', 'ki']

AI_EXCLUSIONS = [
    'aicover', 'aivoice', 'aiart', 'airdrop', 'air', 'hair', 'fair', 'chair', 'stairs',
    'kia', 'bikini', 'skiing', 'skirt', 'skin', 'kilo', 'kid', 'kids', 'kind', 'king',
    'kiss', 'kit', 'kite', 'kitchen', 'hiking', 'liking', 'making', 'taking', 'waking',
    'breaking', 'speaking', 'media', 'via'
]

# Colors
CYAN_FILL = PatternFill(start_color="E0FFFF", end_color="E0FFFF", fill_type="solid")
ORANGE_FILL = PatternFill(start_color="FFE4B5", end_color="FFE4B5", fill_type="solid")
GOLD_FILL = PatternFill(start_color="FFD700", end_color="FFD700", fill_type="solid")
HEADER_FILL = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
HEADER_FONT = Font(bold=True, color="FFFFFF")
LIGHT_YELLOW_FILL = PatternFill(start_color="FFFFE0", end_color="FFFFE0", fill_type="solid")

STATUS_COLORS = {
    '🆕 NEW': PatternFill(start_color="FFFFE0", end_color="FFFFE0", fill_type="solid"),
    '🚀 SPIKING': PatternFill(start_color="00FF00", end_color="00FF00", fill_type="solid"),
    '📈 RISING': PatternFill(start_color="90EE90", end_color="90EE90", fill_type="solid"),
    '📉 COOLING': PatternFill(start_color="FFB6C1", end_color="FFB6C1", fill_type="solid"),
    '❄️ DYING': PatternFill(start_color="FF0000", end_color="FF0000", fill_type="solid"),
}

TRIGGER_COLORS = {
    '🔴 MAKE_NOW': PatternFill(start_color="FF6B6B", end_color="FF6B6B", fill_type="solid"),
    '🟡 WATCH': PatternFill(start_color="FFD93D", end_color="FFD93D", fill_type="solid"),
}

URGENCY_COLORS = {
    '🔥 URGENT': PatternFill(start_color="8B0000", end_color="8B0000", fill_type="solid"),
    '⚡ HIGH': PatternFill(start_color="FFA500", end_color="FFA500", fill_type="solid"),
    '🟡 WATCH': PatternFill(start_color="FFD93D", end_color="FFD93D", fill_type="solid"),
}


def get_author_name(row):
    """Extract author name from various possible column names.
    
    Apify can return author data in different formats:
    - Nested: {"authorMeta": {"name": "user"}} -> flattened to authorMeta_name
    - Direct: {"author": "user"}
    - Various naming conventions across different scraper versions
    """
    possible_cols = [
        # Most common after flattening
        'authorMeta_name', 'authorMeta_uniqueId', 'authorMeta_nickname',
        # Alternative naming
        'author_name', 'authorName', 'author',
        # Direct fields
        'username', 'creator', 'nickname',
        # With dots (in case data comes from different source)
        'authorMeta.name', 'authorMeta.uniqueId'
    ]
    for col in possible_cols:
        if col in row.index and pd.notna(row[col]) and str(row[col]).strip():
            return str(row[col]).strip()
    return 'Unknown'


def detect_ai(text):
    """Detect if content is AI-related."""
    if pd.isna(text):
        return 'NON-AI'
    text_lower = str(text).lower()
    
    # Check multi-word/phrase keywords (substring match)
    for kw in AI_KEYWORDS:
        if kw in text_lower:
            return 'AI'
    
    # Check short keywords with word boundary matching (#ia, #ki, ia, ki)
    for kw in AI_KEYWORDS_WORD_BOUNDARY:
        if kw.startswith('#'):
            # Hashtag: match exactly as #word with boundary after
            if re.search(r'(?:^|\s)' + re.escape(kw) + r'(?:\s|$)', text_lower):
                return 'AI'
        else:
            # Standalone word: must be whole word
            if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
                # Check it's not part of an excluded word
                match_pos = re.search(r'\b' + re.escape(kw) + r'\b', text_lower)
                if match_pos:
                    # Get the full word containing this match
                    start = match_pos.start()
                    end = match_pos.end()
                    # Expand to find the full token
                    while start > 0 and text_lower[start-1].isalnum():
                        start -= 1
                    while end < len(text_lower) and text_lower[end].isalnum():
                        end += 1
                    full_word = text_lower[start:end]
                    if full_word not in AI_EXCLUSIONS:
                        return 'AI'
    
    # Check words containing 'ai' with exclusion list
    for word in re.findall(r'\b\w*ai\w*\b', text_lower):
        if word not in AI_EXCLUSIONS:
            return 'AI'
    
    return 'NON-AI'


def calculate_metrics(df):
    """Calculate time-normalized metrics."""
    now = datetime.utcnow()
    
    # Find createTime column
    time_col = None
    for col in ['createTimeISO', 'createTime', 'created_time']:
        if col in df.columns:
            time_col = col
            break
    
    if time_col is None:
        df['age_hours'] = 24
    else:
        df['createTime_parsed'] = pd.to_datetime(df[time_col], errors='coerce', utc=True)
        df['createTime_parsed'] = df['createTime_parsed'].dt.tz_localize(None)
        df['age_hours'] = (now - df['createTime_parsed']).dt.total_seconds() / 3600
        df['age_hours'] = df['age_hours'].clip(lower=0.1)
    
    # Get counts - ensure Series even if column missing
    for col, default in [('shareCount', 0), ('diggCount', 0), ('playCount', 0)]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            df[col] = 0
    
    # Calculate per-hour metrics
    df['shares_per_hour'] = df['shareCount'] / df['age_hours']
    df['likes_per_hour'] = df['diggCount'] / df['age_hours']
    df['views_per_hour'] = df['playCount'] / df['age_hours']
    
    # Momentum score
    df['momentum_score'] = (
        df['shares_per_hour'] * 10 +
        df['likes_per_hour'] * 3 +
        df['views_per_hour'] * 0.01
    )
    
    return df


def calculate_status(df, yesterday_data=None):
    """Calculate 24h status based on momentum delta."""
    if yesterday_data is None:
        df['status'] = '🆕 NEW'
        return df
    
    yesterday_df = pd.DataFrame(yesterday_data)
    
    if 'webVideoUrl' not in yesterday_df.columns or len(yesterday_df) == 0:
        df['status'] = '🆕 NEW'
        return df
    
    yesterday_momentum = dict(zip(
        yesterday_df['webVideoUrl'],
        yesterday_df.get('momentum_score', [0] * len(yesterday_df))
    ))
    
    def get_status(row):
        url = row.get('webVideoUrl', '')
        if url not in yesterday_momentum:
            return '🆕 NEW'
        
        delta = row['momentum_score'] - yesterday_momentum.get(url, 0)
        
        if delta > 100:
            return '🚀 SPIKING'
        elif delta > 0:
            return '📈 RISING'
        elif delta > -100:
            return '📉 COOLING'
        else:
            return '❄️ DYING'
    
    df['status'] = df.apply(get_status, axis=1)
    return df


def calculate_build_now(row):
    """Calculate BUILD_NOW flag."""
    try:
        age = row.get('age_hours', 999)
        shares_h = row.get('shares_per_hour', 0)
        views_h = row.get('views_per_hour', 0)
        # Guard against None/NaN
        if pd.isna(age) or pd.isna(shares_h) or pd.isna(views_h):
            return 'NO'
        if age <= 72 and shares_h >= 5 and views_h >= 1000:
            return 'BUILD NOW'
        return 'NO'
    except (TypeError, ValueError):
        return 'NO'


def calculate_tutorial_trigger(row):
    """Calculate tutorial trigger and urgency."""
    momentum = row.get('momentum_score', 0)
    shares_h = row.get('shares_per_hour', 0)
    status = str(row.get('status', ''))
    build_now = row.get('BUILD_NOW', '')
    
    if momentum >= 3000:
        return '🔴 MAKE_NOW', '🔥 URGENT', f'Momentum {int(momentum)} ≥ 3,000'
    if shares_h >= 100:
        return '🔴 MAKE_NOW', '🔥 URGENT', f'Shares/h {round(shares_h,1)} ≥ 100'
    if '🚀 SPIKING' in status and momentum >= 2000:
        return '🔴 MAKE_NOW', '🔥 URGENT', f'SPIKING + Momentum {int(momentum)}'
    if momentum >= 2000:
        return '🔴 MAKE_NOW', '⚡ HIGH', f'Momentum {int(momentum)} ≥ 2,000'
    if shares_h >= 60:
        return '🔴 MAKE_NOW', '⚡ HIGH', f'Shares/h {round(shares_h,1)} ≥ 60'
    if '🚀 SPIKING' in status and momentum >= 1500:
        return '🔴 MAKE_NOW', '⚡ HIGH', f'SPIKING + Momentum {int(momentum)}'
    if momentum >= 1000:
        return '🟡 WATCH', '🟡 WATCH', f'Momentum {int(momentum)} ≥ 1,000'
    if shares_h >= 25:
        return '🟡 WATCH', '🟡 WATCH', f'Shares/h {round(shares_h,1)} ≥ 25'
    if '📈 RISING' in status and momentum >= 800:
        return '🟡 WATCH', '🟡 WATCH', f'RISING + Momentum {int(momentum)}'
    if build_now == 'BUILD NOW':
        return '🟡 WATCH', '🟡 WATCH', 'BUILD_NOW active'
    
    return 'NONE', '', ''


def process_audio_data(audio_data):
    """Process audio/music data into standardized format."""
    if not audio_data:
        return pd.DataFrame()
    
    df = pd.DataFrame(audio_data)
    
    # Deduplicate by musicId or musicName
    if 'musicMeta_musicId' in df.columns:
        df = df.drop_duplicates(subset=['musicMeta_musicId'], keep='first')
    elif 'musicMeta_musicName' in df.columns:
        df = df.drop_duplicates(subset=['musicMeta_musicName'], keep='first')
    
    # Extract music metadata
    result = pd.DataFrame()
    result['music_name'] = df.get('musicMeta_musicName', df.get('musicName', 'Unknown'))
    result['artist'] = df.get('musicMeta_musicAuthor', df.get('musicAuthor', 'Unknown'))
    result['is_original'] = df.get('musicMeta_musicOriginal', df.get('musicOriginal', False))
    result['play_url'] = df.get('musicMeta_playUrl', df.get('playUrl', ''))
    result['used_count'] = 1  # Each row is one video using this audio
    
    # Aggregate by music
    if 'music_name' in result.columns and len(result) > 0:
        aggregated = result.groupby(['music_name', 'artist', 'is_original', 'play_url']).agg({
            'used_count': 'sum'
        }).reset_index()
        aggregated = aggregated.sort_values('used_count', ascending=False).head(100)
        return aggregated
    
    return result.head(100)


def process_data(us_data, uk_data, us_music_data, uk_music_data, yesterday_us, yesterday_uk, output_dir, cache_dir):
    """Main processing function."""
    today = datetime.now().strftime('%Y-%m-%d')
    stats = {}
    
    print("  Processing US data...")
    us_df = pd.DataFrame(us_data) if us_data else pd.DataFrame()
    if len(us_df) > 0:
        us_df = us_df.drop_duplicates(subset=['webVideoUrl'], keep='first')
        us_df = calculate_metrics(us_df)
        us_df = calculate_status(us_df, yesterday_us)
        us_df['author'] = us_df.apply(get_author_name, axis=1)
        us_df['AI_CATEGORY'] = us_df.get('text', pd.Series([''])).apply(detect_ai)
        us_df['BUILD_NOW'] = us_df.apply(calculate_build_now, axis=1)
    
    print("  Processing UK data...")
    uk_df = pd.DataFrame(uk_data) if uk_data else pd.DataFrame()
    if len(uk_df) > 0:
        uk_df = uk_df.drop_duplicates(subset=['webVideoUrl'], keep='first')
        uk_df = calculate_metrics(uk_df)
        uk_df = calculate_status(uk_df, yesterday_uk)
        uk_df['author'] = uk_df.apply(get_author_name, axis=1)
        uk_df['AI_CATEGORY'] = uk_df.get('text', pd.Series([''])).apply(detect_ai)
        uk_df['BUILD_NOW'] = uk_df.apply(calculate_build_now, axis=1)
    
    # Cross-market detection
    print("  Detecting cross-market content...")
    us_urls = set(us_df['webVideoUrl']) if len(us_df) > 0 else set()
    uk_urls = set(uk_df['webVideoUrl']) if len(uk_df) > 0 else set()
    both_urls = us_urls & uk_urls
    
    if len(us_df) > 0:
        us_df['market'] = us_df['webVideoUrl'].apply(
            lambda u: '🌐 BOTH' if u in both_urls else '🇺🇸 US ONLY'
        )
    
    if len(uk_df) > 0:
        uk_df['market'] = uk_df['webVideoUrl'].apply(
            lambda u: '🌐 BOTH' if u in both_urls else '🇬🇧 UK ONLY'
        )
    
    # Calculate triggers for ALL data
    print("  Calculating tutorial triggers for ALL data...")
    for df in [us_df, uk_df]:
        if len(df) > 0:
            triggers = df.apply(lambda row: calculate_tutorial_trigger(row), axis=1)
            df['TUTORIAL_TRIGGER'] = [t[0] for t in triggers]
            df['URGENCY'] = [t[1] for t in triggers]
            df['trigger_reason'] = [t[2] for t in triggers]
    
    # Store processed data (before 72h filter) for YOUR posts and competitor detection
    # BUG FIX 1 & 2: Use ALL processed data, not just fresh
    us_processed = us_df.copy() if len(us_df) > 0 else pd.DataFrame()
    uk_processed = uk_df.copy() if len(uk_df) > 0 else pd.DataFrame()
    
    # Fresh content filter (72h) - only for TOP100 video sheets
    us_fresh = us_df[us_df['age_hours'] <= 72].copy() if len(us_df) > 0 else pd.DataFrame()
    uk_fresh = uk_df[uk_df['age_hours'] <= 72].copy() if len(uk_df) > 0 else pd.DataFrame()
    
    # TOP 100 by momentum (from fresh data)
    us_ai_100 = us_fresh[us_fresh['AI_CATEGORY'] == 'AI'].nlargest(100, 'momentum_score') if len(us_fresh) > 0 else pd.DataFrame()
    us_non_100 = us_fresh[us_fresh['AI_CATEGORY'] == 'NON-AI'].nlargest(100, 'momentum_score') if len(us_fresh) > 0 else pd.DataFrame()
    uk_ai_100 = uk_fresh[uk_fresh['AI_CATEGORY'] == 'AI'].nlargest(100, 'momentum_score') if len(uk_fresh) > 0 else pd.DataFrame()
    uk_non_100 = uk_fresh[uk_fresh['AI_CATEGORY'] == 'NON-AI'].nlargest(100, 'momentum_score') if len(uk_fresh) > 0 else pd.DataFrame()
    
    us_ai_20 = us_ai_100.head(20)
    us_non_20 = us_non_100.head(20)
    uk_ai_20 = uk_ai_100.head(20)
    uk_non_20 = uk_non_100.head(20)
    
    # BUG FIX 1: Find YOUR posts from PROCESSED data (not fresh)
    # BUG FIX 4: DON'T deduplicate across markets - concat US and UK separately
    print("  Finding YOUR posts from ALL processed data...")
    us_your = us_processed[us_processed['author'].str.lower().isin([a.lower() for a in YOUR_ACCOUNTS])] if len(us_processed) > 0 else pd.DataFrame()
    uk_your = uk_processed[uk_processed['author'].str.lower().isin([a.lower() for a in YOUR_ACCOUNTS])] if len(uk_processed) > 0 else pd.DataFrame()
    
    # Combine without deduplication - posts in BOTH markets appear twice
    your_posts = pd.concat([us_your, uk_your], ignore_index=True)
    
    # BUG FIX 2: Find COMPETITOR posts from PROCESSED data (not fresh)
    us_comp = us_processed[us_processed['author'].str.lower().isin([a.lower() for a in COMPETITOR_ACCOUNTS])] if len(us_processed) > 0 else pd.DataFrame()
    uk_comp = uk_processed[uk_processed['author'].str.lower().isin([a.lower() for a in COMPETITOR_ACCOUNTS])] if len(uk_processed) > 0 else pd.DataFrame()
    competitor_posts = pd.concat([us_comp, uk_comp]).drop_duplicates(subset=['webVideoUrl'])
    
    # BUG FIX 3: Calculate trigger counts from ALL processed data (not YOUR posts)
    all_processed = pd.concat([us_processed, uk_processed]).drop_duplicates(subset=['webVideoUrl']) if len(us_processed) > 0 or len(uk_processed) > 0 else pd.DataFrame()
    
    # Process audio data (BUG FIX 5)
    # FALLBACK: If no separate music data, extract from video data
    print("  Processing audio data...")
    if us_music_data:
        us_audio = process_audio_data(us_music_data)
    else:
        # Extract music from video data as fallback
        print("    No separate US music data - extracting from video data")
        us_audio = process_audio_data(us_data)
    
    if uk_music_data:
        uk_audio = process_audio_data(uk_music_data)
    else:
        # Extract music from video data as fallback
        print("    No separate UK music data - extracting from video data")
        uk_audio = process_audio_data(uk_data)
    
    print(f"    US audio tracks: {len(us_audio)}")
    print(f"    UK audio tracks: {len(uk_audio)}")
    
    # Stats - BUG FIX 3: Count triggers from ALL data
    stats['us_raw'] = len(us_data) if us_data else 0
    stats['uk_raw'] = len(uk_data) if uk_data else 0
    stats['us_unique'] = len(us_processed)
    stats['uk_unique'] = len(uk_processed)
    stats['us_fresh'] = len(us_fresh)
    stats['uk_fresh'] = len(uk_fresh)
    stats['both_count'] = len(both_urls)
    stats['your_posts'] = len(your_posts)
    stats['competitor'] = len(competitor_posts)
    
    # Count triggers from ALL processed data
    if len(all_processed) > 0 and 'URGENCY' in all_processed.columns:
        stats['urgent'] = len(all_processed[all_processed['URGENCY'] == '🔥 URGENT'])
        stats['high'] = len(all_processed[all_processed['URGENCY'] == '⚡ HIGH'])
        stats['watch'] = len(all_processed[all_processed['URGENCY'] == '🟡 WATCH'])
    else:
        stats['urgent'] = 0
        stats['high'] = 0
        stats['watch'] = 0
    
    # Count SPIKING from ALL processed data
    if len(all_processed) > 0 and 'status' in all_processed.columns:
        stats['spiking'] = len(all_processed[all_processed['status'] == '🚀 SPIKING'])
    else:
        stats['spiking'] = 0
    
    # Create Excel files
    print("  Creating Excel files...")
    
    # BUILD_TODAY_TOP20
    create_build_file(
        f"{output_dir}/BUILD_TODAY_TOP20_{today}.xlsx",
        uk_ai_20, uk_non_20, uk_audio.head(20),
        us_ai_20, us_non_20, us_audio.head(20),
        your_posts, stats, today, "TOP20"
    )
    
    # BUILD_TODAY_TOP100
    create_build_file(
        f"{output_dir}/BUILD_TODAY_TOP100_{today}.xlsx",
        uk_ai_100, uk_non_100, uk_audio,
        us_ai_100, us_non_100, us_audio,
        your_posts, stats, today, "TOP100"
    )
    
    # Full data files
    if len(us_df) > 0:
        us_df.to_excel(f"{output_dir}/TikTok_Trend_System_US_{today}.xlsx", index=False)
    if len(uk_df) > 0:
        uk_df.to_excel(f"{output_dir}/TikTok_Trend_System_UK_{today}.xlsx", index=False)
    
    # Summary report
    with open(f"{output_dir}/SUMMARY_REPORT_{today}.txt", 'w') as f:
        f.write(f"TikTok Daily Summary - {today}\n")
        f.write("=" * 40 + "\n\n")
        f.write(f"US Videos (raw): {stats['us_raw']}\n")
        f.write(f"UK Videos (raw): {stats['uk_raw']}\n")
        f.write(f"US Unique: {stats['us_unique']}\n")
        f.write(f"UK Unique: {stats['uk_unique']}\n")
        f.write(f"US Fresh (72h): {stats['us_fresh']}\n")
        f.write(f"UK Fresh (72h): {stats['uk_fresh']}\n")
        f.write(f"Cross-market (BOTH): {stats['both_count']}\n\n")
        f.write(f"Your Posts: {stats['your_posts']}\n")
        f.write(f"Competitor Posts: {stats['competitor']}\n\n")
        f.write(f"🔥 URGENT: {stats['urgent']}\n")
        f.write(f"⚡ HIGH: {stats['high']}\n")
        f.write(f"🟡 WATCH: {stats['watch']}\n")
        f.write(f"🚀 SPIKING: {stats['spiking']}\n")
    
    print("  Done processing")
    return stats


def create_build_file(filepath, uk_ai, uk_non, uk_audio, us_ai, us_non, us_audio, your_posts, stats, today, suffix):
    """Create BUILD_TODAY Excel file with correct tab order."""
    wb = Workbook()
    
    # START_HERE sheet (BUG FIX 6: Full summary)
    ws = wb.active
    ws.title = "START_HERE"
    create_start_here_sheet(ws, stats, today)
    
    # BUG FIX 7: Correct tab order - UK together, US together
    # UK Video sheets
    ws = wb.create_sheet(f"UK_AI_{suffix}")
    create_video_sheet(ws, uk_ai)
    
    ws = wb.create_sheet(f"UK_NON_AI_{suffix}")
    create_video_sheet(ws, uk_non)
    
    # UK Audio sheet (BUG FIX 5)
    ws = wb.create_sheet(f"UK_AUDIO_{suffix}")
    create_audio_sheet(ws, uk_audio)
    
    # US Video sheets
    ws = wb.create_sheet(f"US_AI_{suffix}")
    create_video_sheet(ws, us_ai)
    
    ws = wb.create_sheet(f"US_NON_AI_{suffix}")
    create_video_sheet(ws, us_non)
    
    # US Audio sheet (BUG FIX 5)
    ws = wb.create_sheet(f"US_AUDIO_{suffix}")
    create_audio_sheet(ws, us_audio)
    
    # MY_PERFORMANCE sheet
    ws = wb.create_sheet("MY_PERFORMANCE")
    create_my_performance_sheet(ws, your_posts, today)
    
    wb.save(filepath)


def create_start_here_sheet(ws, stats, today):
    """Create START_HERE summary sheet (BUG FIX 6)."""
    ws['A1'] = f"TikTok Trend System v3.3.0 - {today}"
    ws['A1'].font = Font(bold=True, size=14)
    
    ws['A3'] = "📊 DAILY SUMMARY"
    ws['A3'].font = Font(bold=True, size=12)
    
    summary_data = [
        ('Your Posts', stats.get('your_posts', 0)),
        ('Competitor Posts', stats.get('competitor', 0)),
        ('🔥 URGENT', stats.get('urgent', 0)),
        ('⚡ HIGH', stats.get('high', 0)),
        ('🟡 WATCH', stats.get('watch', 0)),
        ('🚀 SPIKING', stats.get('spiking', 0)),
        ('US Fresh (72h)', stats.get('us_fresh', 0)),
        ('UK Fresh (72h)', stats.get('uk_fresh', 0)),
        ('US Unique', stats.get('us_unique', 0)),
        ('UK Unique', stats.get('uk_unique', 0)),
    ]
    
    for idx, (label, value) in enumerate(summary_data, 4):
        ws.cell(row=idx, column=1, value=label)
        ws.cell(row=idx, column=2, value=value)


def create_video_sheet(ws, df):
    """Create video sheet with formatting."""
    headers = ['#', 'Market', 'Status', 'Trend', 'Creator', 'Age', 'Momentum', 'Shares/h', 'Views/h', 'URL']
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
    
    if len(df) == 0:
        return
    
    for idx, (_, row) in enumerate(df.iterrows(), 2):
        ws.cell(row=idx, column=1, value=idx-1)
        ws.cell(row=idx, column=2, value=_safe_text(row.get('market', ''), 30))
        ws.cell(row=idx, column=3, value=_safe_text(row.get('status', ''), 20))
        ws.cell(row=idx, column=4, value=_safe_text(row.get('text'), 80))
        ws.cell(row=idx, column=5, value=_safe_text(row.get('author', ''), 20))
        ws.cell(row=idx, column=6, value=f"{_safe_round(row.get('age_hours', 0), 1)}h")
        ws.cell(row=idx, column=7, value=_safe_int(row.get('momentum_score', 0)))
        ws.cell(row=idx, column=8, value=_safe_round(row.get('shares_per_hour', 0), 1))
        ws.cell(row=idx, column=9, value=_safe_int(row.get('views_per_hour', 0)))
        ws.cell(row=idx, column=10, value=row.get('webVideoUrl', ''))
        
        # Apply status color to column C only
        status = row.get('status', '')
        if status in STATUS_COLORS:
            ws.cell(row=idx, column=3).fill = STATUS_COLORS[status]
        
        # Apply GOLD to column B ONLY if BOTH (not whole row)
        if '🌐 BOTH' in str(row.get('market', '')):
            ws.cell(row=idx, column=2).fill = GOLD_FILL
        
        # Apply row highlighting for YOUR/COMPETITOR (overrides other colors)
        author = str(row.get('author', '')).lower()
        if author in [a.lower() for a in YOUR_ACCOUNTS]:
            for col in range(1, 11):
                ws.cell(row=idx, column=col).fill = CYAN_FILL
        elif author in [a.lower() for a in COMPETITOR_ACCOUNTS]:
            for col in range(1, 11):
                ws.cell(row=idx, column=col).fill = ORANGE_FILL


def create_audio_sheet(ws, df):
    """Create audio sheet with formatting (BUG FIX 5)."""
    headers = ['#', 'Status', 'Music Name', 'Artist', 'Type', 'Used By', 'Play URL']
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
    
    if len(df) == 0:
        return
    
    for idx, (_, row) in enumerate(df.iterrows(), 2):
        ws.cell(row=idx, column=1, value=idx-1)
        ws.cell(row=idx, column=2, value='🆕 NEW')  # Audio always NEW (no 24h tracking)
        ws.cell(row=idx, column=3, value=_safe_text(row.get('music_name', ''), 50))
        ws.cell(row=idx, column=4, value=_safe_text(row.get('artist', ''), 30))
        ws.cell(row=idx, column=5, value='Original' if row.get('is_original', False) else 'Sound')
        ws.cell(row=idx, column=6, value=f"{_safe_int(row.get('used_count', 0))} videos")
        ws.cell(row=idx, column=7, value=row.get('play_url', ''))


def create_my_performance_sheet(ws, your_posts, today):
    """Create MY_PERFORMANCE sheet with proper formatting."""
    headers = [
        'Date', 'Account', 'Trend', 'Age', 'Momentum', 'Status', 'Market',
        'Views/h', 'Shares/h', 'BUILD_NOW', 'TikTok URL', 'TUTORIAL_TRIGGER',
        'URGENCY', 'Trigger Reason', 'Competitor Count', 'Tutorial Link',
        'Template Link', 'Revenue', 'Notes'
    ]
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
    
    if len(your_posts) == 0:
        return
    
    for idx, (_, row) in enumerate(your_posts.iterrows(), 2):
        ws.cell(row=idx, column=1, value=today)
        ws.cell(row=idx, column=2, value=_safe_text(row.get('author', ''), 30))
        ws.cell(row=idx, column=3, value=_safe_text(row.get('text'), 60))
        ws.cell(row=idx, column=4, value=f"{_safe_round(row.get('age_hours', 0), 1)}h")
        ws.cell(row=idx, column=5, value=_safe_int(row.get('momentum_score', 0)))
        ws.cell(row=idx, column=6, value=_safe_text(row.get('status', ''), 20))
        ws.cell(row=idx, column=7, value=_safe_text(row.get('market', ''), 20))
        ws.cell(row=idx, column=8, value=_safe_int(row.get('views_per_hour', 0)))
        ws.cell(row=idx, column=9, value=_safe_round(row.get('shares_per_hour', 0), 1))
        ws.cell(row=idx, column=10, value=row.get('BUILD_NOW', ''))
        ws.cell(row=idx, column=11, value=row.get('webVideoUrl', ''))
        ws.cell(row=idx, column=12, value=row.get('TUTORIAL_TRIGGER', ''))
        ws.cell(row=idx, column=13, value=row.get('URGENCY', ''))
        ws.cell(row=idx, column=14, value=_safe_text(row.get('trigger_reason', ''), 80))
        # Columns 15-19 are manual entry (blank)
        
        # Apply CYAN to data columns 1-11
        for col in range(1, 12):
            ws.cell(row=idx, column=col).fill = CYAN_FILL
        
        # Apply trigger colors to column 12
        trigger = row.get('TUTORIAL_TRIGGER', '')
        if trigger in TRIGGER_COLORS:
            ws.cell(row=idx, column=12).fill = TRIGGER_COLORS[trigger]
        
        # Apply urgency colors to column 13
        urgency = row.get('URGENCY', '')
        if urgency in URGENCY_COLORS:
            ws.cell(row=idx, column=13).fill = URGENCY_COLORS[urgency]
            if urgency == '🔥 URGENT':
                ws.cell(row=idx, column=13).font = Font(color="FFFFFF")
        
        # Light yellow for manual entry columns 15-19
        for col in range(15, 20):
            ws.cell(row=idx, column=col).fill = LIGHT_YELLOW_FILL


def load_yesterday_cache(cache_dir):
    """Load yesterday's cached data."""
    us_path = os.path.join(cache_dir, 'yesterday_us.json')
    uk_path = os.path.join(cache_dir, 'yesterday_uk.json')
    
    print(f"  Looking for cache:")
    print(f"    US: {us_path} - exists: {os.path.exists(us_path)}")
    print(f"    UK: {uk_path} - exists: {os.path.exists(uk_path)}")
    
    if not os.path.exists(us_path) or not os.path.exists(uk_path):
        return None, None
    
    try:
        with open(us_path, 'r') as f:
            us_data = json.load(f)
        with open(uk_path, 'r') as f:
            uk_data = json.load(f)
        # Validate cache structure - must be lists of dicts
        if not isinstance(us_data, list) or not isinstance(uk_data, list):
            print(f"  Cache format invalid (expected list, got {type(us_data).__name__}/{type(uk_data).__name__})")
            return None, None
        print(f"    Loaded US: {len(us_data)} records")
        print(f"    Loaded UK: {len(uk_data)} records")
        return us_data, uk_data
    except Exception as e:
        print(f"  Cache load error: {e}")
        return None, None


def save_today_cache(us_df, uk_df, cache_dir):
    """Save today's data for tomorrow's comparison."""
    os.makedirs(cache_dir, exist_ok=True)
    
    us_path = os.path.join(cache_dir, 'yesterday_us.json')
    uk_path = os.path.join(cache_dir, 'yesterday_uk.json')
    
    print(f"  Saving cache to:")
    print(f"    US: {us_path}")
    print(f"    UK: {uk_path}")
    
    # Save only necessary columns for 24h tracking
    # Replace NaN with 0 to produce valid JSON
    if len(us_df) > 0:
        cache_df = us_df[['webVideoUrl', 'momentum_score']].copy()
        cache_df['momentum_score'] = cache_df['momentum_score'].fillna(0)
        us_cache = cache_df.to_dict('records')
    else:
        us_cache = []
    if len(uk_df) > 0:
        cache_df = uk_df[['webVideoUrl', 'momentum_score']].copy()
        cache_df['momentum_score'] = cache_df['momentum_score'].fillna(0)
        uk_cache = cache_df.to_dict('records')
    else:
        uk_cache = []
    
    with open(us_path, 'w') as f:
        json.dump(us_cache, f)
    
    with open(uk_path, 'w') as f:
        json.dump(uk_cache, f)
    
    print(f"    US records: {len(us_cache)}")
    print(f"    UK records: {len(uk_cache)}")
