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
        """Buka browser dan muat profil WA (scan QR atau login nomor+kode jika belum login)."""
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
        print("  [WA] (Menunggu tanpa batas — proses akan lanjut setelah WA Web terload)")

        # Tunggu loading: bisa muncul canvas (QR), chat-list (sudah login), atau intro screen
        element = self._page.wait_for_selector(
            'canvas, [data-testid="chat-list"], #side',
            timeout=0  # Tanpa batas
        )

        # Jika sudah login langsung (ada chat-list / #side), skip proses login
        tag = element.evaluate("el => el.tagName.toLowerCase()") if element else ""
        if tag != "canvas":
            print("  [WA] ✓ WhatsApp Web siap!\n")
            return

        # ── Belum login: tampil QR / intro screen ─────────────────────────────
        login_phone = getattr(config, "WA_LOGIN_PHONE", "").strip()

        if login_phone:
            # ── Mode: Login via Nomor + Kode (tanpa QR) ───────────────────────
            print(f"\n  [WA] 📱 Mode login: Nomor telepon ({login_phone})")
            print("  [WA] Mencari tombol 'Link with phone number'...")

            # Tunggu tombol "Link with phone number" muncul
            link_btn = None
            for _ in range(30):  # Coba max 15 detik
                for sel in [
                    'button:has-text("Link with phone number")',
                    'button:has-text("Tautkan dengan nomor telepon")',
                    '[data-testid="link-device-phone-number-button"]',
                    'span:text-is("Link with phone number")',
                    'span:text-is("Tautkan dengan nomor telepon")',
                ]:
                    try:
                        btn = self._page.query_selector(sel)
                        if btn and btn.is_visible():
                            link_btn = btn
                            break
                    except Exception:
                        pass
                if link_btn:
                    break
                self._page.wait_for_timeout(500)

            if link_btn:
                try:
                    link_btn.click()
                    time.sleep(1.5)
                    print("  [WA] ✓ Tombol 'Link with phone number' diklik.")

                    # Tunggu field input nomor muncul
                    phone_input = None
                    for _ in range(20):
                        for sel in [
                            'input[aria-label*="phone"]',
                            'input[data-testid="phone-number-input"]',
                            'input[type="tel"]',
                            'input[placeholder*="phone"]',
                            'input[aria-label*="nomor"]',
                        ]:
                            try:
                                inp = self._page.query_selector(sel)
                                if inp and inp.is_visible():
                                    phone_input = inp
                                    break
                            except Exception:
                                pass
                        if phone_input:
                            break
                        self._page.wait_for_timeout(500)

                    if phone_input:
                        phone_input.click()
                        time.sleep(0.5)
                        # Bersihkan & isi nomor (format: 628xxxx tanpa +)
                        phone_input.fill("")
                        phone_input.type(login_phone, delay=80)
                        time.sleep(0.5)
                        print(f"  [WA] ✓ Nomor {login_phone} diisi.")

                        # Klik tombol Next / Selanjutnya
                        for sel in [
                            'button:has-text("Next")',
                            'button:has-text("Selanjutnya")',
                            '[data-testid="link-device-phone-number-button"]',
                            'button[type="submit"]',
                        ]:
                            try:
                                nb = self._page.query_selector(sel)
                                if nb and nb.is_visible():
                                    nb.click()
                                    break
                            except Exception:
                                pass

                        time.sleep(2)

                        # Ambil kode 8 digit yang muncul di layar
                        code_text = ""
                        for _ in range(30):  # Coba max 15 detik
                            for sel in [
                                '[data-testid="link-device-phone-number-code"]',
                                'div[class*="landing-otp-code"]',
                                'span[class*="otp-code"]',
                                'div[class*="otp"]',
                                '[aria-label*="code"]',
                            ]:
                                try:
                                    el = self._page.query_selector(sel)
                                    if el:
                                        txt = el.inner_text().strip()
                                        # Kode biasanya format: XXXX-XXXX atau 8 karakter
                                        if txt and len(txt.replace("-", "").replace(" ", "")) >= 7:
                                            code_text = txt
                                            break
                                except Exception:
                                    pass
                            if code_text:
                                break
                            self._page.wait_for_timeout(500)

                        if code_text:
                            print("\n" + "=" * 55)
                            print("  [WA] 🔑 KODE LINK PERANGKAT:")
                            print(f"\n         >>>  {code_text}  <<<\n")
                            print("  Buka WhatsApp HP Anda:")
                            print("  Menu (⋮) → Perangkat Tertaut → Tautkan Perangkat")
                            print("  Masukkan kode di atas saat diminta.")
                            print("=" * 55 + "\n")
                        else:
                            # Kode tidak terdeteksi otomatis — minta user lihat browser
                            print("\n" + "=" * 55)
                            print("  [WA] 🔑 Kode muncul di browser.")
                            print("  Lihat browser, catat kode 8 digit yang tampil,")
                            print("  lalu masukkan ke WhatsApp HP Anda:")
                            print("  Menu (⋮) → Perangkat Tertaut → Tautkan Perangkat")
                            print("=" * 55 + "\n")
                    else:
                        print("  [WA] ⚠ Field input nomor tidak ditemukan — lihat browser.")

                except Exception as e:
                    print(f"  [WA] ⚠ Gagal klik tombol login nomor: {e}")
                    print("  [WA] Silakan lanjutkan manual di browser.")

            else:
                print("  [WA] ⚠ Tombol 'Link with phone number' tidak ditemukan.")
                print("  [WA] Coba klik manual di browser atau gunakan QR.")

        else:
            # ── Mode default: QR Code ──────────────────────────────────────────
            time.sleep(1)
            qr_path = config.SCREENSHOT_DIR / "qr_login.png"
            self._page.screenshot(path=str(qr_path))
            print(f"  [WA] 📸 Screenshot layar login disimpan ke: {qr_path}")
            print("  [WA] Buka file gambar tersebut (di komputer Anda) untuk men-scan QR Code!")

        print("  [WA] Menunggu login selesai... (tidak ada batas waktu)")
        # Tunggu sampai chat list muncul (login berhasil) — tanpa batas waktu
        self._page.wait_for_selector(
            '#side, [data-testid="chat-list"]',
            timeout=0
        )

        # Hapus screenshot QR jika ada
        qr_path_cleanup = config.SCREENSHOT_DIR / "qr_login.png"
        if qr_path_cleanup.exists():
            qr_path_cleanup.unlink()

        print("  [WA] ✓ WhatsApp Web siap!\n")



    def send(self, phone_e164: str, message: str) -> tuple[str, str, str]:
        """
        Kirim pesan WA ke nomor tertentu.

        Dry-run mode: Buka chat, ketik pesan, tapi TIDAK kirim (tidak tekan Enter).
        Pesan dibersihkan setelah 2 detik agar bisa lanjut ke peserta berikutnya.
        """
        # Cukup buka chat-nya saja (teks di-type manual, bukan lewat URL param).
        url = f"https://web.whatsapp.com/send?phone={phone_e164}"

        # Timeout polling terpisah dari timeout goto, agar loading halaman yang
        # lambat tidak memotong jatah waktu deteksi kotak input.
        POLL_TIMEOUT_SEC = max(config.WA_TIMEOUT_SECONDS, 60)

        try:
            # Buka URL — tunggu DOM interactive (bukan networkidle agar tidak hang
            # pada koneksi lambat yang terus-menerus melakukan polling WA)
            self._page.goto(url, timeout=config.WA_TIMEOUT_SECONDS * 1000,
                            wait_until="domcontentloaded")

            # Tunggu network relatif tenang (maks 10 detik extra) sebelum polling
            try:
                self._page.wait_for_load_state("networkidle", timeout=10_000)
            except Exception:
                pass  # Tidak masalah jika masih ada request background

            time.sleep(1.5)  # Jeda minimum agar React SPA sempat merender

            # ── Polling: tunggu kotak input atau modal error ──────────────────
            start_time = time.time()
            input_box = None

            while time.time() - start_time < POLL_TIMEOUT_SEC:
                # Cek kotak input pesan (tanda chat terbuka dan siap)
                for selector in self.SEL_MSG_INPUT.split(','):
                    try:
                        el = self._page.query_selector(selector.strip())
                        if el and el.is_visible():
                            input_box = el
                            break
                    except Exception:
                        pass

                if input_box:
                    time.sleep(1)  # Beri React sedikit waktu stabil
                    break

                # Cek modal error (nomor tidak valid / tidak di WA)
                invalid_modal = self._page.query_selector(self.SEL_INVALID_PHONE)
                if invalid_modal:
                    modal_text = invalid_modal.inner_text().lower()

                    # Jika ini popup "Apa yang baru", tutup dengan menekan Escape agar tidak menghalangi kotak input
                    if "apa yang baru" in modal_text or "what's new" in modal_text:
                        try:
                            self._page.keyboard.press("Escape")
                            time.sleep(1)
                        except Exception:
                            pass
                        continue  # Lanjut polling input_box

                    # Abaikan overlay loading "Starting chat" / "Memulai chat"
                    if ("starting chat" not in modal_text
                            and "memulai chat" not in modal_text
                            and modal_text.strip()):
                        screenshot = self._take_screenshot(phone_e164, "not_on_wa")
                        if ("invalid" in modal_text
                                or "phone number" in modal_text
                                or "tidak valid" in modal_text):
                            return (Status.INVALID_PHONE,
                                    f"Nomor tidak valid di WA: {modal_text[:80].replace(chr(10), ' ')}",
                                    screenshot)
                        return (Status.NOT_ON_WA,
                                f"Nomor tidak terdaftar di WA: {modal_text[:80].replace(chr(10), ' ')}",
                                screenshot)

                self._page.wait_for_timeout(600)  # Poll setiap 600ms
            else:
                screenshot = self._take_screenshot(phone_e164, "timeout")
                return Status.FAILED, "Timeout menunggu kotak input WA Web muncul", screenshot

            # ── Ketik pesan ──────────────────────────────────────────────────
            # Klik input box, pastikan fokus masuk sebelum mengetik
            time.sleep(0.5)
            input_box.click()
            time.sleep(0.8)

            # Klik sekali lagi jika elemen belum terfokus (kondisi race WA SPA)
            try:
                if not self._page.evaluate(
                    "el => el === document.activeElement || el.contains(document.activeElement)",
                    input_box
                ):
                    input_box.click()
                    time.sleep(0.5)
            except Exception:
                pass

            # Bersihkan isi kotak (buang draft lama jika ada)
            self._page.keyboard.press("Control+A")
            self._page.keyboard.press("Backspace")
            time.sleep(0.3)

            # Tempelkan pesan (insert_text = paste tanpa trigger clipboard WA)
            self._page.keyboard.insert_text(message)
            time.sleep(1.2)  # Tunggu React merender teks sebelum aksi selanjutnya

            if self.dry_run:
                # ── DRY RUN: tampilkan pesan di kotak, tapi JANGAN kirim ──────
                # Beri waktu user melihat preview pesan di browser
                time.sleep(2.5)
                # Bersihkan input agar tidak tertinggal draft
                self._page.keyboard.press("Control+A")
                self._page.keyboard.press("Backspace")
                return Status.SUCCESS, "[DRY RUN] Pesan ditampilkan, tidak dikirim", ""
            else:
                # ── REAL: kirim pesan ─────────────────────────────────────────
                self._page.keyboard.press("Enter")
                # Tunggu sebentar untuk memastikan pesan terkirim (centang muncul)
                time.sleep(2.0)
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
