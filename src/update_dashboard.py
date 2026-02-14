"""
update_dashboard.py — Push daily processed data to Google Sheets dashboard
v5.6.1: Added seed_historical_revenue() for one-time historical data import
"""

import os
import json
import base64
from datetime import datetime
import gspread


# ── Historical revenue data from TikTok_Dashboard_With_Revenue.xlsx ──
# Extracted 2026-02-11 — 28 templates, $10,754 total, 4 at cap
HISTORICAL_REVENUE = [
    {'url': 'https://www.tiktok.com/@7597546182721670422/video/7597546182721670422', 'account': '', 'received': 2500, 'estimated': 2500, 'us_installs': 2059, 'row_installs': 8418, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7598141227619388694/video/7598141227619388694', 'account': '', 'received': 2500, 'estimated': 2500, 'us_installs': 839, 'row_installs': 2046, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7596436774478548246/video/7596436774478548246', 'account': '', 'received': 2500, 'estimated': 2500, 'us_installs': 540, 'row_installs': 861, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7597736583386762518/video/7597736583386762518', 'account': '', 'received': 2500, 'estimated': 2500, 'us_installs': 837, 'row_installs': 2202, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7599034433294830870/video/7599034433294830870', 'account': '', 'received': 2500, 'estimated': 2500, 'us_installs': 1399, 'row_installs': 1422, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7596266053953391895/video/7596266053953391895', 'account': '', 'received': 2500, 'estimated': 2500, 'us_installs': 495, 'row_installs': 847, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7588452470355987734/video/7588452470355987734', 'account': '', 'received': 2500, 'estimated': 2500, 'us_installs': 803, 'row_installs': 317, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7597126976427609366/video/7597126976427609366', 'account': 'Account 1 (smaller)', 'received': 2500, 'estimated': 2500, 'us_installs': 2184, 'row_installs': 3782, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7597399641776508163/video/7597399641776508163', 'account': 'Account 1 (smaller)', 'received': 2500, 'estimated': 2500, 'us_installs': 717, 'row_installs': 1984, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7597123284848610582/video/7597123284848610582', 'account': 'Account 1 (smaller)', 'received': 2500, 'estimated': 2500, 'us_installs': 1196, 'row_installs': 1554, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7597924302243007766/video/7597924302243007766', 'account': 'Account 1 (smaller)', 'received': 2500, 'estimated': 2500, 'us_installs': 671, 'row_installs': 1269, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7596261580220763394/video/7596261580220763394', 'account': '', 'received': 2233, 'estimated': 2233, 'us_installs': 333, 'row_installs': 568, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7600100215269412118/video/7600100215269412118', 'account': '', 'received': 2097, 'estimated': 2097, 'us_installs': 303, 'row_installs': 582, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7596653525971520790/video/7596653525971520790', 'account': '', 'received': 1694, 'estimated': 1694, 'us_installs': 223, 'row_installs': 579, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7589641969870081302/video/7589641969870081302', 'account': '', 'received': 1638, 'estimated': 1638, 'us_installs': 252, 'row_installs': 378, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7596264812846353686/video/7596264812846353686', 'account': '', 'received': 1462, 'estimated': 1462, 'us_installs': 209, 'row_installs': 417, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7600762883944893718/video/7600762883944893718', 'account': '', 'received': 1457, 'estimated': 1457, 'us_installs': 122, 'row_installs': 847, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7589953615041711382/video/7589953615041711382', 'account': '', 'received': 1386, 'estimated': 1386, 'us_installs': 173, 'row_installs': 1, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7597416345443675174/video/7597416345443675174', 'account': '', 'received': 1261, 'estimated': 1261, 'us_installs': 154, 'row_installs': 491, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7598499844461743382/video/7598499844461743382', 'account': '', 'received': 1040, 'estimated': 1040, 'us_installs': 136, 'row_installs': 360, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7598144760615947542/video/7598144760615947542', 'account': '', 'received': 1018, 'estimated': 1018, 'us_installs': 150, 'row_installs': 268, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7598494805294959894/video/7598494805294959894', 'account': '', 'received': 893, 'estimated': 893, 'us_installs': 145, 'row_installs': 168, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7598604870899289366/video/7598604870899289366', 'account': '', 'received': 869, 'estimated': 869, 'us_installs': 152, 'row_installs': 109, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7590045885837413654/video/7590045885837413654', 'account': '', 'received': 854, 'estimated': 854, 'us_installs': 187, 'row_installs': 195, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7596803270442601750/video/7596803270442601750', 'account': '', 'received': 818, 'estimated': 818, 'us_installs': 84, 'row_installs': 398, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7596800019433295126/video/7596800019433295126', 'account': '', 'received': 359, 'estimated': 359, 'us_installs': 63, 'row_installs': 44, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7600099102747135254/video/7600099102747135254', 'account': '', 'received': 345, 'estimated': 345, 'us_installs': 31, 'row_installs': 190, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7597114246433869078/video/7597114246433869078', 'account': 'Account 1 (smaller)', 'received': 324, 'estimated': 324, 'us_installs': 49, 'row_installs': 79, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7597084269701270806/video/7597084269701270806', 'account': 'Account 1 (smaller)', 'received': 314, 'estimated': 314, 'us_installs': 47, 'row_installs': 79, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7597737771008085270/video/7597737771008085270', 'account': '', 'received': 305, 'estimated': 305, 'us_installs': 53, 'row_installs': 40, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7596670194215439638/video/7596670194215439638', 'account': '', 'received': 237, 'estimated': 237, 'us_installs': 44, 'row_installs': 17, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7600760603992460566/video/7600760603992460566', 'account': '', 'received': 230, 'estimated': 230, 'us_installs': 16, 'row_installs': 150, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7588890166589246742/video/7588890166589246742', 'account': '', 'received': 191, 'estimated': 191, 'us_installs': 38, 'row_installs': 1, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7595978340461333782/video/7595978340461333782', 'account': '', 'received': 180, 'estimated': 180, 'us_installs': 26, 'row_installs': 50, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7589801229585452290/video/7589801229585452290', 'account': '', 'received': 120, 'estimated': 120, 'us_installs': 15, 'row_installs': 12, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7597805299315068182/video/7597805299315068182', 'account': 'Account 1 (smaller)', 'received': 106, 'estimated': 106, 'us_installs': 13, 'row_installs': 41, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7585413802045295894/video/7585413802045295894', 'account': '', 'received': 84, 'estimated': 84, 'us_installs': 14, 'row_installs': 14, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7598924005176921366/video/7598924005176921366', 'account': '', 'received': 77, 'estimated': 77, 'us_installs': 10, 'row_installs': 27, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7599638833512074518/video/7599638833512074518', 'account': '', 'received': 71, 'estimated': 71, 'us_installs': 13, 'row_installs': 6, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7534055571922750742/video/7534055571922750742', 'account': '', 'received': 66, 'estimated': 66, 'us_installs': 11, 'row_installs': 11, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7600491652389752067/video/7600491652389752067', 'account': '', 'received': 59, 'estimated': 59, 'us_installs': 11, 'row_installs': 4, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7588665170323410198/video/7588665170323410198', 'account': '', 'received': 56, 'estimated': 56, 'us_installs': 9, 'row_installs': 11, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7600349631934909718/video/7600349631934909718', 'account': '', 'received': 53, 'estimated': 53, 'us_installs': 8, 'row_installs': 13, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7584815356997373206/video/7584815356997373206', 'account': '', 'received': 35, 'estimated': 35, 'us_installs': 7, 'row_installs': 0, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7599639960802659606/video/7599639960802659606', 'account': '', 'received': 25, 'estimated': 25, 'us_installs': 4, 'row_installs': 5, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7600069960731200790/video/7600069960731200790', 'account': '', 'received': 19, 'estimated': 19, 'us_installs': 2, 'row_installs': 9, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7588593850516589846/video/7588593850516589846', 'account': '', 'received': 18, 'estimated': 18, 'us_installs': 3, 'row_installs': 3, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7599750339352595735/video/7599750339352595735', 'account': '', 'received': 16, 'estimated': 16, 'us_installs': 2, 'row_installs': 6, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7584827008618646806/video/7584827008618646806', 'account': '', 'received': 15, 'estimated': 15, 'us_installs': 2, 'row_installs': 5, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7592963003901840662/video/7592963003901840662', 'account': '', 'received': 15, 'estimated': 15, 'us_installs': 2, 'row_installs': 5, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7538858594683440406/video/7538858594683440406', 'account': '', 'received': 14, 'estimated': 14, 'us_installs': 2, 'row_installs': 4, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7584811033206803734/video/7584811033206803734', 'account': '', 'received': 13, 'estimated': 13, 'us_installs': 2, 'row_installs': 3, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7595235096404266262/video/7595235096404266262', 'account': '', 'received': 11, 'estimated': 11, 'us_installs': 2, 'row_installs': 1, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7589183622859558167/video/7589183622859558167', 'account': '', 'received': 11, 'estimated': 11, 'us_installs': 2, 'row_installs': 1, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7600770165768228118/video/7600770165768228118', 'account': '', 'received': 8, 'estimated': 8, 'us_installs': 1, 'row_installs': 3, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7599275177226046742/video/7599275177226046742', 'account': '', 'received': 8, 'estimated': 8, 'us_installs': 1, 'row_installs': 3, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7596766270058417430/video/7596766270058417430', 'account': '', 'received': 7, 'estimated': 7, 'us_installs': 1, 'row_installs': 2, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7599177144627154179/video/7599177144627154179', 'account': '', 'received': 6, 'estimated': 6, 'us_installs': 1, 'row_installs': 1, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7589643666491297046/video/7589643666491297046', 'account': '', 'received': 6, 'estimated': 6, 'us_installs': 1, 'row_installs': 1, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7590120022803205397/video/7590120022803205397', 'account': '', 'received': 5, 'estimated': 5, 'us_installs': 0, 'row_installs': 5, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7592645042695802135/video/7592645042695802135', 'account': '', 'received': 5, 'estimated': 5, 'us_installs': 1, 'row_installs': 0, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7599026448749382934/video/7599026448749382934', 'account': '', 'received': 5, 'estimated': 5, 'us_installs': 1, 'row_installs': 0, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7586604785374104854/video/7586604785374104854', 'account': '', 'received': 5, 'estimated': 5, 'us_installs': 1, 'row_installs': 0, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7597362819398503702/video/7597362819398503702', 'account': 'Account 1 (smaller)', 'received': 5, 'estimated': 5, 'us_installs': 1, 'row_installs': 0, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7599372602066390294/video/7599372602066390294', 'account': '', 'received': 3, 'estimated': 3, 'us_installs': 0, 'row_installs': 3, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7599371798970371350/video/7599371798970371350', 'account': '', 'received': 3, 'estimated': 3, 'us_installs': 0, 'row_installs': 3, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7599032518100241686/video/7599032518100241686', 'account': 'Account 1 (smaller)', 'received': 3, 'estimated': 3, 'us_installs': 0, 'row_installs': 3, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7598241192240778518/video/7598241192240778518', 'account': '', 'received': 2, 'estimated': 2, 'us_installs': 0, 'row_installs': 2, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7589955663128775958/video/7589955663128775958', 'account': '', 'received': 2, 'estimated': 2, 'us_installs': 1, 'row_installs': 0, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7592952482741964054/video/7592952482741964054', 'account': '', 'received': 2, 'estimated': 2, 'us_installs': 0, 'row_installs': 2, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7590115654942854422/video/7590115654942854422', 'account': '', 'received': 2, 'estimated': 2, 'us_installs': 0, 'row_installs': 2, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7598188911415938326/video/7598188911415938326', 'account': '', 'received': 2, 'estimated': 2, 'us_installs': 0, 'row_installs': 2, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7585524986576637186/video/7585524986576637186', 'account': '', 'received': 2, 'estimated': 2, 'us_installs': 0, 'row_installs': 2, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7588896788531252502/video/7588896788531252502', 'account': '', 'received': 2, 'estimated': 2, 'us_installs': 0, 'row_installs': 2, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7597064708012920067/video/7597064708012920067', 'account': 'Account 1 (smaller)', 'received': 2, 'estimated': 2, 'us_installs': 0, 'row_installs': 2, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7599268989629549827/video/7599268989629549827', 'account': '', 'received': 1, 'estimated': 1, 'us_installs': 0, 'row_installs': 1, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7589294163988974870/video/7589294163988974870', 'account': '', 'received': 1, 'estimated': 1, 'us_installs': 0, 'row_installs': 1, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7595964773100014870/video/7595964773100014870', 'account': '', 'received': 1, 'estimated': 1, 'us_installs': 0, 'row_installs': 1, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7600781841251061014/video/7600781841251061014', 'account': '', 'received': 1, 'estimated': 1, 'us_installs': 0, 'row_installs': 1, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7600362027797826838/video/7600362027797826838', 'account': '', 'received': 1, 'estimated': 1, 'us_installs': 0, 'row_installs': 1, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7592911940830219542/video/7592911940830219542', 'account': '', 'received': 1, 'estimated': 1, 'us_installs': 0, 'row_installs': 1, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7595908644831694082/video/7595908644831694082', 'account': '', 'received': 1, 'estimated': 1, 'us_installs': 0, 'row_installs': 1, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7601487341189975318/video/7601487341189975318', 'account': '', 'received': 0, 'estimated': 1539, 'us_installs': 284, 'row_installs': 119, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7601835249730915606/video/7601835249730915606', 'account': '', 'received': 0, 'estimated': 56, 'us_installs': 9, 'row_installs': 11, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7601565353419853078/video/7601565353419853078', 'account': '', 'received': 0, 'estimated': 196, 'us_installs': 37, 'row_installs': 11, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7604896624334228758/video/7604896624334228758', 'account': '', 'received': 0, 'estimated': 3, 'us_installs': 0, 'row_installs': 3, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7601828002359430422/video/7601828002359430422', 'account': '', 'received': 0, 'estimated': 78, 'us_installs': 15, 'row_installs': 3, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7603420165602037014/video/7603420165602037014', 'account': '', 'received': 0, 'estimated': 128, 'us_installs': 23, 'row_installs': 13, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7530652618117582102/video/7530652618117582102', 'account': '', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7601622544600354070/video/7601622544600354070', 'account': '', 'received': 0, 'estimated': 5, 'us_installs': 1, 'row_installs': 0, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7589958196710722838/video/7589958196710722838', 'account': '', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7601242576053652758/video/7601242576053652758', 'account': '', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7601537953378143510/video/7601537953378143510', 'account': '', 'received': 0, 'estimated': 179, 'us_installs': 33, 'row_installs': 14, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7601470612418170135/video/7601470612418170135', 'account': '', 'received': 0, 'estimated': 6, 'us_installs': 1, 'row_installs': 1, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7601632405601996054/video/7601632405601996054', 'account': '', 'received': 0, 'estimated': 6, 'us_installs': 1, 'row_installs': 1, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7596811565123374358/video/7596811565123374358', 'account': '', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7604153402934725890/video/7604153402934725890', 'account': '', 'received': 0, 'estimated': 3, 'us_installs': 0, 'row_installs': 3, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7594456162293026070/video/7594456162293026070', 'account': '', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7603017097614232854/video/7603017097614232854', 'account': '', 'received': 0, 'estimated': 5, 'us_installs': 1, 'row_installs': 0, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7595560825469930774/video/7595560825469930774', 'account': '', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7590078610845879574/video/7590078610845879574', 'account': '', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7601468586128952598/video/7601468586128952598', 'account': '', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7602393658146524418/video/7602393658146524418', 'account': '', 'received': 0, 'estimated': 10, 'us_installs': 2, 'row_installs': 0, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7598278879643569430/video/7598278879643569430', 'account': '', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7598212457932393750/video/7598212457932393750', 'account': '', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7599172358380719382/video/7599172358380719382', 'account': '', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7601614140414708995/video/7601614140414708995', 'account': '', 'received': 0, 'estimated': 18, 'us_installs': 3, 'row_installs': 3, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7590381156978199831/video/7590381156978199831', 'account': '', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7598963080218873111/video/7598963080218873111', 'account': '', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7603374540235803926/video/7603374540235803926', 'account': '', 'received': 0, 'estimated': 81, 'us_installs': 6, 'row_installs': 51, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7530023517908159766/video/7530023517908159766', 'account': '', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7601515548182138134/video/7601515548182138134', 'account': '', 'received': 0, 'estimated': 28, 'us_installs': 5, 'row_installs': 3, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7601611906779974934/video/7601611906779974934', 'account': '', 'received': 0, 'estimated': 21, 'us_installs': 4, 'row_installs': 1, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7528031035309821206/video/7528031035309821206', 'account': '', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7603359664142568726/video/7603359664142568726', 'account': '', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7601167547966164246/video/7601167547966164246', 'account': '', 'received': 0, 'estimated': 28, 'us_installs': 2, 'row_installs': 18, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7584426482357882115/video/7584426482357882115', 'account': '', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7601477473322159382/video/7601477473322159382', 'account': '', 'received': 0, 'estimated': 5, 'us_installs': 1, 'row_installs': 0, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7599666081636322583/video/7599666081636322583', 'account': '', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7598945928455720214/video/7598945928455720214', 'account': '', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7603101081257790742/video/7603101081257790742', 'account': '', 'received': 0, 'estimated': 8, 'us_installs': 1, 'row_installs': 3, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7599276140229856534/video/7599276140229856534', 'account': '', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7601245488603565334/video/7601245488603565334', 'account': '', 'received': 0, 'estimated': 20, 'us_installs': 4, 'row_installs': 0, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7601836046355074326/video/7601836046355074326', 'account': '', 'received': 0, 'estimated': 7, 'us_installs': 0, 'row_installs': 7, 'date': '2026-02-14'},
    {'url': 'https://www.tiktok.com/@7597795533490507030/video/7597795533490507030', 'account': 'Account 1 (smaller)', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7597363566458539286/video/7597363566458539286', 'account': 'Account 1 (smaller)', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7597171707987709206/video/7597171707987709206', 'account': 'Account 1 (smaller)', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7591292533720878358/video/7591292533720878358', 'account': 'Account 1 (smaller)', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7597796013792939286/video/7597796013792939286', 'account': 'Account 1 (smaller)', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7597800531087658262/video/7597800531087658262', 'account': 'Account 1 (smaller)', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7597080404323028246/video/7597080404323028246', 'account': 'Account 1 (smaller)', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7597108883814944022/video/7597108883814944022', 'account': 'Account 1 (smaller)', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7603100212176997654/video/7603100212176997654', 'account': 'Account 1 (smaller)', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7597012528090107158/video/7597012528090107158', 'account': 'Account 1 (smaller)', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7597801729450577174/video/7597801729450577174', 'account': 'Account 1 (smaller)', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7597364619035888899/video/7597364619035888899', 'account': 'Account 1 (smaller)', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7590877569394773270/video/7590877569394773270', 'account': 'Account 1 (smaller)', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7582151219729272086/video/7582151219729272086', 'account': 'Account 1 (smaller)', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7581890594608336150/video/7581890594608336150', 'account': 'Account 1 (smaller)', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7597928583667010819/video/7597928583667010819', 'account': 'Account 1 (smaller)', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7582190483133238550/video/7582190483133238550', 'account': 'Account 1 (smaller)', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@7581937222518115606/video/7581937222518115606', 'account': 'Account 1 (smaller)', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-09'},
    {'url': 'https://www.tiktok.com/@capcuttemplatesai/video/7433474060589223201', 'account': 'capcuttemplatesai', 'received': 0, 'estimated': 0, 'us_installs': 0, 'row_installs': 0, 'date': '2026-02-09'},
]


def get_gspread_client():
    """Get authenticated gspread client. Tries OAuth2 first, then service account."""
    
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
        print("  Auth: OAuth2 refresh token (personal account)")
        return gspread.authorize(creds)
    
    # Method 2: Service account (Google Workspace)
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
        print("  Auth: Service account")
        return gspread.authorize(creds)
    
    raise ValueError('No Google credentials configured')


def safe_get_worksheet(sheet, tab_name):
    """Safely get a worksheet by name, return None if not found."""
    try:
        return sheet.worksheet(tab_name)
    except gspread.exceptions.WorksheetNotFound:
        print(f'  ⚠️ Tab "{tab_name}" not found in spreadsheet — skipping')
        return None


def seed_historical_revenue(sheet):
    """One-time seed of historical revenue data into REVENUE_TRACKER.
    
    Checks if data already exists (by URL) and only adds missing entries.
    Safe to call on every run — skips if all entries already present.
    """
    ws = safe_get_worksheet(sheet, 'REVENUE_TRACKER')
    if ws is None:
        return 0

    # Get existing URLs to avoid duplicates
    existing_urls = set()
    try:
        url_col = ws.col_values(1)
        existing_urls = set(url_col[1:])  # Skip header
    except Exception:
        pass

    # Filter to only entries not already in the sheet
    new_entries = [h for h in HISTORICAL_REVENUE if h['url'] not in existing_urls]

    if not new_entries:
        print('  REVENUE_SEED: All historical data already present — skipping')
        return 0

    # Build rows matching the 19-column REVENUE_TRACKER structure
    next_row = len(existing_urls) + 2  # +1 for header, +1 for next empty
    rows = []
    for i, entry in enumerate(new_entries):
        r = next_row + i

        rows.append([
            entry['url'],                    # Col 1: TikTok URL
            entry['account'],                # Col 2: Account
            '',                              # Col 3: Template Link
            entry['received'],               # Col 4: Received ($)
            entry['estimated'],              # Col 5: Estimated ($)
            entry['us_installs'],            # Col 6: US & EU3 Installs
            entry['row_installs'],           # Col 7: ROW Installs
            f'=F{r}+G{r}',                  # Col 8: Total Installs (formula)
            f'=IFERROR(E{r}/H{r},0)',        # Col 9: Rev/Install (formula)
            f'=IF(E{r}>=2500,"✅ CAP","")',  # Col 10: At Cap? (formula)
            '',                              # Col 11: Trend Description
            '',                              # Col 12: Momentum at Detection
            '',                              # Col 13: Trigger Level
            '',                              # Col 14: Action Window
            '',                              # Col 15: Market
            '',                              # Col 16: AI Category
            '',                              # Col 17: Age at Detection
            entry['date'],                   # Col 18: Date First Seen
            'Historical import',             # Col 19: Notes
        ])

    if rows:
        ws.append_rows(rows, value_input_option='USER_ENTERED')

    total_rev = sum(e['received'] for e in new_entries)
    cap_count = sum(1 for e in new_entries if e['received'] >= 2500)
    print(f'  REVENUE_SEED: {len(rows)} historical entries added (${total_rev:,} revenue, {cap_count} at cap)')
    return len(rows)


def update_opportunity_now(sheet, opportunity_data):
    ws = safe_get_worksheet(sheet, 'OPPORTUNITY_NOW')
    if ws is None:
        return 0
    if ws.row_count > 1:
        try:
            ws.delete_rows(2, ws.row_count)
        except Exception:
            pass
    if not opportunity_data:
        return 0
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
    ws = safe_get_worksheet(sheet, 'COMPETITOR_VIEW')
    if ws is None:
        return 0
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
    ws = safe_get_worksheet(sheet, 'PREDICTION_LOG')
    if ws is None:
        return 0
    if not model_summary or 'direction_accuracy_pct' not in model_summary:
        print('  PREDICTION_LOG: No accuracy data')
        return 0
    outcomes = model_summary.get('action_outcomes', {})
    suggestions = model_summary.get('tuning_suggestions', [])
    row = [
        date_str,
        model_summary.get('trends_tracked', 0),
        model_summary.get('direction_accuracy_pct', 0) / 100,
        model_summary.get('bias', 'N/A'),
        model_summary.get('mean_absolute_pct_error', 0),
        outcomes.get('CORRECT_BUILD', 0),
        outcomes.get('FALSE_POSITIVE', 0),
        outcomes.get('MISSED_OPPORTUNITY', 0),
        outcomes.get('CORRECT_SKIP', 0),
        suggestions[0][:100] if suggestions else '',
    ]
    ws.append_row(row, value_input_option='USER_ENTERED')
    print(f'  PREDICTION_LOG: 1 row appended')
    return 1


def append_data_feed(sheet, my_performance_data, date_str):
    ws = safe_get_worksheet(sheet, 'DATA_FEED')
    if ws is None:
        return 0
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
    ws = safe_get_worksheet(sheet, 'DASHBOARD')
    if ws is None:
        return
    alert_start_row = 18
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
    ws = safe_get_worksheet(sheet, 'REVENUE_TRACKER')
    if ws is None:
        return 0
    existing_urls = set()
    try:
        url_col = ws.col_values(1)
        existing_urls = set(url_col[1:])
    except Exception:
        pass
    new_rows = []
    for tpl in new_templates:
        url = tpl.get('TikTok URL', tpl.get('webVideoUrl', ''))
        if url and url not in existing_urls and url != 'nan':
            new_rows.append([
                url, tpl.get('Account', ''), '', 0, 0, 0, 0,
                '', '', '',
                str(tpl.get('Trend', ''))[:60],
                tpl.get('Momentum', 0),
                tpl.get('URGENCY', tpl.get('trigger_level', '')),
                tpl.get('action_window', ''),
                tpl.get('Market', ''),
                tpl.get('AI_CATEGORY', tpl.get('ai_category', '')),
                tpl.get('Age', ''),
                datetime.now().strftime('%Y-%m-%d'),
                '',
            ])
    if new_rows:
        next_row = len(existing_urls) + 2
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
    
    try:
        sheet = client.open_by_key(sheet_id)
    except gspread.exceptions.SpreadsheetNotFound:
        print(f"  ❌ Spreadsheet not found. Check sharing and ID.")
        raise
    except Exception as e:
        print(f"  ❌ Cannot open spreadsheet: {e}")
        raise
    
    today = datetime.now().strftime('%Y-%m-%d')
    print(f'Updating dashboard for {today}...')
    
    tab_names = [ws.title for ws in sheet.worksheets()]
    print(f'  Available tabs: {tab_names}')

    # ── Seed historical revenue (runs once, skips if already done) ──
    seed_historical_revenue(sheet)

    cache_dir = os.environ.get('CACHE_DIR', 'data')
    payload_path = os.path.join(cache_dir, 'dashboard_payload.json')
    
    try:
        with open(payload_path, 'r') as f:
            payload = json.load(f)
    except FileNotFoundError:
        print(f'ERROR: {payload_path} not found.')
        return

    update_opportunity_now(sheet, payload.get('opportunity_matrix', []))
    append_competitor_view(sheet, payload.get('competitor_gaps', []), today)
    append_prediction_log(sheet, payload.get('model_summary', {}), today)
    append_data_feed(sheet, payload.get('my_performance', []), today)
    update_seasonal_alerts(sheet, payload.get('seasonal_alerts', []))
    update_revenue_tracker_metadata(sheet, payload.get('new_templates', []))

    print(f'\n✅ Dashboard updated successfully')


if __name__ == '__main__':
    main()
