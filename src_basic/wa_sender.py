"""
wa_sender.py — WhatsApp Web automation menggunakan Playwright

Fitur:
- Persistent browser profile (QR scan sekali saja)
- Deteksi nomor tidak terdaftar di WA
- Screenshot otomatis saat error
- Dry run mode

Catatan Windows:
- Playwright di-import secara lazy (hanya saat WA benar-benar digunakan)
- Untuk SMS-only di Windows, file ini bisa di-import tanpa playwright terinstall
"""

import time
import urllib.parse
from pathlib import Path
from datetime import datetime
from typing import Optional

# Playwright di-import lazy di dalam method start() agar tidak error
# jika hanya pakai SMS (requirements-sms.txt, tanpa playwright)

from config import config
from reporter import Status

# Flag untuk cek apakah playwright tersedia
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class WAError(Exception):
    pass


class WASender:
    """Mengelola pengiriman pesan via WhatsApp Web menggunakan Playwright."""

    # Selector yang digunakan di WA Web
    SEL_SEND_BTN      = '[data-testid="send"], span[data-icon="send"]'
    SEL_MSG_INPUT     = 'div[contenteditable="true"][data-tab="10"], div[title="Type a message"], [data-testid="conversation-compose-box-input"]'
    SEL_INVALID_PHONE = 'div[data-animate-modal-body="true"]'   # Modal "nomor tidak valid"
    SEL_INTRO_TITLE   = '._amig'                                # Elemen saat WA pertama buka
    SEL_CHAT_HEADER   = '[data-testid="conversation-header"]'   # Konfirmasi chat terbuka

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None

    def start(self):
        """Buka browser dan muat profil WA (scan QR jika belum login)."""
        if not PLAYWRIGHT_AVAILABLE:
            raise WAError(
                "Playwright tidak terinstall.\n"
                "Untuk WA: gunakan Docker (docker-compose run --rm blast run --wa-only)\n"
                "Atau install: pip install playwright && playwright install chromium"
            )

        config.ensure_dirs()
        
        # Bersihkan SingletonLock yang tertinggal jika browser crash / Docker distop paksa
        singleton_lock = config.WA_PROFILE_DIR / "SingletonLock"
        if singleton_lock.exists():
            try:
                singleton_lock.unlink()
            except OSError:
                pass
                
        self._playwright = sync_playwright().start()

        import shutil
        executable_path = shutil.which("chromium") or shutil.which("google-chrome") or shutil.which("chrome")
        
        launch_args = {
            "user_data_dir": str(config.WA_PROFILE_DIR),
            "headless": config.WA_HEADLESS,
            "args": ["--no-sandbox", "--disable-dev-shm-usage"],
            "viewport": {"width": 1280, "height": 800},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        if executable_path:
            launch_args["executable_path"] = executable_path

        self._context = self._playwright.chromium.launch_persistent_context(**launch_args)

        self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
        self._page.goto("https://web.whatsapp.com", timeout=config.WA_TIMEOUT_SECONDS * 1000)

        print("\n  [WA] Menunggu WhatsApp Web siap...")
        print("  [WA] Jika belum login, silakan scan QR code di browser.")

        # Tunggu loading selesai (bisa muncul QR atau langsung chat list jika sudah login)
        try:
            # Wait for either the QR code canvas or the main chat window
            element = self._page.wait_for_selector(
                'canvas, [data-testid="chat-list"], #side',
                timeout=60_000  # 1 menit nunggu loading
            )
            
            # Jika yang muncul adalah canvas, berarti minta QR
            if element and element.evaluate("el => el.tagName.toLowerCase()") == "canvas":
                # Beri sedikit waktu agar QR dirender sempurna
                time.sleep(1)
                qr_path = config.SCREENSHOT_DIR / "qr_login.png"
                self._page.screenshot(path=str(qr_path))
                print(f"  [WA] 📸 Screenshot layar login disimpan ke: {qr_path}")
                print("  [WA] Buka file gambar tersebut (di komputer Anda) untuk men-scan QR Code!")
                
                # Sekarang tunggu user scan QR sampai chat list muncul
                self._page.wait_for_selector(
                    '#side, [data-testid="chat-list"]',
                    timeout=120_000,  # 2 menit untuk scan QR
                )
                
                if qr_path.exists():
                    qr_path.unlink()
                    
            print("  [WA] ✓ WhatsApp Web siap!\n")
        except PWTimeout:
            raise WAError("Timeout menunggu login WA Web. Pastikan koneksi internet stabil dan QR di-scan tepat waktu.")

    def send(self, phone_e164: str, message: str) -> tuple[str, str, str]:
        """
        Kirim pesan WA ke nomor tertentu.
        """
        if self.dry_run:
            return Status.SUCCESS, "", ""

        # Kita TIDAK memasukkan teks ke URL lagi karena bisa memicu bug rendering WA.
        # Cukup buka chat-nya saja.
        url = f"https://web.whatsapp.com/send?phone={phone_e164}"

        try:
            self._page.goto(url, timeout=config.WA_TIMEOUT_SECONDS * 1000)
            time.sleep(2)  # Tunggu SPA WhatsApp Web transisi ke chat baru

            # Tunggu: apakah chat terbuka (kotak input muncul) atau ada modal error
            start_time = time.time()
            input_box = None
            
            while time.time() - start_time < config.WA_TIMEOUT_SECONDS:
                # Cek jika kotak input pesan sudah muncul (tanda chat siap)
                for selector in self.SEL_MSG_INPUT.split(','):
                    try:
                        input_box = self._page.query_selector(selector.strip())
                        if input_box and input_box.is_visible():
                            break
                    except Exception:
                        pass
                        
                if input_box:
                    # Tunggu sebentar lagi untuk memastikan React sudah stabil
                    time.sleep(1)
                    break
                    
                # Cek jika ada modal yang muncul
                invalid_modal = self._page.query_selector(self.SEL_INVALID_PHONE)
                if invalid_modal:
                    modal_text = invalid_modal.inner_text().lower()
                    # ABAIKAN modal loading "starting chat" atau "memulai chat"
                    if "starting chat" not in modal_text and "memulai chat" not in modal_text and modal_text.strip():
                        screenshot = self._take_screenshot(phone_e164, "not_on_wa")
                        if "invalid" in modal_text or "phone number" in modal_text or "tidak valid" in modal_text:
                            return Status.INVALID_PHONE, f"Nomor tidak valid di WA: {modal_text[:80].replace(chr(10), ' ')}", screenshot
                        return Status.NOT_ON_WA, f"Nomor tidak terdaftar di WA: {modal_text[:80].replace(chr(10), ' ')}", screenshot
                
                self._page.wait_for_timeout(500) # Tunggu 500ms
            else:
                screenshot = self._take_screenshot(phone_e164, "timeout")
                return Status.FAILED, "Timeout menunggu WA Web merespons", screenshot

            # KETIK PESAN SECARA VIRTUAL!
            # Ini sangat solid karena persis seperti manusia mengetik
            # Beri jeda 1 detik agar animasi loading chat WA benar-benar selesai sebelum mengetik
            time.sleep(1)
            
            input_box.click()
            time.sleep(0.5)
            
            # Kita bersihkan dulu (siapa tahu ada sisa draf)
            self._page.keyboard.press("Control+A")
            self._page.keyboard.press("Backspace")
            
            # Paste/fill pesannya menggunakan insert_text (seperti Ctrl+V)
            self._page.keyboard.insert_text(message)
            time.sleep(1) # Beri waktu sedikit agar React merender teksnya
            
            # Tekan Enter
            self._page.keyboard.press("Enter")

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
        """Fungsi screenshot dinonaktifkan atas permintaan user untuk menghemat memori (1K data)."""
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
