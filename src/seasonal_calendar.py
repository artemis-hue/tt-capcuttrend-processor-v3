#!/usr/bin/env python3
"""
TIKTOK SEASONAL CALENDAR
Version: 1.0.0
Notification windows: 14 days BEFORE and 1 day AFTER each event.
Used by: main.py (get_seasonal_alerts, format functions)
"""
from datetime import date, timedelta

ADVANCE_DAYS = 14
AFTER_DAYS = 2

FIXED_EVENTS = [
    (1, 1, "New Year's Day", "\U0001f386", ["new year","2026","resolution","fresh start","new me","goals","nye"], "Before/after transformations, goal-setting templates, year review"),
    (1, 17, "Blue Monday", "\U0001f614", ["blue monday","sad","motivation","self care","mental health"], "Mood boost templates, self-care transitions"),
    (1, 25, "Burns Night", "\U0001f3f4\U000e0067\U000e0062\U000e0073\U000e0063\U000e0074\U000e007f", ["burns night","scotland","haggis","scottish"], "Scottish-themed templates (UK niche)"),
    (1, 29, "Chinese New Year", "\U0001f9e7", ["chinese new year","lunar new year","cny","year of"], "Red/gold themed templates, zodiac animal reveals"),
    (2, 1, "LGBT History Month UK Start", "\U0001f3f3\ufe0f\u200d\U0001f308", ["lgbt history","pride","lgbtq"], "Pride-themed templates (UK-specific month)"),
    (2, 2, "Groundhog Day", "\U0001f9ab", ["groundhog","repeat","deja vu"], "Loop/repeat style templates"),
    (2, 11, "Safer Internet Day", "\U0001f6e1\ufe0f", ["safer internet","online safety","cyberbullying","digital wellness","internet safety"], "Online safety awareness templates, digital wellness content"),
    (2, 11, "International Day of Women in Science", "\U0001f52c", ["women in science","stem","female scientist","girls in stem","science day"], "Women in STEM reveals, science career templates"),
    (2, 13, "Galentine's Day", "\U0001f469\u200d\U0001f469\u200d\U0001f467", ["galentine","bestie","girls night","best friend","friendship","girl gang","squad"], "Best friend templates, girls night out, friendship reveals"),
    (2, 14, "Valentine's Day", "\U0001f49d", ["valentine","love","couple","boyfriend","girlfriend","romantic","heart","crush","relationship","date night"], "Couple reveals, love story templates, anti-valentine, galentine's"),
    (2, 17, "Random Acts of Kindness Day", "\U0001f495", ["kindness","kind","random act"], "Kindness challenge templates"),
    (3, 1, "St David's Day", "\U0001f3f4\U000e0067\U000e0062\U000e0077\U000e006c\U000e0073\U000e007f", ["st david","wales","welsh","daffodil"], "Welsh-themed templates (UK niche)"),
    (3, 8, "International Women's Day", "\U0001f469", ["women's day","iwd","girl power","female empowerment"], "Empowerment templates, women in history reveals"),
    (3, 14, "Pi Day", "\U0001f967", ["pi day","3.14","math"], "Niche maths templates"),
    (3, 17, "St Patrick's Day", "\u2618\ufe0f", ["st patrick","irish","shamrock","green","ireland","lucky"], "Green-themed templates, Irish culture"),
    (3, 20, "Spring Equinox", "\U0001f338", ["spring","equinox","first day of spring"], "Season change templates, spring transformation"),
    (3, 31, "Transgender Day of Visibility", "\U0001f3f3\ufe0f\u200d\u26a7\ufe0f", ["trans visibility","transgender","tdov"], "Visibility/reveal templates"),
    (4, 1, "April Fools' Day", "\U0001f921", ["april fool","prank","joke","fool","gotcha"], "Prank reveal templates, fake-out transitions"),
    (4, 22, "Earth Day", "\U0001f30d", ["earth day","environment","climate","sustainable","planet","eco"], "Nature transformation templates, eco-challenge"),
    (4, 23, "St George's Day", "\U0001f3f4\U000e0067\U000e0062\U000e0065\U000e006e\U000e0067\U000e007f", ["st george","england","english"], "England-themed templates (UK niche)"),
    (5, 4, "Star Wars Day", "\u2694\ufe0f", ["star wars","may the 4th","force","jedi","lightsaber"], "Star Wars themed transitions"),
    (5, 5, "Cinco de Mayo", "\U0001f1f2\U0001f1fd", ["cinco de mayo","mexican","fiesta"], "Fiesta-themed templates (US market)"),
    (5, 11, "Mother's Day (US)", "\U0001f469\u200d\U0001f466", ["mother's day","mom","mum","mama","mommy"], "Mom tribute templates (US date)"),
    (5, 26, "Memorial Day (US)", "\U0001f1fa\U0001f1f8", ["memorial day","remember","honor","fallen"], "Tribute templates (US market)"),
    (6, 1, "Pride Month Start", "\U0001f3f3\ufe0f\u200d\U0001f308", ["pride month","pride","lgbtq","rainbow"], "Rainbow templates, pride transformation"),
    (6, 15, "Father's Day (US/UK)", "\U0001f468\u200d\U0001f466", ["father's day","dad","daddy","papa","father"], "Dad tribute templates, father-child reveal"),
    (6, 20, "Summer Solstice", "\u2600\ufe0f", ["summer solstice","longest day","midsummer"], "Summer transformation templates"),
    (6, 21, "World Music Day", "\U0001f3b5", ["world music day","music day"], "Music-themed templates"),
    (7, 4, "US Independence Day", "\U0001f1fa\U0001f1f8", ["4th of july","fourth of july","independence day","fireworks"], "Red/white/blue templates (US)"),
    (7, 30, "International Friendship Day", "\U0001f46f", ["friendship day","best friend","bff","bestie"], "Best friend reveal templates"),
    (8, 1, "Back to School Season Start", "\U0001f4da", ["back to school","school","college","university","uni","freshman","freshers"], "School transformation, outfit of the day, dorm room reveals"),
    (8, 25, "Notting Hill Carnival", "\U0001f3ad", ["notting hill","carnival","london"], "Carnival-themed templates (UK)"),
    (9, 1, "Autumn Aesthetic Season Start", "\U0001f342", ["autumn","fall","cozy","pumpkin spice","sweater weather"], "Autumn transformation templates, cozy aesthetic"),
    (9, 22, "Autumn Equinox", "\U0001f341", ["autumn equinox","first day of fall"], "Season change templates"),
    (10, 1, "Black History Month UK Start", "\u270a", ["black history month","bhm"], "History reveal templates (UK-specific)"),
    (10, 10, "World Mental Health Day", "\U0001f9e0", ["mental health day","mental health","self care","wellbeing"], "Mental health awareness templates"),
    (10, 31, "Halloween", "\U0001f383", ["halloween","spooky","costume","trick or treat","scary","horror","ghost","witch","zombie","skeleton"], "Costume reveal, spooky transitions, horror edits, makeup transformation"),
    (11, 1, "Dia de los Muertos", "\U0001f480", ["dia de los muertos","day of the dead","muertos"], "Day of the Dead themed templates"),
    (11, 5, "Bonfire Night", "\U0001f386", ["bonfire night","guy fawkes","fireworks","5th november"], "Fireworks templates (UK-specific)"),
    (11, 11, "Remembrance Day", "\U0001f33a", ["remembrance","lest we forget","poppy","veterans"], "Tribute templates"),
    (11, 11, "Singles' Day (11.11)", "\U0001f6cd\ufe0f", ["singles day","11.11","double eleven"], "Shopping/deal templates"),
    (11, 28, "Thanksgiving (US)", "\U0001f983", ["thanksgiving","thankful","grateful","turkey day"], "Gratitude templates (US)"),
    (11, 29, "Black Friday", "\U0001f3f7\ufe0f", ["black friday","sale","deals","shopping","discount","haul"], "Shopping haul templates, deal reveal"),
    (12, 1, "Advent / Christmas Season Start", "\U0001f384", ["advent","christmas countdown","december","festive"], "Countdown templates, advent calendar reveal"),
    (12, 2, "Cyber Monday", "\U0001f4bb", ["cyber monday","online deals","tech deals"], "Tech/shopping templates"),
    (12, 21, "Winter Solstice", "\u2744\ufe0f", ["winter solstice","shortest day","midwinter"], "Winter aesthetic templates"),
    (12, 25, "Christmas Day", "\U0001f385", ["christmas","xmas","santa","present","gift","merry christmas"], "Gift reveal, Christmas morning, outfit templates"),
    (12, 26, "Boxing Day", "\U0001f381", ["boxing day","boxing day sale","haul"], "Sales haul templates (UK)"),
    (12, 31, "New Year's Eve", "\U0001f942", ["new year's eve","nye","countdown","new year","party"], "Year review, countdown templates"),
]

VARIABLE_EVENTS = {
    2026: [
        (2, 17, "Pancake Day / Shrove Tuesday", "\U0001f95e", ["pancake day","shrove tuesday","pancake","lent"], "Pancake recipe/flip templates"),
        (2, 18, "Ash Wednesday / Lent Start", "\u271d\ufe0f", ["lent","ash wednesday","giving up"], "Lent challenge templates"),
        (3, 15, "Mother's Day (UK)", "\U0001f490", ["mother's day","mothering sunday","mum","mom","mama"], "Mum tribute templates (UK date)"),
        (4, 3, "Good Friday", "\u271d\ufe0f", ["good friday","easter","bank holiday"], "Easter weekend templates"),
        (4, 5, "Easter Sunday", "\U0001f423", ["easter","easter egg","bunny","spring","egg hunt","chocolate"], "Easter egg reveal, bunny templates"),
        (4, 6, "Easter Monday", "\U0001f430", ["easter monday","bank holiday","easter"], "Easter content continuation"),
        (5, 4, "Early May Bank Holiday", "\U0001f337", ["bank holiday","may day","long weekend"], "Long weekend content"),
        (5, 25, "Spring Bank Holiday", "\u2600\ufe0f", ["bank holiday","spring","long weekend"], "Long weekend content"),
        (8, 31, "Summer Bank Holiday", "\U0001f3d6\ufe0f", ["bank holiday","end of summer","last weekend"], "End of summer templates"),
        (10, 29, "Half Term Week", "\U0001f383", ["half term","school holiday"], "Halloween prep + family content"),
        (11, 1, "Diwali", "\U0001fa94", ["diwali","deepavali","festival of lights","rangoli"], "Festival of lights templates"),
        (12, 18, "Hanukkah Start", "\U0001f54e", ["hanukkah","chanukah","menorah"], "Hanukkah-themed templates"),
    ],
    2027: [
        (2, 9, "Pancake Day / Shrove Tuesday", "\U0001f95e", ["pancake day","shrove tuesday","pancake","lent"], "Pancake recipe/flip templates"),
        (3, 7, "Mother's Day (UK)", "\U0001f490", ["mother's day","mothering sunday","mum","mom","mama"], "Mum tribute templates"),
        (3, 26, "Good Friday", "\u271d\ufe0f", ["good friday","easter","bank holiday"], "Easter weekend templates"),
        (3, 28, "Easter Sunday", "\U0001f423", ["easter","easter egg","bunny","spring","egg hunt"], "Easter egg reveal"),
        (5, 3, "Early May Bank Holiday", "\U0001f337", ["bank holiday","may day"], "May Day content"),
        (5, 31, "Spring Bank Holiday", "\u2600\ufe0f", ["bank holiday","spring"], "Bank holiday content"),
        (8, 30, "Summer Bank Holiday", "\U0001f3d6\ufe0f", ["bank holiday","end of summer"], "End of summer templates"),
        (10, 21, "Diwali", "\U0001fa94", ["diwali","deepavali","festival of lights"], "Festival of lights templates"),
    ],
}

SEASONAL_TREND_WINDOWS = [
    ((1,1),(1,31),"New Year New Me Season","\U0001f4aa",["new year new me","glow up","transformation","goals"],"Transformation/glow-up templates peak in January"),
    ((2,1),(2,16),"Valentine's Content Window","\U0001f49d",["valentine","love","couple","galentine","single"],"PEAK: Valentine's content goes viral 2 weeks before. Still relevant through weekend after."),
    ((3,1),(3,31),"Spring Glow-Up Season","\U0001f338",["spring","glow up","new season","fresh"],"Spring outfit/aesthetic transformation templates"),
    ((6,1),(8,31),"Summer Content Season","\u2600\ufe0f",["summer","beach","vacation","holiday","travel"],"Travel/beach/summer aesthetic templates"),
    ((9,1),(10,31),"Autumn Aesthetic Season","\U0001f342",["autumn","fall","cozy","pumpkin","sweater"],"Cozy/autumn aesthetic templates"),
    ((10,15),(10,31),"Halloween Peak Window","\U0001f383",["halloween","costume","spooky","scary"],"PEAK: Halloween content."),
    ((11,15),(12,25),"Christmas Content Window","\U0001f384",["christmas","xmas","festive","gift","santa","advent"],"PEAK: Christmas content."),
    ((12,26),(12,31),"Year Review Window","\U0001f4ca",["year review","wrapped","best of","recap"],"Year-in-review templates"),
]

def _get_all_events_for_year(year):
    events = []
    for m, d, name, emoji, kw, ideas in FIXED_EVENTS:
        try: events.append((date(year, m, d), name, emoji, kw, ideas))
        except ValueError: pass
    if year in VARIABLE_EVENTS:
        for m, d, name, emoji, kw, ideas in VARIABLE_EVENTS[year]:
            try: events.append((date(year, m, d), name, emoji, kw, ideas))
            except ValueError: pass
    return sorted(events, key=lambda e: e[0])

def _classify_priority(days_until):
    if days_until < 0: return "REVIEW", "review"
    if days_until == 0: return "TODAY", "today"
    if days_until == 1: return "TOMORROW", "urgent"
    if days_until <= 3: return "THIS WEEK", "high"
    if days_until <= 7: return "NEXT WEEK", "medium"
    if days_until <= 14: return "2 WEEKS", "low"
    return "UPCOMING", "info"

def _format_timing(days_until, event_date):
    if days_until < -1: return f"{abs(days_until)} days ago - still capitalize on late posts"
    if days_until == -1: return "Yesterday - last day to review/capitalize"
    if days_until == 0: return "TODAY - peak content day!"
    if days_until == 1: return "TOMORROW - final prep!"
    if days_until <= 3: return f"In {days_until} days ({event_date.strftime('%A')})"
    if days_until <= 7: return f"In {days_until} days ({event_date.strftime('%A %d %b')})"
    return f"In {days_until} days ({event_date.strftime('%d %b %Y')})"

def get_seasonal_alerts(today=None):
    if today is None: today = date.today()
    alerts = []
    years = [today.year]
    if today.month >= 11: years.append(today.year + 1)
    if today.month <= 1: years.append(today.year - 1)
    for year in years:
        for ev_date, name, emoji, kw, ideas in _get_all_events_for_year(year):
            days = (ev_date - today).days
            if -AFTER_DAYS <= days <= ADVANCE_DAYS:
                pri, pri_level = _classify_priority(days)
                alerts.append({'event':name,'emoji':emoji,'priority':pri,'priority_level':pri_level,
                    'timing':_format_timing(days, ev_date),'days_until':days,'keywords':kw,
                    'template_ideas':ideas,'event_date':ev_date.isoformat()})
    for (sm,sd),(em,ed),name,emoji,kw,ideas in SEASONAL_TREND_WINDOWS:
        try:
            ws, we = date(today.year, sm, sd), date(today.year, em, ed)
            if ws <= today <= we:
                alerts.append({'event':name,'emoji':emoji,'priority':'ACTIVE WINDOW','priority_level':'window',
                    'timing':f"Active now - {(we-today).days} days left",'days_until':0,'keywords':kw,
                    'template_ideas':ideas,'event_date':f"{ws.isoformat()} to {we.isoformat()}"})
        except ValueError: pass
    alerts.sort(key=lambda a:(0 if a['priority_level']=='today' else 1 if a['priority_level']=='urgent' else
        2 if a['priority_level']=='review' else 3 if a['priority_level']=='high' else
        4 if a['priority_level']=='window' else 5 if a['priority_level']=='medium' else
        6 if a['priority_level']=='low' else 7, abs(a['days_until'])))
    return alerts

def format_seasonal_for_discord(alerts):
    if not alerts: return []
    fields = []
    urgent = [a for a in alerts if a['priority_level'] in ('today','urgent','review')]
    upcoming = [a for a in alerts if a['priority_level'] in ('high','medium')]
    watching = [a for a in alerts if a['priority_level'] in ('low','window')]
    if urgent:
        fields.append({"name":"SEASONAL ALERTS","value":"\n".join(f"{a['emoji']} **{a['event']}** - {a['timing']}" for a in urgent[:5]),"inline":False})
    if upcoming:
        fields.append({"name":"UPCOMING","value":"\n".join(f"{a['emoji']} {a['event']} - {a['timing']}" for a in upcoming[:5]),"inline":False})
    if watching:
        fields.append({"name":"ON RADAR","value":"\n".join(f"{a['emoji']} {a['event']} - {a['timing']}" for a in watching[:3]),"inline":False})
    if alerts:
        fields.append({"name":f"Keywords to watch for {alerts[0]['event']}","value":", ".join(alerts[0]['keywords'][:8]),"inline":False})
    return fields

def format_seasonal_for_summary(alerts):
    if not alerts: return "\n\nSEASONAL: No upcoming events in notification window.\n"
    lines = ["\n\n"+"="*50,"SEASONAL CALENDAR ALERTS","="*50,f"Window: {ADVANCE_DAYS} days before, {AFTER_DAYS} day after\n"]
    for a in alerts:
        lines.append(f"  {a['priority']} {a['emoji']} {a['event']}")
        lines.append(f"     Timing: {a['timing']}")
        lines.append(f"     Keywords: {', '.join(a['keywords'][:6])}")
        lines.append(f"     Ideas: {a['template_ideas']}")
        lines.append("")
    return "\n".join(lines)+"\n"

def format_seasonal_for_enhanced(alerts):
    if not alerts: return ["No seasonal events in notification window."]
    result = []
    for a in alerts[:5]:
        line = f"{a['priority']} {a['emoji']} {a['event']} - {a['timing']}"
        if a['priority_level'] in ('today','urgent','high'):
            line += f" | Keywords: {', '.join(a['keywords'][:5])}"
        result.append(line)
    return result

def get_active_seasonal_keywords(today=None):
    return list(set(kw for a in get_seasonal_alerts(today) for kw in a['keywords']))

def match_trend_to_seasonal(trend_text, today=None):
    if not trend_text: return ''
    text_lower = str(trend_text).lower()
    for a in get_seasonal_alerts(today):
        for kw in a['keywords']:
            if kw.lower() in text_lower: return f"{a['emoji']} {a['event']}"
    return ''
