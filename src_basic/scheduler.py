"""
scheduler.py — Penjadwalan otomatis menggunakan APScheduler
Dinonaktifkan secara default. Aktifkan via SCHEDULER_ENABLED=true di .env
"""

from config import config


def start_scheduler(job_func):
    """
    Jalankan job_func sesuai jadwal cron dari config.
    Hanya berjalan jika SCHEDULER_ENABLED=true.

    Args:
        job_func: Fungsi yang akan dijadwalkan (callable tanpa argumen)
    """
    if not config.SCHEDULER_ENABLED:
        # Langsung jalankan sekali jika scheduler tidak aktif
        job_func()
        return

    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        print("[Scheduler] APScheduler tidak terinstall. Jalankan: pip install apscheduler")
        job_func()
        return

    parts = config.SCHEDULER_CRON.split()
    if len(parts) != 5:
        print(f"[Scheduler] Format SCHEDULER_CRON tidak valid: '{config.SCHEDULER_CRON}'")
        print("[Scheduler] Format harus: 'menit jam hari bulan hari_minggu'")
        print("[Scheduler] Menjalankan sekali sekarang...")
        job_func()
        return

    minute, hour, day, month, day_of_week = parts
    trigger = CronTrigger(
        minute=minute,
        hour=hour,
        day=day,
        month=month,
        day_of_week=day_of_week,
    )

    scheduler = BlockingScheduler()
    scheduler.add_job(job_func, trigger)

    print(f"\n[Scheduler] ✓ Aktif — Jadwal: '{config.SCHEDULER_CRON}'")
    print("[Scheduler] Tekan Ctrl+C untuk menghentikan scheduler.\n")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n[Scheduler] Scheduler dihentikan.")
        scheduler.shutdown()
