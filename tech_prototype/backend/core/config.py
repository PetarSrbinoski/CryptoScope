from __future__ import annotations

from pathlib import Path
from typing import List
import os

BASE_DIR = Path(__file__).resolve().parents[1]
# Allow overriding the DB path via environment (used by Docker compose volumes)
DB_PATH = Path(os.getenv("DB_PATH", str(BASE_DIR / "crypto.db")))

# CORS Origins - Add your Azure App Service URL here
# Format: https://<app-name>.azurewebsites.net
AZURE_APP_URL = os.getenv("AZURE_APP_URL", "")
CUSTOM_DOMAIN = os.getenv("CUSTOM_DOMAIN", "")

CORS_ALLOW_ORIGINS: List[str] = [
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost",
    "http://127.0.0.1",
    "https://frontend.thankfulocean-990ed71e.italynorth.azurecontainerapps.io",
    # Azure frontend App Service (HTTP + HTTPS)
    "http://cryptoscope-frontend.azurewebsites.net",
    "https://cryptoscope-frontend.azurewebsites.net",
    
]

# Add Azure App Service URL if available
if AZURE_APP_URL:
    CORS_ALLOW_ORIGINS.append(f"https://{AZURE_APP_URL}")
if CUSTOM_DOMAIN:
    CORS_ALLOW_ORIGINS.append(f"https://{CUSTOM_DOMAIN}")

TECHNICAL_MS_URL = os.getenv(
    "TECHNICAL_MS_URL",
    "https://cryptoscope-technical-ms.azurewebsites.net",
)

LSTM_MS_URL = os.getenv(
    "LSTM_MS_URL",
    "https://cryptoscope-lstm-ms.azurewebsites.net",
)
