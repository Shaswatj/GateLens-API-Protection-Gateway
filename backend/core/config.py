import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "secret")
API_KEY = os.getenv("API_KEY", "hackathon2026")
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8001")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
LOGS_MAX_SIZE = int(os.getenv("LOGS_MAX_SIZE", "500"))
BLOCK_SCORE = int(os.getenv("BLOCK_SCORE", "40"))
ALERT_SCORE = int(os.getenv("ALERT_SCORE", "20"))
BLOCK_THRESHOLD = int(os.getenv("BLOCK_THRESHOLD", "5"))
BLOCK_WINDOW_SECONDS = int(os.getenv("BLOCK_WINDOW_SECONDS", "300"))
RATE_LIMIT = os.getenv("RATE_LIMIT", "50/minute")
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"

USER_TIERS = {
    "free": os.getenv("FREE_TIER_LIMIT", "10/minute"),
    "premium": os.getenv("PREMIUM_TIER_LIMIT", "30/minute"),
}

CORS_ORIGINS = ["http://127.0.0.1:8000", "http://localhost:8000"]

MALICIOUS_HEADER_PATTERNS = [
    r"<script", r"javascript:", r"on\w+=",
    r"union.*select", r"';--", r"1=1", r"@@version",
    r"eval\(", r"alert\(", r"document\.cookie"
]

MALICIOUS_BODY_PATTERNS = [
    r"union.*select", r"';--", r"1=1", r"@@version",
    r"<script", r"javascript:", r"on\w+="
]
