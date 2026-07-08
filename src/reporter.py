"""
reporter.py — Pencatatan log dan pembuatan laporan CSV hasil pengiriman
"""

import csv
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from config import config
from csv_handler import Peserta

# ─── Setup logging ke file ────────────────────────────────────────────────────
log_formatter = logging.Formatter("[%(asctime)s] %(levelname)s — %(message)s", "%Y-%m-%d %H:%M:%S")
logger = logging.getLogger("blast")
logger.setLevel(logging.DEBUG)

_log_file = config.REPORT_DIR / f"blast_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
_fh = logging.FileHandler(_log_file, encoding="utf-8")
_fh.setFormatter(log_formatter)
logger.addHandler(_fh)


# ─── Status Constants ─────────────────────────────────────────────────────────
class Status:
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    INVALID_PHONE = "INVALID_PHONE"
    NOT_ON_WA = "NOT_ON_WA"
    SKIPPED = "SKIPPED"
    NO_DEVICE = "NO_DEVICE"
    RETRYING = "RETRYING"


@dataclass
class SendResult:
    """Hasil pengiriman untuk satu peserta, satu channel."""
    row_index: int
    nomor: Optional[int]
    nama_peserta: str
    nokapst: str
    nohp_original: str
    nohp_normalized: str
    phone_valid: bool
    wa_status: str = Status.SKIPPED
    wa_error: str = ""
    wa_screenshot: str = ""
    sms_status: str = Status.SKIPPED
    sms_error: str = ""
    failure_reason: str = ""   # Alasan gagal gabungan (diisi otomatis oleh Reporter.record)
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    retry_count: int = 0


class Reporter:
    """Mengelola pencatatan hasil dan penulisan laporan CSV."""

    REPORT_COLUMNS = [
        "nomor", "nama_peserta", "nokapst",
        "nohp_original", "nohp_normalized", "phone_valid",
        "wa_status", "wa_error", "wa_screenshot",
        "sms_status", "sms_error",
        "failure_reason",
        "timestamp", "retry_count",
    ]

    def __init__(self):
        config.ensure_dirs()
        self.done_dir = config.REPORT_DIR / "done"
        self._done_file_inited = False
        
        self._results: List[SendResult] = []
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.report_path = config.REPORT_DIR / f"report_{ts}.csv"
        self.done_path = self.done_dir / f"report_done_{ts}.csv"
        
        self._init_report_file()

    def record_success(self, peserta: Peserta):
        """Pindahkan/salin data mentah peserta yang sukses ke CSV done."""
        done_columns = ["nomor", "nama_peserta", "nokapst", "nohp", "nominal_tunggakan", "send_wa", "send_sms"]
        
        if not self._done_file_inited:
            self.done_dir.mkdir(parents=True, exist_ok=True)
            with open(self.done_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=done_columns)
                writer.writeheader()
            self._done_file_inited = True
        row = {
            "nomor": peserta.nomor if peserta.nomor else "",
            "nama_peserta": peserta.nama_peserta,
            "nokapst": peserta.nokapst,
            "nohp": peserta.nohp_original,
            "nominal_tunggakan": peserta.nominal_tunggakan if peserta.nominal_tunggakan else "",
            "send_wa": str(peserta.send_wa).upper(),
            "send_sms": str(peserta.send_sms).upper()
        }
        with open(self.done_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=done_columns)
            writer.writerow(row)

    def _init_report_file(self):
        """Buat file CSV dan tulis header."""
        with open(self.report_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.REPORT_COLUMNS)
            writer.writeheader()

    def record(self, result: SendResult):
        """Catat hasil pengiriman dan append ke CSV secara langsung (real-time)."""
        # Otomatis isi failure_reason dari error yang paling informatif
        if not result.failure_reason:
            reasons = []
            # WA
            if result.wa_status == Status.INVALID_PHONE:
                reasons.append(f"[WA] Nomor tidak valid: {result.wa_error or 'format salah'}")
            elif result.wa_status == Status.NOT_ON_WA:
                reasons.append(f"[WA] Nomor tidak terdaftar di WhatsApp")
            elif result.wa_status == Status.FAILED:
                reasons.append(f"[WA] Gagal kirim: {result.wa_error or 'error tidak diketahui'}")
            # SMS
            if result.sms_status == Status.INVALID_PHONE:
                reasons.append(f"[SMS] Nomor tidak valid: {result.sms_error or 'format salah'}")
            elif result.sms_status == Status.NO_DEVICE:
                reasons.append(f"[SMS] Perangkat Android tidak terdeteksi")
            elif result.sms_status == Status.FAILED:
                reasons.append(f"[SMS] Gagal kirim: {result.sms_error or 'error tidak diketahui'}")
            result.failure_reason = " | ".join(reasons)

        self._results.append(result)
        self._append_to_csv(result)

        # Log berdasarkan status
        wa_info = f"WA={result.wa_status}" if result.wa_status != Status.SKIPPED else ""
        sms_info = f"SMS={result.sms_status}" if result.sms_status != Status.SKIPPED else ""
        channel_info = " | ".join(filter(None, [wa_info, sms_info]))

        if result.wa_status in (Status.FAILED, Status.NOT_ON_WA, Status.INVALID_PHONE) or \
                result.sms_status in (Status.FAILED, Status.NO_DEVICE, Status.INVALID_PHONE):
            logger.warning(
                f"[{result.nama_peserta}] {result.nohp_original} → {channel_info}"
                f"{' | ERR: ' + result.wa_error if result.wa_error else ''}"
                f"{' | ERR: ' + result.sms_error if result.sms_error else ''}"
            )
        else:
            logger.info(f"[{result.nama_peserta}] {result.nohp_original} → {channel_info}")

    def _append_to_csv(self, result: SendResult):
        with open(self.report_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.REPORT_COLUMNS)
            row = asdict(result)
            writer.writerow({k: row[k] for k in self.REPORT_COLUMNS})

    def get_summary(self) -> dict:
        """Hitung ringkasan hasil pengiriman."""
        total = len(self._results)
        wa_results = [r for r in self._results if r.wa_status != Status.SKIPPED]
        sms_results = [r for r in self._results if r.sms_status != Status.SKIPPED]

        return {
            "total": total,
            "wa_total": len(wa_results),
            "wa_success": sum(1 for r in wa_results if r.wa_status == Status.SUCCESS),
            "wa_failed": sum(1 for r in wa_results if r.wa_status == Status.FAILED),
            "wa_not_on_wa": sum(1 for r in wa_results if r.wa_status == Status.NOT_ON_WA),
            "wa_invalid": sum(1 for r in wa_results if r.wa_status == Status.INVALID_PHONE),
            "sms_total": len(sms_results),
            "sms_success": sum(1 for r in sms_results if r.sms_status == Status.SUCCESS),
            "sms_failed": sum(1 for r in sms_results if r.sms_status == Status.FAILED),
            "sms_no_device": sum(1 for r in sms_results if r.sms_status == Status.NO_DEVICE),
            "invalid_phone": sum(1 for r in self._results if not r.phone_valid),
            "report_path": str(self.report_path),
            "log_path": str(_log_file),
        }

    def get_failed_for_retry(self) -> List[int]:
        """Kembalikan row_index dari semua pengiriman yang gagal."""
        failed = []
        for r in self._results:
            if r.wa_status in (Status.FAILED,) or r.sms_status in (Status.FAILED,):
                failed.append(r.row_index)
        return failed


# ─── State File (Resume Mode) ─────────────────────────────────────────────────
class StateManager:
    """Menyimpan progress pengiriman agar bisa resume jika proses terhenti."""

    def __init__(self, state_file: Path = config.STATE_FILE):
        self.state_file = state_file
        self._state = self._load()

    def _load(self) -> dict:
        if self.state_file.exists():
            try:
                with open(self.state_file, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save(self):
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self._state, f, indent=2)

    def is_done(self, row_index: int) -> bool:
        return str(row_index) in self._state.get("done", {})

    def mark_done(self, row_index: int, wa_status: str, sms_status: str):
        if "done" not in self._state:
            self._state["done"] = {}
        self._state["done"][str(row_index)] = {
            "wa": wa_status,
            "sms": sms_status,
            "at": datetime.now().isoformat(),
        }
        self._save()

    def clear(self):
        """Reset state (mulai dari awal)."""
        if self.state_file.exists():
            self.state_file.unlink()
        self._state = {}

    @property
    def done_count(self) -> int:
        return len(self._state.get("done", {}))
