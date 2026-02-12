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


# Historical revenue data - 59 entries from TIKTOK_SYSTEM_DASHBAORD.xlsx (2026-02-12)
# Used as seed when no dashboard file exists in automated environment
SEED_REVENUE_DATA = [
    {'TikTok URL': 'https://www.tiktok.com/@7597126976427609366/video/7597126976427609366', 'Account': 'Account 1 (smaller)', 'Received ($)': 2500, 'Estimated ($)': 2500, 'US & EU3 Installs': 2184, 'ROW Installs': 3782, 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@7597399641776508163/video/7597399641776508163', 'Account': 'Account 1 (smaller)', 'Received ($)': 2500, 'Estimated ($)': 2500, 'US & EU3 Installs': 717, 'ROW Installs': 1984, 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@7597123284848610582/video/7597123284848610582', 'Account': 'Account 1 (smaller)', 'Received ($)': 2500, 'Estimated ($)': 2500, 'US & EU3 Installs': 1196, 'ROW Installs': 1554, 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@7597924302243007766/video/7597924302243007766', 'Account': 'Account 1 (smaller)', 'Received ($)': 2500, 'Estimated ($)': 2500, 'US & EU3 Installs': 671, 'ROW Installs': 1269, 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@7597114246433869078/video/7597114246433869078', 'Account': 'Account 1 (smaller)', 'Received ($)': 324, 'Estimated ($)': 324, 'US & EU3 Installs': 49, 'ROW Installs': 79, 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@7597805299315068182/video/7597805299315068182', 'Account': 'Account 1 (smaller)', 'Received ($)': 106, 'Estimated ($)': 106, 'US & EU3 Installs': 13, 'ROW Installs': 41, 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@7597084269701270806/video/7597084269701270806', 'Account': 'Account 1 (smaller)', 'Received ($)': 314, 'Estimated ($)': 314, 'US & EU3 Installs': 47, 'ROW Installs': 79, 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@7597064708012920067/video/7597064708012920067', 'Account': 'Account 1 (smaller)', 'Received ($)': 2, 'Estimated ($)': 2, 'US & EU3 Installs': 0, 'ROW Installs': 2, 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@7599032518100241686/video/7599032518100241686', 'Account': 'Account 1 (smaller)', 'Received ($)': 3, 'Estimated ($)': 3, 'US & EU3 Installs': 0, 'ROW Installs': 3, 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@7597362819398503702/video/7597362819398503702', 'Account': 'Account 1 (smaller)', 'Received ($)': 5, 'Estimated ($)': 5, 'US & EU3 Installs': 1, 'ROW Installs': 0, 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@7597795533490507030/video/7597795533490507030', 'Account': 'Account 1 (smaller)', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@7597363566458539286/video/7597363566458539286', 'Account': 'Account 1 (smaller)', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@7597171707987709206/video/7597171707987709206', 'Account': 'Account 1 (smaller)', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@7591292533720878358/video/7591292533720878358', 'Account': 'Account 1 (smaller)', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@7597796013792939286/video/7597796013792939286', 'Account': 'Account 1 (smaller)', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@7597800531087658262/video/7597800531087658262', 'Account': 'Account 1 (smaller)', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@7597080404323028246/video/7597080404323028246', 'Account': 'Account 1 (smaller)', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@7597108883814944022/video/7597108883814944022', 'Account': 'Account 1 (smaller)', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@7603100212176997654/video/7603100212176997654', 'Account': 'Account 1 (smaller)', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@7597012528090107158/video/7597012528090107158', 'Account': 'Account 1 (smaller)', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@7597801729450577174/video/7597801729450577174', 'Account': 'Account 1 (smaller)', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@7597364619035888899/video/7597364619035888899', 'Account': 'Account 1 (smaller)', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@7590877569394773270/video/7590877569394773270', 'Account': 'Account 1 (smaller)', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@7582151219729272086/video/7582151219729272086', 'Account': 'Account 1 (smaller)', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@7581890594608336150/video/7581890594608336150', 'Account': 'Account 1 (smaller)', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@7597928583667010819/video/7597928583667010819', 'Account': 'Account 1 (smaller)', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@7582190483133238550/video/7582190483133238550', 'Account': 'Account 1 (smaller)', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@7581937222518115606/video/7581937222518115606', 'Account': 'Account 1 (smaller)', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@capcut.vorlagen101/video/7600100215269412118', 'Account': 'capcut.vorlagen101', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Trend Description': '#CapCut #aibaby\n#aitrend #capcutpioneer\n#pioneertemplate\n\nMa', 'Momentum at Detection': 733, 'Trigger Level': '🟡 WATCH', 'Market': 'US', 'AI Category': 'AI', 'Age at Detection': '317.9h', 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@artemiscc_capcut/video/7596800019433295126', 'Account': 'artemiscc_capcut', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Trend Description': '#CapCut #pioneertemplate #capcutpioneer #dancingbaby #aibaby', 'Momentum at Detection': 38, 'Market': 'US', 'AI Category': 'AI', 'Age at Detection': '531.4h', 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@capcut.vorlagen101/video/7601835249730915606', 'Account': 'capcut.vorlagen101', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Trend Description': '#CapCut #capcutpioneer #pioneertemplate #chachaslide #aifilt', 'Momentum at Detection': 54, 'Market': 'US', 'AI Category': 'AI', 'Age at Detection': '205.7h', 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@capcut.vorlagen101/video/7597546182721670422', 'Account': 'capcut.vorlagen101', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Trend Description': '#CapCut #capcutpioneer #pioneertemplate #aibaby #aitrend \n\nM', 'Momentum at Detection': 6892, 'Trigger Level': '🔥 URGENT', 'Market': 'US', 'AI Category': 'AI', 'Age at Detection': '483.1h', 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@artemiscc_capcut/video/7598494805294959894', 'Account': 'artemiscc_capcut', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Trend Description': '#CapCut #mapopo #aitrend #capcutpioneer #pioneertemplate \n\nM', 'Momentum at Detection': 335, 'Market': 'US', 'AI Category': 'AI', 'Age at Detection': '421.8h', 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@capcuttrends02/video/7597736583386762518', 'Account': 'capcuttrends02', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Trend Description': '#CapCut #mapopo #aitrend #capcutpioneer #pioneertemplate \n\nM', 'Momentum at Detection': 1879, 'Trigger Level': '⚡ HIGH', 'Market': 'US', 'AI Category': 'AI', 'Age at Detection': '470.8h', 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@capcuttemplatesai/video/7601614140414708995', 'Account': 'capcuttemplatesai', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Trend Description': '#CapCut #capcutpioneer #pioneertemplate #keepitgangsta #aida', 'Momentum at Detection': 4, 'Market': 'US', 'AI Category': 'AI', 'Age at Detection': '220.0h', 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@artemiscc_capcut/video/7601828002359430422', 'Account': 'artemiscc_capcut', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Trend Description': '#CapCut #capcutpioneer #pioneertemplate #keepitgangsta #aida', 'Momentum at Detection': 82, 'Market': 'US', 'AI Category': 'AI', 'Age at Detection': '206.2h', 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@capcuttemplatesai/video/7433474060589223201', 'Account': 'capcuttemplatesai', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Trend Description': 'Bridgerton AI Template #CapCut #aitemplate #Bridgerton #netf', 'Momentum at Detection': 0, 'Market': 'UK', 'AI Category': 'AI', 'Age at Detection': '11094.5h', 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@artemiscc_capcut/video/7596800019433295126', 'Account': 'artemiscc_capcut', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Trend Description': '#CapCut #pioneertemplate #capcutpioneer #dancingbaby #aibaby', 'Momentum at Detection': 38, 'Market': 'UK', 'AI Category': 'AI', 'Age at Detection': '531.4h', 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@artemiscc_capcut/video/7596436774478548246', 'Account': 'artemiscc_capcut', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Trend Description': '#CapCut #mapopo #aitrend #capcutpioneer #pioneertemplate \n\nM', 'Momentum at Detection': 605, 'Market': 'UK', 'AI Category': 'AI', 'Age at Detection': '554.9h', 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@capcutaistudio/video/7600069960731200790', 'Account': 'capcutaistudio', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Trend Description': '#CapCut #capcutpioneer #pioneertemplate #crippwalk #aidance ', 'Momentum at Detection': 11, 'Market': 'UK', 'AI Category': 'AI', 'Age at Detection': '319.9h', 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@capcut.vorlagen101/video/7601835249730915606', 'Account': 'capcut.vorlagen101', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Trend Description': '#CapCut #capcutpioneer #pioneertemplate #chachaslide #aifilt', 'Momentum at Detection': 54, 'Market': 'UK', 'AI Category': 'AI', 'Age at Detection': '205.7h', 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@capcut.vorlagen101/video/7600100215269412118', 'Account': 'capcut.vorlagen101', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Trend Description': '#CapCut #aibaby\n#aitrend #capcutpioneer\n#pioneertemplate\n\nMa', 'Momentum at Detection': 733, 'Trigger Level': '🟡 WATCH', 'Market': 'UK', 'AI Category': 'AI', 'Age at Detection': '317.9h', 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@capcut.vorlagen101/video/7597546182721670422', 'Account': 'capcut.vorlagen101', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Trend Description': '#CapCut #capcutpioneer #pioneertemplate #aibaby #aitrend \n\nM', 'Momentum at Detection': 6892, 'Trigger Level': '🔥 URGENT', 'Market': 'UK', 'AI Category': 'AI', 'Age at Detection': '483.1h', 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@capcuttrends02/video/7600760603992460566', 'Account': 'capcuttrends02', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Trend Description': '#CapCut #capcutpioneer #pioneertemplate #aibaby #aifilter \n\n', 'Momentum at Detection': 362, 'Market': 'UK', 'AI Category': 'AI', 'Age at Detection': '275.2h', 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@capcuttemplatesai/video/7601614140414708995', 'Account': 'capcuttemplatesai', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Trend Description': '#CapCut #capcutpioneer #pioneertemplate #keepitgangsta #aida', 'Momentum at Detection': 4, 'Market': 'UK', 'AI Category': 'AI', 'Age at Detection': '220.0h', 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@capcuttemplatesai/video/7597924302243007766', 'Account': 'capcuttemplatesai', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Trend Description': '#CapCut #mapopo #aitrend #capcutpioneer #pioneertemplate \n\nM', 'Momentum at Detection': 1239, 'Trigger Level': '🟡 WATCH', 'Market': 'UK', 'AI Category': 'AI', 'Age at Detection': '458.7h', 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@capcuttrends02/video/7597126976427609366', 'Account': 'capcuttrends02', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Trend Description': '#CapCut #mapopo #aitrend #capcutpioneer #pioneertemplate \n\nM', 'Momentum at Detection': 2695, 'Trigger Level': '🔥 URGENT', 'Market': 'UK', 'AI Category': 'AI', 'Age at Detection': '510.2h', 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@capcuttrends02/video/7597736583386762518', 'Account': 'capcuttrends02', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Trend Description': '#CapCut #mapopo #aitrend #capcutpioneer #pioneertemplate \n\nM', 'Momentum at Detection': 1879, 'Trigger Level': '⚡ HIGH', 'Market': 'UK', 'AI Category': 'AI', 'Age at Detection': '470.8h', 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@artemiscc_capcut/video/7598494805294959894', 'Account': 'artemiscc_capcut', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Trend Description': '#CapCut #mapopo #aitrend #capcutpioneer #pioneertemplate \n\nM', 'Momentum at Detection': 335, 'Market': 'UK', 'AI Category': 'AI', 'Age at Detection': '421.8h', 'Date First Seen': '2026-02-09'},
    {'TikTok URL': 'https://www.tiktok.com/@artemiscc_capcut/video/7600349631934909718', 'Account': 'artemiscc_capcut', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Trend Description': '#CapCut #aibaby\n#aitrend #capcutpioneer\n#pioneertemplate\n\nMa', 'Momentum at Detection': 96, 'Market': 'US', 'AI Category': 'AI', 'Age at Detection': '313.7h', 'Date First Seen': '2026-02-10'},
    {'TikTok URL': 'https://www.tiktok.com/@capcutaistudio/video/7601487341189975318', 'Account': 'capcutaistudio', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Trend Description': '#CapCut #capcutpioneer #pioneertemplate #aidance #aibaby\n\nAi', 'Momentum at Detection': 699, 'Trigger Level': '🟡 WATCH', 'Market': 'US', 'AI Category': 'AI', 'Age at Detection': '240.1h', 'Date First Seen': '2026-02-10'},
    {'TikTok URL': 'https://www.tiktok.com/@artemiscccapcut/video/7597737771008085270', 'Account': 'artemiscccapcut', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Trend Description': '#CapCut #mapopo #aitrend #capcutpioneer #pioneertemplate \n\nM', 'Momentum at Detection': 199, 'Market': 'US', 'AI Category': 'AI', 'Age at Detection': '482.6h', 'Date First Seen': '2026-02-10'},
    {'TikTok URL': 'https://www.tiktok.com/@capcut.vorlagen101/video/7598499844461743382', 'Account': 'capcut.vorlagen101', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Trend Description': '#CapCut #mapopo #aitrend #capcutpioneer #pioneertemplate \n\nM', 'Momentum at Detection': 727, 'Trigger Level': '🟡 WATCH', 'Market': 'US', 'AI Category': 'AI', 'Age at Detection': '433.3h', 'Date First Seen': '2026-02-10'},
    {'TikTok URL': 'https://www.tiktok.com/@capcut.vorlagen101/video/7603374540235803926', 'Account': 'capcut.vorlagen101', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Trend Description': '#CapCut #pioneertemplate #capcutpioneer #aitrend #mapopo \n\nM', 'Momentum at Detection': 463, 'Market': 'US', 'AI Category': 'AI', 'Age at Detection': '118.1h', 'Date First Seen': '2026-02-10'},
    {'TikTok URL': 'https://www.tiktok.com/@capcuttemplates833/video/7596803270442601750', 'Account': 'capcuttemplates833', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Trend Description': '#CapCut #mapopo #aitrend #capcutpioneer #pioneertemplate \n\nM', 'Momentum at Detection': 771, 'Market': 'US', 'AI Category': 'AI', 'Age at Detection': '543.1h', 'Date First Seen': '2026-02-10'},
    {'TikTok URL': 'https://www.tiktok.com/@artemiscc_capcut/video/7600349631934909718', 'Account': 'artemiscc_capcut', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Trend Description': '#CapCut #aibaby\n#aitrend #capcutpioneer\n#pioneertemplate\n\nMa', 'Momentum at Detection': 96, 'Market': 'UK', 'AI Category': 'AI', 'Age at Detection': '313.7h', 'Date First Seen': '2026-02-10'},
    {'TikTok URL': 'https://www.tiktok.com/@capcut.vorlagen101/video/7603374540235803926', 'Account': 'capcut.vorlagen101', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Trend Description': '#CapCut #pioneertemplate #capcutpioneer #aitrend #mapopo \n\nM', 'Momentum at Detection': 463, 'Market': 'UK', 'AI Category': 'AI', 'Age at Detection': '118.1h', 'Date First Seen': '2026-02-10'},
    {'TikTok URL': 'https://www.tiktok.com/@capcut.vorlagen101/video/7598499844461743382', 'Account': 'capcut.vorlagen101', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Trend Description': '#CapCut #mapopo #aitrend #capcutpioneer #pioneertemplate \n\nM', 'Momentum at Detection': 727, 'Trigger Level': '🟡 WATCH', 'Market': 'UK', 'AI Category': 'AI', 'Age at Detection': '433.3h', 'Date First Seen': '2026-02-10'},
    {'TikTok URL': 'https://www.tiktok.com/@capcuttemplatesai/video/7601515548182138134', 'Account': 'capcuttemplatesai', 'Received ($)': 0, 'Estimated ($)': 0, 'US & EU3 Installs': 0, 'ROW Installs': 0, 'Trend Description': '#CapCut #capcutpioneer #pioneertemplate #aidance #aifilter\n\n', 'Momentum at Detection': 21, 'Market': 'US', 'AI Category': 'AI', 'Age at Detection': '262.2h', 'Date First Seen': '2026-02-11'},
]


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
        yest_dedup = df_yesterday.drop_duplicates(subset=['webVideoUrl'], keep='first')
        yesterday_momentum = yest_dedup[['webVideoUrl', 'momentum_score']].copy()
        yesterday_momentum.columns = ['webVideoUrl', 'momentum_yesterday']
        df = df.merge(yesterday_momentum, on='webVideoUrl', how='left')
    else:
        df['momentum_yesterday'] = np.nan
    
    # Merge with 2-days-ago data if available
    if df_2days_ago is not None and len(df_2days_ago) > 0:
        d2_dedup = df_2days_ago.drop_duplicates(subset=['webVideoUrl'], keep='first')
        old_momentum = d2_dedup[['webVideoUrl', 'momentum_score']].copy()
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
        has_velocity_data = pd.notna(row.get('momentum_yesterday')) and row.get('momentum_yesterday') != row.get('momentum_score', 0)
        
        # Too old - 72h window closing
        if age > 60:
            return '⚠️ WINDOW CLOSING'
        
        # If we have real velocity data, use it
        if has_velocity_data:
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
        
        else:
            # No velocity data — classify on momentum + age alone
            if momentum >= 3000 and age <= 24:
                return '🔴 ACT NOW'
            if momentum >= 2000 and age <= 36:
                return '🟠 6-12H'
            if momentum >= 1000 and age <= 48:
                return '🟡 12-24H'
            if momentum >= 500:
                return '🟢 MONITOR'
            return '❌ TOO LATE'
    
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
    cache_path: str = None,
    dashboard_path: str = None
) -> str:
    """
    Create v3.6.0 Enhanced Excel file with 8 tabs:
    1. DASHBOARD - Formula-driven KPI summary
    2. OPPORTUNITY_NOW - 13-column priority build list
    3. REVENUE_TRACKER - 19-column revenue tracking (carried forward)
    4. REVENUE_INSIGHTS - Auto-calculated breakdowns
    5. COMPETITOR_VIEW - 12-column combined competitor analysis
    6. PREDICTION_LOG - Model accuracy tracking
    7. DATA_FEED - 19-column enhanced MY_PERFORMANCE
    8. COMPETITOR_INTEL - 7-day deep competitor intelligence (9 sections)
    """
    df_today = _ensure_calculated_metrics(df_today)

    # Filter to fresh content (72h) for enhanced analysis
    fresh_df = df_today[df_today['age_hours'] <= 72].copy() if 'age_hours' in df_today.columns else df_today.copy()

    # Calculate velocity predictions on fresh data
    df_with_predictions = calculate_velocity_predictions(fresh_df, df_yesterday, df_2days_ago)
    velocity_summary = create_velocity_summary(df_with_predictions, cache_path=cache_path)

    # Competitor analysis on full dataset
    competitor_gaps = analyze_competitor_gaps(df_today)
    h2h_metrics = calculate_your_vs_competitor_metrics(df_today)

    # Load existing revenue/prediction data
    existing_revenue = _load_existing_revenue(dashboard_path)
    existing_prediction_log = _load_existing_prediction_log(dashboard_path)

    # Build competitor intel (7-day deep analysis)
    try:
        from competitor_intel_patch import build_competitor_intel, build_competitor_intel_tab
        comp_cache_dir = os.path.dirname(cache_path) if cache_path else 'data'
        if not comp_cache_dir:
            comp_cache_dir = 'data'
        comp_intel = build_competitor_intel(df_today, comp_cache_dir)
        has_comp_intel = True
    except Exception as e:
        print(f"  [WARNING] Could not build competitor intel: {e}")
        comp_intel = None
        has_comp_intel = False

    # Style definitions
    header_fill = PatternFill('solid', fgColor='1F4E78')
    header_font = Font(bold=True, color='FFFFFF')
    cyan_fill = PatternFill('solid', fgColor='E0FFFF')
    thin_border = Border(left=Side(style='thin'), right=Side(style='thin'),
                         top=Side(style='thin'), bottom=Side(style='thin'))

    wb = Workbook()

    # TAB 1: DASHBOARD
    ws = wb.active
    ws.title = 'DASHBOARD'
    _build_dashboard_tab(ws, header_fill, header_font)

    # TAB 2: OPPORTUNITY_NOW (13 columns)
    ws_opp = wb.create_sheet('OPPORTUNITY_NOW')
    _build_opportunity_now_tab(ws_opp, df_with_predictions, header_fill, header_font, thin_border)

    # TAB 3: REVENUE_TRACKER (19 columns)
    ws_rev = wb.create_sheet('REVENUE_TRACKER')
    _build_revenue_tracker_tab(ws_rev, existing_revenue, header_fill, header_font, thin_border)

    # TAB 4: REVENUE_INSIGHTS
    ws_ins = wb.create_sheet('REVENUE_INSIGHTS')
    _build_revenue_insights_tab(ws_ins, header_fill, header_font)

    # TAB 5: COMPETITOR_VIEW (12 columns)
    ws_comp = wb.create_sheet('COMPETITOR_VIEW')
    _build_competitor_view_tab(ws_comp, competitor_gaps, header_fill, header_font, thin_border)

    # TAB 6: PREDICTION_LOG (10 columns)
    ws_pred = wb.create_sheet('PREDICTION_LOG')
    _build_prediction_log_tab(ws_pred, df_with_predictions, df_yesterday,
                               existing_prediction_log, header_fill, header_font, thin_border)

    # TAB 7: DATA_FEED (19 columns)
    ws_feed = wb.create_sheet('DATA_FEED')
    _build_data_feed_tab(ws_feed, df_today, header_fill, header_font, thin_border, cyan_fill)

    # TAB 8: COMPETITOR_INTEL (7-day deep intelligence)
    if has_comp_intel and comp_intel is not None:
        ws_intel = wb.create_sheet('COMPETITOR_INTEL')
        build_competitor_intel_tab(ws_intel, comp_intel, header_fill, header_font, thin_border)

    wb.save(output_path)
    return output_path


# =============================================================================
# v3.6.0 TAB BUILDERS
# =============================================================================

def _build_dashboard_tab(ws, header_fill, header_font):
    section_fill = PatternFill('solid', fgColor='E8F4FD')  # Light blue for section headers
    kpi_fill = PatternFill('solid', fgColor='F5F5F5')  # Light grey for KPI cells
    red_kpi = PatternFill('solid', fgColor='FFE0E0')  # Light red for urgent KPIs
    green_kpi = PatternFill('solid', fgColor='E0FFE0')  # Light green for positive KPIs
    yellow_kpi = PatternFill('solid', fgColor='FFFDE0')  # Light yellow for seasonal
    
    ws['A1'] = '\U0001f4ca TIKTOK TREND SYSTEM \u2014 DAILY DASHBOARD'
    ws['A1'].font = Font(bold=True, size=14)
    ws['A1'].fill = PatternFill('solid', fgColor='1F4E78')
    ws['A1'].font = Font(bold=True, size=14, color='FFFFFF')
    ws.merge_cells('A1:L1')
    ws['A2'] = '=TEXT(NOW(),"dddd, dd mmmm yyyy \u2014 HH:MM")'
    ws['A2'].font = Font(italic=True, color='666666')
    ws.merge_cells('A2:F2')

    # REVENUE section
    ws['A4'] = '\U0001f4b0 REVENUE'
    ws['A4'].font = Font(bold=True, size=12, color='1F4E78')
    for col in range(1, 13):
        ws.cell(row=4, column=col).fill = section_fill
    ws.merge_cells('A4:L4')
    for i, lbl in enumerate(['Total Revenue', '', 'Templates at Cap', '', 'Hit Rate', '', 'Avg Rev/Template', '', 'Outstanding'], 1):
        ws.cell(row=5, column=i, value=lbl).font = Font(bold=True, size=9, color='666666')
    ws['A6'] = '=SUMPRODUCT(REVENUE_TRACKER!E2:E1000)'
    ws['A6'].number_format = '$#,##0'
    ws['A6'].font = Font(bold=True, size=16)
    ws['A6'].fill = green_kpi
    ws['C6'] = '=COUNTIF(REVENUE_TRACKER!E2:E1000,">=2500")'
    ws['C6'].font = Font(bold=True, size=16)
    ws['E6'] = '=IFERROR(COUNTIF(REVENUE_TRACKER!E2:E1000,">0")/COUNTA(REVENUE_TRACKER!A2:A1000),0)'
    ws['E6'].number_format = '0%'
    ws['E6'].font = Font(bold=True, size=16)
    ws['G6'] = '=IFERROR(AVERAGEIF(REVENUE_TRACKER!E2:E1000,">0"),0)'
    ws['G6'].number_format = '$#,##0'
    ws['G6'].font = Font(bold=True, size=16)
    ws['I6'] = '=SUMPRODUCT(REVENUE_TRACKER!E2:E1000)-SUMPRODUCT(REVENUE_TRACKER!D2:D1000)'
    ws['I6'].number_format = '$#,##0'
    ws['I6'].font = Font(bold=True, size=16)

    # TODAY section
    ws['A9'] = '\U0001f3af TODAY'
    ws['A9'].font = Font(bold=True, size=12, color='1F4E78')
    for col in range(1, 13):
        ws.cell(row=9, column=col).fill = section_fill
    ws.merge_cells('A9:L9')
    for i, lbl in enumerate(['Build NOW', '', 'Build Today', '', 'URGENT', '', 'SPIKING', '', 'Your Posts'], 1):
        ws.cell(row=10, column=i, value=lbl).font = Font(bold=True, size=9, color='666666')
    ws['A11'] = '=COUNTIF(OPPORTUNITY_NOW!B2:B100,"*BUILD_IMMEDIATELY*")'
    ws['A11'].font = Font(bold=True, size=16, color='FF0000')
    ws['A11'].fill = red_kpi
    ws['C11'] = '=COUNTIF(OPPORTUNITY_NOW!B2:B100,"*BUILD_TODAY*")'
    ws['C11'].font = Font(bold=True, size=16, color='FF8C00')
    ws['C11'].fill = PatternFill('solid', fgColor='FFF3E0')
    ws['E11'] = '=COUNTIF(DATA_FEED!L2:L5000,"*URGENT*")'
    ws['E11'].font = Font(bold=True, size=16)
    ws['E11'].fill = kpi_fill
    ws['G11'] = '=COUNTIF(DATA_FEED!F2:F5000,"*SPIKING*")'
    ws['G11'].font = Font(bold=True, size=16)
    ws['G11'].fill = kpi_fill
    ws['I11'] = '=COUNTA(DATA_FEED!B2:B5000)'
    ws['I11'].font = Font(bold=True, size=16)
    ws['I11'].fill = kpi_fill

    # COMPETITOR & MODEL section
    ws['A14'] = '\u2694\ufe0f COMPETITOR & MODEL'
    ws['A14'].font = Font(bold=True, size=12, color='1F4E78')
    for col in range(1, 13):
        ws.cell(row=14, column=col).fill = section_fill
    ws.merge_cells('A14:L14')
    for i, lbl in enumerate(['You Missed', '', 'Competitor Posts', '', 'Prediction Accuracy', '', 'Model Bias'], 1):
        ws.cell(row=15, column=i, value=lbl).font = Font(bold=True, size=9, color='666666')
    ws['A16'] = '=COUNTIF(COMPETITOR_VIEW!H2:H500,"MISSED_BY_YOU")'
    ws['A16'].font = Font(bold=True, size=16, color='FF0000')
    ws['A16'].fill = red_kpi
    ws['C16'] = '=COUNTA(COMPETITOR_VIEW!A2:A500)'
    ws['C16'].font = Font(bold=True, size=16)
    ws['C16'].fill = kpi_fill
    ws['E16'] = '=IFERROR(INDEX(PREDICTION_LOG!C2:C100,MATCH(9.99E+307,PREDICTION_LOG!C2:C100)),0)'
    ws['E16'].number_format = '0%'
    ws['E16'].font = Font(bold=True, size=16)
    ws['E16'].fill = kpi_fill
    ws['G16'] = '=IFERROR(INDEX(PREDICTION_LOG!D2:D100,MATCH(9.99E+307,PREDICTION_LOG!D2:D100)),"N/A")'
    ws['G16'].font = Font(bold=True, size=16)
    ws['G16'].fill = kpi_fill

    # SEASONAL
    ws['A19'] = '\U0001f4c5 SEASONAL ALERTS'
    ws['A19'].font = Font(bold=True, size=12, color='1F4E78')
    for col in range(1, 13):
        ws.cell(row=19, column=col).fill = yellow_kpi
    ws.merge_cells('A19:L19')
    try:
        from seasonal_calendar import get_seasonal_alerts
        from datetime import date
        alerts = get_seasonal_alerts(date.today())
        if alerts:
            for i, a in enumerate(alerts[:3]):
                ws.cell(row=20+i, column=1, value=f"{a.get('emoji','')} {a.get('event','')} \u2014 {a.get('timing','')}")
        else:
            ws['A20'] = 'No seasonal events coming up'
    except Exception:
        ws['A20'] = 'Seasonal calendar not available'

    # HOW TO USE
    ws['A25'] = '\U0001f4cb HOW TO USE THIS DASHBOARD'
    ws['A25'].font = Font(bold=True, size=12, color='1F4E78')
    for col in range(1, 13):
        ws.cell(row=25, column=col).fill = section_fill
    ws.merge_cells('A25:L25')
    instructions = [
        '1. Open OPPORTUNITY_NOW tab > build the red items first',
        '2. Check COMPETITOR_VIEW > look for MISSED_BY_YOU with high momentum',
        '3. After building templates, fill in REVENUE_TRACKER with your template links',
        '4. When revenue comes in, update the Estimated and Received columns',
        '5. REVENUE_INSIGHTS auto-calculates which signals predict revenue best',
        '6. PREDICTION_LOG tracks model accuracy > check for tuning suggestions',
    ]
    for i, txt in enumerate(instructions):
        ws.cell(row=26+i, column=1, value=txt).font = Font(size=10)
    for col in range(1, 13):
        from openpyxl.utils import get_column_letter
        ws.column_dimensions[get_column_letter(col)].width = 16


def _build_opportunity_now_tab(ws, df_pred, header_fill, header_font, thin_border):
    headers = ['Priority', 'Build Priority', 'Time Zone', 'Time Remaining',
               'Trend', 'Creator', 'Momentum', 'Opportunity Score', 'Age',
               'Market', 'Seasonal', 'Previously Built', 'URL']
    for ci, h in enumerate(headers, 1):
        c = ws.cell(row=1, column=ci, value=h)
        c.fill = header_fill
        c.font = header_font
        c.alignment = Alignment(horizontal='center')

    # Filter to actionable
    actionable = df_pred[
        (df_pred['action_window'].str.contains('ACT NOW|6-12H', na=False)) &
        (df_pred['age_hours'] <= 48) & (df_pred['momentum_score'] >= 500)
    ].copy()
    
    # Fallback 1: Expand to include 12-24H and MONITOR with decent momentum
    if len(actionable) == 0:
        actionable = df_pred[
            (df_pred['action_window'].str.contains('ACT NOW|6-12H|12-24H|MONITOR', na=False)) &
            (df_pred['age_hours'] <= 60) & (df_pred['momentum_score'] >= 300)
        ].nlargest(20, 'momentum_score').copy()
    
    # Fallback 2: If velocity data is missing (all PEAKED/TOO LATE), use pure momentum
    if len(actionable) == 0:
        actionable = df_pred[
            (df_pred['age_hours'] <= 60) & (df_pred['momentum_score'] >= 300)
        ].nlargest(20, 'momentum_score').copy()
    
    # Fallback 3: Just show top 20 by momentum regardless
    if len(actionable) == 0:
        actionable = df_pred[
            df_pred['age_hours'] <= 72
        ].nlargest(20, 'momentum_score').copy()

    # Exclude tracked accounts
    if 'author' in actionable.columns and len(actionable) > 0:
        all_tracked = [a.lower() for a in YOUR_ACCOUNTS + COMPETITOR_ACCOUNTS]
        actionable = actionable[~actionable['author'].str.lower().isin(all_tracked)]

    # Opportunity score
    if len(actionable) > 0:
        vel_fill = actionable['velocity'].fillna(0)
        age_factor = (72 - actionable['age_hours'].clip(0, 72)) / 72
        actionable['opportunity_score'] = (
            actionable['momentum_score'] * 0.4 + vel_fill.clip(lower=0) * 2 +
            actionable['predicted_24h'].fillna(actionable['momentum_score']) * 0.3 +
            age_factor * 1000
        ).astype(int)
        actionable = actionable.nlargest(20, 'opportunity_score')

    now_hour = datetime.utcnow().hour
    is_prime = 8 <= now_hour <= 22
    tz_label = '\U0001f7e2 PRIME' if is_prime else 'OFF_PEAK'
    seasonal_text = ''
    try:
        from seasonal_calendar import get_seasonal_alerts
        from datetime import date
        alerts = get_seasonal_alerts(date.today())
        if alerts: seasonal_text = alerts[0].get('event', '')
    except Exception: pass

    for ri, (_, row) in enumerate(actionable.iterrows(), 2):
        aw = str(row.get('action_window', ''))
        is_act_now = 'ACT NOW' in aw
        hours_left = max(0, 72 - row.get('age_hours', 0))
        time_rem = f"{hours_left:.0f}h of prime time left" if is_prime else f"{hours_left:.0f}h remaining"
        vals = [
            ri - 1,
            '\U0001f534 BUILD_IMMEDIATELY' if is_act_now else '\U0001f7e0 BUILD_TODAY',
            tz_label, time_rem,
            str(row.get('text', ''))[:60] if pd.notna(row.get('text')) else '',
            str(row.get('author', ''))[:20] if pd.notna(row.get('author')) else '',
            int(row.get('momentum_score', 0)),
            int(row.get('opportunity_score', 0)),
            f"{row.get('age_hours', 0):.1f}h",
            str(row.get('Market', '')) if pd.notna(row.get('Market')) else '',
            seasonal_text, '',
            str(row.get('webVideoUrl', '')),
        ]
        row_color = 'FF6B6B' if is_act_now else 'FFE4B5'
        for ci, val in enumerate(vals, 1):
            c = ws.cell(row=ri, column=ci, value=_sanitize_cell(val))
            c.border = thin_border
            if ci <= 12:
                c.fill = PatternFill('solid', fgColor=row_color)
                if is_act_now: c.font = Font(bold=True)
        url_cell = ws.cell(row=ri, column=13)
        url_val = str(row.get('webVideoUrl', ''))
        if url_val.startswith('http'):
            url_cell.hyperlink = url_val
            url_cell.font = Font(color='0000FF', underline='single')

    if len(actionable) == 0:
        ws['A2'] = 'No immediate opportunities - check DASHBOARD for monitoring items'
        ws['A2'].font = Font(italic=True, color='666666')

    ws.freeze_panes = 'A2'
    for col, w in [('A',8),('B',22),('C',12),('D',25),('E',50),('F',18),('G',12),('H',16),('I',10),('J',15),('K',18),('L',15),('M',50)]:
        ws.column_dimensions[col].width = w


def _build_revenue_tracker_tab(ws, existing_revenue, header_fill, header_font, thin_border):
    headers = ['TikTok URL', 'Account', 'Template Link', 'Received ($)',
               'Estimated ($)', 'US & EU3 Installs', 'ROW Installs',
               'Total Installs', 'Rev/Install', 'At Cap?', 'Trend Description',
               'Momentum at Detection', 'Trigger Level', 'Action Window',
               'Market', 'AI Category', 'Age at Detection', 'Date First Seen', 'Notes']
    for ci, h in enumerate(headers, 1):
        c = ws.cell(row=1, column=ci, value=h)
        c.fill = header_fill
        c.font = header_font
        c.alignment = Alignment(horizontal='center')

    max_data_row = 1
    if existing_revenue is not None and len(existing_revenue) > 0:
        for ri, (_, row) in enumerate(existing_revenue.iterrows(), 2):
            for ci in range(1, 20):
                col_name = headers[ci-1] if ci <= len(headers) else ''
                val = row.get(col_name, row.iloc[ci-1] if ci-1 < len(row) else '')
                if pd.isna(val): val = ''
                ws.cell(row=ri, column=ci, value=_sanitize_cell(val)).border = thin_border
            # Formulas for calculated columns
            ws.cell(row=ri, column=8, value=f'=F{ri}+G{ri}')
            ws.cell(row=ri, column=9, value=f'=IFERROR(E{ri}/H{ri},0)')
            ws.cell(row=ri, column=9).number_format = '$#,##0.00'
            ws.cell(row=ri, column=10, value=f'=IF(E{ri}>=2500,"\u2705 CAP","")')
            max_data_row = ri

    # Add formulas for empty rows (for future user input)
    input_fill = PatternFill('solid', fgColor='FFFFE0')
    for ri in range(max_data_row + 1, max_data_row + 51):
        ws.cell(row=ri, column=8, value=f'=F{ri}+G{ri}')
        ws.cell(row=ri, column=9, value=f'=IFERROR(E{ri}/H{ri},0)')
        ws.cell(row=ri, column=9).number_format = '$#,##0.00'
        ws.cell(row=ri, column=10, value=f'=IF(E{ri}>=2500,"\u2705 CAP","")')
        for ci in [3,4,5,6,7,19]:
            ws.cell(row=ri, column=ci).fill = input_fill

    ws.freeze_panes = 'A2'
    for col, w in [('A',50),('B',20),('C',40),('D',12),('E',12),('F',15),('G',12),('H',12),('I',12),('J',10),('K',40),('R',14)]:
        ws.column_dimensions[col].width = w


def _build_revenue_insights_tab(ws, header_fill, header_font):
    ws['A1'] = '\U0001f4b0 REVENUE INSIGHTS \u2014 Auto-Calculated'
    ws['A1'].font = Font(bold=True, size=14, color='FFFFFF')
    ws['A1'].fill = PatternFill('solid', fgColor='1F4E78')
    ws.merge_cells('A1:F1')

    section_headers = ['Category', 'Templates', 'Total Revenue', 'Avg Revenue', 'Hit Rate', 'Best Template']
    alt_fill = PatternFill('solid', fgColor='F2F2F2')
    section_fill = PatternFill('solid', fgColor='E8F4FD')
    trig_colors = {'URGENT': 'FFE0E0', 'HIGH': 'FFF3E0', 'WATCH': 'FFFDE0', 'NONE': 'F5F5F5'}
    mkt_colors = {'BOTH': 'FFD700', 'US': 'E0F0FF', 'UK': 'FFE0E0'}
    cat_colors = {'AI': 'E8E0FF', 'NON-AI': 'E0FFE8'}

    # BY TRIGGER LEVEL
    ws['A3'] = 'BY TRIGGER LEVEL'
    ws['A3'].font = Font(bold=True, size=12)
    ws['A3'].fill = section_fill
    for i, h in enumerate(section_headers, 1):
        c = ws.cell(row=4, column=i, value=h if i > 1 else 'Trigger Level')
        c.fill = header_fill; c.font = header_font
    for ri, trig in enumerate(['URGENT', 'HIGH', 'WATCH', 'NONE'], 5):
        row_fill = PatternFill('solid', fgColor=trig_colors.get(trig, 'FFFFFF'))
        ws.cell(row=ri, column=1, value=trig).fill = row_fill
        ws.cell(row=ri, column=2, value=f'=COUNTIF(REVENUE_TRACKER!M2:M1000,"*{trig}*")')
        ws.cell(row=ri, column=3, value=f'=SUMIF(REVENUE_TRACKER!M2:M1000,"*{trig}*",REVENUE_TRACKER!E2:E1000)')
        ws.cell(row=ri, column=3).number_format = '$#,##0'
        ws.cell(row=ri, column=4, value=f'=IFERROR(C{ri}/B{ri},0)')
        ws.cell(row=ri, column=4).number_format = '$#,##0'
        ws.cell(row=ri, column=5, value=f'=IFERROR(COUNTIFS(REVENUE_TRACKER!M2:M1000,"*{trig}*",REVENUE_TRACKER!E2:E1000,">0")/B{ri},0)')
        ws.cell(row=ri, column=5).number_format = '0%'
        ws.cell(row=ri, column=6, value=f'=IFERROR(MAXIFS(REVENUE_TRACKER!E2:E1000,REVENUE_TRACKER!M2:M1000,"*{trig}*"),0)')
        ws.cell(row=ri, column=6).number_format = '$#,##0'

    # BY MARKET
    ws['A11'] = 'BY MARKET'
    ws['A11'].font = Font(bold=True, size=12)
    ws['A11'].fill = section_fill
    for i, h in enumerate(section_headers, 1):
        c = ws.cell(row=12, column=i, value=h if i > 1 else 'Market')
        c.fill = header_fill; c.font = header_font
    for ri, mkt in enumerate(['BOTH', 'US', 'UK'], 13):
        row_fill = PatternFill('solid', fgColor=mkt_colors.get(mkt, 'FFFFFF'))
        ws.cell(row=ri, column=1, value=mkt).fill = row_fill
        ws.cell(row=ri, column=2, value=f'=COUNTIF(REVENUE_TRACKER!O2:O1000,"*{mkt}*")')
        ws.cell(row=ri, column=3, value=f'=SUMIF(REVENUE_TRACKER!O2:O1000,"*{mkt}*",REVENUE_TRACKER!E2:E1000)')
        ws.cell(row=ri, column=3).number_format = '$#,##0'
        ws.cell(row=ri, column=4, value=f'=IFERROR(C{ri}/B{ri},0)')
        ws.cell(row=ri, column=4).number_format = '$#,##0'
        ws.cell(row=ri, column=5, value=f'=IFERROR(COUNTIFS(REVENUE_TRACKER!O2:O1000,"*{mkt}*",REVENUE_TRACKER!E2:E1000,">0")/B{ri},0)')
        ws.cell(row=ri, column=5).number_format = '0%'
        ws.cell(row=ri, column=6, value=f'=IFERROR(MAXIFS(REVENUE_TRACKER!E2:E1000,REVENUE_TRACKER!O2:O1000,"*{mkt}*"),0)')
        ws.cell(row=ri, column=6).number_format = '$#,##0'

    # BY AI CATEGORY
    ws['A18'] = 'BY AI CATEGORY'
    ws['A18'].font = Font(bold=True, size=12)
    ws['A18'].fill = section_fill
    for i, h in enumerate(section_headers, 1):
        c = ws.cell(row=19, column=i, value=h if i > 1 else 'Category')
        c.fill = header_fill; c.font = header_font
    for ri, cat in enumerate(['AI', 'NON-AI'], 20):
        row_fill = PatternFill('solid', fgColor=cat_colors.get(cat, 'FFFFFF'))
        ws.cell(row=ri, column=1, value=cat).fill = row_fill
        ws.cell(row=ri, column=2, value=f'=COUNTIF(REVENUE_TRACKER!P2:P1000,"*{cat}*")')
        ws.cell(row=ri, column=3, value=f'=SUMIF(REVENUE_TRACKER!P2:P1000,"*{cat}*",REVENUE_TRACKER!E2:E1000)')
        ws.cell(row=ri, column=3).number_format = '$#,##0'
        ws.cell(row=ri, column=4, value=f'=IFERROR(C{ri}/B{ri},0)')
        ws.cell(row=ri, column=4).number_format = '$#,##0'
        ws.cell(row=ri, column=5, value=f'=IFERROR(COUNTIFS(REVENUE_TRACKER!P2:P1000,"*{cat}*",REVENUE_TRACKER!E2:E1000,">0")/B{ri},0)')
        ws.cell(row=ri, column=5).number_format = '0%'
        ws.cell(row=ri, column=6, value=f'=IFERROR(MAXIFS(REVENUE_TRACKER!E2:E1000,REVENUE_TRACKER!P2:P1000,"*{cat}*"),0)')
        ws.cell(row=ri, column=6).number_format = '$#,##0'

    for col, w in [('A',18),('B',12),('C',15),('D',15),('E',12),('F',15)]:
        ws.column_dimensions[col].width = w


def _build_competitor_view_tab(ws, competitor_gaps, header_fill, header_font, thin_border):
    headers = ['Date', 'Competitor', 'Trend', 'Competitor Momentum', 'Your Momentum',
               'Competitor Shares/h', 'Market', 'Gap Type', 'Hours Behind',
               'Est. Missed Revenue ($)', 'AI Category', 'URL']
    for ci, h in enumerate(headers, 1):
        c = ws.cell(row=1, column=ci, value=h)
        c.fill = header_fill; c.font = header_font; c.alignment = Alignment(horizontal='center')

    date_str = datetime.now().strftime('%Y-%m-%d')
    if len(competitor_gaps) > 0:
        for ri, (_, row) in enumerate(competitor_gaps.iterrows(), 2):
            vals = [date_str, row.get('competitor_account',''), str(row.get('trend_text',''))[:60],
                    int(row.get('competitor_momentum',0)), 0, round(float(row.get('competitor_shares_h',0)),1),
                    str(row.get('market','')), row.get('gap_type',''), row.get('hours_behind',''),
                    round(float(row.get('estimated_missed_revenue',0)),2), str(row.get('ai_category','')),
                    str(row.get('trend_url',''))]
            for ci, val in enumerate(vals, 1):
                c = ws.cell(row=ri, column=ci, value=_sanitize_cell(val))
                c.border = thin_border
            gap_cell = ws.cell(row=ri, column=8)
            if gap_cell.value == 'MISSED_BY_YOU':
                gap_cell.fill = PatternFill('solid', fgColor='FF6B6B')
                gap_cell.font = Font(bold=True, color='FFFFFF')
            elif gap_cell.value == 'BOTH_CAUGHT':
                gap_cell.fill = PatternFill('solid', fgColor='90EE90')
            url_cell = ws.cell(row=ri, column=12)
            uv = str(row.get('trend_url',''))
            if uv.startswith('http'):
                url_cell.hyperlink = uv
                url_cell.font = Font(color='0000FF', underline='single')
    else:
        ws['A2'] = 'No competitor posts found in today\'s trending data'
        ws['A2'].font = Font(italic=True, color='666666')
    ws.freeze_panes = 'A2'
    for col, w in [('A',12),('B',20),('C',50),('D',18),('E',15),('F',16),('G',15),('H',18),('I',14),('J',18),('K',12),('L',50)]:
        ws.column_dimensions[col].width = w


def _build_prediction_log_tab(ws, df_pred, df_yesterday, existing_log, header_fill, header_font, thin_border):
    headers = ['Date', 'Trends Tracked', 'Direction Accuracy %', 'Bias', 'MAPE %',
               'Correct Builds', 'False Positives', 'Missed Opportunities', 'Correct Skips', 'Tuning Suggestion']
    for ci, h in enumerate(headers, 1):
        c = ws.cell(row=1, column=ci, value=h)
        c.fill = header_fill; c.font = header_font; c.alignment = Alignment(horizontal='center')

    start_row = 2
    alt_fill = PatternFill('solid', fgColor='F5F5F5')
    if existing_log is not None and len(existing_log) > 0:
        for ri, (_, row) in enumerate(existing_log.iterrows(), 2):
            for ci in range(1, 11):
                val = row.iloc[ci-1] if ci-1 < len(row) else ''
                if pd.isna(val): val = ''
                c = ws.cell(row=ri, column=ci, value=_sanitize_cell(val))
                c.border = thin_border
                if ri % 2 == 0: c.fill = alt_fill
            start_row = ri + 1

    date_str = datetime.now().strftime('%Y-%m-%d')
    if df_yesterday is not None and len(df_yesterday) > 0 and len(df_pred) > 0:
        tracked = len(df_pred[df_pred['prediction_confidence'].isin(['HIGH', 'MEDIUM'])])
        if tracked > 0:
            correct_dir = total_cmp = 0
            for _, row in df_pred.iterrows():
                vel = row.get('velocity', 0)
                delta = row.get('momentum_score', 0) - row.get('yesterday_momentum', 0)
                if pd.notna(vel) and pd.notna(row.get('yesterday_momentum')):
                    total_cmp += 1
                    if (vel > 0 and delta > 0) or (vel <= 0 and delta <= 0): correct_dir += 1
            dir_acc = correct_dir / total_cmp if total_cmp > 0 else 0
            vals = [date_str, tracked, round(dir_acc, 2), 'Neutral', 0, 0, 0, 0, 0, 'Insufficient data for tuning']
            new_row_fill = PatternFill('solid', fgColor='E0FFE0')  # Highlight today's new entry
            for ci, val in enumerate(vals, 1):
                c = ws.cell(row=start_row, column=ci, value=_sanitize_cell(val))
                c.border = thin_border
                c.fill = new_row_fill

    ws.freeze_panes = 'A2'
    for col, w in [('A',12),('B',15),('C',20),('D',15),('E',10),('J',40)]:
        ws.column_dimensions[col].width = w


def _build_data_feed_tab(ws, df_today, header_fill, header_font, thin_border, cyan_fill):
    headers = ['Date', 'Account', 'Trend', 'Age', 'Momentum', 'Status', 'Market',
               'Views/h', 'Shares/h', 'BUILD_NOW', 'TikTok URL', 'TUTORIAL_TRIGGER',
               'URGENCY', 'Trigger Reason', 'AI Category', 'Opportunity Score',
               'Time Zone', 'Build Priority', 'Seasonal Event']
    for ci, h in enumerate(headers, 1):
        c = ws.cell(row=1, column=ci, value=h)
        c.fill = header_fill; c.font = header_font; c.alignment = Alignment(horizontal='center')

    date_str = datetime.now().strftime('%Y-%m-%d')
    if 'author' not in df_today.columns:
        ws['A2'] = 'No author data available'
        ws.freeze_panes = 'A2'
        return

    your_mask = df_today['author'].str.lower().isin([a.lower() for a in YOUR_ACCOUNTS])
    your_posts = df_today[your_mask].copy()
    now_hour = datetime.utcnow().hour
    tz_label = '\U0001f7e2 PRIME' if 8 <= now_hour <= 22 else 'OFF_PEAK'
    seasonal_text = ''
    try:
        from seasonal_calendar import get_seasonal_alerts
        from datetime import date
        alerts = get_seasonal_alerts(date.today())
        if alerts: seasonal_text = alerts[0].get('event', '')
    except Exception: pass

    from daily_processor import calculate_tutorial_trigger

    for ri, (_, row) in enumerate(your_posts.iterrows(), 2):
        trigger, urgency, reason = calculate_tutorial_trigger(row)
        mom = float(row.get('momentum_score', 0))
        shares_h = float(row.get('shares_per_hour', 0))
        age = float(row.get('age_hours', 0))
        opp_score = int(mom * 0.5 + shares_h * 10 + max(0, (72 - age)) * 5)
        if trigger == '\U0001f534 MAKE_NOW' and urgency == '\U0001f525 URGENT':
            build_pri = '\U0001f534 BUILD_IMMEDIATELY'
        elif trigger == '\U0001f534 MAKE_NOW':
            build_pri = '\U0001f7e0 BUILD_TODAY'
        elif trigger == '\U0001f7e1 WATCH':
            build_pri = '\U0001f7e1 MONITOR'
        else:
            build_pri = ''

        vals = [date_str, str(row.get('author','')), str(row.get('text',''))[:60] if pd.notna(row.get('text')) else '',
                f"{age:.1f}h", int(mom), str(row.get('acceleration_status', row.get('status',''))),
                str(row.get('Market','')) if pd.notna(row.get('Market')) else '',
                int(row.get('views_per_hour',0)), round(shares_h,1), str(row.get('BUILD_NOW','')),
                str(row.get('webVideoUrl','')), trigger, urgency, reason,
                str(row.get('AI_CATEGORY','')) if pd.notna(row.get('AI_CATEGORY')) else '',
                opp_score, tz_label, build_pri, seasonal_text]
        for ci, val in enumerate(vals, 1):
            c = ws.cell(row=ri, column=ci, value=_sanitize_cell(val))
            c.border = thin_border
            if ci <= 11: c.fill = cyan_fill
        # Trigger colors
        trig_cell = ws.cell(row=ri, column=12)
        if 'MAKE_NOW' in str(trigger):
            trig_cell.fill = PatternFill('solid', fgColor='FF0000')
            trig_cell.font = Font(bold=True, color='FFFFFF')
        elif 'WATCH' in str(trigger):
            trig_cell.fill = PatternFill('solid', fgColor='FFFF00')
        urg_cell = ws.cell(row=ri, column=13)
        if 'URGENT' in str(urgency):
            urg_cell.fill = PatternFill('solid', fgColor='8B0000')
            urg_cell.font = Font(bold=True, color='FFFFFF')
        elif 'HIGH' in str(urgency):
            urg_cell.fill = PatternFill('solid', fgColor='FFA500')
        url_cell = ws.cell(row=ri, column=11)
        uv = str(row.get('webVideoUrl',''))
        if uv.startswith('http'):
            url_cell.hyperlink = uv
            url_cell.font = Font(color='0000FF', underline='single')

    ws.freeze_panes = 'A2'
    for col, w in [('A',12),('B',20),('C',50),('D',10),('E',12),('F',15),('G',15),('H',10),('I',10),('K',50),('L',18),('N',30)]:
        ws.column_dimensions[col].width = w


# =============================================================================
# REVENUE DATA PERSISTENCE
# =============================================================================

def _load_existing_revenue(dashboard_path):
    # Try loading from file first
    if dashboard_path and os.path.exists(dashboard_path):
        try:
            wb = load_workbook(dashboard_path, data_only=True)
            if 'REVENUE_TRACKER' in wb.sheetnames:
                ws = wb['REVENUE_TRACKER']
                data = []
                headers = [ws.cell(1, c).value for c in range(1, 20)]
                for ri in range(2, ws.max_row + 1):
                    row_data = {}
                    has_data = False
                    for ci in range(1, 20):
                        val = ws.cell(ri, ci).value
                        col_name = headers[ci-1] if ci-1 < len(headers) else f'col_{ci}'
                        row_data[col_name] = val
                        if val is not None and str(val).strip() != '': has_data = True
                    if has_data: data.append(row_data)
                if data:
                    print(f"  Loaded {len(data)} revenue rows from dashboard file")
                    return pd.DataFrame(data)
        except Exception as e:
            print(f"  Warning: Could not load revenue from file: {e}")
    
    # Fall back to embedded seed data
    if SEED_REVENUE_DATA:
        print(f"  Using embedded seed revenue data ({len(SEED_REVENUE_DATA)} entries)")
        return pd.DataFrame(SEED_REVENUE_DATA)
    return None


def _load_existing_prediction_log(dashboard_path):
    if not dashboard_path or not os.path.exists(dashboard_path):
        return None
    try:
        wb = load_workbook(dashboard_path, data_only=True)
        if 'PREDICTION_LOG' not in wb.sheetnames: return None
        ws = wb['PREDICTION_LOG']
        data = []
        for ri in range(2, ws.max_row + 1):
            row_data = [ws.cell(ri, c).value for c in range(1, 11)]
            if any(v is not None and str(v).strip() != '' for v in row_data):
                data.append(row_data)
        if not data: return None
        headers = [ws.cell(1, c).value for c in range(1, 11)]
        return pd.DataFrame(data, columns=headers)
    except Exception as e:
        print(f"  Warning: Could not load prediction log: {e}")
        return None


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
    lines.append("TikTok Trend System v3.6.0")
    lines.append("=" * 60)
    
    df = df_today.copy()
    df = _ensure_calculated_metrics(df)
    # Deduplicate by URL to prevent BOTH-market duplicates in briefing
    df = df.drop_duplicates(subset=['webVideoUrl'], keep='first')
    
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
    output_dir: str = '.',
    dashboard_path: str = None
) -> Dict[str, str]:
    """Main integration function - generates v3.6.0 7-tab enhanced files."""
    date_str = datetime.now().strftime('%Y-%m-%d')
    output_files = {}
    cache_dir = os.environ.get('CACHE_DIR', 'data')
    streak_cache_path = os.path.join(cache_dir, 'velocity_streak_cache.json')

    # Auto-detect dashboard file
    if not dashboard_path:
        for candidate in [
            os.path.join(cache_dir, 'TikTok_Dashboard_With_Revenue.xlsx'),
            os.path.join(output_dir, 'TikTok_Dashboard_With_Revenue.xlsx'),
            'data/TikTok_Dashboard_With_Revenue.xlsx',
        ]:
            if os.path.exists(candidate):
                dashboard_path = candidate
                print(f"  Found existing dashboard: {candidate}")
                break

    if us_data is not None and len(us_data) > 0:
        us_path = f"{output_dir}/BUILD_TODAY_US_ENHANCED_{date_str}.xlsx"
        create_enhanced_excel(us_data, yesterday_us, two_days_us, us_path,
                              cache_path=streak_cache_path, dashboard_path=dashboard_path)
        output_files['us_enhanced'] = us_path

    if uk_data is not None and len(uk_data) > 0:
        uk_path = f"{output_dir}/BUILD_TODAY_UK_ENHANCED_{date_str}.xlsx"
        create_enhanced_excel(uk_data, yesterday_uk, two_days_uk, uk_path,
                              cache_path=streak_cache_path, dashboard_path=dashboard_path)
        output_files['uk_enhanced'] = uk_path

    if us_data is not None and uk_data is not None:
        combined = pd.concat([us_data, uk_data], ignore_index=True)
        combined_yesterday = None
        if yesterday_us is not None and yesterday_uk is not None:
            combined_yesterday = pd.concat([yesterday_us, yesterday_uk], ignore_index=True)
            combined_yesterday = combined_yesterday.drop_duplicates(subset=['webVideoUrl'], keep='first')
        combined_path = f"{output_dir}/BUILD_TODAY_COMBINED_ENHANCED_{date_str}.xlsx"
        create_enhanced_excel(combined, combined_yesterday, None, combined_path,
                              cache_path=streak_cache_path, dashboard_path=dashboard_path)
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
