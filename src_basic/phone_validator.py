"""
phone_validator.py — Validasi dan normalisasi nomor HP Indonesia
"""

import re
from dataclasses import dataclass
from enum import Enum


class PhoneStatus(str, Enum):
    VALID = "VALID"
    INVALID_LENGTH = "INVALID_LENGTH"
    INVALID_PREFIX = "INVALID_PREFIX"
    EMPTY = "EMPTY"


@dataclass
class PhoneResult:
    original: str
    normalized: str        # Format E.164 tanpa '+': 628xxxxxxxxxx
    wa_format: str         # Untuk URL WA: 628xxxxxxxxxx
    display_format: str    # Untuk tampilan: 08xxxxxxxxxx
    status: PhoneStatus
    message: str

    @property
    def is_valid(self) -> bool:
        return self.status == PhoneStatus.VALID


# Prefix valid operator Indonesia
VALID_PREFIXES = (
    "0811", "0812", "0813", "0821", "0822", "0823",  # Telkomsel
    "0851", "0852", "0853",                            # Telkomsel
    "0814", "0815", "0816", "0855", "0856", "0857",  # Indosat
    "0858",
    "0817", "0818", "0819", "0859", "0877", "0878",  # XL
    "0831", "0832", "0833", "0838",                   # Axis
    "0881", "0882", "0883", "0884", "0885",           # Smartfren
    "0886", "0887", "0888", "0889",
    "0895", "0896", "0897", "0898", "0899",           # Three (3)
    "0828", "0868",                                    # Lain-lain
)


def normalize_phone(raw: str) -> PhoneResult:
    """
    Normalisasi nomor HP ke format standar E.164 Indonesia (628xx).

    Contoh transformasi:
      08xx      → 628xx
      628xx     → 628xx (sudah benar)
      +628xx    → 628xx
      62-8xx    → 628xx
      (08xx)    → 628xx
    """
    if not raw or str(raw).strip() in ("", "nan", "None"):
        return PhoneResult(
            original=str(raw),
            normalized="",
            wa_format="",
            display_format="",
            status=PhoneStatus.EMPTY,
            message="Nomor HP kosong",
        )

    # Bersihkan: hapus spasi, strip, tanda minus, kurung, titik
    cleaned = re.sub(r"[\s\-\.\(\)\+]", "", str(raw).strip())

    # Normalisasi prefix
    if cleaned.startswith("628"):
        normalized = cleaned
    elif cleaned.startswith("08"):
        normalized = "62" + cleaned[1:]
    elif cleaned.startswith("8") and len(cleaned) >= 9:
        normalized = "62" + cleaned
    else:
        return PhoneResult(
            original=raw,
            normalized=cleaned,
            wa_format="",
            display_format=cleaned,
            status=PhoneStatus.INVALID_PREFIX,
            message=f"Prefix nomor tidak valid: {cleaned[:4]}...",
        )

    # Validasi panjang (format 628xx: 11–14 digit)
    if not (11 <= len(normalized) <= 14):
        return PhoneResult(
            original=raw,
            normalized=normalized,
            wa_format="",
            display_format="0" + normalized[2:],
            status=PhoneStatus.INVALID_LENGTH,
            message=f"Panjang nomor tidak valid: {len(normalized)} digit (harusnya 11–14)",
        )

    # Validasi prefix operator
    display = "0" + normalized[2:]
    prefix_valid = any(display.startswith(p) for p in VALID_PREFIXES)
    if not prefix_valid:
        return PhoneResult(
            original=raw,
            normalized=normalized,
            wa_format=normalized,
            display_format=display,
            status=PhoneStatus.INVALID_PREFIX,
            message=f"Prefix operator tidak dikenali: {display[:4]}",
        )

    return PhoneResult(
        original=raw,
        normalized=normalized,
        wa_format=normalized,
        display_format=display,
        status=PhoneStatus.VALID,
        message="Nomor valid",
    )
