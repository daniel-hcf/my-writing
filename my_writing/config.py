from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data.db"
WEB_DIR = PROJECT_ROOT / "web"

HOST = "127.0.0.1"
PORT = 3000

DIMENSIONS = [
    "人物塑造",
    "对话描写",
    "场景描写",
    "叙事结构",
    "情感表达",
    "语言文采",
    "细节描写",
]

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

MIN_CHAR_COUNT = 500
