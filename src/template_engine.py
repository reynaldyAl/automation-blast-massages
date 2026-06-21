"""
template_engine.py — Render template pesan Jinja2
"""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader, TemplateNotFound, TemplateError


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

    def render(self, nama_peserta: str, nokapst: str, **extra_vars) -> str:
        """
        Render template dengan data peserta.

        Args:
            nama_peserta: Nama peserta (kapital)
            nokapst: Nomor kartu JKN-KIS
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
            return template.render(
                nama_peserta=nama_peserta,
                nokapst=nokapst,
                **extra_vars,
            )
        except TemplateError as e:
            raise ValueError(f"Error render template: {e}")

    def preview(self, nama_peserta: str = "CONTOH NAMA", nokapst: str = "000123456789") -> str:
        """Render template dengan data dummy untuk preview."""
        return self.render(nama_peserta=nama_peserta, nokapst=nokapst)
