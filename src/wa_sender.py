"""
wa_sender.py — WhatsApp Web automation menggunakan Playwright

Fitur:
- Persistent browser profile (QR scan sekali saja)
- Deteksi nomor tidak terdaftar di WA
- Screenshot otomatis saat error
- Dry run mode
"""

import time
import urllib.parse
from pathlib import Path
from datetime import datetime
from typing import Optional

from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, TimeoutError as PWTimeout

from config import config
from reporter import Status


class WAError(Exception):
    pass


class WASender:
    """Mengelola pengiriman pesan via WhatsApp Web menggunakan Playwright."""

    # Selector yang digunakan di WA Web
    SEL_SEND_BTN      = '[data-testid="send"]'
    SEL_MSG_INPUT     = '[data-testid="compose-input"]'
    SEL_INVALID_PHONE = 'div[data-animate-modal-body="true"]'   # Modal "nomor tidak valid"
    SEL_INTRO_TITLE   = '._amig'                                # Elemen saat WA pertama buka
    SEL_CHAT_HEADER   = '[data-testid="conversation-header"]'   # Konfirmasi chat terbuka

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    def start(self):
        """Buka browser dan muat profil WA (scan QR jika belum login)."""
        if self.dry_run:
            return

        config.ensure_dirs()
        self._playwright = sync_playwright().start()

        self._context = self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(config.WA_PROFILE_DIR),
            headless=config.WA_HEADLESS,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
            viewport={"width": 1280, "height": 800},
        )

        self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
        self._page.goto("https://web.whatsapp.com", timeout=config.WA_TIMEOUT_SECONDS * 1000)

        print("\n  [WA] Menunggu WhatsApp Web siap...")
        print("  [WA] Jika belum login, silakan scan QR code di browser.")

        # Tunggu sampai chat list muncul (tanda sudah login)
        try:
            self._page.wait_for_selector(
                '#side, [data-testid="chat-list"]',
                timeout=120_000,  # 2 menit untuk scan QR
            )
            print("  [WA] ✓ WhatsApp Web siap!\n")
        except PWTimeout:
            raise WAError("Timeout menunggu login WA Web. Pastikan QR sudah di-scan.")

    def send(self, phone_e164: str, message: str) -> tuple[str, str, str]:
        """
        Kirim pesan WA ke nomor tertentu.

        Args:
            phone_e164: Nomor dalam format E.164 tanpa '+' (contoh: 62812xxx)
            message: Isi pesan

        Returns:
            tuple (status, error_message, screenshot_path)
        """
        if self.dry_run:
            return Status.SUCCESS, "", ""

        encoded_msg = urllib.parse.quote(message)
        url = f"https://web.whatsapp.com/send?phone={phone_e164}&text={encoded_msg}"

        try:
            self._page.goto(url, timeout=config.WA_TIMEOUT_SECONDS * 1000)

            # Tunggu: apakah chat terbuka atau ada modal error
            try:
                self._page.wait_for_selector(
                    f"{self.SEL_SEND_BTN}, {self.SEL_INVALID_PHONE}",
                    timeout=config.WA_TIMEOUT_SECONDS * 1000,
                )
            except PWTimeout:
                screenshot = self._take_screenshot(phone_e164, "timeout")
                return Status.FAILED, "Timeout menunggu WA Web merespons", screenshot

            # Cek apakah muncul modal "nomor tidak valid" atau "tidak di WA"
            invalid_modal = self._page.query_selector(self.SEL_INVALID_PHONE)
            if invalid_modal:
                modal_text = invalid_modal.inner_text().lower()
                screenshot = self._take_screenshot(phone_e164, "not_on_wa")
                if "invalid" in modal_text or "phone number" in modal_text or "tidak valid" in modal_text:
                    return Status.INVALID_PHONE, f"Nomor tidak valid di WA: {modal_text[:80]}", screenshot
                return Status.NOT_ON_WA, f"Nomor tidak terdaftar di WA: {modal_text[:80]}", screenshot

            # Cek apakah tombol Send ada dan bisa diklik
            send_btn = self._page.query_selector(self.SEL_SEND_BTN)
            if not send_btn:
                screenshot = self._take_screenshot(phone_e164, "no_send_btn")
                return Status.FAILED, "Tombol kirim tidak ditemukan", screenshot

            send_btn.click()

            # Tunggu sebentar untuk konfirmasi pesan terkirim
            time.sleep(1.5)
            return Status.SUCCESS, "", ""

        except PWTimeout as e:
            screenshot = self._take_screenshot(phone_e164, "timeout")
            return Status.FAILED, f"Playwright timeout: {str(e)[:100]}", screenshot
        except Exception as e:
            screenshot = self._take_screenshot(phone_e164, "error")
            return Status.FAILED, f"Error tidak terduga: {str(e)[:100]}", screenshot

    def _take_screenshot(self, phone: str, reason: str) -> str:
        """Ambil screenshot dan simpan. Kembalikan path file."""
        try:
            config.SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"error_{phone}_{reason}_{ts}.png"
            path = config.SCREENSHOT_DIR / filename
            self._page.screenshot(path=str(path))
            return str(path)
        except Exception:
            return ""

    def close(self):
        """Tutup browser."""
        if self._context:
            try:
                self._context.close()
            except Exception:
                pass
        if self._playwright:
            try:
                self._playwright.stop()
            except Exception:
                pass

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.close()
