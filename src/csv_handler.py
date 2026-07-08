"""
csv_handler.py — Baca, validasi, dan normalisasi data dari CSV input
"""

import pandas as pd
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from phone_validator import normalize_phone, PhoneResult, PhoneStatus


REQUIRED_COLUMNS = {"nama_peserta", "nokapst", "nohp"}
OPTIONAL_COLUMNS = {"send_wa", "send_sms", "nomor", "nominal_tunggakan"}


@dataclass
class Peserta:
    """Representasi satu baris data peserta."""
    row_index: int
    nomor: Optional[int]
    nama_peserta: str
    nokapst: str
    nohp_original: str
    phone: PhoneResult
    send_wa: bool = True
    send_sms: bool = True
    nominal_tunggakan: Optional[str] = None  # Opsional — dari kolom nominal_tunggakan CSV


@dataclass
class CSVLoadResult:
    peserta_list: List[Peserta] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    total_rows: int = 0
    valid_rows: int = 0
    invalid_phone_rows: int = 0


def load_csv(csv_path: Path) -> CSVLoadResult:
    """
    Muat CSV, validasi kolom, dan normalisasi setiap nomor HP.

    Returns:
        CSVLoadResult dengan daftar Peserta dan laporan error/warning.
    """
    result = CSVLoadResult()

    # --- Baca file ---
    try:
        df = pd.read_csv(csv_path, dtype=str)
    except FileNotFoundError:
        result.errors.append(f"File CSV tidak ditemukan: {csv_path}")
        return result
    except Exception as e:
        result.errors.append(f"Gagal membaca CSV: {e}")
        return result

    # --- Normalisasi nama kolom (lowercase, strip spasi & ganti spasi dengan _) ---
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # --- Validasi kolom wajib ---
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        result.errors.append(
            f"Kolom wajib tidak ditemukan di CSV: {', '.join(missing)}\n"
            f"Kolom yang ada: {', '.join(df.columns)}"
        )
        return result

    result.total_rows = len(df)

    for idx, row in df.iterrows():
        row_num = int(idx) + 2  # +2 karena row 1 = header, index mulai 0

        nama = str(row.get("nama_peserta", "")).strip()
        nokapst = str(row.get("nokapst", "")).strip()
        nohp_raw = str(row.get("nohp", "")).strip()
        nomor_val = row.get("nomor")

        # Skip baris kosong
        if not nama and not nokapst and not nohp_raw:
            result.warnings.append(f"Baris {row_num}: Baris kosong, dilewati.")
            continue

        # Validasi field wajib
        if not nama:
            result.warnings.append(f"Baris {row_num}: nama_peserta kosong, dilewati.")
            continue
        if not nokapst:
            result.warnings.append(f"Baris {row_num}: nokapst kosong untuk {nama}, dilewati.")
            continue

        # Normalisasi nomor HP
        phone_result = normalize_phone(nohp_raw)
        if not phone_result.is_valid:
            result.invalid_phone_rows += 1
            result.warnings.append(
                f"Baris {row_num} ({nama}): Nomor HP tidak valid — {phone_result.message}"
            )

        # Parse flag send_wa / send_sms
        def parse_bool_col(key: str, default: bool = True) -> bool:
            val = str(row.get(key, str(default))).strip().lower()
            return val in ("true", "1", "yes", "ya")

        send_wa = parse_bool_col("send_wa", True)
        send_sms = parse_bool_col("send_sms", True)

        try:
            nomor = int(float(nomor_val)) if nomor_val and str(nomor_val) != "nan" else None
        except (ValueError, TypeError):
            nomor = None

        # Baca nominal_tunggakan (opsional) — None jika kolom tidak ada atau kosong
        raw_nominal = row.get("nominal_tunggakan", None)
        if raw_nominal is not None:
            raw_nominal = str(raw_nominal).strip()
        nominal_tunggakan = raw_nominal if raw_nominal and raw_nominal.lower() != "nan" else None

        peserta = Peserta(
            row_index=int(idx),
            nomor=nomor,
            nama_peserta=nama.upper(),  # Nama dalam kapital (sesuai template BPJS)
            nokapst=nokapst,
            nohp_original=nohp_raw,
            phone=phone_result,
            send_wa=send_wa,
            send_sms=send_sms,
            nominal_tunggakan=nominal_tunggakan,
        )
        result.peserta_list.append(peserta)
        result.valid_rows += 1

    return result
