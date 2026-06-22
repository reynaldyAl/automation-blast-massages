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
  python src/main.py report --all           # Semua baris, dipaginasi
"""

import sys
import time
from pathlib import Path

# ── Fix encoding UTF-8 untuk Windows (mencegah UnicodeEncodeError pada emoji) ─
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

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
    print_dry_run_preview_table,
)
from scheduler import start_scheduler


# ─── CLI Group ────────────────────────────────────────────────────────────────
@click.group()
def cli():
    """🏥 BPJS Blast Message Automation — BPJS Kesehatan Kantor Cabang Serang"""
    pass


# ─── run command ─────────────────────────────────────────────────────────────
@cli.command()
@click.option("--dry-run",  is_flag=True, default=False, help="Preview tanpa kirim pesan")
@click.option("--wa-only",  is_flag=True, default=False, help="Hanya kirim via WhatsApp")
@click.option("--sms-only", is_flag=True, default=False, help="Hanya kirim via SMS")
@click.option("--fresh",    is_flag=True, default=False, help="Reset state, mulai dari awal")
@click.option("--csv",      "csv_path",   default=None,  help="Path CSV input (override .env)")
@click.option("--template", "tpl_path",   default=None,  help="Path template (override .env)")
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
    send_wa  = config.SEND_WA  and not sms_only
    send_sms = config.SEND_SMS and not wa_only
    if wa_only:
        send_sms = False
    if sms_only:
        send_wa = False

    if dry_run:
        print_dry_run_warning()

    # ── Validasi config ───────────────────────────────────────────────────────
    errs = config.validate()
    if errs:
        for e in errs:
            console.print(f"  [bold red]✗ Config Error:[/bold red] {e}")
        sys.exit(1)

    config.ensure_dirs()

    # ── Load CSV ──────────────────────────────────────────────────────────────
    input_csv  = Path(csv_path) if csv_path else config.INPUT_CSV
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
    engine   = TemplateEngine(tpl_file)

    # ── Dry-run: tabel preview semua peserta ──────────────────────────────────
    if dry_run:
        print_dry_run_preview_table(csv_result.peserta_list, engine)

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
    wa  = WASender(dry_run=dry_run)
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
    total        = len(peserta_list)

    with create_progress() as progress:
        task_id = progress.add_task("Mengirim pesan...", total=total)

        for peserta in peserta_list:
            progress.advance(task_id)

            # Skip jika sudah selesai (resume mode)
            if state.is_done(peserta.row_index):
                progress.update(task_id, description=f"[dim]Skip (sudah): {peserta.nama_peserta}[/dim]")
                continue

            result = SendResult(
                row_index       = peserta.row_index,
                nomor           = peserta.nomor,
                nama_peserta    = peserta.nama_peserta,
                nokapst         = peserta.nokapst,
                nohp_original   = peserta.nohp_original,
                nohp_normalized = peserta.phone.normalized,
                phone_valid     = peserta.phone.is_valid,
            )

            # Nomor tidak valid → skip kirim
            if not peserta.phone.is_valid:
                print_invalid_phone(peserta.nama_peserta, peserta.nohp_original, peserta.phone.message)
                if send_wa  and peserta.send_wa:
                    result.wa_status  = Status.INVALID_PHONE
                    result.wa_error   = peserta.phone.message
                if send_sms and peserta.send_sms:
                    result.sms_status = Status.INVALID_PHONE
                    result.sms_error  = peserta.phone.message
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
                result.wa_status    = wa_status
                result.wa_error     = wa_error
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
                result.sms_error  = sms_error

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
                    row_index       = peserta.row_index,
                    nomor           = peserta.nomor,
                    nama_peserta    = peserta.nama_peserta,
                    nokapst         = peserta.nokapst,
                    nohp_original   = peserta.nohp_original,
                    nohp_normalized = peserta.phone.normalized,
                    phone_valid     = peserta.phone.is_valid,
                    retry_count     = attempt,
                )

                if send_wa and peserta.send_wa:
                    wa_status, wa_err, wa_ss = wa.send(peserta.phone.wa_format, message)
                    retry_result.wa_status    = wa_status
                    retry_result.wa_error     = wa_err
                    retry_result.wa_screenshot = wa_ss

                if send_sms and peserta.send_sms:
                    sms_status, sms_err = sms.send(peserta.phone.display_format, message)
                    retry_result.sms_status = sms_status
                    retry_result.sms_error  = sms_err

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
    state.clear()

    # ── Summary ───────────────────────────────────────────────────────────────
    summary = reporter.get_summary()
    print_summary(summary, dry_run=dry_run)


# ─── preview command ──────────────────────────────────────────────────────────
@cli.command()
@click.option("--template", "tpl_path", default=None,           help="Path template")
@click.option("--nama",     default="SUROTO",                   help="Nama peserta untuk preview")
@click.option("--nokapst",  default="0002223480115",            help="No kartu untuk preview")
def preview(tpl_path, nama, nokapst):
    """Tampilkan preview pesan dari template."""
    print_banner()
    tpl_file = Path(tpl_path) if tpl_path else config.TEMPLATE_FILE
    engine   = TemplateEngine(tpl_file)

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

    errs = config.validate()
    if errs:
        for e in errs:
            console.print(f"  [red]✗[/red] {e}")
    else:
        console.print("  [green]✓[/green] Konfigurasi valid")

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

    sms = SMSSender()
    ok, info = sms.check_device()
    if ok:
        console.print(f"  [green]✓[/green] ADB: HP terdeteksi — {info}")
    else:
        console.print(f"  [yellow]⚠[/yellow] ADB: {info}")

    console.print()


# ─── report command ───────────────────────────────────────────────────────────
@cli.command()
@click.option("--all",       "show_all",  is_flag=True, default=False,
              help="Tampilkan semua baris (default: hanya yang bermasalah)")
@click.option("--page-size", default=25,  show_default=True,
              help="Jumlah baris per halaman saat --all digunakan")
def report(show_all, page_size):
    """Tampilkan laporan terakhir. Default: hanya baris gagal/invalid."""
    import glob
    import pandas as pd
    from rich.table import Table
    from rich import box as rich_box
    from rich.panel import Panel

    reports = sorted(glob.glob(str(config.REPORT_DIR / "report_*.csv")), reverse=True)
    if not reports:
        console.print("  [yellow]Belum ada laporan. Jalankan 'run' terlebih dahulu.[/yellow]")
        return

    latest = reports[0]
    print_section("📊 Laporan Pengiriman Terakhir")
    console.print(f"  [dim]File: {latest}[/dim]")

    # ── Baca CSV per chunk — hemat memory untuk data besar ────────────────────
    PROBLEM_STATUSES = {"FAILED", "INVALID_PHONE", "NOT_ON_WA", "NO_DEVICE"}

    total = wa_ok = sms_ok = wa_gagal = sms_gagal = wa_not_wa = invalid_phone = 0
    problem_rows = []

    for chunk in pd.read_csv(latest, chunksize=500, dtype=str):
        chunk = chunk.fillna("")
        total         += len(chunk)
        wa_ok         += (chunk["wa_status"]  == "SUCCESS").sum()
        sms_ok        += (chunk["sms_status"] == "SUCCESS").sum()
        wa_gagal      += (chunk["wa_status"]  == "FAILED").sum()
        sms_gagal     += (chunk["sms_status"] == "FAILED").sum()
        wa_not_wa     += (chunk["wa_status"]  == "NOT_ON_WA").sum()
        invalid_phone += (chunk["phone_valid"].str.lower() == "false").sum()

        if not show_all:
            mask = (
                chunk["wa_status"].isin(PROBLEM_STATUSES) |
                chunk["sms_status"].isin(PROBLEM_STATUSES) |
                (chunk["phone_valid"].str.lower() == "false")
            )
            problem_rows.append(chunk[mask])

    # ── Summary panel ─────────────────────────────────────────────────────────
    wa_pct  = f"{wa_ok  / total * 100:.1f}%" if total else "—"
    sms_pct = f"{sms_ok / total * 100:.1f}%" if total else "—"

    st = Table(box=rich_box.SIMPLE, show_header=False, padding=(0, 2))
    st.add_column("Label", style="dim")
    st.add_column("Value", style="bold white")
    st.add_row("Total peserta",     str(total))
    st.add_row("WA sukses",         f"[green]{wa_ok}[/green]  ({wa_pct})")
    st.add_row("SMS sukses",        f"[green]{sms_ok}[/green]  ({sms_pct})")
    st.add_row("WA gagal kirim",    f"[red]{wa_gagal}[/red]")
    st.add_row("SMS gagal kirim",   f"[red]{sms_gagal}[/red]")
    st.add_row("Tidak di WA",       f"[magenta]{wa_not_wa}[/magenta]")
    st.add_row("Nomor tidak valid", f"[yellow]{invalid_phone}[/yellow]")

    console.print()
    console.print(Panel(st, title="[bold]Ringkasan[/bold]", border_style="cyan", padding=(0, 1)))

    # ── Helpers ───────────────────────────────────────────────────────────────
    def badge(status):
        if str(status) in ("nan", "", "None", "SKIPPED"):
            return "[dim]—[/dim]"
        return {
            "SUCCESS":       "[bold green]✓ OK[/bold green]",
            "FAILED":        "[bold red]✗ GAGAL[/bold red]",
            "INVALID_PHONE": "[bold yellow]⚠ INVALID[/bold yellow]",
            "NOT_ON_WA":     "[bold magenta]⚠ TDK DI WA[/bold magenta]",
            "NO_DEVICE":     "[bold red]⚠ NO DEVICE[/bold red]",
        }.get(str(status), f"[dim]{status}[/dim]")

    def make_table():
        t = Table(box=rich_box.SIMPLE_HEAD, border_style="dim",
                  show_header=True, header_style="bold cyan",
                  show_lines=False, padding=(0, 1))
        t.add_column("#",          style="dim",        width=5,  justify="right")
        t.add_column("Nama",       style="bold white",  min_width=16)
        t.add_column("No HP",      style="cyan",        min_width=13)
        t.add_column("WA",         justify="center",    min_width=13)
        t.add_column("SMS",        justify="center",    min_width=13)
        t.add_column("Keterangan", style="dim red",     min_width=35)
        t.add_column("Jam",        style="dim",         width=6)
        return t

    def add_row(t, row):
        reason = str(row.get("failure_reason", ""))
        if reason in ("nan", "", "None"):
            reason = ""
        elif len(reason) > 60:
            reason = reason[:60] + "…"
        ts = str(row.get("timestamp", ""))
        t.add_row(
            str(row.get("nomor",         "")),
            str(row.get("nama_peserta",  "")),
            str(row.get("nohp_original", "")),
            badge(row.get("wa_status",  "")),
            badge(row.get("sms_status", "")),
            reason,
            ts[11:16] if len(ts) >= 16 else ts,
        )

    # ── Default: tampilkan HANYA baris bermasalah ─────────────────────────────
    if not show_all:
        df_prob = pd.concat(problem_rows, ignore_index=True) if problem_rows else pd.DataFrame()
        n = len(df_prob)
        console.print()
        if n == 0:
            console.print(
                "  [bold green]✓ Semua peserta berhasil dikirim! "
                "Tidak ada baris bermasalah.[/bold green]\n"
            )
        else:
            console.print(
                f"  [bold yellow]⚠ {n} baris bermasalah (dari {total} total):[/bold yellow]\n"
            )
            t = make_table()
            for _, row in df_prob.iterrows():
                add_row(t, row)
            console.print(t)
            console.print(
                f"\n  [dim]Gunakan  python src/main.py report --all  "
                f"untuk lihat seluruh {total} baris.[/dim]\n"
            )
        return

    # ── Mode --all: baca ulang + paginasi ────────────────────────────────────
    console.print(
        f"\n  Menampilkan semua [bold]{total}[/bold] baris, "
        f"{page_size} per halaman.\n"
        f"  Tekan [bold]Enter[/bold] untuk lanjut, "
        f"[bold]q[/bold]+Enter untuk berhenti.\n"
    )

    buf, page, shown = [], 1, 0
    for chunk in pd.read_csv(latest, chunksize=500, dtype=str):
        chunk = chunk.fillna("")
        for _, row in chunk.iterrows():
            buf.append(row)
            shown += 1
            if len(buf) >= page_size:
                t = make_table()
                for r in buf:
                    add_row(t, r)
                console.print(t)
                console.print(
                    f"  [dim]Hal. {page} — baris "
                    f"{shown - page_size + 1}–{shown} dari {total}[/dim]"
                )
                buf, page = [], page + 1
                if shown < total:
                    try:
                        if input("\n  [Enter=lanjut | q=berhenti]: ").strip().lower() == "q":
                            console.print("  [dim]Dihentikan.[/dim]\n")
                            return
                    except (EOFError, KeyboardInterrupt):
                        return
                    console.print()

    if buf:
        t = make_table()
        for r in buf:
            add_row(t, r)
        console.print(t)

    console.print(f"\n  [dim]Selesai — {total} baris ditampilkan.[/dim]\n")


# ─── Entry Point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    cli()
