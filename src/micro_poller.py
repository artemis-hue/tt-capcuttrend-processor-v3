#!/usr/bin/env python3
"""
TikTok Micro-Polling System v1.0
Detects accelerating trends and sends Discord alerts every 2 hours.

Based on AUTOMATION_HANDOVER_MICRO_POLLING.md specifications.
"""

import os
import json
import requests
from datetime import datetime, timezone
from typing import Optional
import re

# =============================================================================
# CONFIGURATION
# =============================================================================

# Entry Criteria (to become a candidate)
ENTRY_MAX_AGE_HOURS = 48
ENTRY_MIN_SHARES_PER_HOUR = 6
ENTRY_MIN_VIEWS_PER_HOUR = 150

# Alert Criteria (triggers Discord notification)
ALERT_MAX_AGE_HOURS = 36
ALERT_MIN_SHARES_PER_HOUR = 8
ALERT_MIN_VIEWS_PER_HOUR = 200
ALERT_MIN_DELTA_SHARES = 4

# Stop Tracking Criteria
STOP_AGE_HOURS = 60
STOP_CONSECUTIVE_NEGATIVE_DELTAS = 2

# System Limits
MAX_CANDIDATES = 8

# Alert Priority Thresholds
URGENT_MOMENTUM = 3000
URGENT_SHARES_PER_HOUR = 100
HIGH_MOMENTUM = 2000
HIGH_SHARES_PER_HOUR = 60

# Discord Colors
COLOR_URGENT = 16711680   # Red
COLOR_HIGH = 16744192     # Orange
COLOR_WATCH = 16776960    # Yellow

# Your Accounts (for identification)
YOUR_ACCOUNTS = [
    'capcuttemplates833',
    'capcuttrends02',
    'capcuttemplatesai',
    'artemiscc_capcut',
    'capcutaistudio',
    'artemiscccapcut',
    'capcut.vorlagen101'
]

# Competitor Accounts
COMPETITOR_ACCOUNTS = [
    'capcutdailyuk',
    'capcut__creations',
    'jyoung101capcut',
    'capcut_templatetrends',
    'capcut_core',
    'capcut.trends.uk1'
]

# AI Detection
AI_KEYWORDS = [
    'artificial intelligence', 'capcut ai', 'capcutai', 'ai filter', 'ai effect',
    'ai generated', 'ai video', 'ai photo', 'ai template', 'aifilter', 'aieffect',
    'ki filter', 'ki effect', 'ki video', 'ki foto', 'ki vorlage',
    'ia filter', 'ia effect', 'ia filtro', 'ia efecto', 'ia video'
]
AI_EXCLUSIONS = ['aicover', 'aivoice', 'aiart', 'airdrop', 'air', 'hair', 'fair', 'chair', 'stairs']
AI_STANDALONE = ['ai', 'ki', 'ia']

# File paths
CANDIDATES_FILE = 'data/micro_candidates.json'

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_env_var(name: str, alternatives: list = None) -> str:
    """Get environment variable, checking alternatives."""
    value = os.environ.get(name)
    if value:
        return value
    if alternatives:
        for alt in alternatives:
            value = os.environ.get(alt)
            if value:
                return value
    return None


def load_candidates() -> dict:
    """Load candidates from JSON file."""
    if os.path.exists(CANDIDATES_FILE):
        try:
            with open(CANDIDATES_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"\u26a0\ufe0f Error loading candidates: {e}")
    return {
        "last_updated": None,
        "candidates": []
    }


def save_candidates(data: dict):
    """Save candidates to JSON file."""
    os.makedirs(os.path.dirname(CANDIDATES_FILE), exist_ok=True)
    data["last_updated"] = datetime.now(timezone.utc).isoformat()
    with open(CANDIDATES_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"\u2705 Saved {len(data['candidates'])} candidates to {CANDIDATES_FILE}")


def calculate_age_hours(create_time_iso: str) -> float:
    """Calculate age in hours from ISO timestamp."""
    try:
        # Handle various timestamp formats
        if create_time_iso.endswith('Z'):
            create_time_iso = create_time_iso[:-1] + '+00:00'
        create_time = datetime.fromisoformat(create_time_iso)
        if create_time.tzinfo is None:
            create_time = create_time.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        age_seconds = (now - create_time).total_seconds()
        return max(age_seconds / 3600, 0.1)  # Minimum 0.1 to avoid division by zero
    except Exception as e:
        print(f"\u26a0\ufe0f Error parsing timestamp {create_time_iso}: {e}")
        return 999  # Return high value to exclude


def calculate_metrics(video: dict) -> dict:
    """Calculate all metrics for a video."""
    age_hours = calculate_age_hours(video.get('createTimeISO', ''))

    share_count = video.get('shareCount', 0) or 0
    digg_count = video.get('diggCount', 0) or 0
    play_count = video.get('playCount', 0) or 0

    shares_per_hour = share_count / age_hours
    likes_per_hour = digg_count / age_hours
    views_per_hour = play_count / age_hours

    momentum = (shares_per_hour * 10) + (likes_per_hour * 3) + (views_per_hour * 0.01)

    return {
        'age_hours': round(age_hours, 1),
        'shares_per_hour': round(shares_per_hour, 1),
        'likes_per_hour': round(likes_per_hour, 1),
        'views_per_hour': int(views_per_hour),
        'momentum': int(momentum)
    }


def detect_ai(text: str) -> bool:
    """Detect if video is AI-related."""
    if not text:
        return False
    text_lower = text.lower()

    # Check explicit keywords
    for kw in AI_KEYWORDS:
        if kw in text_lower:
            return True

    # Check standalone terms with word boundaries
    for term in AI_STANDALONE:
        if re.search(rf'\b{term}\b', text_lower):
            return True

    return False


def get_priority(momentum: int, shares_per_hour: float) -> tuple:
    """Determine alert priority and color."""
    if momentum >= URGENT_MOMENTUM or shares_per_hour >= URGENT_SHARES_PER_HOUR:
        return '\U0001f525 URGENT', COLOR_URGENT
    elif momentum >= HIGH_MOMENTUM or shares_per_hour >= HIGH_SHARES_PER_HOUR:
        return '\u26a1 HIGH', COLOR_HIGH
    else:
        return '\U0001f7e1 WATCH', COLOR_WATCH


def truncate_text(text: str, max_length: int = 80) -> str:
    """Truncate text to max length."""
    if not text:
        return "(no description)"
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


def get_author_name(video: dict) -> str:
    """Extract author name from video data, handling nested structures."""
    # Try various field names
    for field in ['authorMeta_name', 'authorMeta_uniqueId', 'author_name', 'username', 'creator']:
        if field in video and video[field]:
            return str(video[field])

    # Try nested authorMeta
    author_meta = video.get('authorMeta', {})
    if isinstance(author_meta, dict):
        for field in ['name', 'uniqueId', 'nickname']:
            if field in author_meta and author_meta[field]:
                return str(author_meta[field])

    return 'Unknown'


# =============================================================================
# APIFY API FUNCTIONS
# =============================================================================

def fetch_apify_data(task_id: str, api_token: str) -> list:
    """Fetch latest data from Apify task."""
    url = f"https://api.apify.com/v2/actor-tasks/{task_id}/runs/last/dataset/items"
    headers = {"Authorization": f"Bearer {api_token}"}

    print(f"\U0001f4e1 Fetching data from Apify task: {task_id}")

    try:
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()
        data = response.json()
        print(f"\u2705 Received {len(data)} videos from Apify")
        return data
    except requests.exceptions.RequestException as e:
        print(f"\u274c Apify API error: {e}")
        return []


def flatten_dict(d: dict, parent_key: str = '', sep: str = '_') -> dict:
    """Flatten nested dictionary."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def flatten_apify_data(data: list) -> list:
    """Flatten all records in Apify data."""
    return [flatten_dict(record) if isinstance(record, dict) else record for record in data]


# =============================================================================
# DISCORD NOTIFICATION
# =============================================================================

def send_discord_alert(candidate: dict, metrics: dict, delta: float, webhook_url: str):
    """Send Discord alert for a trending video."""
    priority_label, color = get_priority(metrics['momentum'], metrics['shares_per_hour'])

    # Determine if it's AI content
    is_ai = detect_ai(candidate.get('text', ''))
    category = "\U0001f916 AI" if is_ai else "\U0001f4f1 NON-AI"

    embed = {
        "title": f"\U0001f680 TREND ALERT: BUILD NOW - {priority_label}",
        "color": color,
        "url": candidate.get('url', ''),
        "fields": [
            {"name": "Trend", "value": truncate_text(candidate.get('text', '')), "inline": False},
            {"name": "Market", "value": candidate.get('market', 'Unknown'), "inline": True},
            {"name": "Category", "value": category, "inline": True},
            {"name": "Creator", "value": candidate.get('creator', 'Unknown')[:20], "inline": True},
            {"name": "Age", "value": f"{metrics['age_hours']}h", "inline": True},
            {"name": "Momentum", "value": f"{metrics['momentum']:,}", "inline": True},
            {"name": "Shares/h", "value": f"{metrics['shares_per_hour']}", "inline": True},
            {"name": "\u0394 Shares/h", "value": f"+{delta:.1f}", "inline": True},
            {"name": "Views/h", "value": f"{metrics['views_per_hour']:,}", "inline": True}
        ],
        "footer": {"text": "TikTok Micro-Polling System v1.0"},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    payload = {"embeds": [embed]}

    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        print(f"\u2705 Discord alert sent for: {truncate_text(candidate.get('text', ''), 40)}")
    except requests.exceptions.RequestException as e:
        print(f"\u274c Discord webhook error: {e}")


def send_summary_notification(webhook_url: str, new_candidates: int, alerts_sent: int,
                              removed: int, total_tracked: int):
    """Send summary of polling run to Discord."""
    embed = {
        "title": "\U0001f4ca Micro-Polling Summary",
        "color": 3447003,  # Blue
        "fields": [
            {"name": "New Candidates", "value": str(new_candidates), "inline": True},
            {"name": "Alerts Sent", "value": str(alerts_sent), "inline": True},
            {"name": "Removed", "value": str(removed), "inline": True},
            {"name": "Total Tracked", "value": f"{total_tracked}/{MAX_CANDIDATES}", "inline": True}
        ],
        "footer": {"text": "TikTok Micro-Polling System v1.0"},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    payload = {"embeds": [embed]}

    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        print("\u2705 Summary notification sent to Discord")
    except requests.exceptions.RequestException as e:
        print(f"\u26a0\ufe0f Failed to send summary: {e}")


# =============================================================================
# CORE POLLING LOGIC
# =============================================================================

def meets_entry_criteria(metrics: dict) -> bool:
    """Check if video meets entry criteria to become a candidate."""
    return (
        metrics['age_hours'] <= ENTRY_MAX_AGE_HOURS and
        metrics['shares_per_hour'] >= ENTRY_MIN_SHARES_PER_HOUR and
        metrics['views_per_hour'] >= ENTRY_MIN_VIEWS_PER_HOUR
    )


def meets_alert_criteria(metrics: dict, delta: Optional[float]) -> bool:
    """Check if candidate meets alert criteria."""
    if delta is None:
        return False
    return (
        metrics['age_hours'] <= ALERT_MAX_AGE_HOURS and
        metrics['shares_per_hour'] >= ALERT_MIN_SHARES_PER_HOUR and
        metrics['views_per_hour'] >= ALERT_MIN_VIEWS_PER_HOUR and
        delta >= ALERT_MIN_DELTA_SHARES
    )


def should_stop_tracking(candidate: dict, metrics: dict) -> bool:
    """Check if candidate should stop being tracked."""
    # Age exceeded
    if metrics['age_hours'] > STOP_AGE_HOURS:
        return True

    # Too many consecutive negative deltas
    if candidate.get('consecutive_negative_deltas', 0) >= STOP_CONSECUTIVE_NEGATIVE_DELTAS:
        return True

    return False


def detect_market(url: str, us_urls: set, uk_urls: set) -> str:
    """Detect market for a video URL."""
    in_us = url in us_urls
    in_uk = url in uk_urls

    if in_us and in_uk:
        return "\U0001f310 BOTH"
    elif in_us:
        return "\U0001f1fa\U0001f1f8 US ONLY"
    elif in_uk:
        return "\U0001f1ec\U0001f1e7 UK ONLY"
    return "Unknown"


def process_polling_run(us_data: list, uk_data: list, webhook_url: str) -> dict:
    """Main polling logic - process data and update candidates."""

    # Flatten nested data
    us_data = flatten_apify_data(us_data)
    uk_data = flatten_apify_data(uk_data)

    # Load existing candidates
    state = load_candidates()
    candidates = state.get('candidates', [])

    # Build URL sets for market detection
    us_urls = {v.get('webVideoUrl') for v in us_data if v.get('webVideoUrl')}
    uk_urls = {v.get('webVideoUrl') for v in uk_data if v.get('webVideoUrl')}

    # Combine all videos (deduplicated by URL)
    all_videos = {}
    for video in us_data + uk_data:
        url = video.get('webVideoUrl')
        if url and url not in all_videos:
            all_videos[url] = video

    print(f"\U0001f4ca Processing {len(all_videos)} unique videos")

    # Track URLs we're already monitoring
    tracked_urls = {c['url'] for c in candidates}

    # Stats
    new_candidates_added = 0
    alerts_sent = 0
    removed_count = 0

    # Current timestamp
    now = datetime.now(timezone.utc).isoformat()

    # -------------------------------------------------------------------------
    # STEP 1: Update existing candidates
    # -------------------------------------------------------------------------
    updated_candidates = []

    for candidate in candidates:
        url = candidate['url']

        # Find current video data
        video = all_videos.get(url)
        if not video:
            # Video not in this Apify pull - keep candidate but track misses
            # Apify returns different videos each scrape, so missing is normal
            misses = candidate.get('consecutive_misses', 0) + 1
            candidate['consecutive_misses'] = misses
            if misses >= 3:
                # Only remove after 3 consecutive misses (6+ hours absent)
                print(f"\U0001f6d1 Removed (missing 3 runs): {truncate_text(candidate.get('text', ''), 30)}")
                removed_count += 1
                continue
            else:
                print(f"\u23f3 Kept candidate (miss {misses}/3): {truncate_text(candidate.get('text', ''), 30)}")
                updated_candidates.append(candidate)
                continue

        # Reset miss counter when found
        candidate['consecutive_misses'] = 0

        # Calculate current metrics
        metrics = calculate_metrics(video)

        # Calculate delta from last check
        checks = candidate.get('checks', [])
        delta = None
        if checks:
            last_shares_per_hour = checks[-1].get('shares_per_hour', 0)
            delta = metrics['shares_per_hour'] - last_shares_per_hour

        # Check if should stop tracking
        if should_stop_tracking(candidate, metrics):
            reason = "age exceeded" if metrics['age_hours'] > STOP_AGE_HOURS else "declining"
            print(f"\U0001f6d1 Stopped tracking ({reason}): {truncate_text(candidate.get('text', ''), 30)}")
            removed_count += 1
            continue

        # Update consecutive negative deltas counter
        if delta is not None and delta <= 0:
            candidate['consecutive_negative_deltas'] = candidate.get('consecutive_negative_deltas', 0) + 1
        else:
            candidate['consecutive_negative_deltas'] = 0

        # Add new check
        checks.append({
            'timestamp': now,
            'age_hours': metrics['age_hours'],
            'shares_per_hour': metrics['shares_per_hour'],
            'views_per_hour': metrics['views_per_hour'],
            'momentum': metrics['momentum'],
            'delta_shares_per_hour': delta
        })
        candidate['checks'] = checks

        # Check for alert criteria (only if not already alerted)
        if not candidate.get('alerted', False) and meets_alert_criteria(metrics, delta):
            send_discord_alert(candidate, metrics, delta, webhook_url)
            candidate['alerted'] = True
            alerts_sent += 1

        updated_candidates.append(candidate)

    # -------------------------------------------------------------------------
    # STEP 2: Find new candidates
    # -------------------------------------------------------------------------
    slots_available = MAX_CANDIDATES - len(updated_candidates)

    if slots_available > 0:
        potential_candidates = []

        for url, video in all_videos.items():
            if url in tracked_urls:
                continue

            metrics = calculate_metrics(video)

            if meets_entry_criteria(metrics):
                potential_candidates.append({
                    'video': video,
                    'metrics': metrics,
                    'url': url
                })

        # Sort by momentum (highest first)
        potential_candidates.sort(key=lambda x: x['metrics']['momentum'], reverse=True)

        # Add top candidates up to available slots
        for pc in potential_candidates[:slots_available]:
            video = pc['video']
            metrics = pc['metrics']
            url = pc['url']

            market = detect_market(url, us_urls, uk_urls)

            new_candidate = {
                'url': url,
                'first_seen': now,
                'market': market,
                'text': video.get('text', ''),
                'creator': get_author_name(video),
                'checks': [{
                    'timestamp': now,
                    'age_hours': metrics['age_hours'],
                    'shares_per_hour': metrics['shares_per_hour'],
                    'views_per_hour': metrics['views_per_hour'],
                    'momentum': metrics['momentum'],
                    'delta_shares_per_hour': None
                }],
                'consecutive_negative_deltas': 0,
                'alerted': False
            }

            updated_candidates.append(new_candidate)
            new_candidates_added += 1
            print(f"\u2795 New candidate: {truncate_text(video.get('text', ''), 40)} (momentum: {metrics['momentum']})")

    # -------------------------------------------------------------------------
    # STEP 3: Save updated state
    # -------------------------------------------------------------------------
    state['candidates'] = updated_candidates
    save_candidates(state)

    # Send summary notification (only if something happened)
    if new_candidates_added > 0 or alerts_sent > 0 or removed_count > 0:
        send_summary_notification(
            webhook_url,
            new_candidates_added,
            alerts_sent,
            removed_count,
            len(updated_candidates)
        )

    return {
        'new_candidates': new_candidates_added,
        'alerts_sent': alerts_sent,
        'removed': removed_count,
        'total_tracked': len(updated_candidates)
    }


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Main entry point for micro-polling."""
    print("=" * 60)
    print("\U0001f680 TikTok Micro-Polling System v1.0")
    print(f"\u23f0 Run started: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    # Get environment variables (check multiple possible names)
    apify_token = get_env_var('APIFY_TOKEN')
    discord_webhook = get_env_var('DISCORD_WEBHOOK')

    if not apify_token:
        print("\u274c APIFY_TOKEN not set")
        return 1

    if not discord_webhook:
        print("\u274c DISCORD_WEBHOOK not set")
        return 1

    # Get task IDs (check multiple possible names for compatibility)
    us_task_id = get_env_var('US_VIDEO_TASK_ID', ['APIFY_US_TASK_ID', 'US_TASK_ID'])
    uk_task_id = get_env_var('UK_VIDEO_TASK_ID', ['APIFY_UK_TASK_ID', 'UK_TASK_ID'])

    if not us_task_id and not uk_task_id:
        print("\u274c No task IDs configured")
        print("   Set US_VIDEO_TASK_ID and/or UK_VIDEO_TASK_ID")
        return 1

    print(f"\U0001f4cb US Task ID: {us_task_id or 'Not set'}")
    print(f"\U0001f4cb UK Task ID: {uk_task_id or 'Not set'}")

    # Fetch data from Apify
    us_data = []
    uk_data = []

    if us_task_id:
        us_data = fetch_apify_data(us_task_id, apify_token)

    if uk_task_id:
        uk_data = fetch_apify_data(uk_task_id, apify_token)

    if not us_data and not uk_data:
        print("\u274c No data received from Apify")
        return 1

    # Process the data
    results = process_polling_run(us_data, uk_data, discord_webhook)

    print("\n" + "=" * 60)
    print("\U0001f4ca POLLING COMPLETE")
    print(f"   New candidates: {results['new_candidates']}")
    print(f"   Alerts sent: {results['alerts_sent']}")
    print(f"   Removed: {results['removed']}")
    print(f"   Total tracked: {results['total_tracked']}/{MAX_CANDIDATES}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())
