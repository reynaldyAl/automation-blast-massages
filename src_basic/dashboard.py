"""
dashboard.py — Terminal UI menggunakan Rich untuk tampilan progress real-time
"""

from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import (
    Progress, SpinnerColumn, BarColumn,
    TextColumn, TimeElapsedColumn, TaskID,
)
from rich.text import Text
from rich import box
from rich.align import Align
from rich.columns import Columns

console = Console()


# ─── Banner ──────────────────────────────────────────────────────────────────
def print_banner():
    banner = Text()
    banner.append("  ╔══════════════════════════════════════════════╗\n", style="bold cyan")
    banner.append("  ║   BPJS BLAST MESSAGE AUTOMATION SYSTEM       ║\n", style="bold cyan")
    banner.append("  ║   BPJS Kesehatan — Kantor Cabang Serang       ║\n", style="cyan")
    banner.append("  ╚══════════════════════════════════════════════╝\n", style="bold cyan")
    console.print(banner)
    console.print(
        f"  [dim]Started at {datetime.now().strftime('%A, %d %B %Y — %H:%M:%S')}[/dim]\n"
    )


# ─── Config Summary ───────────────────────────────────────────────────────────
def print_config_summary(config, total_peserta: int):
    table = Table(box=box.ROUNDED, border_style="dim", show_header=False, padding=(0, 1))
    table.add_column("Key", style="bold dim", width=22)
    table.add_column("Value", style="white")

    table.add_row("📂 Input CSV", str(config.INPUT_CSV))
    table.add_row("📄 Template", str(config.TEMPLATE_FILE))
    table.add_row("👥 Total Peserta", str(total_peserta))
    table.add_row("📱 Kirim WA", "[green]✓ Aktif[/green]" if config.SEND_WA else "[dim]✗ Nonaktif[/dim]")
    table.add_row("💬 Kirim SMS", "[green]✓ Aktif[/green]" if config.SEND_SMS else "[dim]✗ Nonaktif[/dim]")
    table.add_row("⏱ Delay WA", f"{config.WA_DELAY_SECONDS}s" if config.SEND_WA else "-")
    table.add_row("⏱ Delay SMS", f"{config.SMS_DELAY_SECONDS}s" if config.SEND_SMS else "-")
    table.add_row("🔁 Retry Failed", "[green]✓[/green]" if config.RETRY_FAILED else "[dim]✗[/dim]")

    console.print(Panel(table, title="[bold]Konfigurasi[/bold]", border_style="cyan"))


# ─── Progress Bar ─────────────────────────────────────────────────────────────
def create_progress() -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40),
        TextColumn("[cyan]{task.completed}/{task.total}[/cyan]"),
        TextColumn("[dim]{task.percentage:>5.1f}%[/dim]"),
        TimeElapsedColumn(),
        console=console,
        refresh_per_second=10,
    )


# ─── Status Display Helpers ───────────────────────────────────────────────────
def status_badge(status: str) -> str:
    mapping = {
        "SUCCESS":      "[bold green]✓ SUCCESS[/bold green]",
        "FAILED":       "[bold red]✗ FAILED[/bold red]",
        "INVALID_PHONE":"[bold yellow]⚠ INVALID PHONE[/bold yellow]",
        "NOT_ON_WA":    "[bold magenta]⚠ NOT ON WA[/bold magenta]",
        "SKIPPED":      "[dim]— SKIPPED[/dim]",
        "NO_DEVICE":    "[bold red]⚠ NO DEVICE[/bold red]",
        "RETRYING":     "[bold yellow]↺ RETRYING[/bold yellow]",
    }
    return mapping.get(status, f"[dim]{status}[/dim]")


def print_send_result(peserta_name: str, phone: str, wa_status: str, sms_status: str, error: str = ""):
    wa_badge = status_badge(wa_status)
    sms_badge = status_badge(sms_status)
    line = f"  [bold white]{peserta_name:<20}[/bold white]  [dim]{phone:<15}[/dim]  WA: {wa_badge}  SMS: {sms_badge}"
    if error:
        line += f"\n    [dim red]↳ {error}[/dim red]"
    console.print(line)


def print_invalid_phone(peserta_name: str, phone_raw: str, reason: str):
    console.print(
        f"  [bold yellow]⚠ SKIP[/bold yellow]  [white]{peserta_name}[/white]  "
        f"[red]{phone_raw}[/red]  [dim]→ {reason}[/dim]"
    )


def print_section(title: str):
    console.rule(f"[bold cyan]{title}[/bold cyan]")


def print_dry_run_warning():
    console.print(Panel(
        "[bold yellow]🧪 DRY RUN MODE[/bold yellow]\n"
        "[dim]Tidak ada pesan yang akan dikirim. Mode ini hanya untuk preview.[/dim]",
        border_style="yellow",
    ))


def print_resume_info(done_count: int):
    console.print(
        f"\n  [cyan]↺ Resume mode:[/cyan] [dim]{done_count} baris sebelumnya sudah diproses, dilanjutkan...[/dim]\n"
    )


# ─── Final Summary ────────────────────────────────────────────────────────────
def print_summary(summary: dict, dry_run: bool = False):
    console.print()
    console.rule("[bold green]✅ SELESAI[/bold green]" if not dry_run else "[bold yellow]🧪 DRY RUN SELESAI[/bold yellow]")

    # WA Table
    wa_table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan")
    wa_table.add_column("Channel", style="bold")
    wa_table.add_column("Total", justify="right")
    wa_table.add_column("Sukses", justify="right", style="green")
    wa_table.add_column("Gagal", justify="right", style="red")
    wa_table.add_column("Tdk di WA", justify="right", style="magenta")
    wa_table.add_column("No Invalid", justify="right", style="yellow")

    wa_table.add_row(
        "📱 WhatsApp",
        str(summary["wa_total"]),
        str(summary["wa_success"]),
        str(summary["wa_failed"]),
        str(summary["wa_not_on_wa"]),
        str(summary["wa_invalid"]),
    )
    wa_table.add_row(
        "💬 SMS",
        str(summary["sms_total"]),
        str(summary["sms_success"]),
        str(summary["sms_failed"]),
        str(summary.get("sms_no_device", 0)),
        str(summary["wa_invalid"]),
    )

    console.print(Panel(wa_table, title="[bold]Ringkasan Pengiriman[/bold]", border_style="green"))

    if not dry_run:
        console.print(f"\n  📄 [cyan]Laporan CSV[/cyan]  : [link]{summary['report_path']}[/link]")
        console.print(f"  📋 [cyan]Log file[/cyan]    : [link]{summary['log_path']}[/link]")

    console.print()
