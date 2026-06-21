"""
main.py — Entry point utama CLI untuk BPJS Blast Message Automation

Penggunaan:
  python src/main.py run                    # Kirim semua pesan
  python src/main.py run --dry-run          # Preview tanpa kirim
  python src/main.py run --wa-only          # Hanya WA
  python src/main.py run --sms-only         # Hanya SMS
  python src/main.py run --fresh            # Mulai ulang (reset resume state)
  python src/main.py preview                # Tampilkan preview template
  python src/main.py validate               # Validasi CSV & config saja
  python src/main.py report                 # Tampilkan laporan terakhir
"""

import sys
import time
from pathlib import Path

# Pastikan src/ ada di path
sys.path.insert(0, str(Path(__file__).parent))

import click
from rich.console import Console

from config import config
from csv_handler import load_csv
from template_engine import TemplateEngine
from wa_sender import WASender
from sms_sender import SMSSender
from reporter import Reporter, StateManager, SendResult, Status
from dashboard import (
    console, print_banner, print_config_summary,
    create_progress, print_send_result, print_invalid_phone,
    print_section, print_dry_run_warning, print_resume_info, print_summary,
)
from scheduler import start_scheduler


# ─── CLI Group ────────────────────────────────────────────────────────────────
@click.group()
def cli():
    """🏥 BPJS Blast Message Automation — BPJS Kesehatan Kantor Cabang Serang"""
    pass


# ─── run command ─────────────────────────────────────────────────────────────
@cli.command()
@click.option("--dry-run", is_flag=True, default=False, help="Preview tanpa kirim pesan")
@click.option("--wa-only", is_flag=True, default=False, help="Hanya kirim via WhatsApp")
@click.option("--sms-only", is_flag=True, default=False, help="Hanya kirim via SMS")
@click.option("--fresh", is_flag=True, default=False, help="Reset state, mulai dari awal")
@click.option("--csv", "csv_path", default=None, help="Path CSV input (override .env)")
@click.option("--template", "tpl_path", default=None, help="Path template (override .env)")
def run(dry_run, wa_only, sms_only, fresh, csv_path, tpl_path):
    """Jalankan pengiriman pesan blast."""

    def _run():
        _do_run(dry_run=dry_run, wa_only=wa_only, sms_only=sms_only, fresh=fresh,
                csv_path=csv_path, tpl_path=tpl_path)

    start_scheduler(_run)


def _do_run(dry_run=False, wa_only=False, sms_only=False, fresh=False,
            csv_path=None, tpl_path=None):

    print_banner()

    # Override channel dari flag
    send_wa = config.SEND_WA and not sms_only
    send_sms = config.SEND_SMS and not wa_only
    if wa_only:
        send_sms = False
    if sms_only:
        send_wa = False

    if dry_run:
        print_dry_run_warning()

    # ── Validasi config ──────────────────────────────────────────────────────
    errs = config.validate()
    if errs:
        for e in errs:
            console.print(f"  [bold red]✗ Config Error:[/bold red] {e}")
        sys.exit(1)

    config.ensure_dirs()

    # ── Load CSV ─────────────────────────────────────────────────────────────
    input_csv = Path(csv_path) if csv_path else config.INPUT_CSV
    csv_result = load_csv(input_csv)

    if csv_result.errors:
        for e in csv_result.errors:
            console.print(f"  [bold red]✗ CSV Error:[/bold red] {e}")
        sys.exit(1)

    if csv_result.warnings:
        print_section("⚠ Peringatan CSV")
        for w in csv_result.warnings:
            console.print(f"  [yellow]⚠[/yellow] {w}")

    # ── Load Template ─────────────────────────────────────────────────────────
    tpl_file = Path(tpl_path) if tpl_path else config.TEMPLATE_FILE
    engine = TemplateEngine(tpl_file)

    # ── Tampilkan summary config ──────────────────────────────────────────────
    print_config_summary(config, csv_result.valid_rows)

    # ── State / Resume ────────────────────────────────────────────────────────
    state = StateManager()
    if fresh:
        state.clear()
        console.print("  [cyan]↺ State direset, mulai dari awal.[/cyan]\n")
    elif state.done_count > 0:
        print_resume_info(state.done_count)

    # ── Init sender & reporter ────────────────────────────────────────────────
    reporter = Reporter()
    wa = WASender(dry_run=dry_run)
    sms = SMSSender(dry_run=dry_run)

    # Cek ADB jika SMS aktif
    if send_sms and not dry_run:
        ok, info = sms.check_device()
        if not ok:
            console.print(f"\n  [bold yellow]⚠ SMS dinonaktifkan:[/bold yellow] {info}")
            send_sms = False
        else:
            console.print(f"  [green]✓ HP Android terdeteksi:[/green] [dim]{info}[/dim]")

    # Mulai WA browser
    if send_wa:
        try:
            wa.start()
        except Exception as e:
            console.print(f"\n  [bold red]✗ Gagal buka WA Web:[/bold red] {e}")
            sys.exit(1)

    # ── Proses pengiriman ─────────────────────────────────────────────────────
    print_section("📤 Pengiriman Pesan")

    peserta_list = csv_result.peserta_list
    total = len(peserta_list)

    with create_progress() as progress:
        task_id = progress.add_task("Mengirim pesan...", total=total)

        for peserta in peserta_list:
            progress.advance(task_id)

            # Skip jika sudah selesai (resume mode)
            if state.is_done(peserta.row_index):
                progress.update(task_id, description=f"[dim]Skip (sudah): {peserta.nama_peserta}[/dim]")
                continue

            # Build result object
            result = SendResult(
                row_index=peserta.row_index,
                nomor=peserta.nomor,
                nama_peserta=peserta.nama_peserta,
                nokapst=peserta.nokapst,
                nohp_original=peserta.nohp_original,
                nohp_normalized=peserta.phone.normalized,
                phone_valid=peserta.phone.is_valid,
            )

            # Nomor tidak valid → skip kirim
            if not peserta.phone.is_valid:
                print_invalid_phone(peserta.nama_peserta, peserta.nohp_original, peserta.phone.message)
                if send_wa and peserta.send_wa:
                    result.wa_status = Status.INVALID_PHONE
                    result.wa_error = peserta.phone.message
                if send_sms and peserta.send_sms:
                    result.sms_status = Status.INVALID_PHONE
                    result.sms_error = peserta.phone.message
                reporter.record(result)
                state.mark_done(peserta.row_index, result.wa_status, result.sms_status)
                continue

            # Render pesan
            message = engine.render(
                nama_peserta=peserta.nama_peserta,
                nokapst=peserta.nokapst,
            )

            progress.update(task_id, description=f"Mengirim: [cyan]{peserta.nama_peserta}[/cyan]")

            # ── Kirim WA ──────────────────────────────────────────────────────
            if send_wa and peserta.send_wa:
                wa_status, wa_error, wa_screenshot = wa.send(
                    phone_e164=peserta.phone.wa_format,
                    message=message,
                )
                result.wa_status = wa_status
                result.wa_error = wa_error
                result.wa_screenshot = wa_screenshot

                if wa_status == Status.SUCCESS:
                    time.sleep(config.WA_DELAY_SECONDS)

            # ── Kirim SMS ─────────────────────────────────────────────────────
            if send_sms and peserta.send_sms:
                sms_status, sms_error = sms.send(
                    phone_display=peserta.phone.display_format,
                    message=message,
                )
                result.sms_status = sms_status
                result.sms_error = sms_error

                if sms_status == Status.SUCCESS:
                    time.sleep(config.SMS_DELAY_SECONDS)

            # Catat hasil
            reporter.record(result)
            state.mark_done(peserta.row_index, result.wa_status, result.sms_status)
            print_send_result(
                peserta.nama_peserta, peserta.phone.display_format,
                result.wa_status, result.sms_status,
                result.wa_error or result.sms_error,
            )

    # ── Retry Mode ────────────────────────────────────────────────────────────
    failed_indices = reporter.get_failed_for_retry()
    if config.RETRY_FAILED and failed_indices and not dry_run:
        print_section(f"🔁 Retry — {len(failed_indices)} pesan gagal")
        retry_list = [p for p in peserta_list if p.row_index in failed_indices]

        for attempt in range(1, config.MAX_RETRY + 1):
            console.print(f"  [yellow]Percobaan retry ke-{attempt}...[/yellow]")
            still_failing = []

            for peserta in retry_list:
                message = engine.render(nama_peserta=peserta.nama_peserta, nokapst=peserta.nokapst)
                retry_result = SendResult(
                    row_index=peserta.row_index,
                    nomor=peserta.nomor,
                    nama_peserta=peserta.nama_peserta,
                    nokapst=peserta.nokapst,
                    nohp_original=peserta.nohp_original,
                    nohp_normalized=peserta.phone.normalized,
                    phone_valid=peserta.phone.is_valid,
                    retry_count=attempt,
                )

                if send_wa and peserta.send_wa:
                    wa_status, wa_err, wa_ss = wa.send(peserta.phone.wa_format, message)
                    retry_result.wa_status = wa_status
                    retry_result.wa_error = wa_err
                    retry_result.wa_screenshot = wa_ss

                if send_sms and peserta.send_sms:
                    sms_status, sms_err = sms.send(peserta.phone.display_format, message)
                    retry_result.sms_status = sms_status
                    retry_result.sms_error = sms_err

                reporter.record(retry_result)
                print_send_result(
                    peserta.nama_peserta, peserta.phone.display_format,
                    retry_result.wa_status, retry_result.sms_status,
                )

                if retry_result.wa_status == Status.FAILED or retry_result.sms_status == Status.FAILED:
                    still_failing.append(peserta)

            retry_list = still_failing
            if not still_failing:
                break

    # ── Cleanup ───────────────────────────────────────────────────────────────
    wa.close()
    state.clear()  # Bersihkan state setelah selesai

    # ── Summary ───────────────────────────────────────────────────────────────
    summary = reporter.get_summary()
    print_summary(summary, dry_run=dry_run)


# ─── preview command ──────────────────────────────────────────────────────────
@cli.command()
@click.option("--template", "tpl_path", default=None, help="Path template")
@click.option("--nama", default="SUROTO", help="Nama peserta untuk preview")
@click.option("--nokapst", default="0002223480115", help="No kartu untuk preview")
def preview(tpl_path, nama, nokapst):
    """Tampilkan preview pesan dari template."""
    print_banner()
    tpl_file = Path(tpl_path) if tpl_path else config.TEMPLATE_FILE
    engine = TemplateEngine(tpl_file)

    print_section("📄 Preview Template Pesan")
    rendered = engine.preview(nama_peserta=nama.upper(), nokapst=nokapst)
    console.print()
    console.print(rendered)
    console.print()


# ─── validate command ─────────────────────────────────────────────────────────
@cli.command()
def validate():
    """Validasi file CSV dan konfigurasi tanpa mengirim pesan."""
    print_banner()
    print_section("🔍 Validasi Konfigurasi & CSV")

    # Config
    errs = config.validate()
    if errs:
        for e in errs:
            console.print(f"  [red]✗[/red] {e}")
    else:
        console.print("  [green]✓[/green] Konfigurasi valid")

    # CSV
    csv_result = load_csv(config.INPUT_CSV)
    if csv_result.errors:
        for e in csv_result.errors:
            console.print(f"  [red]✗[/red] CSV: {e}")
    else:
        console.print(f"  [green]✓[/green] CSV valid: {csv_result.valid_rows} peserta ditemukan")
        if csv_result.invalid_phone_rows:
            console.print(
                f"  [yellow]⚠[/yellow] {csv_result.invalid_phone_rows} nomor HP tidak valid "
                f"(akan di-skip saat pengiriman)"
            )
        for w in csv_result.warnings:
            console.print(f"  [yellow]⚠[/yellow] {w}")

    # ADB
    sms = SMSSender()
    ok, info = sms.check_device()
    if ok:
        console.print(f"  [green]✓[/green] ADB: HP terdeteksi — {info}")
    else:
        console.print(f"  [yellow]⚠[/yellow] ADB: {info}")

    console.print()


# ─── report command ───────────────────────────────────────────────────────────
@cli.command()
def report():
    """Tampilkan laporan terakhir dari folder data/reports/."""
    import glob
    reports = sorted(glob.glob(str(config.REPORT_DIR / "report_*.csv")), reverse=True)
    if not reports:
        console.print("  [yellow]Belum ada laporan. Jalankan 'run' terlebih dahulu.[/yellow]")
        return

    latest = reports[0]
    console.print(f"\n  📄 Laporan terbaru: [cyan]{latest}[/cyan]\n")

    import pandas as pd
    df = pd.read_csv(latest)
    console.print(df.to_string(index=False))
    console.print()


# ─── Entry Point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    cli()
