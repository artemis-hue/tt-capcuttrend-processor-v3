#!/usr/bin/env python3
"""
DISCORD NOTIFICATION
Sends summary to Discord webhook
"""

import os
import requests
import json
from datetime import datetime


def send_discord_notification(stats):
    """Send processing summary to Discord."""
    webhook_url = os.environ.get('DISCORD_WEBHOOK')
    
    if not webhook_url:
        print("  WARNING: DISCORD_WEBHOOK not set, skipping notification")
        return
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    embed = {
        "title": f"📊 TikTok Daily Report - {today}",
        "color": 3447003,
        "fields": [
            {"name": "Your Posts", "value": str(stats.get('your_posts', 0)), "inline": True},
            {"name": "Competitor Posts", "value": str(stats.get('competitor', 0)), "inline": True},
            {"name": "🔥 URGENT", "value": str(stats.get('urgent', 0)), "inline": True},
            {"name": "⚡ HIGH", "value": str(stats.get('high', 0)), "inline": True},
            {"name": "🟡 WATCH", "value": str(stats.get('watch', 0)), "inline": True},
            {"name": "🚀 SPIKING", "value": str(stats.get('spiking', 0)), "inline": True},
            {"name": "US Fresh (72h)", "value": str(stats.get('us_fresh', 0)), "inline": True},
            {"name": "UK Fresh (72h)", "value": str(stats.get('uk_fresh', 0)), "inline": True},
        ],
        "footer": {"text": "TikTok Trend System v5.3.0"}
    }
    
    payload = {"embeds": [embed]}
    
    try:
        response = requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        response.raise_for_status()
        print("  Discord notification sent!")
    except Exception as e:
        print(f"  Discord notification failed: {e}")
