"""
sms_sender.py — Kirim SMS via ADB (Android Debug Bridge)

Cara kerja:
1. Script membuka aplikasi SMS bawaan HP via ADB
2. Nomor tujuan & pesan sudah terisi otomatis
3. Pesan TAMPIL di layar HP untuk konfirmasi visual
4. Script otomatis tap tombol "Kirim" via ADB input tap
5. Pesan terkirim

Persyaratan:
- ADB terinstall dan ada di PATH sistem
- HP Android terhubung via USB
- USB Debugging aktif di HP (Settings > Developer Options > USB Debugging)
- HP tidak dalam keadaan terkunci layar
"""

import subprocess
import time
import shutil
from typing import Optional

from config import config
from reporter import Status


class ADBError(Exception):
    pass


class SMSSender:
    """Mengelola pengiriman SMS via Android Debug Bridge (ADB)."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self._device_id = config.ADB_DEVICE_ID.strip() or None
        self._adb_available: Optional[bool] = None

    def _adb(self, *args: str, timeout: int = 15) -> subprocess.CompletedProcess:
        """Jalankan perintah ADB."""
        cmd = ["adb"]
        if self._device_id:
            cmd += ["-s", self._device_id]
        cmd += list(args)

        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )

    def check_device(self) -> tuple[bool, str]:
        """
        Periksa apakah HP Android terhubung dan terdeteksi ADB.

        Returns:
            (True, device_id) jika terhubung
            (False, error_message) jika tidak
        """
        if self.dry_run:
            return True, "dry-run"

        if not shutil.which("adb"):
            return False, "ADB tidak terinstall. Install Android SDK Platform Tools."

        result = self._adb("devices")
        if result.returncode != 0:
            return False, f"ADB error: {result.stderr[:100]}"

        lines = result.stdout.strip().splitlines()
        # Format output: "List of devices attached\nXXXXX\tdevice"
        devices = [
            ln for ln in lines[1:]
            if ln.strip() and "\tdevice" in ln
        ]

        if not devices:
            # Cek apakah ada device unauthorized
            unauthorized = [ln for ln in lines[1:] if "unauthorized" in ln]
            if unauthorized:
                return False, (
                    "HP terdeteksi tapi belum diizinkan. "
                    "Centang 'Always allow' di popup USB Debugging di HP."
                )
            return False, "Tidak ada HP Android yang terdeteksi. Cek koneksi USB & USB Debugging."

        device_id = devices[0].split("\t")[0].strip()
        if not self._device_id:
            self._device_id = device_id

        return True, device_id

    def wake_screen(self):
        """Nyalakan layar HP jika sedang mati."""
        # Cek status layar
        result = self._adb("shell", "dumpsys", "power")
        if "mWakefulness=Awake" not in result.stdout:
            self._adb("shell", "input", "keyevent", "KEYCODE_WAKEUP")
            time.sleep(0.5)

    def send(self, phone_display: str, message: str) -> tuple[str, str]:
        """
        Kirim SMS ke nomor tujuan via ADB.

        Args:
            phone_display: Nomor HP format 08xx (ditampilkan di SMS app)
            message: Isi pesan SMS

        Returns:
            tuple (status, error_message)
        """
        if self.dry_run:
            return Status.SUCCESS, ""

        # Cek device
        ok, info = self.check_device()
        if not ok:
            return Status.NO_DEVICE, info

        try:
            # Bangunkan layar HP terlebih dahulu
            self.wake_screen()

            # Escape karakter khusus untuk shell Android
            # ADB shell am start tidak mendukung newline langsung di --es
            # Ganti newline dengan spasi untuk kompatibilitas SMS
            safe_msg = message.replace("\n", " ").replace('"', '\\"').replace("'", "\\'")

            # Buka SMS composer dengan nomor & pesan terisi
            result = self._adb(
                "shell", "am", "start",
                "-a", "android.intent.action.SENDTO",
                "-d", f"sms:{phone_display}",
                "--es", "sms_body", safe_msg,
                "--ez", "exit_on_sent", "true",
            )

            if result.returncode != 0:
                return Status.FAILED, f"Gagal buka SMS app: {result.stderr[:100]}"

            # Tunggu SMS composer terbuka di layar HP
            time.sleep(config.ADB_SEND_WAIT)

            # Tap tombol Send SMS
            # Koordinat tombol Send bervariasi per HP, gunakan input keyevent
            # KEYCODE_ENTER = 66 (pada banyak SMS app, ini sama dengan Send)
            self._adb("shell", "input", "keyevent", "66")

            # Tunggu sebentar setelah send
            time.sleep(1.0)

            return Status.SUCCESS, ""

        except subprocess.TimeoutExpired:
            return Status.FAILED, "ADB command timeout"
        except FileNotFoundError:
            return Status.NO_DEVICE, "ADB tidak ditemukan. Install Android SDK Platform Tools."
        except Exception as e:
            return Status.FAILED, f"Error ADB: {str(e)[:100]}"
