# Revenue Model Update — v5.8.0
## Pioneer Programme Data Integration + Payments Tracking

**Date:** 2026-02-14
**Input:** Pioneer_Revenue_Data.xlsx (114 templates)
**Merged with:** 29 existing seed entries (no overlap)
**Total templates:** 143 unique

---

## Key Findings from Your Real Data

| Metric | Value |
|--------|-------|
| **US & EU3 rate** | **$3.51 per install** |
| **ROW rate** | **$1.50 per install** |
| **Blended rate** | $1.19 per install |
| **Model accuracy (R²)** | 0.96 |
| **Templates at cap** | 9 ($2,500 each) |
| **Total revenue** | $49,681 (143 templates) |
| **Avg installs to cap** | 3,298 |
| **Min installs to cap** | 1,120 |
| **Avg US & EU3 share** | 41.5% of installs |

The regression tells us US & EU3 installs are worth **2.3× more** than ROW installs. This is the real conversion rate from your Pioneer Programme payments.

---

## New Tabs Added to Enhanced Files

### PAYMENTS tab (NEW)
Day-by-day breakdown of all Pioneer Programme payments, sorted by post date (newest first). Includes:
- Post date extracted automatically from video URL (no manual entry)
- Revenue, installs, rev/install for each template
- Daily subtotals
- Grand total row
- Color coding: Green = capped, Yellow = earning, Orange = pending

### MONTHLY_REVENUE tab (NEW)
Month-by-month summary with:
- Templates posted, revenue received/estimated, installs
- Cap rate and average revenue per template
- Month-over-month growth section showing trends

### REVENUE_TRACKER update
- Added **Post Date** as column 20 (auto-derived from video URL)
- Now 20 columns (was 19)
- Existing formulas unaffected (they reference columns by letter)

### Enhanced files now have 10 tabs (was 8):
1. DASHBOARD
2. OPPORTUNITY_NOW
3. REVENUE_TRACKER (now 20 cols)
4. REVENUE_INSIGHTS
5. COMPETITOR_VIEW
6. PREDICTION_LOG
7. DATA_FEED
8. COMPETITOR_INTEL
9. **PAYMENTS** (NEW)
10. **MONTHLY_REVENUE** (NEW)

---

## What Changed

### NEW FILE: `revenue_model.py`
Data-driven revenue estimation with:
- **Install-based** estimation (HIGH confidence): $3.51 US + $1.50 ROW rates
- **Momentum-based** estimation (LOW confidence): Tiered model for competitors
- **Post date extraction**: `extract_post_date(url)` — derives exact post time from TikTok video ID

### Old formula removed everywhere:
```
# BEFORE (in 4 locations)
estimated_revenue = (momentum / 1000) * 5

# AFTER
from revenue_model import estimate_competitor_revenue
result = estimate_competitor_revenue(momentum, shares_per_hour, age_hours)
```

### Files Modified (6 total)

| File | Change |
|------|--------|
| `revenue_model.py` | **NEW** — Revenue estimation + post date extraction |
| `v35_enhancements.py` | SEED: 59→143 entries, 2 formula fixes, REVENUE_TRACKER 20 cols, 2 new tabs |
| `update_dashboard.py` | HISTORICAL_REVENUE: 59→143 entries |
| `main.py` | Version 5.6→5.8, 1 formula replacement, new import |
| `competitor_intel_patch.py` | 1 formula replacement |
| `revenue_persistence.py` | Updated docstring |

---

## How to Deploy

Drop all 6 files into your `src/` directory on GitHub:
```
src/
├── revenue_model.py          ← NEW
├── main.py                   ← updated
├── v35_enhancements.py       ← updated (PAYMENTS + MONTHLY_REVENUE tabs)
├── update_dashboard.py       ← updated
├── competitor_intel_patch.py  ← updated
└── revenue_persistence.py    ← updated
```

No new dependencies. No config changes. No secrets needed.

---

## Revenue by Month (from your data)

| Month | Templates | Revenue | At Cap |
|-------|-----------|---------|--------|
| 2024-11 | 1 | $0 | 0 |
| 2025-07 | 3 | $0 | 0 |
| 2025-08 | 2 | $80 | 0 |
| 2025-12 | 28 | $6,946 | 1 |
| 2026-01 | 97 | $42,655 | 8 |
| 2026-02 | 12 | $0 (pending) | 0 |
| **TOTAL** | **143** | **$49,681** | **9** |
