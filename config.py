"""
config.py — Centralized configuration loader.

Reads environment variables from .env and exposes typed constants.
Validates that all required keys are present on import.
"""

import os
import sys
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv()


def _get_required(key: str) -> str:
    """Get a required environment variable or exit with an error."""
    value = os.getenv(key)
    if not value:
        print(f"[ERROR] Missing required environment variable: {key}")
        print(f"        Please set it in your .env file. See .env.example for reference.")
        sys.exit(1)
    return value


def _get_optional(key: str, default: str = "") -> str:
    """Get an optional environment variable with a default."""
    return os.getenv(key, default)


# Supabase (PostgreSQL)
SUPABASE_URL: str = _get_required("SUPABASE_URL")
SUPABASE_KEY: str = _get_required("SUPABASE_KEY")

# LLM Provider
LLM_PROVIDER: str = _get_optional("LLM_PROVIDER", "gemini").lower()  # "gemini" or "openai"

# Google Gemini (primary — free)
GEMINI_API_KEY: str = _get_optional("GEMINI_API_KEY")
GEMINI_MODEL: str = _get_optional("GEMINI_MODEL", "gemini-2.0-flash")

# OpenAI (fallback)
OPENAI_API_KEY: str = _get_optional("OPENAI_API_KEY")
OPENAI_MODEL: str = _get_optional("OPENAI_MODEL", "gpt-4o-mini")

# SMTP Email
SMTP_HOST: str = _get_optional("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT: int = int(_get_optional("SMTP_PORT", "587"))
SMTP_USER: str = _get_optional("SMTP_USER")
SMTP_PASSWORD: str = _get_optional("SMTP_PASSWORD")
NOTIFICATION_EMAIL: str = _get_optional("NOTIFICATION_EMAIL")

# MS Teams Webhook
TEAMS_WEBHOOK_URL: str = _get_optional("TEAMS_WEBHOOK_URL")

# Derived flags
EMAIL_CONFIGURED: bool = bool(SMTP_USER and SMTP_PASSWORD and NOTIFICATION_EMAIL)
TEAMS_CONFIGURED: bool = bool(TEAMS_WEBHOOK_URL)

# Validate LLM keys
if LLM_PROVIDER == "gemini" and not GEMINI_API_KEY:
    print("[ERROR] LLM_PROVIDER is set to 'gemini' but GEMINI_API_KEY is missing.")
    print("        Set GEMINI_API_KEY in .env, or switch LLM_PROVIDER to 'openai'.")
    sys.exit(1)
elif LLM_PROVIDER == "openai" and not OPENAI_API_KEY:
    print("[ERROR] LLM_PROVIDER is set to 'openai' but OPENAI_API_KEY is missing.")
    print("        Set OPENAI_API_KEY in .env, or switch LLM_PROVIDER to 'gemini'.")
    sys.exit(1)