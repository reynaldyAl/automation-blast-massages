"""
config.py — Konfigurasi terpusat dari file .env
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env dari root project
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _get_bool(key: str, default: bool = False) -> bool:
    return os.getenv(key, str(default)).strip().lower() in ("true", "1", "yes")


def _get_int(key: str, default: int = 0) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


class Config:
    # === BASE ===
    BASE_DIR: Path = BASE_DIR

    # === CHANNEL ===
    SEND_WA: bool = _get_bool("SEND_WA", True)
    SEND_SMS: bool = _get_bool("SEND_SMS", True)

    # === WHATSAPP ===
    WA_DELAY_SECONDS: int = _get_int("WA_DELAY_SECONDS", 5)
    WA_TIMEOUT_SECONDS: int = _get_int("WA_TIMEOUT_SECONDS", 30)
    WA_HEADLESS: bool = _get_bool("WA_HEADLESS", False)
    WA_PROFILE_DIR: Path = BASE_DIR / os.getenv("WA_PROFILE_DIR", "wa_profile")

    # === SMS / ADB ===
    SMS_DELAY_SECONDS: int = _get_int("SMS_DELAY_SECONDS", 10)
    ADB_DEVICE_ID: str = os.getenv("ADB_DEVICE_ID", "").strip()
    ADB_SEND_WAIT: int = _get_int("ADB_SEND_WAIT", 3)

    # === RETRY ===
    RETRY_FAILED: bool = _get_bool("RETRY_FAILED", True)
    MAX_RETRY: int = _get_int("MAX_RETRY", 2)

    # === SCHEDULER ===
    SCHEDULER_ENABLED: bool = _get_bool("SCHEDULER_ENABLED", False)
    SCHEDULER_CRON: str = os.getenv("SCHEDULER_CRON", "0 9 * * *")

    # === PATHS ===
    INPUT_CSV: Path = BASE_DIR / os.getenv("INPUT_CSV", "data/input.csv")
    TEMPLATE_FILE: Path = BASE_DIR / os.getenv("TEMPLATE_FILE", "templates/bpjs_message.txt")
    REPORT_DIR: Path = BASE_DIR / os.getenv("REPORT_DIR", "data/reports")
    SCREENSHOT_DIR: Path = BASE_DIR / os.getenv("SCREENSHOT_DIR", "screenshots")
    STATE_FILE: Path = BASE_DIR / os.getenv("STATE_FILE", ".state.json")

    @classmethod
    def ensure_dirs(cls):
        """Buat semua direktori yang dibutuhkan jika belum ada."""
        for d in [cls.REPORT_DIR, cls.SCREENSHOT_DIR, cls.WA_PROFILE_DIR]:
            d.mkdir(parents=True, exist_ok=True)

    @classmethod
    def validate(cls):
        """Validasi konfigurasi wajib."""
        errors = []
        if not cls.INPUT_CSV.exists():
            errors.append(f"File CSV tidak ditemukan: {cls.INPUT_CSV}")
        if not cls.TEMPLATE_FILE.exists():
            errors.append(f"File template tidak ditemukan: {cls.TEMPLATE_FILE}")
        if not cls.SEND_WA and not cls.SEND_SMS:
            errors.append("Minimal satu channel (SEND_WA atau SEND_SMS) harus aktif.")
        return errors


# Singleton instance
config = Config()
