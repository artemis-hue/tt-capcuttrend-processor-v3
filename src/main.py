#!/usr/bin/env python3
"""
TIKTOK AUTOMATION MAIN
Version: 5.6.0 - Added Google Drive + Dashboard Integration
Changes from 5.4.0:
  - Added Google Drive upload for all output files
  - Added Google Sheets dashboard auto-update
  - Added dashboard_payload.json generation for dashboard sync
  - Discord notification now includes Drive folder link
  - All existing v3.3.0 + v3.5.0 functionality preserved
"""

import os
import sys
import json

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from apify_fetcher import fetch_all_data
from daily_processor import process_data, load_yesterday_cache, save_today_cache, calculate_metrics
from discord_notify import send_discord_notification
from v35_enhancements import integrate_with_daily_processor, generate_daily_briefing
from seasonal_calendar import get_seasonal_alerts, format_seasonal_for_discord, format_seasonal_for_summary, format_seasonal_for_enhanced
import pandas as pd


def run_v35_enhancements(us_data, uk_data, yesterday_us, yesterday_uk, output_dir, cache_dir):
    """
    Run v3.5.0 enhanced analytics: velocity predictions, competitor analysis,
    variant allocation, and stop rules.
    
    Returns dict of generated file paths, or empty dict on failure.
    """
    try:
        from v35_enhancements import integrate_with_daily_processor
    except ImportError as e:
        print(f"  WARNING: v3.5.0 enhancements not available: {e}")
        print("  Continuing with standard files only.")
        return {}
    
    print("\n[Step 3b] Running v3.5.0 Enhanced Analytics...")
    
    # Convert raw data to DataFrames with calculated metrics
    us_df = pd.DataFrame(us_data) if us_data else pd.DataFrame()
    uk_df = pd.DataFrame(uk_data) if uk_data else pd.DataFrame()
    
    if len(us_df) > 0:
        us_df = us_df.drop_duplicates(subset=['webVideoUrl'], keep='first')
        us_df = calculate_metrics(us_df)
        from daily_processor import get_author_name, detect_ai, calculate_status, calculate_build_now
        us_df['author'] = us_df.apply(get_author_name, axis=1)
        us_df['AI_CATEGORY'] = us_df.get('text', pd.Series([''])).apply(detect_ai)
        us_df = calculate_status(us_df, yesterday_us)
        us_df['BUILD_NOW'] = us_df.apply(calculate_build_now, axis=1)
        uk_urls = set(pd.DataFrame(uk_data)['webVideoUrl']) if uk_data else set()
        us_df['Market'] = us_df['webVideoUrl'].apply(
            lambda u: '🌐 BOTH' if u in uk_urls else '🇺🇸 US ONLY'
        )
        if 'status' in us_df.columns and 'acceleration_status' not in us_df.columns:
            us_df['acceleration_status'] = us_df['status']
    
    if len(uk_df) > 0:
        uk_df = uk_df.drop_duplicates(subset=['webVideoUrl'], keep='first')
        uk_df = calculate_metrics(uk_df)
        from daily_processor import get_author_name, detect_ai, calculate_status, calculate_build_now
        uk_df['author'] = uk_df.apply(get_author_name, axis=1)
        uk_df['AI_CATEGORY'] = uk_df.get('text', pd.Series([''])).apply(detect_ai)
        uk_df = calculate_status(uk_df, yesterday_uk)
        uk_df['BUILD_NOW'] = uk_df.apply(calculate_build_now, axis=1)
        us_urls = set(pd.DataFrame(us_data)['webVideoUrl']) if us_data else set()
        uk_df['Market'] = uk_df['webVideoUrl'].apply(
            lambda u: '🌐 BOTH' if u in us_urls else '🇬🇧 UK ONLY'
        )
        if 'status' in uk_df.columns and 'acceleration_status' not in uk_df.columns:
            uk_df['acceleration_status'] = uk_df['status']
    
    yesterday_us_df = None
    yesterday_uk_df = None
    if yesterday_us:
        yesterday_us_df = pd.DataFrame(yesterday_us)
    if yesterday_uk:
        yesterday_uk_df = pd.DataFrame(yesterday_uk)
    
    try:
        enhanced_files = integrate_with_daily_processor(
            us_data=us_df,
            uk_data=uk_df,
            yesterday_us=yesterday_us_df,
            yesterday_uk=yesterday_uk_df,
            two_days_us=None,
            two_days_uk=None,
            output_dir=output_dir
        )
        
        if enhanced_files:
            print(f"  ✅ Generated {len(enhanced_files)} enhanced files:")
            for key, path in enhanced_files.items():
                print(f"    {key}: {os.path.basename(path)}")
        else:
            print("  ⚠️ No enhanced files generated (possibly empty data)")
        
        return enhanced_files
        
    except Exception as e:
        print(f"  ❌ v3.5.0 enhancement error: {e}")
        import traceback
        traceback.print_exc()
        print("  Continuing with standard files only.")
        return {}


def generate_dashboard_payload(us_data, uk_data, yesterday_us, yesterday_uk, stats, output_dir, cache_dir):
    """
    Generate dashboard_payload.json for Google Sheets dashboard updates.
    This file is read by update_dashboard.py to push data to the live Sheet.
    """
    from datetime import datetime
    from daily_processor import (get_author_name, detect_ai, calculate_metrics,
                                  calculate_status, calculate_build_now,
                                  calculate_tutorial_trigger, YOUR_ACCOUNTS,
                                  COMPETITOR_ACCOUNTS)
    
    print("\n[Step 5b] Generating dashboard payload...")
    
    payload = {
        'opportunity_matrix': [],
        'competitor_gaps': [],
        'model_summary': {},
        'my_performance': [],
        'seasonal_alerts': [],
        'new_templates': [],
    }
    
    try:
        # Generate seasonal alerts for today
        from datetime import date as date_cls
        seasonal_alerts = get_seasonal_alerts(date_cls.today())
        payload['seasonal_alerts'] = seasonal_alerts
        if seasonal_alerts:
            print(f"  📅 {len(seasonal_alerts)} seasonal alerts active:")
            for sa in seasonal_alerts[:3]:
                print(f"     {sa['priority']} {sa['emoji']} {sa['event']} — {sa['timing']}")
        
        # Build MY_PERFORMANCE data for dashboard
        us_df = pd.DataFrame(us_data) if us_data else pd.DataFrame()
        uk_df = pd.DataFrame(uk_data) if uk_data else pd.DataFrame()
        
        for df, market_label in [(us_df, 'US'), (uk_df, 'UK')]:
            if len(df) == 0:
                continue
            df = df.drop_duplicates(subset=['webVideoUrl'], keep='first')
            df = calculate_metrics(df)
            df['author'] = df.apply(get_author_name, axis=1)
            df['AI_CATEGORY'] = df.get('text', pd.Series([''])).apply(detect_ai)
            
            # Find YOUR posts
            your_mask = df['author'].str.lower().isin([a.lower() for a in YOUR_ACCOUNTS])
            your_posts = df[your_mask]
            
            for _, row in your_posts.iterrows():
                trigger, urgency, reason = calculate_tutorial_trigger(row)
                payload['my_performance'].append({
                    'Account': str(row.get('author', '')),
                    'Trend': str(row.get('text', ''))[:60],
                    'Age': f"{round(row.get('age_hours', 0), 1)}h",
                    'Momentum': int(row.get('momentum_score', 0)),
                    'Status': str(row.get('status', '')),
                    'Market': market_label,
                    'Views/h': int(row.get('views_per_hour', 0)),
                    'Shares/h': round(row.get('shares_per_hour', 0), 1),
                    'BUILD_NOW': str(row.get('BUILD_NOW', '')),
                    'TikTok URL': str(row.get('webVideoUrl', '')),
                    'TUTORIAL_TRIGGER': trigger,
                    'URGENCY': urgency,
                    'Trigger Reason': reason,
                    'AI_CATEGORY': str(row.get('AI_CATEGORY', '')),
                })
            
            # Find COMPETITOR posts for gap analysis
            comp_mask = df['author'].str.lower().isin([a.lower() for a in COMPETITOR_ACCOUNTS])
            comp_posts = df[comp_mask]
            
            for _, row in comp_posts.iterrows():
                # Check if you also posted this trend (by URL match)
                url = row.get('webVideoUrl', '')
                you_also = url in set(your_posts.get('webVideoUrl', []))
                
                payload['competitor_gaps'].append({
                    'competitor': str(row.get('author', '')),
                    'trend_text': str(row.get('text', ''))[:60],
                    'competitor_momentum': int(row.get('momentum_score', 0)),
                    'your_momentum': 0,
                    'competitor_shares_h': round(row.get('shares_per_hour', 0), 1),
                    'market': market_label,
                    'gap_type': 'BOTH_CAUGHT' if you_also else 'MISSED_BY_YOU',
                    'hours_behind': '',
                    'estimated_missed_revenue': round(row.get('momentum_score', 0) / 1000 * 5, 2) if not you_also else 0,
                    'ai_category': str(row.get('AI_CATEGORY', '')),
                    'trend_url': str(row.get('webVideoUrl', '')),
                })
        
        # New templates = YOUR posts that could be added to REVENUE_TRACKER
        payload['new_templates'] = payload['my_performance']
        
        # Save payload
        payload_path = os.path.join(cache_dir, 'dashboard_payload.json')
        with open(payload_path, 'w') as f:
            json.dump(payload, f, default=str)
        
        print(f"  ✅ Dashboard payload saved: {len(payload['my_performance'])} MY_PERFORMANCE rows")
        print(f"     {len(payload['competitor_gaps'])} competitor gap entries")
        
    except Exception as e:
        print(f"  ❌ Dashboard payload error: {e}")
        import traceback
        traceback.print_exc()
    
    return payload


def upload_to_google_drive(output_dir):
    """Upload output files to Google Drive (if credentials available)."""
    has_oauth2 = all([
        os.environ.get('GOOGLE_CLIENT_ID', ''),
        os.environ.get('GOOGLE_CLIENT_SECRET', ''),
        os.environ.get('GOOGLE_REFRESH_TOKEN', ''),
    ])
    has_service_account = bool(os.environ.get('GOOGLE_CREDENTIALS', ''))
    drive_folder = os.environ.get('DRIVE_FOLDER_ID', '')
    
    if not (has_oauth2 or has_service_account) or not drive_folder:
        print("  ⚠️ Google Drive not configured")
        print("  Skipping Drive upload — files available as GitHub artifacts")
        return None
    
    try:
        from upload_drive import main as upload_main
        upload_main()
        return f"https://drive.google.com/drive/folders/{drive_folder}"
    except ImportError:
        print("  ⚠️ upload_drive.py not found — skipping Drive upload")
        return None
    except Exception as e:
        print(f"  ❌ Drive upload error: {e}")
        import traceback
        traceback.print_exc()
        return None


def update_google_dashboard(cache_dir):
    """Update Google Sheets dashboard (if credentials available)."""
    has_oauth2 = all([
        os.environ.get('GOOGLE_CLIENT_ID', ''),
        os.environ.get('GOOGLE_CLIENT_SECRET', ''),
        os.environ.get('GOOGLE_REFRESH_TOKEN', ''),
    ])
    has_service_account = bool(os.environ.get('GOOGLE_CREDENTIALS', ''))
    sheet_id = os.environ.get('DASHBOARD_SHEET_ID', '')
    
    if not (has_oauth2 or has_service_account) or not sheet_id:
        print("  ⚠️ Dashboard not configured")
        print("  Skipping dashboard update")
        return False
    
    try:
        from update_dashboard import main as dashboard_main
        dashboard_main()
        return True
    except ImportError:
        print("  ⚠️ update_dashboard.py not found — skipping dashboard update")
        return False
    except Exception as e:
        print(f"  ❌ Dashboard update error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 50)
    print("TikTok Daily Processor v5.5.0")
    print("  Standard processing: v3.3.0")
    print("  Enhanced analytics:  v3.5.0")
    print("  Dashboard + Drive:   v3.6.0")
    print("=" * 50)
    
    # Directories
    output_dir = os.environ.get('OUTPUT_DIR', 'output')
    cache_dir = os.environ.get('CACHE_DIR', 'data')
    
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(cache_dir, exist_ok=True)
    
    print(f"\nOutput directory: {output_dir}")
    print(f"Cache directory: {cache_dir}")
    
    # Step 1: Fetch data from Apify
    print("\n[Step 1] Fetching data from Apify...")
    us_data, uk_data, us_music, uk_music = fetch_all_data()
    
    if not us_data and not uk_data:
        print("ERROR: No data fetched from Apify!")
        sys.exit(1)
    
    print(f"  US videos: {len(us_data) if us_data else 0}")
    print(f"  UK videos: {len(uk_data) if uk_data else 0}")
    print(f"  US music: {len(us_music) if us_music else 0}")
    print(f"  UK music: {len(uk_music) if uk_music else 0}")
    
    # Step 2: Load yesterday's cache
    print("\n[Step 2] Loading yesterday's cache...")
    yesterday_us, yesterday_uk = load_yesterday_cache(cache_dir)
    
    if yesterday_us and yesterday_uk:
        print(f"  Cache found! US: {len(yesterday_us)}, UK: {len(yesterday_uk)} records")
    else:
        print("  No cache found - all statuses will be NEW")
    
    # Step 3: Process data (standard v3.3.0 files)
    print("\n[Step 3] Processing data (standard files)...")
    stats = process_data(
        us_data, uk_data, 
        us_music, uk_music,
        yesterday_us, yesterday_uk,
        output_dir, cache_dir
    )
    
    # Step 3b: Run v3.5.0 enhancements (non-blocking)
    enhanced_files = run_v35_enhancements(
        us_data, uk_data,
        yesterday_us, yesterday_uk,
        output_dir, cache_dir
    )
    
    if enhanced_files:
        stats['enhanced_files'] = len(enhanced_files)
    
    # Step 3c: Generate daily briefing and append to SUMMARY_REPORT
    print("\n[Step 3c] Generating daily briefing...")
    try:
        combined_df = pd.concat(
            [df for df in [
                pd.DataFrame(us_data) if us_data else pd.DataFrame(),
                pd.DataFrame(uk_data) if uk_data else pd.DataFrame()
            ] if len(df) > 0],
            ignore_index=True
        )
        
        if len(combined_df) > 0:
            combined_df = combined_df.drop_duplicates(subset=['webVideoUrl'], keep='first')
            combined_df = calculate_metrics(combined_df)
            from daily_processor import get_author_name, detect_ai, calculate_status, calculate_build_now
            combined_df['author'] = combined_df.apply(get_author_name, axis=1)
            combined_df['AI_CATEGORY'] = combined_df.get('text', pd.Series([''])).apply(detect_ai)
            
            us_urls = set(pd.DataFrame(us_data)['webVideoUrl']) if us_data else set()
            uk_urls = set(pd.DataFrame(uk_data)['webVideoUrl']) if uk_data else set()
            both_urls = us_urls & uk_urls
            combined_df['Market'] = combined_df['webVideoUrl'].apply(
                lambda u: '🌐 BOTH' if u in both_urls else '🇺🇸/🇬🇧 SINGLE'
            )
            
            combined_yesterday = None
            if yesterday_us and yesterday_uk:
                combined_yesterday = yesterday_us + yesterday_uk
            elif yesterday_us:
                combined_yesterday = yesterday_us
            elif yesterday_uk:
                combined_yesterday = yesterday_uk
            combined_df = calculate_status(combined_df, combined_yesterday)
            if 'status' in combined_df.columns:
                combined_df['acceleration_status'] = combined_df['status']
            
            yesterday_combined_df = None
            if combined_yesterday:
                yesterday_combined_df = pd.DataFrame(combined_yesterday)
            
            cache_dir_path = os.environ.get('CACHE_DIR', 'data')
            streak_cache = os.path.join(cache_dir_path, 'velocity_streak_cache.json')
            
            briefing_text = generate_daily_briefing(
                combined_df, yesterday_combined_df,
                output_dir, cache_path=streak_cache
            )
            
            from datetime import datetime
            today = datetime.now().strftime('%Y-%m-%d')
            summary_path = f"{output_dir}/SUMMARY_REPORT_{today}.txt"
            
            with open(summary_path, 'a') as f:
                f.write("\n\n")
                f.write(briefing_text)
            
            print("  ✅ Daily briefing appended to SUMMARY_REPORT")
        else:
            print("  ⚠️ No data available for briefing")
    except Exception as e:
        print(f"  ❌ Briefing generation error: {e}")
        import traceback
        traceback.print_exc()
        print("  Continuing without briefing.")
    
    # Step 4: Save today's cache for tomorrow
    print("\n[Step 4] Saving cache for tomorrow...")
    us_df = pd.DataFrame(us_data) if us_data else pd.DataFrame()
    uk_df = pd.DataFrame(uk_data) if uk_data else pd.DataFrame()
    
    if len(us_df) > 0:
        us_df = us_df.drop_duplicates(subset=['webVideoUrl'], keep='first')
        us_df = calculate_metrics(us_df)
    
    if len(uk_df) > 0:
        uk_df = uk_df.drop_duplicates(subset=['webVideoUrl'], keep='first')
        uk_df = calculate_metrics(uk_df)
    
    save_today_cache(us_df, uk_df, cache_dir)
    
    # Step 4b: Save competitor history for 7-day intel (NEW v3.6.0)
    try:
        from competitor_intel_patch import save_competitor_history
        # Need full data with author column for competitor detection
        combined_for_comp = pd.concat([df for df in [us_df, uk_df] if len(df) > 0], ignore_index=True)
        if len(combined_for_comp) > 0:
            combined_for_comp = combined_for_comp.drop_duplicates(subset=['webVideoUrl'], keep='first')
            from daily_processor import get_author_name, detect_ai
            if 'author' not in combined_for_comp.columns:
                combined_for_comp['author'] = combined_for_comp.apply(get_author_name, axis=1)
            if 'AI_CATEGORY' not in combined_for_comp.columns:
                combined_for_comp['AI_CATEGORY'] = combined_for_comp.get('text', pd.Series([''])).apply(detect_ai)
            if 'Market' not in combined_for_comp.columns:
                us_urls_set = set(us_df['webVideoUrl']) if len(us_df) > 0 else set()
                uk_urls_set = set(uk_df['webVideoUrl']) if len(uk_df) > 0 else set()
                both_urls_set = us_urls_set & uk_urls_set
                combined_for_comp['Market'] = combined_for_comp['webVideoUrl'].apply(
                    lambda u: '🌐 BOTH' if u in both_urls_set else ('🇺🇸 US ONLY' if u in us_urls_set else '🇬🇧 UK ONLY')
                )
            save_competitor_history(combined_for_comp, cache_dir)
    except Exception as e:
        print(f"  ⚠️ Could not save competitor history: {e}")
        import traceback
        traceback.print_exc()
    
    # Step 5: Send Discord notification (with seasonal alerts)
    print("\n[Step 5] Sending Discord notification...")
    seasonal_alerts = get_seasonal_alerts()
    if seasonal_alerts:
        stats['seasonal_alerts'] = seasonal_alerts
        stats['seasonal_discord_fields'] = format_seasonal_for_discord(seasonal_alerts)
    send_discord_notification(stats)
    
    # Append seasonal info to SUMMARY_REPORT if it exists
    summary_files = [f for f in os.listdir(output_dir) if f.startswith('SUMMARY_REPORT')] if os.path.exists(output_dir) else []
    if summary_files and seasonal_alerts:
        try:
            summary_path = os.path.join(output_dir, summary_files[0])
            seasonal_text = format_seasonal_for_summary(seasonal_alerts)
            with open(summary_path, 'a') as f:
                f.write(seasonal_text)
            print(f"  📅 Seasonal alerts appended to summary report")
        except Exception as e:
            print(f"  ⚠️ Could not append seasonal to summary: {e}")
    
    # Step 5b: Generate dashboard payload (NEW v3.6.0)
    generate_dashboard_payload(us_data, uk_data, yesterday_us, yesterday_uk, stats, output_dir, cache_dir)
    
    # Step 6: Upload to Google Drive (NEW v3.6.0)
    print("\n[Step 6] Uploading to Google Drive...")
    drive_url = upload_to_google_drive(output_dir)
    if drive_url:
        stats['drive_url'] = drive_url
    
    # Step 7: Update Google Sheets Dashboard (NEW v3.6.0)
    print("\n[Step 7] Updating Google Sheets dashboard...")
    dashboard_updated = update_google_dashboard(cache_dir)
    
    # Done
    print("\n" + "=" * 50)
    print("Processing complete!")
    print("=" * 50)
    
    # Print summary
    print(f"\nSummary:")
    print(f"  Your Posts: {stats.get('your_posts', 0)}")
    print(f"  Competitor Posts: {stats.get('competitor', 0)}")
    print(f"  🔥 URGENT: {stats.get('urgent', 0)}")
    print(f"  ⚡ HIGH: {stats.get('high', 0)}")
    print(f"  🟡 WATCH: {stats.get('watch', 0)}")
    print(f"  🚀 SPIKING: {stats.get('spiking', 0)}")
    if enhanced_files:
        print(f"  📊 Enhanced files: {len(enhanced_files)}")
    if drive_url:
        print(f"  📁 Google Drive: {drive_url}")
    if dashboard_updated:
        print(f"  📊 Dashboard: Updated")


if __name__ == '__main__':
    main()
