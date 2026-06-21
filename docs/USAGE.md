# 📖 Panduan Penggunaan — BPJS Blast Message Automation

## Alur Kerja Setiap Pengiriman

```
1. Edit data/input.csv  →  2. (Opsional) Edit template  →  3. Validate  →  4. Run
```

---

## 💬 Daftar Perintah

Setiap perintah tersedia dalam dua versi: **Docker** dan **Python langsung**.

### `run` — Kirim Pesan

```bash
# 🐳 Docker
docker-compose run --rm blast run

# 🐍 Python
python src/main.py run
```

| Option | Keterangan |
|---|---|
| `--dry-run` | Preview tanpa kirim pesan |
| `--wa-only` | Hanya kirim via WhatsApp |
| `--sms-only` | Hanya kirim via SMS |
| `--fresh` | Reset progress, mulai dari awal |
| `--csv PATH` | Gunakan CSV selain default |
| `--template PATH` | Gunakan template selain default |

**Contoh:**
```bash
# 🐳 Docker
docker-compose run --rm blast run --dry-run
docker-compose run --rm blast run --wa-only
docker-compose run --rm blast run --csv data/batch2.csv
docker-compose run --rm blast run --wa-only --template templates/reminder.txt

# 🐍 Python
python src/main.py run --dry-run
python src/main.py run --wa-only
python src/main.py run --csv data/batch2.csv
```

---

### `validate` — Validasi Sebelum Kirim

```bash
# 🐳 Docker
docker-compose run --rm blast validate

# 🐍 Python
python src/main.py validate
```

Mengecek:
- ✓ File CSV ditemukan dan kolom lengkap
- ✓ Konfigurasi `.env` valid
- ✓ HP Android terdeteksi via ADB
- ⚠ Nomor HP yang tidak valid (akan di-skip)

---

### `preview` — Lihat Preview Pesan

```bash
# 🐳 Docker
docker-compose run --rm blast preview
docker-compose run --rm blast preview --nama "BUDI SANTOSO" --nokapst "0001234567890"

# 🐍 Python
python src/main.py preview
python src/main.py preview --nama "BUDI SANTOSO" --nokapst "0001234567890"
```

---

### `report` — Lihat Laporan Terakhir

```bash
# 🐳 Docker
docker-compose run --rm blast report

# 🐍 Python
python src/main.py report
```

---

## 📊 Memahami Status Pengiriman

| Status | Keterangan | Tindakan |
|---|---|---|
| `SUCCESS` | ✅ Pesan berhasil dikirim | — |
| `FAILED` | ❌ Gagal kirim (error teknis) | Cek log, akan di-retry otomatis |
| `INVALID_PHONE` | ⚠ Nomor HP tidak valid | Perbaiki di CSV |
| `NOT_ON_WA` | ⚠ Nomor tidak terdaftar di WA | Kirim SMS saja |
| `NO_DEVICE` | ⚠ HP tidak terdeteksi ADB | Cek koneksi USB |
| `SKIPPED` | — Channel dinonaktifkan | Normal |

---

## ↺ Resume Mode (Lanjut Setelah Gangguan)

Jika proses berhenti di tengah (mati lampu, error kritis, dll.):

```bash
# 🐳 Docker — otomatis lanjut dari yang belum terkirim
docker-compose run --rm blast run

# 🐍 Python
python src/main.py run
```

Sistem menyimpan progress di file `.state.json`. Untuk mulai dari awal:

```bash
# 🐳 Docker
docker-compose run --rm blast run --fresh

# 🐍 Python
python src/main.py run --fresh
```

---

## 📦 Multi-Batch / Multi-Template

Untuk mengirim ke beberapa kelompok dengan template berbeda:

```bash
# 🐳 Docker
docker-compose run --rm blast run --csv data/tunggakan.csv --template templates/bpjs_message.txt
docker-compose run --rm blast run --csv data/reminder.csv --template templates/reminder.txt

# 🐍 Python
python src/main.py run --csv data/tunggakan.csv --template templates/bpjs_message.txt
python src/main.py run --csv data/reminder.csv --template templates/reminder.txt
```

---

## 📋 Laporan CSV

File laporan tersimpan di `data/reports/report_YYYYMMDD_HHMMSS.csv`.

| Kolom | Keterangan |
|---|---|
| `nomor` | Nomor urut |
| `nama_peserta` | Nama peserta |
| `nokapst` | Nomor kartu |
| `nohp_original` | Nomor asli dari CSV |
| `nohp_normalized` | Nomor setelah normalisasi |
| `phone_valid` | TRUE/FALSE |
| `wa_status` | Status pengiriman WA |
| `wa_error` | Pesan error WA (jika ada) |
| `wa_screenshot` | Path screenshot error |
| `sms_status` | Status pengiriman SMS |
| `sms_error` | Pesan error SMS (jika ada) |
| `timestamp` | Waktu pengiriman |
| `retry_count` | Jumlah percobaan retry |

---

## 📅 Mengaktifkan Scheduler

Untuk mengirim otomatis setiap hari jam 09:00, edit `.env`:

```ini
SCHEDULER_ENABLED=true
SCHEDULER_CRON=0 9 * * *
```

Lalu jalankan:

```bash
# 🐳 Docker
docker-compose run --rm blast run

# 🐍 Python
python src/main.py run
```

Proses menunggu jadwal dan berjalan otomatis. Tekan `Ctrl+C` untuk menghentikan.

---

## 💡 Tips & Best Practices

1. **Selalu `validate` dulu** sebelum run di produksi
2. **Gunakan `--dry-run`** untuk cek template dengan data baru
3. **Jangan terlalu cepat** — atur `WA_DELAY_SECONDS` minimal 5 detik
4. **Backup laporan** CSV dari `data/reports/` secara berkala
5. **Layar HP harus menyala** saat proses SMS berlangsung
6. **Docker untuk produksi**, Python langsung untuk development/testing
