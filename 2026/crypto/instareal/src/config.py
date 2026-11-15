import os
import secrets

FLAG = os.environ.get("flag")
MONGO_URI = "mongodb://mongo:27017/instareal"
SESSION_SECRET = secrets.token_urlsafe(24)
ADMIN_PASSWORD = secrets.token_urlsafe(24)

# Seeding / audit config
MAX_AUDIT_RECORDS = 500
FLAG_COUNTER_ID_MIN = 500
FLAG_COUNTER_ID_MAX = 1000
SEED_REALS = 2000

# Real view derivation constants
HUE_MODULO = 360
HUE_OFFSET = 82
LIKES_BASE = 1200
LIKES_MAX = 90000
TILT_RANGE = 12
TILT_CENTER = 6

# Real view / seeding pools
REAL_CATEGORIES = (
    "perspective",
    "courage",
    "growth",
    "gratitude",
    "possibility",
    "resilience",
    "mindfulness",
    "compassion",
    "creativity",
    "determination",
)
REAL_TITLES = (
    "Begin before you feel ready",
    "There is still time",
    "Make room for wonder",
    "Small steps still count",
    "Let the light in",
    "Your journey is unique and worth taking",
    "Every day is a fresh start",
    "Trust the process of becoming",
    "The best is yet to come",
    "Embrace the beauty of imperfection",
    "What you seek is seeking you",
    "Today holds infinite possibilities",
    "Growth begins at the edge of comfort",
    "Your potential is unlimited",
)
REAL_CONTENTS = (
    "You do not have to see the whole path to take the next step.",
    "The life you want can begin with one honest choice today.",
    "Progress is still progress, even when nobody else can see it.",
    "There is something good waiting on the other side of trying.",
    "Your pace is allowed to be different and still be enough.",
    "What you have in mind matters less than what you do.",
    "The only way to discover limits is to go beyond them.",
    "Small daily improvements are the key to transforming yourself.",
    "Every moment is a chance to start over.",
    "Believe in your ability to overcome anything.",
)

# Creator username pools
CREATOR_ADJECTIVES = (
    "quiet",
    "amber",
    "little",
    "neon",
    "soft",
    "hidden",
    "brisk",
    "hazy",
    "slow",
    "bright",
    "wild",
    "silver",
    "velvet",
    "restless",
    "warm",
    "electric",
)
CREATOR_NOUNS = (
    "orbit",
    "signal",
    "static",
    "comet",
    "echo",
    "current",
    "mosaic",
    "drift",
    "window",
    "garden",
    "radio",
    "moon",
    "river",
    "shadow",
    "spark",
    "story",
)
CREATOR_SUFFIXES = (
    "drifter",
    "keeper",
    "walker",
    "dreamer",
    "listener",
    "maker",
    "finder",
    "watcher",
    "rider",
    "wanderer",
    "sketcher",
    "caller",
    "seeker",
    "dancer",
    "scout",
    "writer",
)
