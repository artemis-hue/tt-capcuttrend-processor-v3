#!/usr/bin/env python3
"""
TIKTOK SEASONAL CALENDAR
Version: 2.0.0
Events: 174 fixed + 25 variable (2026) + 3 awareness months + 8 variable (2027)
Notification windows: 14 days BEFORE and 1 day AFTER each event.
Awareness months: Day 1 with 30-day window.
Used by: main.py (get_seasonal_alerts, format functions)
"""
from datetime import date, timedelta

ADVANCE_DAYS = 14
AFTER_DAYS = 1
AWARENESS_MONTH_DAYS = 30  # Awareness months stay active for full month

FIXED_EVENTS = [
    # ── JANUARY ──
    (1, 1, "New Year's Day", "🎆", ["new year's day", "new year", "new beginnings", "2026"], "New year goals/transformation content"),
    (1, 2, "Science Fiction Day", "🚀", ["science fiction day", "sci fi"], "AI/sci-fi themed content — great for your niche"),
    (1, 2, "World Introvert Day", "🤐", ["world introvert day", "introvert"], "Relatable introvert content — high engagement"),
    (1, 4, "World Braille Day", "⠀", ["world braille day", "accessibility"], "Accessibility awareness content"),
    (1, 6, "Epiphany/Three Kings Day", "👑", ["epiphany/three kings day", "three kings day", "epiphany"], "Post-holiday cultural content"),
    (1, 13, "National Sticker Day", "📋", ["national sticker day", "sticker day", "stickers"], "Fun sticker/collage themed content"),
    (1, 14, "Dress Up Your Pet Day", "🐶", ["dress up your pet day", "pet fashion"], "Pet costume content — always viral"),
    (1, 15, "Wikipedia Day", "📖", ["wikipedia day", "knowledge"], "Fun facts or AI knowledge content"),
    (1, 17, "Blue Monday", "😔", ["blue monday", "mental health"], "Motivational/uplifting content"),
    (1, 19, "National Popcorn Day", "🍿", ["national popcorn day", "popcorn"], "Snack/movie night themed content"),
    (1, 21, "National Hugging Day", "🤗", ["national hugging day", "hugging day", "hugs", "love"], "Wholesome relationship content"),
    (1, 24, "International Day of Education", "🎓", ["international day of education", "education day", "learning"], "Learning/growth themed content"),
    (1, 25, "Burns Night", "\U0001f3f4\U000e0067\U000e0062\U000e0073\U000e0063\U000e0074\U000e007f", ["burns night", "scotland", "haggis", "scottish"], "Scottish-themed templates (UK niche)"),
    (1, 27, "Holocaust Memorial Day", "🕯️", ["holocaust memorial day", "never forget"], "Respectful remembrance content"),
    (1, 28, "Data Privacy Day", "🔒", ["data privacy day", "privacy"], "Digital safety tips content"),
    (1, 29, "National Puzzle Day", "🧩", ["national puzzle day", "puzzle day", "brain teaser"], "Interactive puzzle/quiz content"),
    # ── FEBRUARY ──
    (2, 1, "World Hijab Day", "🧣", ["world hijab day", "diversity"], "Cultural appreciation content"),
    (2, 2, "Groundhog Day", "🦫", ["groundhog day"], "Prediction/fortune themed content"),
    (2, 4, "World Cancer Day", "🎗️", ["world cancer day", "cancer awareness"], "Health awareness content"),
    (2, 7, "Send a Card to a Friend Day", "💌", ["send a card to a friend day", "send acard", "friendship"], "Friendship appreciation content"),
    (2, 9, "National Pizza Day", "🍕", ["national pizza day", "pizza"], "Universal food content — always trends"),
    (2, 11, "International Day of Women in Science", "🔬", ["international day of women in science", "women in science", "stem"], "Empowerment/science content"),
    (2, 11, "Safer Internet Day", "🛡️", ["safer internet day", "online safety"], "Digital safety awareness — relevant for AI audience"),
    (2, 13, "Galentine's Day", "👩‍👩‍👧", ["galentine's day", "galentines day", "girl power"], "Female friendship celebration"),
    (2, 14, "Valentine's Day", "💝", ["valentine's day", "valentines day", "love"], "Love/romance themed content"),
    (2, 17, "Random Acts of Kindness Day", "💕", ["random acts of kindness day", "rakday", "kindness"], "Kindness challenge content"),
    (2, 20, "World Day of Social Justice", "⚖️", ["world day of social justice", "social justice day"], "Equality/justice awareness"),
    (2, 20, "Love Your Pet Day", "🐾", ["love your pet day", "pet love"], "Pet appreciation content"),
    (2, 21, "International Mother Language Day", "🗣️", ["international mother language day", "mother language day"], "Language/culture content"),
    (2, 27, "International Polar Bear Day", "🐻‍❄️", ["international polar bear day", "polar bear day", "save the planet"], "Wildlife/environment content"),
    # ── MARCH ──
    (3, 1, "World Compliment Day", "😊", ["world compliment day", "positivity"], "Compliment chain/positivity content"),
    (3, 3, "World Wildlife Day", "🦎", ["world wildlife day", "wildlife"], "Animal/nature content"),
    (3, 8, "International Women's Day", "👩", ["international women's day", "iwd", "womens day"], "Empowerment/celebration content"),
    (3, 10, "Mario Day (Mar10)", "🍄", ["mario day (mar10)", "mario day", "mar10", "gaming"], "Gaming nostalgia content"),
    (3, 14, "Pi Day", "🥧", ["pi day", "math", "314"], "Fun math/nerd culture content"),
    (3, 17, "St Patrick's Day", "☘️", ["st patrick's day", "st patricks day", "irish", "lucky"], "Green/luck themed content"),
    (3, 20, "International Day of Happiness", "😃", ["international day of happiness"], "Happy/uplifting content"),
    (3, 20, "Spring Equinox", "🌸", ["spring equinox", "first day of spring"], "New season/renewal content"),
    (3, 21, "World Poetry Day", "📝", ["world poetry day", "poetry"], "Creative writing/poetry content"),
    (3, 22, "World Water Day", "💧", ["world water day", "water"], "Environmental awareness content"),
    (3, 25, "Waffle Day", "🧇", ["waffle day", "waffles"], "Fun food content"),
    (3, 27, "World Theatre Day", "🎭", ["world theatre day", "theatre"], "Drama/performance content"),
    (3, 31, "World Backup Day", "💾", ["world backup day", "data backup"], "Tech tips content"),
    (3, 31, "Transgender Day of Visibility", "🏳️‍⚧️", ["trans visibility", "transgender", "tdov"], "Visibility/reveal templates"),
    # ── APRIL ──
    (4, 1, "April Fools' Day", "🤡", ["april fools' day", "april fools", "pranks"], "Prank/comedy content"),
    (4, 2, "World Autism Awareness Day", "🧩", ["world autism awareness day", "autism awareness", "waad"], "Awareness/inclusion content"),
    (4, 6, "International Day of Sport", "⚽", ["international day of sport", "sport day", "active life"], "Fitness/sport content"),
    (4, 7, "World Health Day", "🏥", ["world health day", "health"], "Health tips content"),
    (4, 10, "National Siblings Day", "👫", ["national siblings day", "siblings day", "siblings"], "Sibling relationship content"),
    (4, 12, "International Day of Human Space Flight", "🚀", ["international day of human space flight", "space day", "cosmonautics"], "Space/future content"),
    (4, 15, "World Art Day", "🎨", ["world art day", "art"], "Art showcase content"),
    (4, 17, "World Haemophilia Day", "🩸", ["world haemophilia day", "haemophilia day", "awareness"], "Health awareness content"),
    (4, 18, "International Amateur Radio Day", "📻", ["international amateur radio day", "amateur radio day"], "Tech/hobby content"),
    (4, 21, "World Creativity Day", "💡", ["world creativity day", "creativity day", "innovation"], "Creative challenge content"),
    (4, 22, "Earth Day", "🌍", ["earth day", "climate action"], "Environmental action content"),
    (4, 23, "World Book Day", "📚", ["world book day", "reading"], "Book recommendation content"),
    (4, 25, "World Penguin Day", "🐧", ["world penguin day", "penguins"], "Cute animal content"),
    (4, 28, "World Day for Safety at Work", "🛡️", ["world day for safety at work", "safety at work"], "Workplace safety content"),
    (4, 30, "International Jazz Day", "🎷", ["international jazz day", "jazz day", "jazz"], "Music appreciation content"),
    # ── MAY ──
    (5, 1, "International Workers' Day", "🛠️", ["international workers' day", "may day", "workers day"], "Work appreciation content"),
    (5, 2, "Harry Potter Day", "⚡", ["harry potter day", "wizarding"], "Fantasy/nostalgia themed content — huge fandom"),
    (5, 3, "World Press Freedom Day", "📰", ["world press freedom day", "press freedom day"], "Media freedom content"),
    (5, 4, "Star Wars Day", "⚔️", ["star wars day", "may the4th"], "Star Wars/sci-fi content"),
    (5, 5, "Cinco de Mayo", "🇲🇽", ["cinco de mayo", "mexican"], "Cultural celebration content"),
    (5, 8, "World Red Cross Day", "✚", ["world red cross day", "red cross day", "humanitarian"], "Humanitarian content"),
    (5, 10, "World Migratory Bird Day", "🐦", ["world migratory bird day", "migratory bird day", "birds"], "Nature/bird content"),
    (5, 15, "International Day of Families", "👪", ["international day of families", "family day", "family"], "Family themed content"),
    (5, 15, "Endangered Species Day", "🦏", ["endangered species day", "wildlife"], "Wildlife conservation content"),
    (5, 17, "World Telecommunication Day", "📡", ["world telecommunication day", "telecom day", "connectivity"], "Tech/connectivity content"),
    (5, 18, "International Museum Day", "🏛️", ["international museum day", "museum day", "museums", "art"], "Art/culture showcase content"),
    (5, 20, "World Bee Day", "🐝", ["world bee day", "save the bees"], "Bee/pollinator awareness"),
    (5, 21, "World Cultural Diversity Day", "🌏", ["world cultural diversity day", "cultural diversity"], "Diversity celebration content"),
    (5, 25, "Towel Day", "🧴", ["towel day", "dont panic"], "Hitchhiker's Guide fun content"),
    (5, 31, "World No-Tobacco Day", "🚭", ["world no-tobacco day", "no tobacco day", "quit smoking"], "Health awareness content"),
    # ── JUNE ──
    (6, 1, "Global Day of Parents", "👪", ["global day of parents", "global parents day"], "Parent appreciation content"),
    (6, 1, "Pride Month Begins", "🌍", ["pride month begins", "pride month", "pride", "lgbtq"], "Month-long celebration of diversity"),
    (6, 3, "World Bicycle Day", "🚲", ["world bicycle day", "cycling"], "Cycling/active lifestyle content"),
    (6, 5, "World Environment Day", "🌳", ["world environment day", "nature"], "Eco-friendly content"),
    (6, 8, "World Oceans Day", "🌊", ["world oceans day", "ocean life"], "Ocean conservation content"),
    (6, 8, "National Best Friends Day", "👭", ["national best friends day", "best friends day", "bff"], "Friendship content — massive engagement driver"),
    (6, 12, "World Day Against Child Labour", "✋", ["world day against child labour", "end child labour"], "Awareness/advocacy content"),
    (6, 14, "World Blood Donor Day", "🩸", ["world blood donor day", "blood donor day", "give blood"], "Health/donation awareness"),
    (6, 17, "World Day to Combat Desertification", "🏜️", ["world day to combat desertification", "desertification"], "Environmental awareness"),
    (6, 19, "Juneteenth", "✊🏿", ["juneteenth", "freedom"], "Freedom/celebration content"),
    (6, 20, "World Refugee Day", "🕊️", ["world refugee day", "refugees"], "Humanitarian awareness"),
    (6, 21, "Summer Solstice", "☀️", ["summer solstice", "longest day"], "Summer themed content"),
    (6, 21, "International Day of Yoga", "🧘", ["international day of yoga", "yoga day", "yoga"], "Yoga/wellness content"),
    (6, 21, "National Selfie Day", "🤳", ["national selfie day", "selfie"], "Perfect for AI influencer content like Clara"),
    (6, 21, "World Music Day", "🎵", ["world music day", "fete de la musique"], "Music appreciation/playlist content"),
    (6, 23, "International Olympic Day", "🏅", ["international olympic day", "olympic day", "olympics"], "Sport/achievement content"),
    (6, 27, "National Sunglasses Day", "🕶️", ["national sunglasses day", "shades"], "Summer fashion/lifestyle content"),
    (6, 30, "Social Media Day", "📱", ["social media day", "smday"], "Meta social media content"),
    # ── JULY ──
    (7, 1, "International Joke Day", "😂", ["international joke day", "joke day", "funny"], "Comedy/joke content"),
    (7, 2, "World UFO Day", "🛸", ["world ufo day", "world ufoday", "ufo", "aliens"], "Sci-fi/mystery content — great for AI themes"),
    (7, 4, "Independence Day (US)", "🌍", ["independence day (us)", "4th of july", "independence day"], "Celebration/freedom content"),
    (7, 6, "International Kissing Day", "💋", ["international kissing day", "kiss"], "Romance/couple content"),
    (7, 7, "World Chocolate Day", "🍫", ["world chocolate day", "chocolate"], "Chocolate themed content"),
    (7, 11, "World Population Day", "🌍", ["world population day"], "Global awareness content"),
    (7, 15, "World Youth Skills Day", "💪", ["world youth skills day", "youth skills day", "skills"], "Youth empowerment content"),
    (7, 17, "World Emoji Day", "😎", ["world emoji day", "emoji"], "Emoji themed fun content"),
    (7, 18, "Nelson Mandela Day", "✊", ["nelson mandela day", "mandela day", "67minutes"], "Service/leadership content"),
    (7, 20, "International Moon Day", "🌙", ["international moon day", "moon day", "space"], "Space/lunar content"),
    (7, 20, "International Chess Day", "♟️", ["international chess day", "chess day", "chess"], "Strategy/chess content"),
    (7, 26, "International Day of Mangroves", "🌳", ["international day of mangroves", "mangrove day"], "Conservation content"),
    (7, 28, "World Nature Conservation Day", "🌿", ["world nature conservation day", "nature conservation"], "Nature conservation content"),
    (7, 30, "International Friendship Day", "👯", ["international friendship day", "friendship day", "bff"], "Friendship celebration content"),
    # ── AUGUST ──
    (8, 1, "World Wide Web Day", "🌐", ["world wide web day", "wwwday", "internet"], "Internet/web nostalgia content"),
    (8, 8, "International Cat Day", "🐱", ["international cat day", "cats"], "Cat content (always viral)"),
    (8, 9, "International Day of Indigenous Peoples", "🌍", ["international day of indigenous peoples", "indigenous peoples day"], "Cultural respect content"),
    (8, 10, "World Lion Day", "🦁", ["world lion day", "lions"], "Wildlife content"),
    (8, 10, "National Lazy Day", "😴", ["national lazy day", "relax"], "Relatable lazy day content"),
    (8, 12, "International Youth Day", "🤝", ["international youth day", "youth day", "youth"], "Youth empowerment content"),
    (8, 12, "World Elephant Day", "🐘", ["world elephant day", "elephants"], "Wildlife content"),
    (8, 13, "International Left Handers Day", "✋", ["international left handers day", "left handers day"], "Fun quirky content"),
    (8, 15, "National Relaxation Day", "🛀", ["national relaxation day", "relaxation day", "self care"], "Self-care/relaxation content"),
    (8, 19, "World Photography Day", "📷", ["world photography day", "photography"], "Photo showcase content"),
    (8, 19, "World Humanitarian Day", "❤️", ["world humanitarian day"], "Humanitarian awareness"),
    (8, 23, "International Day Against Trafficking", "✋", ["international day against trafficking", "end trafficking"], "Awareness content"),
    (8, 26, "National Dog Day", "🐶", ["national dog day", "dogs"], "Dog content (always viral)"),
    # ── SEPTEMBER ──
    (9, 1, "World Letter Writing Day", "✉️", ["world letter writing day", "letter writing day", "write aletter"], "Handwriting/letter content"),
    (9, 5, "International Day of Charity", "💛", ["international day of charity", "charity day", "give back"], "Charitable giving content"),
    (9, 8, "International Literacy Day", "📖", ["international literacy day", "literacy day", "reading"], "Education/reading content"),
    (9, 10, "World Suicide Prevention Day", "💛", ["world suicide prevention day", "wspd", "suicide prevention"], "Sensitive awareness content"),
    (9, 12, "National Video Games Day", "🎮", ["national video games day", "video games day", "gaming"], "Gaming content"),
    (9, 15, "International Day of Democracy", "🗳️", ["international day of democracy", "democracy day"], "Civic engagement content"),
    (9, 17, "World Patient Safety Day", "🏥", ["world patient safety day", "patient safety day"], "Healthcare awareness content"),
    (9, 19, "Talk Like a Pirate Day", "🏴‍☠️", ["talk like a pirate day", "talk like apirate day", "pirate", "arrr"], "Always goes viral — fun character content"),
    (9, 21, "International Day of Peace", "☮️", ["international day of peace", "peace day", "world peace"], "Peace themed content"),
    (9, 22, "World Car-Free Day", "🚶", ["world car-free day", "car free day", "go green"], "Eco transport content"),
    (9, 23, "Autumn Equinox", "🍁", ["autumn equinox", "first day of fall"], "Autumn/cozy content"),
    (9, 27, "World Tourism Day", "✈️", ["world tourism day", "travel"], "Travel content"),
    (9, 28, "World Rabies Day", "🐕", ["world rabies day"], "Animal health awareness"),
    (9, 29, "World Heart Day", "❤️", ["world heart day", "heart health"], "Heart health content"),
    (9, 30, "International Podcast Day", "🎧", ["international podcast day", "podcast day", "podcasting"], "Podcast themed content"),
    # ── OCTOBER ──
    (10, 1, "International Coffee Day", "☕", ["international coffee day", "coffee"], "Coffee culture content"),
    (10, 1, "World Vegetarian Day", "🥕", ["world vegetarian day", "vegetarian day", "plant based"], "Vegetarian/vegan content"),
    (10, 2, "International Day of Non-Violence", "☮️", ["international day of non-violence", "non violence day", "gandhi"], "Peace/non-violence content"),
    (10, 4, "World Animal Day", "🐾", ["world animal day", "animals"], "Animal welfare content"),
    (10, 5, "World Teachers' Day", "🍎", ["world teachers' day", "world teachers day", "thank ateacher"], "Teacher appreciation content"),
    (10, 10, "World Mental Health Day", "🧠", ["world mental health day", "mental health"], "Mental health awareness"),
    (10, 11, "International Day of the Girl", "👩", ["international day of the girl", "day of the girl", "girl power"], "Girl empowerment content"),
    (10, 16, "World Food Day", "🍽️", ["world food day", "zero hunger"], "Food/hunger awareness content"),
    (10, 16, "Boss's Day", "👔", ["boss's day", "boss day", "bosses day"], "Work culture/appreciation content"),
    (10, 20, "World Statistics Day", "📊", ["world statistics day", "statistics day", "data"], "Fun data/stats content"),
    (10, 24, "United Nations Day", "🇺🇳", ["united nations day", "unday", "united nations"], "Global unity content"),
    (10, 29, "National Internet Day", "💻", ["national internet day", "internet day", "online safety"], "Internet culture content"),
    (10, 31, "Halloween", "🎃", ["halloween", "spooky", "trick or treat"], "Halloween themed content"),
    # ── NOVEMBER ──
    (11, 1, "World Vegan Day", "🌱", ["world vegan day", "vegan"], "Vegan lifestyle content"),
    (11, 3, "National Sandwich Day", "🥪", ["national sandwich day"], "Fun food content"),
    (11, 8, "National STEM Day", "🔬", ["national stem day", "stemday", "science", "tech"], "STEM education content"),
    (11, 11, "Veterans Day / Remembrance Day", "🌍", ["veterans day / remembrance day", "veterans day", "remembrance day", "poppy"], "Respectful remembrance"),
    (11, 11, "Singles' Day (11.11)", "🛍️", ["singles day", "11.11", "double eleven"], "Shopping/deal templates"),
    (11, 13, "World Kindness Day", "💚", ["world kindness day", "be kind"], "Kindness themed content"),
    (11, 14, "World Diabetes Day", "💙", ["world diabetes day", "diabetes"], "Health awareness content"),
    (11, 16, "International Day of Tolerance", "🤝", ["international day of tolerance", "tolerance day"], "Tolerance/acceptance content"),
    (11, 19, "International Men's Day", "👨", ["international men's day", "international mens day"], "Men's wellbeing content"),
    (11, 20, "World Children's Day", "🧒", ["world children's day", "world childrens day", "children"], "Children's rights content"),
    (11, 21, "World Television Day", "📺", ["world television day", "tv"], "TV nostalgia/streaming content"),
    (11, 25, "International Day Against Violence Against Women", "🧡", ["international day against violence against women", "orange day", "end violence"], "Awareness/advocacy content"),
    (11, 29, "Black Friday", "🏷️", ["black friday", "deals", "shopping"], "Deal/shopping content"),
    # ── DECEMBER ──
    (12, 1, "World AIDS Day", "🎗️", ["world aids day", "world aidsday", "hiv"], "Health awareness content"),
    (12, 2, "Cyber Monday", "💻", ["cyber monday", "deals"], "Tech deals content"),
    (12, 3, "International Day of Disabled Persons", "♿", ["international day of disabled persons", "idpd", "disability"], "Inclusion/accessibility content"),
    (12, 4, "National Cookie Day", "🍪", ["national cookie day", "cookies"], "Festive baking/food content"),
    (12, 5, "International Volunteer Day", "🤝", ["international volunteer day", "volunteer day", "give back"], "Volunteering content"),
    (12, 10, "Human Rights Day", "✊", ["human rights day", "rights"], "Human rights awareness"),
    (12, 11, "International Mountain Day", "⛰️", ["international mountain day", "mountain day", "mountains"], "Nature/mountain content"),
    (12, 18, "International Migrants Day", "🌍", ["international migrants day", "migrants day"], "Cultural diversity content"),
    (12, 18, "Ugly Sweater Day", "🧶", ["ugly sweater day", "ugly christmas sweater"], "Viral festive fashion content"),
    (12, 21, "Winter Solstice", "❄️", ["winter solstice", "shortest day"], "Winter themed content"),
    (12, 24, "Christmas Eve", "🎄", ["christmas eve", "xmas"], "Pre-Christmas excitement content"),
    (12, 25, "Christmas Day", "🎅", ["christmas day", "christmas", "merry christmas"], "Christmas celebration content"),
    (12, 26, "Boxing Day", "🎁", ["boxing day", "sales"], "Post-Christmas content"),
    (12, 26, "Kwanzaa Begins", "🕯️", ["kwanzaa begins", "kwanzaa", "happy kwanzaa"], "Cultural celebration content"),
    (12, 31, "New Year's Eve", "🥂", ["new year's eve", "nye", "new years eve", "goodbye2026"], "Year-end reflection content"),
]

AWARENESS_MONTHS = [
    (2, 1, "Black History Month", "✊", ["black history month", "bhm"], "Month-long cultural celebration content"),
    (5, 1, "Mental Health Awareness Month", "🧠", ["mental health awareness month", "mental health month", "mental health"], "Month-long wellbeing content series"),
    (10, 1, "Breast Cancer Awareness Month", "🎀", ["breast cancer awareness month", "breast cancer awareness", "pink october"], "Month-long awareness campaign content"),
]

VARIABLE_EVENTS = {
    2026: [
        (2, 1, "Grammy Awards", "📅", ["grammy awards (approx)", "grammys", "grammy awards", "music"], "Awards reaction/fashion content"),
        (2, 8, "Super Bowl LX", "🏈", ["super bowl lx", "super bowl", "sblx", "game day"], "Massive template opportunity — halftime/ads content"),
        (2, 10, "Chinese New Year", "🧧", ["chinese new year (approx)", "chinese new year", "lunar new year"], "Festive cultural celebration content"),
        (2, 17, "Pancake Day / Shrove Tuesday", "🥞", ["pancake day", "shrove tuesday", "pancake", "lent"], "Pancake recipe/flip templates"),
        (2, 18, "Ash Wednesday / Lent Start", "✝️", ["lent", "ash wednesday", "giving up"], "Lent challenge templates"),
        (3, 1, "Oscars/Academy Awards", "🎬", ["oscars/academy awards (approx)", "oscars", "academy awards"], "Awards show reaction/fashion content"),
        (3, 15, "Mother's Day (UK)", "💐", ["mother's day", "mothering sunday", "mum", "mom", "mama"], "Mum tribute templates (UK date)"),
        (4, 3, "Good Friday", "✝️", ["good friday", "easter", "bank holiday"], "Easter weekend templates"),
        (4, 5, "Easter Sunday", "🐣", ["easter", "easter egg", "bunny", "spring", "egg hunt", "chocolate"], "Easter egg reveal, bunny templates"),
        (4, 6, "Easter Monday", "🐰", ["easter monday", "bank holiday", "easter"], "Easter content continuation"),
        (4, 13, "Eid al-Fitr", "🌙", ["eid al-fitr (approx - varies)", "eid mubarak", "eid", "eid al fitr"], "Major global celebration — end of Ramadan"),
        (4, 14, "Ramadan Begins", "🕌", ["ramadan begins (approx)", "ramadan", "ramadan mubarak"], "Respectful cultural observance content"),
        (5, 4, "Met Gala", "👗", ["met gala", "fashion"], "Fashion/glamour content — massive viral potential"),
        (5, 4, "Early May Bank Holiday", "🌷", ["bank holiday", "may day", "long weekend"], "Long weekend content"),
        (5, 11, "Mother's Day (US/UK approx)", "📅", ["mother's day (us/uk approx)", "mothers day", "mom"], "Mother appreciation content"),
        (5, 25, "Spring Bank Holiday", "☀️", ["bank holiday", "spring", "long weekend"], "Long weekend content"),
        (6, 11, "FIFA World Cup 2026 Kicks Off", "⚽", ["fifa world cup 2026 kicks off (approx)", "fifaworld cup", "world cup2026"], "MASSIVE — hosted in US/Mexico/Canada. Template goldmine"),
        (6, 15, "Father's Day (US/UK approx)", "📅", ["father's day (us/uk approx)", "fathers day", "dad"], "Father appreciation content"),
        (7, 13, "FIFA World Cup 2026 Final", "🏆", ["fifa world cup 2026 final (approx)", "world cup final", "fifa"], "Biggest single sporting event — peak engagement"),
        (8, 26, "Gamescom", "🎮", ["gamescom (approx)", "gamescom", "gaming"], "Gaming convention — template opportunity for gaming content"),
        (8, 31, "Summer Bank Holiday", "🏖️", ["bank holiday", "end of summer", "last weekend"], "End of summer templates"),
        (10, 20, "Diwali (approx - varies yearly)", "🪔", ["diwali (approx - varies yearly)", "diwali", "festival of lights", "happy diwali"], "Major global festival — huge engagement worldwide"),
        (10, 29, "Half Term Week", "🎃", ["half term", "school holiday"], "Halloween prep + family content"),
        (11, 28, "Thanksgiving (US approx)", "📅", ["thanksgiving (us approx)", "thanksgiving", "grateful"], "Gratitude themed content"),
        (12, 26, "Hanukkah Begins", "📅", ["hanukkah begins (approx)", "hanukkah", "chanukah", "festival of lights"], "Cultural celebration content"),
    ],
    2027: [
        (2, 9, "Pancake Day / Shrove Tuesday", "🥞", ["pancake day", "shrove tuesday", "pancake", "lent"], "Pancake recipe/flip templates"),
        (3, 7, "Mother's Day (UK)", "💐", ["mother's day", "mothering sunday", "mum", "mom", "mama"], "Mum tribute templates"),
        (3, 26, "Good Friday", "✝️", ["good friday", "easter", "bank holiday"], "Easter weekend templates"),
        (3, 28, "Easter Sunday", "🐣", ["easter", "easter egg", "bunny", "spring", "egg hunt"], "Easter egg reveal"),
        (5, 3, "Early May Bank Holiday", "🌷", ["bank holiday", "may day"], "May Day content"),
        (5, 31, "Spring Bank Holiday", "☀️", ["bank holiday", "spring"], "Bank holiday content"),
        (8, 30, "Summer Bank Holiday", "🏖️", ["bank holiday", "end of summer"], "End of summer templates"),
        (10, 21, "Diwali", "🪔", ["diwali", "deepavali", "festival of lights"], "Festival of lights templates"),
    ],
}

SEASONAL_TREND_WINDOWS = [
    ((1,1),(1,31),"New Year New Me Season","💪",["new year new me", "glow up", "transformation", "goals"],"Transformation/glow-up templates peak in January"),
    ((2,1),(2,14),"Valentine's Content Window","💝",["valentine", "love", "couple", "galentine", "single"],"PEAK: Valentine's content goes viral 2 weeks before."),
    ((3,1),(3,31),"Spring Glow-Up Season","🌸",["spring", "glow up", "new season", "fresh"],"Spring outfit/aesthetic transformation templates"),
    ((6,1),(8,31),"Summer Content Season","☀️",["summer", "beach", "vacation", "holiday", "travel"],"Travel/beach/summer aesthetic templates"),
    ((9,1),(10,31),"Autumn Aesthetic Season","🍂",["autumn", "fall", "cozy", "pumpkin", "sweater"],"Cozy/autumn aesthetic templates"),
    ((10,15),(10,31),"Halloween Peak Window","🎃",["halloween", "costume", "spooky", "scary"],"PEAK: Halloween content."),
    ((11,15),(12,25),"Christmas Content Window","🎄",["christmas", "xmas", "festive", "gift", "santa", "advent"],"PEAK: Christmas content."),
    ((12,26),(12,31),"Year Review Window","📊",["year review", "wrapped", "best of", "recap"],"Year-in-review templates"),
]


def _get_all_events_for_year(year):
    events = []
    for m, d, name, emoji, kw, ideas in FIXED_EVENTS:
        try: events.append((date(year, m, d), name, emoji, kw, ideas, False))
        except ValueError: pass
    for m, d, name, emoji, kw, ideas in AWARENESS_MONTHS:
        try: events.append((date(year, m, d), name, emoji, kw, ideas, True))
        except ValueError: pass
    if year in VARIABLE_EVENTS:
        for m, d, name, emoji, kw, ideas in VARIABLE_EVENTS[year]:
            try: events.append((date(year, m, d), name, emoji, kw, ideas, False))
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
    if days_until < -1: return f"Ended {abs(days_until)} days ago (review window)"
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
        for ev_date, name, emoji, kw, ideas, is_awareness in _get_all_events_for_year(year):
            after_days = AWARENESS_MONTH_DAYS if is_awareness else AFTER_DAYS
            days = (ev_date - today).days
            if -after_days <= days <= ADVANCE_DAYS:
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
