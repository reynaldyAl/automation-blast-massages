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
import random
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
from csv_handler import load_csv, Peserta
from template_engine import TemplateEngine, get_salam
from wa_sender import WASender
from sms_sender import SMSSender
from reporter import Reporter, StateManager, SendResult, Status, init_file_logger
from dashboard import (
    console, print_banner, print_config_summary,
    create_progress, print_send_result, print_invalid_phone,
    print_section, print_dry_run_warning, print_resume_info, print_summary,
    print_dry_run_preview_table,
)
from scheduler import start_scheduler


# ─── Helper: pilih template engine berdasarkan ada/tidaknya nominal ────────────
def _get_engine(tpl_file: Path, peserta: "Peserta") -> TemplateEngine:
    """
    Pilih template engine sesuai kondisi peserta:
    - Ada nominal_tunggakan → pakai bpjs_message_nominal.txt (di folder yang sama)
    - Tidak ada / kolom tidak ada → pakai template default
    """
    if peserta.nominal_tunggakan:
        nominal_tpl = tpl_file.parent / "bpjs_message_nominal.txt"
        if nominal_tpl.exists():
            return TemplateEngine(nominal_tpl)
    return TemplateEngine(tpl_file)


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
        print_dry_run_preview_table(
            csv_result.peserta_list, engine,
            tpl_file=tpl_file,
            get_engine_fn=_get_engine,
        )

    # ── Tampilkan summary config ──────────────────────────────────────────────
    print_config_summary(config, csv_result.valid_rows)

    # ── State / Resume ────────────────────────────────────────────────────────
    state = StateManager()
    if fresh:
        state.clear()
        console.print("  [cyan]↺ State direset, mulai dari awal.[/cyan]\n")
    elif state.done_count > 0:
        print_resume_info(state.done_count)
        from rich.prompt import Prompt
        pilihan = Prompt.ask(
            "\n  [bold]Lanjutkan (resume) pengiriman sebelumnya?[/bold]\n"
            "  Ketik [green]y[/green] = Lanjutkan (Resume)\n"
            "  Ketik [red]n[/red] = Ulang dari awal (Reset)",
            choices=["y", "n"],
            default="y"
        ).strip().lower()
        
        if pilihan == "n":
            state.clear()
            console.print("\n  [cyan]↺ State direset, mulai ulang dari baris pertama.[/cyan]\n")
        else:
            console.print("\n  [green]▶ Melanjutkan proses...[/green]\n")

    # ── Init sender & reporter ────────────────────────────────────────────────
    init_file_logger()
    reporter = Reporter()
    wa  = WASender(dry_run=dry_run) if send_wa else None
    sms = SMSSender(dry_run=dry_run) if send_sms else None

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
    print_section("Proses Pengiriman")
    
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

            # Render pesan — pilih template otomatis berdasarkan ada/tidaknya nominal
            _engine = _get_engine(tpl_file, peserta)
            message_wa = _engine.render(
                nama_peserta=peserta.nama_peserta,
                nokapst=peserta.nokapst,
                nominal_tunggakan=peserta.nominal_tunggakan,
            )
            message_sms = _engine.render(
                nama_peserta=peserta.nama_peserta,
                nokapst=peserta.nokapst,
                nominal_tunggakan=peserta.nominal_tunggakan,
                strip_markdown=True,
            )

            progress.update(task_id, description=f"Mengirim: [cyan]{peserta.nama_peserta}[/cyan]")

            # ── Kirim WA ──────────────────────────────────────────────────────
            if send_wa and peserta.send_wa:
                wa_status, wa_error, wa_screenshot = wa.send(
                    phone_e164=peserta.phone.wa_format,
                    message=message_wa,
                )
                result.wa_status    = wa_status
                result.wa_error     = wa_error
                result.wa_screenshot = wa_screenshot

                if wa_status == Status.SUCCESS:
                    delay = random.uniform(config.WA_DELAY_MIN, config.WA_DELAY_MAX)
                    time.sleep(delay)

            # ── Kirim SMS ─────────────────────────────────────────────────────
            if send_sms and peserta.send_sms:
                sms_status, sms_error = sms.send(
                    phone_display=peserta.phone.display_format,
                    message=message_sms,
                )
                result.sms_status = sms_status
                result.sms_error  = sms_error

                if sms_status == Status.SUCCESS:
                    delay = random.uniform(config.SMS_DELAY_MIN, config.SMS_DELAY_MAX)
                    time.sleep(delay)



            # Catat hasil
            reporter.record(result)
            state.mark_done(peserta.row_index, result.wa_status, result.sms_status)
            
            # Jika pesan berhasil terkirim (WA atau SMS) dan bukan mode dry-run, catat ke laporan done
            if not dry_run and (result.wa_status == Status.SUCCESS or result.sms_status == Status.SUCCESS):
                reporter.record_success(peserta)

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
                _engine = _get_engine(tpl_file, peserta)
                message_wa = _engine.render(
                    nama_peserta=peserta.nama_peserta,
                    nokapst=peserta.nokapst,
                    nominal_tunggakan=peserta.nominal_tunggakan,
                )
                message_sms = _engine.render(
                    nama_peserta=peserta.nama_peserta,
                    nokapst=peserta.nokapst,
                    nominal_tunggakan=peserta.nominal_tunggakan,
                    strip_markdown=True,
                )
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
                    wa_status, wa_err, wa_ss = wa.send(peserta.phone.wa_format, message_wa)
                    retry_result.wa_status    = wa_status
                    retry_result.wa_error     = wa_err
                    retry_result.wa_screenshot = wa_ss

                if send_sms and peserta.send_sms:
                    sms_status, sms_err = sms.send(peserta.phone.display_format, message_sms)
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


# ─── generate command ─────────────────────────────────────────────────────────
@cli.command()
@click.option("--template", "tpl_path", default=None, help="Path template (override .env)")
@click.option("--csv",      "csv_path", default=None, help="Path CSV input (langsung pakai, skip menu pilihan)")
@click.option("--output",   "out_path", default=None,
              help="Path file output (default: templates/messages/messages.txt)")
@click.option("--channel",  "channel",  default=None, type=click.Choice(["wa", "sms", "all"]), help="Pilih format untuk WA atau SMS")
def generate(tpl_path, csv_path, out_path, channel):
    """Generate pesan blast per nomor dari CSV."""
    import datetime
    from rich.panel import Panel
    from rich.prompt import Prompt
    from rich import box as rich_box
    from rich.table import Table

    print_banner()
    print_section("✏️  Generate Pesan Blast (Otomatis per Batch)")

    if not channel:
        channel = Prompt.ask(
            "  [bold]Pilih format pesan yang akan di-generate:[/bold]\n"
            "  Ketik [green]wa[/green]  = WhatsApp (dengan format *bold*)\n"
            "  Ketik [cyan]sms[/cyan] = SMS (tanpa format bintang/markdown)\n"
            "  Ketik [yellow]all[/yellow] = Gabungan WA & SMS",
            choices=["wa", "sms", "all"],
            default="wa",
        ).strip().lower()

    # (Resolve template & output dilakukan setelah CSV dipilih)

    # ── Pilih CSV: jika --csv tidak diberikan, tampilkan menu interaktif ───────
    if csv_path:
        csv_file = Path(csv_path)
    else:
        # Scan file .csv di data/ dan data/messages/
        base_dir = config.INPUT_CSV.parent          # biasanya: data/
        msg_dir  = base_dir / "messages"

        csv_candidates = sorted(base_dir.glob("*.csv")) + sorted(msg_dir.glob("*.csv"))

        if not csv_candidates:
            console.print(
                f"  [bold red]✗ Tidak ada file CSV ditemukan di:[/bold red]\n"
                f"    • {base_dir}\n"
                f"    • {msg_dir}\n"
            )
            return

        if len(csv_candidates) == 1:
            # Hanya satu file — langsung pakai
            csv_file = csv_candidates[0]
            console.print(
                f"  [dim]CSV ditemukan (1 file):[/dim] [cyan]{csv_file}[/cyan]\n"
            )
        else:
            # Tampilkan menu pilihan
            console.print("  [bold]Pilih file CSV yang akan digunakan:[/bold]\n")
            for i, f in enumerate(csv_candidates, start=1):
                # Tampilkan path relatif agar lebih pendek
                try:
                    label = f.relative_to(base_dir.parent)
                except ValueError:
                    label = f
                size_kb = f.stat().st_size / 1024
                console.print(
                    f"  [bold cyan][{i}][/bold cyan] {label}  "
                    f"[dim]({size_kb:.1f} KB)[/dim]"
                )
            console.print()

            while True:
                try:
                    raw = Prompt.ask(
                        f"  Masukkan nomor CSV [1-{len(csv_candidates)}]",
                        default="1",
                    ).strip()
                    idx_csv = int(raw)
                    if 1 <= idx_csv <= len(csv_candidates):
                        csv_file = csv_candidates[idx_csv - 1]
                        break
                    console.print(
                        f"  [yellow]⚠ Masukkan angka antara 1 dan {len(csv_candidates)}.[/yellow]"
                    )
                except (ValueError, EOFError, KeyboardInterrupt):
                    console.print("  [bold yellow]⚠ Dibatalkan.[/bold yellow]")
                    return

        console.print()

    # ── Resolve template ──────────────────────────────────────────────
    tpl_file = Path(tpl_path) if tpl_path else config.TEMPLATE_FILE
    nominal_tpl = tpl_file.parent / "bpjs_message_nominal.txt"
    has_nominal_tpl = nominal_tpl.exists()

    # ── Load CSV ──────────────────────────────────────────────────────────────
    csv_result = load_csv(csv_file)
    if csv_result.errors:
        for e in csv_result.errors:
            console.print(f"  [bold red]✗ CSV Error:[/bold red] {e}")
        sys.exit(1)

    peserta_list = csv_result.peserta_list
    total        = len(peserta_list)

    if total == 0:
        console.print("  [yellow]⚠ Tidak ada data peserta di CSV.[/yellow]")
        return

    # ── Konfigurasi Batch & Salam ──
    batches = []
    console.print(f"\n  [bold]Konfigurasi Batch (Total Data: {total})[/bold]")
    mode = Prompt.ask("  Pilih mode: [bold cyan]1[/bold cyan] (Auto-split), [bold cyan]2[/bold cyan] (Manual rentang), [bold cyan]3[/bold cyan] (Tanpa batch)", choices=["1", "2", "3"], default="1")
    
    if mode == "1":
        import math
        from rich.prompt import IntPrompt
        chunk_size = IntPrompt.ask("  Jumlah data per batch", default=50)
        
        total_batches = math.ceil(total / chunk_size)
        last_batch_size = total % chunk_size or chunk_size
        
        console.print(f"  [cyan]=> Total akan terbentuk {total_batches} batch. (Batch ke-{total_batches} berisi sisa {last_batch_size} data).[/cyan]")
        
        batch_salam_map = {}
        unassigned = set(range(1, total_batches + 1))
        
        while unassigned:
            unassigned_str = ", ".join(map(str, sorted(unassigned)))
            console.print(f"\n  [dim]Batch belum diatur: {unassigned_str}[/dim]")
            target_str = Prompt.ask("  Pilih nomor batch (contoh: 1,3,5 atau 1-3) [Enter = isi semua sisanya]").strip()
            
            targets = set()
            if not target_str:
                targets = unassigned.copy()
            else:
                for part in target_str.split(','):
                    part = part.strip()
                    if '-' in part:
                        try:
                            s, e = map(int, part.split('-'))
                            targets.update(range(s, e + 1))
                        except ValueError:
                            pass
                    elif part.isdigit():
                        targets.add(int(part))
            
            valid_targets = targets.intersection(unassigned)
            if not valid_targets:
                console.print("  [red]Input salah, atau batch tersebut sudah diatur sebelumnya.[/red]")
                continue
                
            tgt_list_str = ', '.join(map(str, sorted(valid_targets)))
            salam = Prompt.ask(f"  Salam untuk batch {tgt_list_str} [Enter = otomatis]").strip()
            if not salam:
                salam = get_salam()
                
            for b in valid_targets:
                batch_salam_map[b] = salam
                unassigned.remove(b)

        start_idx = 1
        for batch_num in range(1, total_batches + 1):
            end_idx = min(start_idx + chunk_size - 1, total)
            salam = batch_salam_map[batch_num]
            batches.append({"start": start_idx, "end": end_idx, "salam": salam})
            start_idx = end_idx + 1
            
        console.print(f"\n  [green]✓ Selesai! Mengonfigurasi {len(batches)} batch.[/green]\n")
        
    elif mode == "2":
        console.print("  [dim]Anda bisa membagi data berdasarkan rentang (contoh: 1-50 pagi, 51-100 siang).")
        console.print("  [dim]Kosongkan rentang (tekan Enter) untuk langsung memproses tanpa membagi batch.[/dim]\n")
        start_idx = 1
        batch_num = 1
        while start_idx <= total:
            rentang = Prompt.ask(f"  Batch {batch_num} - Rentang data (contoh: {start_idx}-{min(start_idx+49, total)}) [Enter = selesai]").strip()
            if not rentang:
                break
            try:
                r_start, r_end = map(int, rentang.split('-'))
            except ValueError:
                console.print("  [red]Format salah! Gunakan format start-end (contoh: 1-50)[/red]")
                continue
            
            salam = Prompt.ask(f"  Salam manual untuk Batch {batch_num} [Enter = otomatis]").strip()
            batches.append({"start": r_start, "end": r_end, "salam": salam if salam else get_salam()})
            start_idx = r_end + 1
            batch_num += 1

    if not batches:
        salam = Prompt.ask("  [bold]Masukkan salam manual untuk semua data[/bold] [Enter = otomatis]").strip()
        batches.append({"start": 1, "end": total, "salam": salam if salam else get_salam()})

    # ── Resolve output file ───────────────────────────────────────────────────
    if out_path:
        output_file = Path(out_path)
    else:
        msg_dir = Path(tpl_file).parent / "messages"
        msg_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = f"_{channel}" 
        
        if len(batches) == 1:
            salam_slug = batches[0]['salam'].replace(" ", "").lower()
            output_file = msg_dir / f"messages_{csv_file.stem}{suffix}_{salam_slug}_{total}data_{ts}.txt"
        else:
            output_file = msg_dir / f"messages_{csv_file.stem}{suffix}_multibatch_{total}data_{ts}.txt"

    # ── Buat direktori output jika belum ada ──────────────────────────────────
    output_file.parent.mkdir(parents=True, exist_ok=True)

    console.print(
        f"  [dim]Template default :[/dim] [cyan]{tpl_file}[/cyan]\n"
        + (
            f"  [dim]Template nominal  :[/dim] [cyan]{nominal_tpl}[/cyan]\n"
            if has_nominal_tpl else
            f"  [dim]Template nominal  :[/dim] [yellow]tidak ditemukan (akan pakai default)[/yellow]\n"
        )
        + f"  [dim]CSV              :[/dim] [cyan]{csv_file}[/cyan]\n"
        + f"  [dim]Output           :[/dim] [cyan]{output_file}[/cyan]\n"
        + f"  [dim]Total data       :[/dim] [bold white]{total}[/bold white] peserta\n"
    )
    generated_count = 0

    with open(output_file, "w", encoding="utf-8") as f:
        # Loop per batch
        for batch in batches:
            r_start = batch["start"]
            r_end = batch["end"]
            current_salam = batch["salam"]
            
            # Tulis Header Batch
            f.write(f"===== BLAST WA DAN SMS ({current_salam.upper()}) | Data {r_start}-{r_end} =====\n\n")
            
            # Ambil peserta dalam rentang ini (berdasarkan urutan baris 1-N)
            batch_peserta = [p for p in peserta_list if r_start <= (p.row_index + 1) <= r_end]
            
            for peserta in batch_peserta:
                _engine = _get_engine(tpl_file, peserta)
                
                # Fungsi helper untuk merender pesan
                def render_msg(is_sms_format: bool):
                    return _engine.render(
                        nama_peserta=peserta.nama_peserta,
                        nokapst=peserta.nokapst,
                        nominal_tunggakan=peserta.nominal_tunggakan,
                        strip_markdown=is_sms_format,
                        custom_salam=current_salam,
                        **peserta.extra_data
                    )
                
                wa_link = f" (https://wa.me/{peserta.phone.wa_format})" if peserta.phone.is_valid else ""
                idx_display = peserta.nomor if peserta.nomor is not None else (peserta.row_index + 1)
                
                separator = (
                    "=" * 60 + "\n"
                    + f"# Nomor   : {idx_display}\n"
                    + f"# Nama    : {peserta.nama_peserta}\n"
                    + f"# NOKAPST : {peserta.nokapst}\n"
                    + f"# No HP   : {peserta.nohp_original}{wa_link}\n"
                    + (f"# Nominal : {peserta.nominal_tunggakan}\n" if peserta.nominal_tunggakan else "")
                    + f"# Waktu   : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                )
                
                f.write(separator)
                f.write("Keterangan : Pesan Blast WA dan SMS\n")
                f.write("===========================\n")
                
                if channel in ("wa", "all"):
                    f.write(render_msg(is_sms_format=False).strip() + "\n")
                    f.write("===========================\n")
                
                if channel in ("sms", "all"):
                    f.write(render_msg(is_sms_format=True).strip() + "\n")
                    f.write("===========================\n")
                
                f.write("\n")
                generated_count += 1
                
            f.write("\n")

    # ── Ringkasan akhir ────────────────────────────────────────────────────────
    console.rule("[bold]Selesai[/bold]")
    console.print(
        f"\n  [bold green]✓ {generated_count}[/bold green] pesan di-generate dan disimpan.\n"
    )

    if generated_count > 0:
        console.print(
            f"  [bold]📄 File output:[/bold] [underline cyan]{output_file.resolve()}[/underline cyan]\n"
        )

        # Tanya apakah mau buka file
        try:
            buka = Prompt.ask(
                "  Buka file hasil generate sekarang?",
                choices=["y", "n"],
                default="n",
            ).strip().lower()
            if buka == "y":
                import os
                os.startfile(str(output_file.resolve()))
        except Exception:
            pass

    console.print()

# ─── connect_wireless command ─────────────────────────────────────────────────
@cli.command(name="connect-wireless")
def connect_wireless():
    """Menghubungkan ADB ke HP Android secara nirkabel (via Wi-Fi)."""
    import subprocess
    from rich.prompt import Prompt
    
    print_banner()
    print_section("📱 Hubungkan HP Nirkabel (Wireless ADB)")
    
    console.print("  [cyan]Pastikan:[/cyan]")
    console.print("  1. HP dan Komputer terhubung di jaringan Wi-Fi/Hotspot yang sama.")
    console.print("  2. 'Proses Debug Nirkabel' (Wireless Debugging) sudah diaktifkan di Opsi Pengembang HP Anda.")
    console.print("  3. Anda sudah melihat Alamat IP & Port dari layar HP Anda.\n")
    
    address = Prompt.ask("  Masukkan Alamat IP dan Port (contoh: [bold]192.168.1.5:5555[/bold])").strip()
    
    if not address:
        console.print("  [dim]Dibatalkan.[/dim]")
        return
        
    console.print(f"\n  [dim]Menghubungkan ke {address}...[/dim]")
    try:
        result = subprocess.run(["adb", "connect", address], capture_output=True, text=True)
        output = result.stdout.lower()
        
        if "connected to" in output and "failed" not in output:
            console.print(f"  [bold green]✓ Berhasil terhubung secara nirkabel ke {address}![/bold green]")
            console.print("  [green]Sekarang Anda bisa menggunakan menu pengiriman SMS tanpa mencolokkan kabel USB.[/green]")
        elif "failed to authenticate" in output:
            console.print(f"  [bold yellow]⚠ HP menolak koneksi.[/bold yellow] Silakan cek layar HP Anda dan klik 'Izinkan' (Allow).")
        else:
            console.print(f"  [bold yellow]⚠ Respons ADB:[/bold yellow] {result.stdout.strip()}")
            console.print("  [dim]Periksa kembali IP, Port, dan pastikan HP & PC berada di Wi-Fi yang sama.[/dim]")
    except FileNotFoundError:
        console.print("  [bold red]✖ ADB tidak terdeteksi.[/bold red]")
    except Exception as e:
        console.print(f"  [bold red]✖ Terjadi kesalahan:[/bold red] {e}")
        
    console.print()

# ─── cleanup command ──────────────────────────────────────────────────────────
@cli.command()
def cleanup():
    """Membersihkan file laporan log dan template hasil generate otomatis."""
    from rich.prompt import Prompt
    print_banner()
    print_section("🧹 Cleanup Log & Messages")
    
    if Prompt.ask("  [bold red]Yakin ingin menghapus file log (.log) dan pesan tergenerate (.txt)?[/bold red]", choices=["y", "n"], default="n").strip().lower() != "y":
        console.print("  [dim]Dibatalkan.[/dim]")
        return
        
    deleted_msgs = 0
    msg_dir = config.TEMPLATE_FILE.parent / "messages"
    if msg_dir.exists():
        for f in msg_dir.glob("messages_*.txt"):
            try:
                f.unlink()
                deleted_msgs += 1
            except Exception as e:
                console.print(f"  [yellow]Gagal menghapus {f.name}: {e}[/yellow]")
                
    deleted_reports = 0
    if config.REPORT_DIR.exists():
        for f in config.REPORT_DIR.glob("*.log"):
            try:
                f.unlink()
                deleted_reports += 1
            except Exception as e:
                console.print(f"  [yellow]Gagal menghapus {f.name}: {e}[/yellow]")
                    
    console.print(f"\n  [bold green]✓ Cleanup Selesai[/bold green]")
    console.print(f"  - {deleted_msgs} file pesan dihapus.")
    console.print(f"  - {deleted_reports} file log laporan dihapus.\n")


# ─── Entry Point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    cli()

