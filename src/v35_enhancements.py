"""
TikTok Trend System v3.5.0 Enhancements
- Velocity Prediction: Predict where trends are heading in 6h, 12h, 24h
- Competitor Analysis: Identify gaps and opportunities vs capcutdailyuk

Integrates with existing v3.4.0 daily_processor.py
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.formatting.rule import ColorScaleRule, FormulaRule
import json
import os
import re as _re
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE


def _sanitize_cell(value):
    """Sanitize a value before writing to an Excel cell.
    Removes illegal XML characters that openpyxl rejects."""
    if isinstance(value, str):
        return ILLEGAL_CHARACTERS_RE.sub('', value)
    return value

# =============================================================================
# CONFIGURATION
# =============================================================================

YOUR_ACCOUNTS = [
    'capcuttemplates833', 'capcuttrends02', 'capcuttemplatesai',
    'artemiscc_capcut', 'capcutaistudio', 'artemiscccapcut', 'capcut.vorlagen101'
]

COMPETITOR_ACCOUNTS = [
    'capcutdailyuk', 'capcut__creations', 'jyoung101capcut',
    'capcut_templatetrends', 'capcut_core', 'capcut.trends.uk1'
]

# Velocity thresholds for predictions
VELOCITY_THRESHOLDS = {
    'EXPLOSIVE': 200,    # momentum increasing >200/day - will peak within 24h
    'STRONG': 100,       # momentum increasing >100/day - strong growth
    'MODERATE': 50,      # momentum increasing >50/day - healthy growth  
    'WEAK': 0,           # momentum flat or declining slightly
    'DECLINING': -50,    # momentum dropping
    'CRASHING': -100     # rapid decline
}

# Status colors (from v3.3.0 spec)
STATUS_COLORS = {
    '🆕 NEW': 'FFFFE0',
    '🚀 SPIKING': '00FF00',
    '📈 RISING': '90EE90',
    '📉 COOLING': 'FFB6C1',
    '❄️ DYING': 'FF0000'
}


# =============================================================================
# VARIANT ALLOCATION & STOP RULES (v3.5.0 Option B - Baked In)
# =============================================================================

VARIANT_CACHE_DEFAULT_TTL = 7  # days

def _strip_emoji(s: str) -> str:
    """Strip leading emoji and whitespace from action_window/trajectory values."""
    if not s:
        return ""
    return _re.sub(r'^[^\x00-\x7F]+\s*', '', str(s)).strip()


def _as_float_vel(x) -> Optional[float]:
    """Robust float parsing for '+8,747/day', '32.9h', 8747, etc."""
    if x is None:
        return None
    try:
        if isinstance(x, (int, float)):
            return float(x)
        s = str(x).strip().lower()
        if not s:
            return None
        s = s.replace(",", "").replace("/day", "").replace("per day", "").replace("h", "")
        if s.startswith("+"):
            s = s[1:]
        return float(s)
    except Exception:
        return None


def calc_recommended_variants(aw: str, tr: str, age: Optional[float], cur: Optional[float]) -> int:
    """Calculate how many template variants to build (0/1/2/3/5/7)."""
    awu = _strip_emoji(aw).upper()
    tru = _strip_emoji(tr).upper()
    agev = age if age is not None else 999999.0
    curv = cur if cur is not None else 0.0

    # Hard stop zones
    if awu in ("PEAKED", "TOO LATE", "WINDOW CLOSING"):
        return 0
    if tru in ("DECLINING", "CRASHING"):
        return 0
    if agev >= 72:
        return 0

    # Last-chance tier (60-72h): exceptional only
    if 60 <= agev < 72:
        if awu in ("ACT NOW", "6-12H") and tru in ("EXPLOSIVE", "STRONG") and curv >= 5000:
            return 1
        return 0

    # Normal allocation
    if awu == "ACT NOW" and tru == "EXPLOSIVE" and agev <= 24:
        return 7
    if awu == "ACT NOW" and tru in ("EXPLOSIVE", "STRONG"):
        return 5
    if awu == "ACT NOW" and tru == "MODERATE":
        return 3
    if awu == "6-12H" and tru == "EXPLOSIVE":
        return 5
    if awu == "6-12H" and tru in ("STRONG", "MODERATE"):
        return 3
    if awu == "12-24H" and tru == "STRONG":
        return 3
    if awu == "12-24H" and tru == "MODERATE":
        return 2
    if awu == "12-24H" and tru == "FLAT":
        return 1
    return 0


def calc_stop_building(aw: str, tr: str, age: Optional[float], streak: int) -> Tuple[bool, str]:
    """Determine if building should stop and why."""
    awu = _strip_emoji(aw).upper()
    tru = _strip_emoji(tr).upper()
    agev = age if age is not None else 999999.0

    if tru in ("DECLINING", "CRASHING"):
        return True, "DECLINING_TRAJECTORY"
    if awu in ("PEAKED", "TOO LATE"):
        return True, "WINDOW_OVER"
    if agev >= 72:
        return True, "AGE_OVER_72H"
    if streak >= 2:
        return True, "VELOCITY_NONPOS_2_RUNS"
    return False, ""


def load_streak_cache(path: str) -> Dict:
    """Load velocity streak cache from JSON file."""
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        out = {}
        for url, obj in raw.items():
            if isinstance(obj, dict):
                out[str(url)] = {"streak": int(obj.get("streak", 0) or 0), "last_seen": obj.get("last_seen")}
            else:
                out[str(url)] = {"streak": int(obj) if str(obj).isdigit() else 0, "last_seen": None}
        return out
    except Exception:
        return {}


def prune_streak_cache(cache: dict, ttl_days: int) -> dict:
    """Remove entries older than TTL days."""
    if ttl_days <= 0:
        return cache
    from datetime import date as _date
    cutoff = _date.today() - timedelta(days=ttl_days)
    keep = {}
    for url, obj in cache.items():
        ls = obj.get("last_seen")
        if not ls:
            keep[url] = obj
            continue
        try:
            d = datetime.strptime(ls, "%Y-%m-%d").date()
            if d >= cutoff:
                keep[url] = obj
        except Exception:
            keep[url] = obj
    return keep


def save_streak_cache(path: str, cache: dict) -> None:
    """Save velocity streak cache to JSON file."""
    if not path:
        return
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, sort_keys=True)


# =============================================================================
# VELOCITY PREDICTION ENGINE
# =============================================================================

@dataclass
class VelocityPrediction:
    """Holds prediction data for a trend"""
    current_momentum: float
    velocity: float  # momentum change per day
    acceleration: float  # velocity change per day
    predicted_6h: float
    predicted_12h: float
    predicted_24h: float
    peak_estimate_hours: Optional[float]  # estimated hours until peak (None if declining)
    trajectory: str  # EXPLOSIVE, STRONG, MODERATE, WEAK, DECLINING, CRASHING
    confidence: str  # HIGH, MEDIUM, LOW based on data quality
    action_window: str  # "ACT NOW", "6-12H", "12-24H", "MONITOR", "TOO LATE"


def calculate_velocity_predictions(
    df_today: pd.DataFrame,
    df_yesterday: pd.DataFrame = None,
    df_2days_ago: pd.DataFrame = None
) -> pd.DataFrame:
    """
    Calculate velocity-based predictions for all trends.
    
    Uses up to 3 days of data to calculate velocity and acceleration.
    Falls back gracefully when historical data is missing.
    """
    df = df_today.copy()
    
    # Auto-calculate metrics if missing (raw Apify data)
    df = _ensure_calculated_metrics(df)
    if df_yesterday is not None:
        df_yesterday = _ensure_calculated_metrics(df_yesterday)
    if df_2days_ago is not None:
        df_2days_ago = _ensure_calculated_metrics(df_2days_ago)
    
    # Merge with yesterday's data if available
    if df_yesterday is not None and len(df_yesterday) > 0:
        yesterday_momentum = df_yesterday[['webVideoUrl', 'momentum_score']].copy()
        yesterday_momentum.columns = ['webVideoUrl', 'momentum_yesterday']
        df = df.merge(yesterday_momentum, on='webVideoUrl', how='left')
    else:
        df['momentum_yesterday'] = np.nan
    
    # Merge with 2-days-ago data if available
    if df_2days_ago is not None and len(df_2days_ago) > 0:
        old_momentum = df_2days_ago[['webVideoUrl', 'momentum_score']].copy()
        old_momentum.columns = ['webVideoUrl', 'momentum_2days']
        df = df.merge(old_momentum, on='webVideoUrl', how='left')
    else:
        df['momentum_2days'] = np.nan
    
    # Calculate velocity (change per day)
    df['velocity'] = df['momentum_score'] - df['momentum_yesterday'].fillna(df['momentum_score'])
    
    # Calculate acceleration (change in velocity)
    if df_yesterday is not None and df_2days_ago is not None:
        velocity_yesterday = df['momentum_yesterday'] - df['momentum_2days']
        df['acceleration'] = df['velocity'] - velocity_yesterday.fillna(0)
    else:
        df['acceleration'] = 0
    
    # Predict future momentum using physics model: position + velocity*t + 0.5*acceleration*t^2
    # But cap acceleration impact to avoid runaway predictions
    df['acceleration_capped'] = df['acceleration'].clip(-50, 50)
    
    # Predictions (time in days: 0.25 = 6h, 0.5 = 12h, 1.0 = 24h)
    df['predicted_6h'] = (
        df['momentum_score'] + 
        df['velocity'] * 0.25 + 
        0.5 * df['acceleration_capped'] * (0.25 ** 2)
    ).clip(lower=0)
    
    df['predicted_12h'] = (
        df['momentum_score'] + 
        df['velocity'] * 0.5 + 
        0.5 * df['acceleration_capped'] * (0.5 ** 2)
    ).clip(lower=0)
    
    df['predicted_24h'] = (
        df['momentum_score'] + 
        df['velocity'] * 1.0 + 
        0.5 * df['acceleration_capped'] * (1.0 ** 2)
    ).clip(lower=0)
    
    # Determine trajectory
    def get_trajectory(velocity):
        if velocity >= VELOCITY_THRESHOLDS['EXPLOSIVE']:
            return '🚀 EXPLOSIVE'
        elif velocity >= VELOCITY_THRESHOLDS['STRONG']:
            return '📈 STRONG'
        elif velocity >= VELOCITY_THRESHOLDS['MODERATE']:
            return '↗️ MODERATE'
        elif velocity >= VELOCITY_THRESHOLDS['WEAK']:
            return '➡️ FLAT'
        elif velocity >= VELOCITY_THRESHOLDS['DECLINING']:
            return '↘️ DECLINING'
        else:
            return '📉 CRASHING'
    
    df['trajectory'] = df['velocity'].apply(get_trajectory)
    
    # Estimate peak timing (when velocity will hit 0)
    # peak_time = -velocity / acceleration (only valid if acceleration < 0 and velocity > 0)
    def estimate_peak(row):
        if row['acceleration'] < -5 and row['velocity'] > 0:
            peak_hours = (-row['velocity'] / row['acceleration']) * 24
            if 0 < peak_hours < 72:
                return round(peak_hours, 1)
        return None
    
    df['peak_estimate_hours'] = df.apply(estimate_peak, axis=1)
    
    # Determine confidence based on data availability
    def get_confidence(row):
        if pd.notna(row.get('momentum_2days')) and pd.notna(row.get('momentum_yesterday')):
            return 'HIGH'
        elif pd.notna(row.get('momentum_yesterday')):
            return 'MEDIUM'
        else:
            return 'LOW'
    
    df['prediction_confidence'] = df.apply(get_confidence, axis=1)
    
    # Determine action window
    def get_action_window(row):
        age = row.get('age_hours', 999)
        velocity = row['velocity']
        momentum = row['momentum_score']
        predicted_24h = row['predicted_24h']
        
        # Too old - 72h window closing
        if age > 60:
            return '⚠️ WINDOW CLOSING'
        
        # Explosive growth - act immediately
        if velocity >= 200 and momentum >= 1000:
            return '🔴 ACT NOW'
        
        # Strong growth - act within 6-12h
        if velocity >= 100 and momentum >= 500:
            return '🟠 6-12H'
        
        # Moderate growth but predicted to be big
        if velocity >= 50 and predicted_24h >= 2000:
            return '🟡 12-24H'
        
        # Flat or declining
        if velocity <= 0:
            if momentum >= 2000:
                return '⚠️ PEAKED'
            else:
                return '❌ TOO LATE'
        
        # Default - worth monitoring
        return '🟢 MONITOR'
    
    df['action_window'] = df.apply(get_action_window, axis=1)
    
    return df


def _ensure_calculated_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure momentum_score, age_hours, shares_per_hour etc. exist.
    Calculate from raw Apify fields if missing.
    """
    df = df.copy()
    
    # Calculate age_hours if missing
    if 'age_hours' not in df.columns or df['age_hours'].isna().all():
        if 'createTimeISO' in df.columns:
            now = pd.Timestamp.now(tz='UTC')
            df['createTimeISO'] = pd.to_datetime(df['createTimeISO'], utc=True, errors='coerce')
            df['age_hours'] = (now - df['createTimeISO']).dt.total_seconds() / 3600
            df['age_hours'] = df['age_hours'].clip(lower=0.1)  # Prevent division by zero
        else:
            df['age_hours'] = 24  # Default assumption
    
    # Ensure numeric columns exist
    for col in ['shareCount', 'diggCount', 'playCount']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Force numeric type on metric columns (may arrive as strings from some sources)
    for col in ['age_hours', 'momentum_score', 'shares_per_hour', 'likes_per_hour', 'views_per_hour']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Calculate per-hour metrics if missing
    if 'shares_per_hour' not in df.columns or df['shares_per_hour'].isna().all():
        if 'shareCount' in df.columns and 'age_hours' in df.columns:
            df['shares_per_hour'] = df['shareCount'] / df['age_hours'].clip(lower=0.1)
    
    if 'likes_per_hour' not in df.columns or df['likes_per_hour'].isna().all():
        if 'diggCount' in df.columns and 'age_hours' in df.columns:
            df['likes_per_hour'] = df['diggCount'] / df['age_hours'].clip(lower=0.1)
    
    if 'views_per_hour' not in df.columns or df['views_per_hour'].isna().all():
        if 'playCount' in df.columns and 'age_hours' in df.columns:
            df['views_per_hour'] = df['playCount'] / df['age_hours'].clip(lower=0.1)
    
    # Calculate momentum_score if missing
    if 'momentum_score' not in df.columns or df['momentum_score'].isna().all():
        shares_h = df.get('shares_per_hour', pd.Series(0, index=df.index))
        likes_h = df.get('likes_per_hour', pd.Series(0, index=df.index))
        views_h = df.get('views_per_hour', pd.Series(0, index=df.index))
        
        df['momentum_score'] = (
            shares_h.fillna(0) * 10 + 
            likes_h.fillna(0) * 3 + 
            views_h.fillna(0) * 0.01
        )
    
    # Ensure Market column exists
    if 'Market' not in df.columns:
        df['Market'] = '🇬🇧 UK ONLY'  # Default
    
    # Ensure AI_CATEGORY exists
    if 'AI_CATEGORY' not in df.columns:
        df['AI_CATEGORY'] = 'Unknown'
    
    return df


def create_velocity_summary(df: pd.DataFrame, cache_path: str = None) -> pd.DataFrame:
    """Create a summary view of velocity predictions sorted by opportunity.
    
    Now includes variant allocation and stop rules (v3.5.0 Option B).
    """
    
    cols = [
        'webVideoUrl', 'text', 'author', 'age_hours',
        'momentum_score', 'velocity', 'acceleration',
        'predicted_6h', 'predicted_12h', 'predicted_24h',
        'trajectory', 'peak_estimate_hours', 'prediction_confidence',
        'action_window', 'Market', 'AI_CATEGORY'
    ]
    
    # Filter to available columns
    available_cols = [c for c in cols if c in df.columns]
    summary = df[available_cols].copy()
    
    # Create opportunity score for sorting (with NaN handling)
    # Prioritize: high predicted growth + young age + ACT NOW status
    summary['opportunity_score'] = (
        (summary['predicted_24h'].fillna(0) - summary['momentum_score'].fillna(0)) * 0.5 +  # Growth potential
        summary['velocity'].fillna(0) * 0.3 +  # Current velocity
        (72 - summary['age_hours'].fillna(72).clip(upper=72)) * 10  # Youth bonus
    )
    
    # Boost ACT NOW items
    summary.loc[summary['action_window'].str.contains('ACT NOW', na=False), 'opportunity_score'] *= 1.5
    
    # Sort by opportunity score
    summary = summary.sort_values('opportunity_score', ascending=False)
    
    # Format for display (with NaN handling)
    summary['Trend'] = summary['text'].fillna('').astype(str).str[:60] + '...' if 'text' in summary.columns else ''
    summary['Creator'] = summary.get('author', '').fillna('')
    summary['Age'] = summary['age_hours'].fillna(0).apply(lambda x: f"{x:.1f}h")
    summary['Current'] = summary['momentum_score'].fillna(0).astype(int)
    summary['Velocity'] = summary['velocity'].fillna(0).apply(lambda x: f"{x:+.0f}/day")
    summary['In 6h'] = summary['predicted_6h'].fillna(0).astype(int)
    summary['In 12h'] = summary['predicted_12h'].fillna(0).astype(int)
    summary['In 24h'] = summary['predicted_24h'].fillna(0).astype(int)
    summary['Peak In'] = summary['peak_estimate_hours'].apply(
        lambda x: f"{x:.0f}h" if pd.notna(x) else "N/A"
    )
    
    # ── Variant allocation & stop rules (Option B inline) ──
    cache = prune_streak_cache(load_streak_cache(cache_path or ''), VARIANT_CACHE_DEFAULT_TTL)
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    rec_variants = []
    streaks = []
    stops = []
    stop_reasons = []
    
    for _, row in summary.iterrows():
        aw = str(row.get('action_window', ''))
        tr = str(row.get('trajectory', ''))
        age_val = row.get('age_hours', None)
        cur_val = row.get('momentum_score', None)
        vel_val = row.get('velocity', None)
        url = str(row.get('webVideoUrl', ''))
        
        # Streak calculation
        prev = cache.get(url, {"streak": 0, "last_seen": None})
        prev_streak = int(prev.get("streak", 0) or 0)
        
        vel_float = _as_float_vel(vel_val)
        if vel_float is not None and vel_float <= 0:
            streak = prev_streak + 1
        elif vel_float is not None and vel_float > 0:
            streak = 0
        else:
            streak = prev_streak  # unknown velocity -> hold
        
        if url:
            cache[url] = {"streak": streak, "last_seen": today_str}
        
        rv = calc_recommended_variants(aw, tr, age_val, cur_val)
        stop, reason = calc_stop_building(aw, tr, age_val, streak)
        
        rec_variants.append(rv)
        streaks.append(streak)
        stops.append(stop)
        stop_reasons.append(reason)
    
    summary['recommended_variants'] = rec_variants
    summary['velocity_nonpos_streak'] = streaks
    summary['stop_building'] = stops
    summary['stop_reason'] = stop_reasons
    
    # Save updated cache
    save_streak_cache(cache_path or '', cache)
    
    # Final columns for output
    output_cols = [
        'action_window', 'trajectory', 'Trend', 'Creator', 'Age',
        'Current', 'Velocity', 'In 6h', 'In 12h', 'In 24h',
        'Peak In', 'prediction_confidence', 'Market', 'webVideoUrl',
        'recommended_variants', 'velocity_nonpos_streak', 'stop_building', 'stop_reason'
    ]
    
    return summary[[c for c in output_cols if c in summary.columns]]


# =============================================================================
# COMPETITOR ANALYSIS ENGINE
# =============================================================================

@dataclass
class CompetitorInsight:
    """Analysis of competitor behavior vs yours"""
    trend_url: str
    trend_text: str
    competitor_posted: bool
    you_posted: bool
    momentum_when_competitor_posted: float
    current_momentum: float
    gap_type: str  # "MISSED_OPPORTUNITY", "BEAT_THEM", "BOTH_CAUGHT", "NEITHER"
    hours_behind: Optional[float]  # How many hours after competitor you posted (None if you didn't)
    potential_revenue_missed: float  # Estimated £ based on momentum


def analyze_competitor_gaps(
    df_today: pd.DataFrame,
    df_historical: pd.DataFrame = None,  # Last 7 days aggregated
    your_accounts: List[str] = YOUR_ACCOUNTS,
    competitor_accounts: List[str] = COMPETITOR_ACCOUNTS
) -> pd.DataFrame:
    """
    Analyze what trends the competitor catches that you miss.
    
    Returns DataFrame with gap analysis.
    """
    df = df_today.copy()
    
    # Identify posts by you vs competitor
    df['is_yours'] = df['author'].isin(your_accounts)
    df['is_competitor'] = df['author'].isin(competitor_accounts)
    
    # Group by trend pattern (using text similarity would be better, but URL works for exact matches)
    # For now, identify trends where competitor posted but you didn't
    
    competitor_urls = set(df[df['is_competitor']]['webVideoUrl'])
    your_urls = set(df[df['is_yours']]['webVideoUrl'])
    
    # Find high-momentum trends competitor caught
    competitor_trends = df[df['is_competitor']].copy()
    
    # Analyze each competitor post
    results = []
    
    for _, comp_row in competitor_trends.iterrows():
        # Did you also post this trend?
        you_also_posted = comp_row['webVideoUrl'] in your_urls
        
        # Get your version if exists
        your_version = df[(df['webVideoUrl'] == comp_row['webVideoUrl']) & df['is_yours']]
        
        if len(your_version) > 0:
            gap_type = 'BOTH_CAUGHT'
            hours_behind = (
                your_version.iloc[0]['age_hours'] - comp_row['age_hours']
            ) if 'age_hours' in your_version.columns else None
        else:
            gap_type = 'MISSED_BY_YOU'
            hours_behind = None
        
        # Estimate missed revenue: £5 per 1000 momentum (rough estimate)
        potential_missed = (comp_row['momentum_score'] / 1000) * 5 if not you_also_posted else 0
        
        results.append({
            'trend_url': comp_row['webVideoUrl'],
            'trend_text': str(comp_row.get('text', '') if pd.notna(comp_row.get('text')) else '')[:60],
            'competitor_account': comp_row['author'],
            'competitor_momentum': comp_row['momentum_score'],
            'competitor_shares_h': comp_row.get('shares_per_hour', 0),
            'competitor_age_hours': comp_row.get('age_hours', 0),
            'you_also_posted': you_also_posted,
            'gap_type': gap_type,
            'hours_behind': hours_behind,
            'estimated_missed_revenue': round(potential_missed, 2),
            'market': comp_row.get('Market', 'Unknown'),
            'ai_category': comp_row.get('AI_CATEGORY', 'Unknown')
        })
    
    return pd.DataFrame(results)


def identify_competitor_patterns(df_historical: pd.DataFrame = None) -> Dict:
    """
    Identify patterns in competitor posting behavior.
    
    Returns insights like:
    - Preferred posting times
    - Hashtag preferences
    - Speed to market (how quickly they catch trends)
    """
    # This would analyze historical data
    # For now, return placeholder structure
    return {
        'avg_posting_hour_utc': None,
        'preferred_hashtags': [],
        'avg_trend_age_when_posted': None,
        'success_rate': None,
        'notes': 'Requires 7+ days of historical data for accurate patterns'
    }


def calculate_your_vs_competitor_metrics(
    df: pd.DataFrame,
    your_accounts: List[str] = YOUR_ACCOUNTS,
    competitor_accounts: List[str] = COMPETITOR_ACCOUNTS
) -> Dict:
    """Calculate head-to-head metrics."""
    
    df = df.copy()
    df['is_yours'] = df['author'].isin(your_accounts)
    df['is_competitor'] = df['author'].isin(competitor_accounts)
    
    your_posts = df[df['is_yours']]
    comp_posts = df[df['is_competitor']]
    
    return {
        'your_post_count': len(your_posts),
        'competitor_post_count': len(comp_posts),
        'your_avg_momentum': your_posts['momentum_score'].mean() if len(your_posts) > 0 else 0,
        'competitor_avg_momentum': comp_posts['momentum_score'].mean() if len(comp_posts) > 0 else 0,
        'your_total_momentum': your_posts['momentum_score'].sum() if len(your_posts) > 0 else 0,
        'competitor_total_momentum': comp_posts['momentum_score'].sum() if len(comp_posts) > 0 else 0,
        'your_spiking_count': len(your_posts[your_posts.get('acceleration_status', '').str.contains('SPIKING', na=False)]) if 'acceleration_status' in your_posts.columns else 0,
        'competitor_spiking_count': len(comp_posts[comp_posts.get('acceleration_status', '').str.contains('SPIKING', na=False)]) if 'acceleration_status' in comp_posts.columns else 0,
    }


# =============================================================================
# EXCEL OUTPUT GENERATION
# =============================================================================

def create_enhanced_excel(
    df_today: pd.DataFrame,
    df_yesterday: pd.DataFrame = None,
    df_2days_ago: pd.DataFrame = None,
    output_path: str = 'BUILD_TODAY_ENHANCED.xlsx',
    cache_path: str = None
) -> str:
    """
    Create enhanced Excel file with new tabs:
    - VELOCITY_PREDICTIONS: Where trends are heading
    - COMPETITOR_ANALYSIS: Gap analysis vs capcutdailyuk
    - OPPORTUNITY_MATRIX: Combined view for decision making
    """
    
    # Ensure numeric types on input data (may arrive as strings)
    df_today = _ensure_calculated_metrics(df_today)
    
    wb = Workbook()
    
    # Style definitions
    header_fill = PatternFill('solid', fgColor='1F4E78')
    header_font = Font(bold=True, color='FFFFFF')
    cyan_fill = PatternFill('solid', fgColor='E0FFFF')
    orange_fill = PatternFill('solid', fgColor='FFE4B5')
    gold_fill = PatternFill('solid', fgColor='FFD700')
    red_fill = PatternFill('solid', fgColor='FF6B6B')
    green_fill = PatternFill('solid', fgColor='90EE90')
    yellow_fill = PatternFill('solid', fgColor='FFFACD')
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # ===================
    # TAB 1: VELOCITY PREDICTIONS
    # ===================
    ws_velocity = wb.active
    ws_velocity.title = 'VELOCITY_PREDICTIONS'
    
    # Calculate predictions
    df_with_predictions = calculate_velocity_predictions(df_today, df_yesterday, df_2days_ago)
    velocity_summary = create_velocity_summary(df_with_predictions, cache_path=cache_path)
    
    # Write header
    headers = list(velocity_summary.columns)
    for col_idx, header in enumerate(headers, 1):
        cell = ws_velocity.cell(row=1, column=col_idx, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center')
    
    # Write data
    for row_idx, (_, row) in enumerate(velocity_summary.iterrows(), 2):
        for col_idx, value in enumerate(row, 1):
            cell = ws_velocity.cell(row=row_idx, column=col_idx, value=_sanitize_cell(value))
            cell.border = thin_border
            
            # Color code action_window column (column 1)
            if col_idx == 1:
                if 'ACT NOW' in str(value):
                    cell.fill = red_fill
                    cell.font = Font(bold=True)
                elif '6-12H' in str(value):
                    cell.fill = orange_fill
                elif '12-24H' in str(value):
                    cell.fill = yellow_fill
                elif 'MONITOR' in str(value):
                    cell.fill = green_fill
            
            # Color code trajectory column (column 2)
            if col_idx == 2:
                if 'EXPLOSIVE' in str(value):
                    cell.fill = PatternFill('solid', fgColor='FF4444')
                    cell.font = Font(bold=True, color='FFFFFF')
                elif 'STRONG' in str(value):
                    cell.fill = PatternFill('solid', fgColor='00AA00')
            
            # Color code recommended_variants column
            header_name = headers[col_idx - 1] if col_idx <= len(headers) else ''
            if header_name == 'recommended_variants':
                cell.alignment = Alignment(horizontal='center')
                variant_fills = {
                    7: PatternFill('solid', fgColor='FF4444'),
                    5: PatternFill('solid', fgColor='FF6B6B'),
                    3: PatternFill('solid', fgColor='FFB347'),
                    2: PatternFill('solid', fgColor='FFFACD'),
                    1: PatternFill('solid', fgColor='E8E8E8'),
                }
                try:
                    iv = int(value) if value is not None else 0
                except (ValueError, TypeError):
                    iv = 0
                if iv in variant_fills:
                    cell.fill = variant_fills[iv]
                    if iv >= 5:
                        cell.font = Font(bold=True, color='FFFFFF')
            
            # Color code stop_building column
            if header_name == 'stop_building' and value is True:
                cell.fill = PatternFill('solid', fgColor='FF0000')
                cell.font = Font(bold=True, color='FFFFFF')
                cell.alignment = Alignment(horizontal='center')
            elif header_name == 'stop_building':
                cell.alignment = Alignment(horizontal='center')
            
            # Center streak column
            if header_name == 'velocity_nonpos_streak':
                cell.alignment = Alignment(horizontal='center')
    
    # Set column widths
    ws_velocity.column_dimensions['A'].width = 18
    ws_velocity.column_dimensions['B'].width = 15
    ws_velocity.column_dimensions['C'].width = 50
    ws_velocity.column_dimensions['D'].width = 15
    
    # Set widths for new variant/stop columns (find by header name)
    from openpyxl.utils import get_column_letter
    for col_idx, h in enumerate(headers, 1):
        if h == 'recommended_variants':
            ws_velocity.column_dimensions[get_column_letter(col_idx)].width = 22
        elif h == 'velocity_nonpos_streak':
            ws_velocity.column_dimensions[get_column_letter(col_idx)].width = 22
        elif h == 'stop_building':
            ws_velocity.column_dimensions[get_column_letter(col_idx)].width = 15
        elif h == 'stop_reason':
            ws_velocity.column_dimensions[get_column_letter(col_idx)].width = 28
    
    # Freeze top row
    ws_velocity.freeze_panes = 'A2'
    
    # ===================
    # TAB 2: COMPETITOR ANALYSIS
    # ===================
    ws_competitor = wb.create_sheet('COMPETITOR_ANALYSIS')
    
    # Analyze gaps
    competitor_gaps = analyze_competitor_gaps(df_today)
    
    if len(competitor_gaps) > 0:
        # Write header
        headers = list(competitor_gaps.columns)
        for col_idx, header in enumerate(headers, 1):
            cell = ws_competitor.cell(row=1, column=col_idx, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center')
        
        # Write data
        for row_idx, (_, row) in enumerate(competitor_gaps.iterrows(), 2):
            for col_idx, value in enumerate(row, 1):
                cell = ws_competitor.cell(row=row_idx, column=col_idx, value=_sanitize_cell(value))
                cell.border = thin_border
                
                # Highlight missed opportunities
                if col_idx == headers.index('gap_type') + 1:
                    if value == 'MISSED_BY_YOU':
                        cell.fill = red_fill
                        cell.font = Font(bold=True)
                    elif value == 'BOTH_CAUGHT':
                        cell.fill = green_fill
        
        ws_competitor.freeze_panes = 'A2'
    else:
        ws_competitor['A1'] = 'No competitor posts found in today\'s data'
    
    # ===================
    # TAB 3: HEAD-TO-HEAD SUMMARY
    # ===================
    ws_h2h = wb.create_sheet('HEAD_TO_HEAD')
    
    metrics = calculate_your_vs_competitor_metrics(df_today)
    
    # Create comparison table
    ws_h2h['A1'] = 'METRIC'
    ws_h2h['B1'] = 'YOU (7 accounts)'
    ws_h2h['C1'] = 'COMPETITOR'
    ws_h2h['D1'] = 'WINNER'
    
    for col in ['A', 'B', 'C', 'D']:
        ws_h2h[f'{col}1'].fill = header_fill
        ws_h2h[f'{col}1'].font = header_font
    
    comparisons = [
        ('Posts in Trending', metrics['your_post_count'], metrics['competitor_post_count']),
        ('Average Momentum', round(metrics['your_avg_momentum'], 0), round(metrics['competitor_avg_momentum'], 0)),
        ('Total Momentum', round(metrics['your_total_momentum'], 0), round(metrics['competitor_total_momentum'], 0)),
        ('SPIKING Posts', metrics['your_spiking_count'], metrics['competitor_spiking_count']),
    ]
    
    for row_idx, (metric, yours, theirs) in enumerate(comparisons, 2):
        ws_h2h[f'A{row_idx}'] = metric
        ws_h2h[f'B{row_idx}'] = yours
        ws_h2h[f'C{row_idx}'] = theirs
        
        if yours > theirs:
            ws_h2h[f'D{row_idx}'] = '✅ YOU'
            ws_h2h[f'D{row_idx}'].fill = green_fill
        elif theirs > yours:
            ws_h2h[f'D{row_idx}'] = '❌ THEM'
            ws_h2h[f'D{row_idx}'].fill = red_fill
        else:
            ws_h2h[f'D{row_idx}'] = '🤝 TIE'
    
    ws_h2h.column_dimensions['A'].width = 25
    ws_h2h.column_dimensions['B'].width = 18
    ws_h2h.column_dimensions['C'].width = 18
    ws_h2h.column_dimensions['D'].width = 12
    
    # ===================
    # TAB 4: OPPORTUNITY MATRIX
    # ===================
    ws_matrix = wb.create_sheet('OPPORTUNITY_MATRIX')
    
    # Combine velocity + competitor analysis for decision matrix
    ws_matrix['A1'] = 'DECISION MATRIX: What to build RIGHT NOW'
    ws_matrix['A1'].font = Font(bold=True, size=14)
    ws_matrix.merge_cells('A1:F1')
    
    # Filter to actionable opportunities
    actionable = df_with_predictions[
        (df_with_predictions['action_window'].str.contains('ACT NOW|6-12H', na=False)) &
        (df_with_predictions['age_hours'] <= 48) &
        (df_with_predictions['momentum_score'] >= 500)
    ].head(20)
    
    if len(actionable) > 0:
        matrix_headers = ['Priority', 'Trend', 'Current', 'Predicted 24h', 'Growth', 'Action Window', 'URL']
        for col_idx, header in enumerate(matrix_headers, 1):
            cell = ws_matrix.cell(row=3, column=col_idx, value=header)
            cell.fill = header_fill
            cell.font = header_font
        
        for row_idx, (_, row) in enumerate(actionable.iterrows(), 4):
            growth = row['predicted_24h'] - row['momentum_score']
            ws_matrix.cell(row=row_idx, column=1, value=row_idx - 3)  # Priority number
            ws_matrix.cell(row=row_idx, column=2, value=str(row.get('text', '') if pd.notna(row.get('text')) else '')[:50])
            ws_matrix.cell(row=row_idx, column=3, value=int(row['momentum_score']))
            ws_matrix.cell(row=row_idx, column=4, value=int(row['predicted_24h']))
            ws_matrix.cell(row=row_idx, column=5, value=f"+{int(growth)}")
            ws_matrix.cell(row=row_idx, column=6, value=row['action_window'])
            ws_matrix.cell(row=row_idx, column=7, value=row['webVideoUrl'])
            
            # Color the priority cell
            priority_cell = ws_matrix.cell(row=row_idx, column=1)
            if row_idx - 3 <= 3:
                priority_cell.fill = red_fill
                priority_cell.font = Font(bold=True)
            elif row_idx - 3 <= 7:
                priority_cell.fill = orange_fill
            else:
                priority_cell.fill = yellow_fill
    else:
        ws_matrix['A3'] = 'No immediate action items - check VELOCITY_PREDICTIONS for monitoring list'
    
    ws_matrix.freeze_panes = 'A4'
    ws_matrix.column_dimensions['B'].width = 45
    ws_matrix.column_dimensions['G'].width = 50
    
    # ===================
    # TAB 5: DOCUMENTATION
    # ===================
    ws_docs = wb.create_sheet('README')
    
    docs = [
        ('TikTok Trend System v3.5.0 Enhancements', '', ''),
        ('', '', ''),
        ('VELOCITY_PREDICTIONS Tab', '', ''),
        ('- Shows where each trend is heading in 6h, 12h, 24h', '', ''),
        ('- Action Window tells you WHEN to act:', '', ''),
        ('  🔴 ACT NOW = Drop everything, build template immediately', '', ''),
        ('  🟠 6-12H = High priority, build today', '', ''),
        ('  🟡 12-24H = Schedule for tomorrow', '', ''),
        ('  🟢 MONITOR = Watch but don\'t build yet', '', ''),
        ('  ⚠️ PEAKED/TOO LATE = Don\'t bother', '', ''),
        ('', '', ''),
        ('COMPETITOR_ANALYSIS Tab', '', ''),
        ('- Shows every trend capcutdailyuk posted', '', ''),
        ('- MISSED_BY_YOU = They caught it, you didn\'t = £££ lost', '', ''),
        ('- BOTH_CAUGHT = Good! Check if you were faster', '', ''),
        ('', '', ''),
        ('HEAD_TO_HEAD Tab', '', ''),
        ('- Daily scorecard: You vs Competitor', '', ''),
        ('- Track who\'s winning the trend detection game', '', ''),
        ('', '', ''),
        ('OPPORTUNITY_MATRIX Tab', '', ''),
        ('- Your BUILD LIST for today', '', ''),
        ('- Sorted by highest opportunity score', '', ''),
        ('- Top 3 (red) = Build FIRST', '', ''),
    ]
    
    for row_idx, (text, _, _) in enumerate(docs, 1):
        ws_docs.cell(row=row_idx, column=1, value=text)
    
    wb.save(output_path)
    return output_path


# =============================================================================
# DAILY BRIEFING - STRATEGIC ANALYSIS TEXT
# =============================================================================

def generate_daily_briefing(
    df_today: pd.DataFrame,
    df_yesterday: pd.DataFrame = None,
    output_dir: str = '.',
    cache_path: str = None
) -> str:
    """
    Generate written daily briefing with:
    1. Immediate Actions - top trends to build RIGHT NOW
    2. Strategic Insights - competitor analysis across ALL 6 competitors
    
    Returns the briefing text.
    """
    from datetime import datetime
    date_str = datetime.now().strftime('%Y-%m-%d')
    lines = []
    lines.append("=" * 60)
    lines.append(f"DAILY BRIEFING - {date_str}")
    lines.append("TikTok Trend System v3.5.0")
    lines.append("=" * 60)
    
    df = df_today.copy()
    df = _ensure_calculated_metrics(df)
    
    # --- SECTION 1: IMMEDIATE ACTIONS ---
    lines.append("")
    lines.append("━" * 60)
    lines.append("🔴 IMMEDIATE ACTIONS")
    lines.append("━" * 60)
    
    # Calculate velocity if yesterday available
    has_velocity = False
    if df_yesterday is not None and len(df_yesterday) > 0:
        velocity_df = calculate_velocity_predictions(df, df_yesterday)
        has_velocity = True
    else:
        velocity_df = df.copy()
        velocity_df['velocity'] = 0
        velocity_df['action_window'] = 'MONITOR'
        velocity_df['trajectory'] = 'FLAT'
        velocity_df['predicted_24h'] = velocity_df.get('momentum_score', 0)
    
    # Filter: fresh content under 48h with momentum >= 500
    fresh = velocity_df[velocity_df['age_hours'] <= 48].copy() if 'age_hours' in velocity_df.columns else velocity_df.copy()
    if 'momentum_score' in fresh.columns:
        fresh = fresh[fresh['momentum_score'] >= 500]
    
    # Exclude your own posts and competitor posts
    if 'author' in fresh.columns:
        all_tracked = [a.lower() for a in YOUR_ACCOUNTS + COMPETITOR_ACCOUNTS]
        fresh = fresh[~fresh['author'].str.lower().isin(all_tracked)]
    
    # Sort by momentum
    if len(fresh) > 0 and 'momentum_score' in fresh.columns:
        fresh = fresh.nlargest(5, 'momentum_score')
    
    if len(fresh) == 0:
        lines.append("")
        lines.append("No high-priority trends found meeting criteria (age <48h, momentum >=500).")
    else:
        for i, (_, row) in enumerate(fresh.iterrows(), 1):
            momentum = _safe_int_val(row.get('momentum_score', 0))
            age = round(float(row.get('age_hours', 0)), 1) if pd.notna(row.get('age_hours')) else 0
            shares_h = round(float(row.get('shares_per_hour', 0)), 1) if pd.notna(row.get('shares_per_hour')) else 0
            trend_text = str(row.get('text') if pd.notna(row.get('text')) else '')[:60]
            creator = str(row.get('author') if pd.notna(row.get('author')) else 'Unknown')[:20]
            market = str(row.get('Market', '')) if pd.notna(row.get('Market')) else ''
            
            # Action window
            action = str(row.get('action_window', '')) if has_velocity else ''
            trajectory = str(row.get('trajectory', '')) if has_velocity else ''
            vel = row.get('velocity', 0) if has_velocity else 0
            vel = vel if pd.notna(vel) else 0
            pred_24 = row.get('predicted_24h', momentum) if has_velocity else momentum
            pred_24 = pred_24 if pd.notna(pred_24) else momentum
            
            hours_left = max(0, 72 - age)
            
            lines.append("")
            lines.append(f"  #{i}. {trend_text}")
            lines.append(f"      Creator: {creator} | {market}")
            lines.append(f"      Momentum: {momentum:,} | Shares/h: {shares_h}")
            lines.append(f"      Age: {age}h | Window: {hours_left:.0f}h remaining")
            if has_velocity:
                lines.append(f"      Velocity: {vel:+,.0f}/day | Predicted 24h: {int(pred_24):,}")
                lines.append(f"      Action: {action} | Trajectory: {trajectory}")
            
            # Why this trend
            reasons = []
            if momentum >= 3000: reasons.append("URGENT momentum")
            elif momentum >= 2000: reasons.append("HIGH momentum")
            if shares_h >= 100: reasons.append(f"very high share rate ({shares_h}/h)")
            elif shares_h >= 25: reasons.append(f"strong share rate ({shares_h}/h)")
            if '🌐 BOTH' in market: reasons.append("trending in BOTH markets (2x revenue potential)")
            if has_velocity and vel > 200: reasons.append("EXPLOSIVE growth trajectory")
            elif has_velocity and vel > 100: reasons.append("strong upward velocity")
            if hours_left < 24: reasons.append(f"only {hours_left:.0f}h left in 72h window")
            
            if reasons:
                lines.append(f"      Why: {'; '.join(reasons)}")
    
    # --- SECTION 2: COMPETITOR ANALYSIS ---
    lines.append("")
    lines.append("━" * 60)
    lines.append("📊 STRATEGIC INSIGHTS - COMPETITOR ANALYSIS")
    lines.append("━" * 60)
    
    # Find all competitor posts
    comp_posts = pd.DataFrame()
    your_posts = pd.DataFrame()
    if 'author' in df.columns:
        comp_mask = df['author'].str.lower().isin([a.lower() for a in COMPETITOR_ACCOUNTS])
        your_mask = df['author'].str.lower().isin([a.lower() for a in YOUR_ACCOUNTS])
        comp_posts = df[comp_mask].copy()
        your_posts = df[your_mask].copy()
    
    lines.append("")
    lines.append(f"  Your posts in trending: {len(your_posts)}")
    lines.append(f"  Competitor posts in trending: {len(comp_posts)}")
    
    if len(comp_posts) == 0:
        lines.append("")
        lines.append("  No competitor posts found in today's trending data.")
        lines.append("  This could mean they're not posting, or their posts aren't trending.")
    else:
        # Per-competitor breakdown
        lines.append("")
        lines.append("  COMPETITOR BREAKDOWN:")
        comp_by_account = comp_posts.groupby('author').agg(
            posts=('author', 'size'),
            avg_momentum=('momentum_score', 'mean'),
            max_momentum=('momentum_score', 'max'),
            total_momentum=('momentum_score', 'sum')
        ).sort_values('total_momentum', ascending=False)
        
        for account, row in comp_by_account.iterrows():
            lines.append(f"    {account}: {int(row['posts'])} posts | "
                        f"avg momentum {int(row['avg_momentum']):,} | "
                        f"best {int(row['max_momentum']):,}")
        
        # Gap analysis - trends competitors caught that you missed
        lines.append("")
        lines.append("  GAP ANALYSIS - TRENDS THEY CAUGHT, YOU DIDN'T:")
        
        # Get your URLs
        your_urls = set(your_posts['webVideoUrl']) if len(your_posts) > 0 else set()
        
        # For each competitor post, find the underlying trend
        # A "missed" trend is where a competitor posted on a trending topic but none of your accounts did
        # We approximate this by checking if your accounts appear for similar content
        # Simpler: just show their highest momentum posts you don't have
        missed = comp_posts[~comp_posts['webVideoUrl'].isin(your_urls)].copy()
        missed = missed.nlargest(min(5, len(missed)), 'momentum_score')
        
        if len(missed) == 0:
            lines.append("    None! You covered all trends they did. 🎯")
        else:
            total_missed_revenue = 0
            for _, row in missed.iterrows():
                m = _safe_int_val(row.get('momentum_score', 0))
                text = str(row.get('text') if pd.notna(row.get('text')) else '')[:50]
                account = str(row.get('author', ''))
                age = round(float(row.get('age_hours', 0)), 1) if pd.notna(row.get('age_hours')) else 0
                est_rev = round(m / 1000 * 5, 2)
                total_missed_revenue += est_rev
                
                lines.append(f"    • {text}")
                lines.append(f"      By: {account} | Momentum: {m:,} | Age: {age}h | Est. missed: £{est_rev:.0f}")
            
            lines.append(f"    Total estimated missed revenue: £{total_missed_revenue:.0f}")
        
        # Head-to-head comparison
        lines.append("")
        lines.append("  HEAD-TO-HEAD SCORECARD:")
        your_avg_m = int(your_posts['momentum_score'].mean()) if len(your_posts) > 0 else 0
        comp_avg_m = int(comp_posts['momentum_score'].mean()) if len(comp_posts) > 0 else 0
        your_total = int(your_posts['momentum_score'].sum()) if len(your_posts) > 0 else 0
        comp_total = int(comp_posts['momentum_score'].sum()) if len(comp_posts) > 0 else 0
        
        your_spiking = len(your_posts[your_posts.get('status', your_posts.get('acceleration_status', pd.Series())).str.contains('SPIKING', na=False)]) if len(your_posts) > 0 else 0
        comp_spiking = len(comp_posts[comp_posts.get('status', comp_posts.get('acceleration_status', pd.Series())).str.contains('SPIKING', na=False)]) if len(comp_posts) > 0 else 0
        
        lines.append(f"    Metric              YOU          COMPETITORS")
        lines.append(f"    Posts in trending    {len(your_posts):<12} {len(comp_posts)}")
        lines.append(f"    Avg momentum        {your_avg_m:<12,} {comp_avg_m:,}")
        lines.append(f"    Total momentum      {your_total:<12,} {comp_total:,}")
        lines.append(f"    SPIKING posts       {your_spiking:<12} {comp_spiking}")
        
        if your_total > comp_total:
            lines.append(f"    → You're WINNING overall ({your_total:,} vs {comp_total:,})")
        elif comp_total > your_total:
            lines.append(f"    → Competitors AHEAD ({comp_total:,} vs {your_total:,}) - find more trends!")
        else:
            lines.append(f"    → Even match")
        
        # Niche analysis
        if 'AI_CATEGORY' in comp_posts.columns:
            comp_ai = len(comp_posts[comp_posts['AI_CATEGORY'] == 'AI'])
            comp_non = len(comp_posts[comp_posts['AI_CATEGORY'] == 'NON-AI'])
            your_ai = len(your_posts[your_posts['AI_CATEGORY'] == 'AI']) if len(your_posts) > 0 and 'AI_CATEGORY' in your_posts.columns else 0
            your_non = len(your_posts[your_posts['AI_CATEGORY'] == 'NON-AI']) if len(your_posts) > 0 and 'AI_CATEGORY' in your_posts.columns else 0
            
            lines.append("")
            lines.append("  NICHE COVERAGE:")
            lines.append(f"    AI trends:     YOU {your_ai} vs COMP {comp_ai}")
            lines.append(f"    NON-AI trends: YOU {your_non} vs COMP {comp_non}")
            
            if comp_ai > your_ai * 2 and comp_ai >= 3:
                lines.append(f"    ⚠️ Competitors are covering more AI trends - consider increasing AI template output")
            if comp_non > your_non * 2 and comp_non >= 3:
                lines.append(f"    ⚠️ Competitors are covering more NON-AI trends - diversify beyond AI")
        
        # Market coverage
        if 'Market' in comp_posts.columns:
            comp_both = len(comp_posts[comp_posts['Market'].str.contains('BOTH', na=False)])
            your_both = len(your_posts[your_posts['Market'].str.contains('BOTH', na=False)]) if len(your_posts) > 0 and 'Market' in your_posts.columns else 0
            
            if comp_both > 0:
                lines.append("")
                lines.append(f"  CROSS-MARKET: Competitors have {comp_both} BOTH-market posts vs your {your_both}")
                if comp_both > your_both:
                    lines.append(f"    ⚠️ They're better at catching cross-market trends (2x revenue potential)")
    
    # --- SECTION 3: RECOMMENDATIONS ---
    lines.append("")
    lines.append("━" * 60)
    lines.append("💡 RECOMMENDATIONS")
    lines.append("━" * 60)
    lines.append("")
    
    recs = []
    if len(fresh) > 0:
        top = fresh.iloc[0]
        top_text = str(top.get('text') if pd.notna(top.get('text')) else 'Unknown trend')[:40]
        recs.append(f"1. BUILD NOW: Start with \"{top_text}\" - highest priority opportunity")
    
    if len(comp_posts) > 0 and len(missed) > 0:
        recs.append(f"2. Check {len(missed)} trends competitors caught that you missed - potential revenue gap")
    
    if len(your_posts) == 0:
        recs.append("3. ⚠️ None of your posts are in today's trending - check posting schedule")
    
    if has_velocity:
        explosive = velocity_df[velocity_df.get('trajectory', pd.Series()) == 'EXPLOSIVE'] if 'trajectory' in velocity_df.columns else pd.DataFrame()
        if len(explosive) > 0:
            recs.append(f"4. {len(explosive)} EXPLOSIVE trajectories detected - these will peak within 24h")
    
    if not recs:
        recs.append("Continue monitoring - no urgent action items today")
    
    for r in recs:
        lines.append(f"  {r}")
    
    lines.append("")
    lines.append("=" * 60)
    lines.append("END OF DAILY BRIEFING")
    lines.append("=" * 60)
    
    return "\n".join(lines)


def _safe_int_val(val, default=0):
    """Safe int conversion for briefing text."""
    try:
        if pd.isna(val):
            return default
        return int(val)
    except (ValueError, TypeError):
        return default


# =============================================================================
# INTEGRATION WITH EXISTING SYSTEM
# =============================================================================

def integrate_with_daily_processor(
    us_data: pd.DataFrame,
    uk_data: pd.DataFrame,
    yesterday_us: pd.DataFrame = None,
    yesterday_uk: pd.DataFrame = None,
    two_days_us: pd.DataFrame = None,
    two_days_uk: pd.DataFrame = None,
    output_dir: str = '.'
) -> Dict[str, str]:
    """
    Main integration function - call this from daily_processor.py
    
    Adds velocity predictions and competitor analysis to both markets.
    Velocity streak cache is stored in the same directory as output
    (or CACHE_DIR if set) for persistence between runs.
    """
    from datetime import datetime
    
    date_str = datetime.now().strftime('%Y-%m-%d')
    output_files = {}
    
    # Use CACHE_DIR env var if available, otherwise fall back to output_dir parent
    cache_dir = os.environ.get('CACHE_DIR', 'data')
    streak_cache_path = os.path.join(cache_dir, 'velocity_streak_cache.json')
    
    # Process US data
    if us_data is not None and len(us_data) > 0:
        us_enhanced_path = f"{output_dir}/BUILD_TODAY_US_ENHANCED_{date_str}.xlsx"
        create_enhanced_excel(
            us_data, yesterday_us, two_days_us, us_enhanced_path,
            cache_path=streak_cache_path
        )
        output_files['us_enhanced'] = us_enhanced_path
    
    # Process UK data
    if uk_data is not None and len(uk_data) > 0:
        uk_enhanced_path = f"{output_dir}/BUILD_TODAY_UK_ENHANCED_{date_str}.xlsx"
        create_enhanced_excel(
            uk_data, yesterday_uk, two_days_uk, uk_enhanced_path,
            cache_path=streak_cache_path
        )
        output_files['uk_enhanced'] = uk_enhanced_path
    
    # Combined analysis (merge US + UK for cross-market insights)
    if us_data is not None and uk_data is not None:
        combined = pd.concat([us_data, uk_data], ignore_index=True)
        combined_yesterday = None
        if yesterday_us is not None and yesterday_uk is not None:
            combined_yesterday = pd.concat([yesterday_us, yesterday_uk], ignore_index=True)
        
        combined_path = f"{output_dir}/BUILD_TODAY_COMBINED_ENHANCED_{date_str}.xlsx"
        create_enhanced_excel(
            combined, combined_yesterday, None, combined_path,
            cache_path=streak_cache_path
        )
        output_files['combined_enhanced'] = combined_path
    
    return output_files


# =============================================================================
# STANDALONE TESTING
# =============================================================================

if __name__ == '__main__':
    # Test with sample data
    print("Creating sample test data...")
    
    # Generate sample data
    np.random.seed(42)
    n_samples = 100
    
    sample_data = pd.DataFrame({
        'webVideoUrl': [f'https://tiktok.com/video/{i}' for i in range(n_samples)],
        'text': [f'Sample trend #{i} with #capcut #trending hashtags' for i in range(n_samples)],
        'author': np.random.choice(
            YOUR_ACCOUNTS + COMPETITOR_ACCOUNTS + ['random_user_' + str(i) for i in range(20)],
            n_samples
        ),
        'age_hours': np.random.uniform(1, 72, n_samples),
        'shareCount': np.random.randint(10, 10000, n_samples),
        'diggCount': np.random.randint(100, 50000, n_samples),
        'playCount': np.random.randint(1000, 1000000, n_samples),
        'momentum_score': np.random.uniform(100, 5000, n_samples),
        'shares_per_hour': np.random.uniform(1, 200, n_samples),
        'views_per_hour': np.random.uniform(100, 50000, n_samples),
        'Market': np.random.choice(['🌐 BOTH', '🇺🇸 US ONLY', '🇬🇧 UK ONLY'], n_samples),
        'AI_CATEGORY': np.random.choice(['AI', 'NON-AI'], n_samples),
        'acceleration_status': np.random.choice(
            ['🆕 NEW', '🚀 SPIKING', '📈 RISING', '📉 COOLING', '❄️ DYING'],
            n_samples
        )
    })
    
    # Create yesterday's data (slightly different momentum)
    yesterday_data = sample_data.copy()
    yesterday_data['momentum_score'] = sample_data['momentum_score'] * np.random.uniform(0.7, 1.0, n_samples)
    
    # Run analysis
    print("Running velocity prediction analysis...")
    output_path = create_enhanced_excel(
        sample_data,
        yesterday_data,
        None,
        'test_enhanced_output.xlsx'
    )
    
    print(f"✅ Test file created: {output_path}")
    print("\nTab summary:")
    print("1. VELOCITY_PREDICTIONS - Where trends are heading")
    print("2. COMPETITOR_ANALYSIS - Gap analysis vs capcutdailyuk")
    print("3. HEAD_TO_HEAD - You vs Competitor scorecard")
    print("4. OPPORTUNITY_MATRIX - Your BUILD list for today")
    print("5. README - Documentation")
