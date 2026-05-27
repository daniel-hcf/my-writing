from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data.db"
WEB_DIR = PROJECT_ROOT / "web"

HOST = "127.0.0.1"
PORT = 3000

DIMENSIONS = ["节奏"]

DEFAULTS = {
    "text": {
        "provider": "anthropic",
        "apiKey": "",
        "baseUrl": "https://api.anthropic.com",
        "model": "claude-sonnet-4-6",
    },
    "image": {
        "provider": "openai",
        "apiKey": "",
        "baseUrl": "https://api.openai.com/v1",
        "model": "gpt-image-1",
    },
}

DAILY_MIN_CHAR_COUNT = 300
OUTLINE_PRACTICE_MIN_CHAR_COUNT = 100
IMAGE_PRACTICE_MIN_CHAR_COUNT = 500
MIN_CHAR_COUNT = IMAGE_PRACTICE_MIN_CHAR_COUNT
