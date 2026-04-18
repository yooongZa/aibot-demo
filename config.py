import os

from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

MAX_TURNS = 20
MAX_HISTORY_MESSAGES = MAX_TURNS * 2
MAX_INPUT_CHARS = 1000
REQUEST_TIMEOUT = 30
RETRY_ATTEMPTS = 3

# Optional auth — set AUTH_ENABLED=1 and AUTH_USERS="user1:pw1,user2:pw2" to require login
AUTH_ENABLED = os.getenv("AUTH_ENABLED", "").strip() in ("1", "true", "yes")


def parse_auth_users() -> dict[str, str]:
    raw = os.getenv("AUTH_USERS", "").strip()
    if not raw:
        return {}
    pairs: dict[str, str] = {}
    for entry in raw.split(","):
        if ":" in entry:
            user, pw = entry.split(":", 1)
            pairs[user.strip()] = pw.strip()
    return pairs


def api_key_available() -> bool:
    return bool(GOOGLE_API_KEY and GOOGLE_API_KEY.strip())
