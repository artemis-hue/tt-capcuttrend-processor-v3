#!/usr/bin/env python3
"""
APIFY DATA FETCHER
Fetches TikTok data from Apify API
INCLUDES: flatten_dict() for nested JSON handling
"""

import os
import requests
import json


def flatten_dict(d, parent_key='', sep='_'):
    """
    CRITICAL FUNCTION: Flatten nested dictionaries from Apify API.
    
    Converts: {"authorMeta": {"name": "user123"}}
    To:       {"authorMeta_name": "user123"}
    
    Without this, pandas creates a column 'authorMeta' containing a dict,
    and the processor can't find 'authorMeta_name' for author detection.
    """
    items = []
    if not isinstance(d, dict):
        return d
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def flatten_apify_data(data_list):
    """
    Flatten all records in Apify response.
    Each record may contain nested objects like authorMeta, musicMeta, etc.
    """
    if not data_list:
        return []
    
    flattened = []
    for record in data_list:
        if isinstance(record, dict):
            flattened.append(flatten_dict(record))
        else:
            flattened.append(record)
    return flattened


def fetch_task_data(task_id, api_token):
    """Fetch latest data from an Apify task and flatten nested JSON."""
    if not task_id or not api_token:
        return None
    
    url = f"https://api.apify.com/v2/actor-tasks/{task_id}/runs/last/dataset/items"
    headers = {"Authorization": f"Bearer {api_token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=120)
        response.raise_for_status()
        data = response.json()
        raw_data = data if isinstance(data, list) else []
        
        # CRITICAL: Flatten nested JSON before returning
        flattened = flatten_apify_data(raw_data)
        print(f"    Fetched {len(raw_data)} records, flattened to columns")
        
        # Debug: Show sample column names to verify flattening worked
        if flattened:
            sample_keys = list(flattened[0].keys())[:10]
            print(f"    Sample columns: {sample_keys}")
        
        return flattened
    except Exception as e:
        print(f"  Error fetching task {task_id}: {e}")
        return None


def fetch_all_data():
    """Fetch all required data from Apify."""
    api_token = os.environ.get('APIFY_TOKEN')
    
    if not api_token:
        print("  WARNING: APIFY_TOKEN not set!")
        return None, None, None, None
    
    # Task IDs from environment
    us_video_task = os.environ.get('US_VIDEO_TASK_ID')
    uk_video_task = os.environ.get('UK_VIDEO_TASK_ID')
    us_music_task = os.environ.get('US_MUSIC_TASK_ID')
    uk_music_task = os.environ.get('UK_MUSIC_TASK_ID')
    
    print(f"  Fetching US videos...")
    us_data = fetch_task_data(us_video_task, api_token)
    
    print(f"  Fetching UK videos...")
    uk_data = fetch_task_data(uk_video_task, api_token)
    
    # Music tasks are optional
    us_music = None
    uk_music = None
    
    if us_music_task:
        print(f"  Fetching US music...")
        us_music = fetch_task_data(us_music_task, api_token)
    
    if uk_music_task:
        print(f"  Fetching UK music...")
        uk_music = fetch_task_data(uk_music_task, api_token)
    
    return us_data, uk_data, us_music, uk_music
