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

import os
import subprocess
import time
import shutil
from pathlib import Path
from typing import Optional

from config import config
from reporter import Status


class ADBError(Exception):
    pass


def _find_adb() -> Optional[str]:
    """
    Cari executable ADB di sistem.
    Mendukung: PATH biasa + lokasi instalasi winget di Windows.
    """
    # Cari di PATH dulu (cara standar)
    adb = shutil.which("adb")
    if adb:
        return adb

    # Fallback: lokasi instalasi winget di Windows
    if os.name == "nt":  # Windows only
        localappdata = os.environ.get("LOCALAPPDATA", "")
        winget_paths = [
            Path(localappdata) / "Microsoft" / "WinGet" / "Links" / "adb.exe",
            Path(localappdata) / "Microsoft" / "WinGet" / "Packages",
        ]

        # Cek link langsung
        if winget_paths[0].exists():
            return str(winget_paths[0])

        # Cari di dalam subfolder Packages (nama folder bervariasi)
        packages_dir = winget_paths[1]
        if packages_dir.exists():
            for pkg_dir in packages_dir.glob("Google.PlatformTools*"):
                adb_exe = pkg_dir / "platform-tools" / "adb.exe"
                if adb_exe.exists():
                    return str(adb_exe)

    return None


class SMSSender:
    """Mengelola pengiriman SMS via Android Debug Bridge (ADB)."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self._device_id = config.ADB_DEVICE_ID.strip() or None
        self._adb_available: Optional[bool] = None
        self._adb_path: Optional[str] = _find_adb()  # Resolve ADB path sekali saja

    def _adb(self, *args: str, timeout: int = 15) -> subprocess.CompletedProcess:
        """Jalankan perintah ADB."""
        if not self._adb_path:
            raise FileNotFoundError("ADB tidak ditemukan")

        cmd = [self._adb_path]
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

        if not self._adb_path:
            return False, (
                "ADB tidak terinstall. Install Android SDK Platform Tools.\n"
                "  Windows: winget install Google.PlatformTools\n"
                "  Atau buka terminal BARU setelah install agar PATH terupdate."
            )

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

    def _find_send_coords_dynamically(self) -> Optional[tuple[int, int]]:
        """Mencari koordinat tombol Send di layar menggunakan uiautomator."""
        try:
            # Beri waktu sebentar agar keyboard atau UI stabil
            time.sleep(1.0)
            # Dump UI XML ke sdcard
            self._adb("shell", "uiautomator", "dump", "/sdcard/window_dump.xml")
            result = self._adb("shell", "cat", "/sdcard/window_dump.xml")
            xml_str = result.stdout
            
            import re
            # Cari tombol Send berdasarkan resource-id yang mengandung 'send' dan 'button'
            match = re.search(r'resource-id="[^"]*send[^"]*button".*?bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml_str, re.IGNORECASE)
            
            # Jika tidak ketemu, cari berdasarkan content-desc (bahasa Inggris/Indonesia)
            if not match:
                match = re.search(r'content-desc="[^"]*(Send|Kirim)[^"]*".*?bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml_str, re.IGNORECASE)
                
            if match:
                groups = match.groups()
                # Jika group pertama adalah teks "Send" atau "Kirim" dari regex kedua
                if len(groups) == 5:
                    x1, y1, x2, y2 = map(int, groups[1:])
                else:
                    x1, y1, x2, y2 = map(int, groups)
                    
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                return center_x, center_y
        except Exception:
            pass
            
        return None

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

            # Escape pesan agar aman dieksekusi oleh shell Android (/system/bin/sh).
            # Dengan membungkus pesan dalam single quote ('), shell tidak akan menganggap
            # tanda kurung '()' atau spesial karakter lainnya sebagai syntax command.
            # Jika ada single quote di dalam pesan, escape menjadi '\''
            safe_msg = "'" + message.replace("'", "'\\''") + "'"

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
            if config.SMS_SEND_COORDS:
                # Manual koordinat dari .env (paling cepat jika sudah diset)
                try:
                    x, y = [p.strip() for p in config.SMS_SEND_COORDS.split(",")]
                    self._adb("shell", "input", "tap", x, y)
                except Exception:
                    self._adb("shell", "input", "keyevent", "22")
                    time.sleep(0.2)
                    self._adb("shell", "input", "keyevent", "66")
            else:
                # Deteksi otomatis letak tombol Send di layar (hanya dihitung sekali per sesion)
                if not getattr(self, '_cached_send_coords', None):
                    self._cached_send_coords = self._find_send_coords_dynamically()
                    
                if self._cached_send_coords:
                    cx, cy = self._cached_send_coords
                    self._adb("shell", "input", "tap", str(cx), str(cy))
                else:
                    # Fallback terakhir jika uiautomator gagal
                    self._adb("shell", "input", "keyevent", "22")
                    time.sleep(0.2)
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
