"""
template_engine.py — Render template pesan Jinja2
"""

import datetime
from pathlib import Path
from typing import Optional
import re
from jinja2 import Environment, FileSystemLoader, TemplateNotFound, TemplateError

def strip_whatsapp_formatting(text: str) -> str:
    """Hapus format markdown WhatsApp (*bold*, _italic_, ~strikethrough~)."""
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'\_(.*?)\_', r'\1', text)
    text = re.sub(r'\~(.*?)\~', r'\1', text)
    return text


def get_salam() -> str:
    """
    Kembalikan salam berdasarkan waktu lokal saat ini.

    Aturan:
      - 05:00 – 11:59 → Selamat pagi
      - 12:00 – 15:59 → Selamat siang
      - 16:00 – 18:59 → Selamat sore
      - 19:00 – 23:59 dan 00:00 – 04:59 → Selamat malam
    """
    hour = datetime.datetime.now().hour
    if 5 <= hour < 12:
        return "Selamat pagi"
    elif 12 <= hour < 16:
        return "Selamat siang"
    elif 16 <= hour < 19:
        return "Selamat sore"
    else:
        return "Selamat malam"


class TemplateEngine:
    def __init__(self, template_file: Path):
        self.template_file = template_file
        self.template_dir = template_file.parent
        self.template_name = template_file.name
        self._env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            trim_blocks=False,
            lstrip_blocks=False,
        )



    def render(
        self,
        nama_peserta: str,
        nokapst: str,
        nominal_tunggakan: Optional[str] = None,
        strip_markdown: bool = False,
        **extra_vars,
    ) -> str:
        """
        Render template dengan data peserta.

        Args:
            nama_peserta: Nama peserta (kapital)
            nokapst: Nomor kartu JKN-KIS
            nominal_tunggakan: Nominal tunggakan (opsional, mis. "Rp210,000")
            strip_markdown: Hapus format WhatsApp (*bold*, _italic_) untuk SMS
            **extra_vars: Variabel tambahan opsional

        Returns:
            String pesan yang sudah dirender

        Raises:
            FileNotFoundError: Jika file template tidak ditemukan
            ValueError: Jika ada error pada template
        """
        try:
            template = self._env.get_template(self.template_name)
        except TemplateNotFound:
            raise FileNotFoundError(f"Template tidak ditemukan: {self.template_file}")

        try:
            msg = template.render(
                nama_peserta=nama_peserta,
                nokapst=nokapst,
                nominal_tunggakan=nominal_tunggakan,
                salam=get_salam(),
                **extra_vars,
            )
            if strip_markdown:
                return strip_whatsapp_formatting(msg)
            return msg
        except TemplateError as e:
            raise ValueError(f"Error render template: {e}")

    def preview(
        self,
        nama_peserta: str = "CONTOH NAMA",
        nokapst: str = "000123456789",
        nominal_tunggakan: Optional[str] = None,
    ) -> str:
        """Render template dengan data dummy untuk preview."""
        return self.render(
            nama_peserta=nama_peserta,
            nokapst=nokapst,
            nominal_tunggakan=nominal_tunggakan,
        )
