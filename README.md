# 🏥 BPJS Blast Message Automation

Sistem otomasi pengiriman pesan blast untuk **BPJS Kesehatan Kantor Cabang Serang**.
Mendukung dua channel: **WhatsApp Web** dan **SMS via HP Android (ADB/USB)**.

> Cukup ganti `data/input.csv` → jalankan → selesai. ✅

---

## ✨ Fitur

| Fitur | Keterangan |
|---|---|
| 📱 **WA Web Automation** | Playwright Chromium, persistent login (QR sekali) |
| 💬 **SMS via ADB** | Kirim SMS langsung dari HP Android via USB |
| 📄 **Template Jinja2** | Edit template pesan tanpa ubah kode |
| ✅ **Validasi Nomor HP** | Normalisasi 08xx→628xx, deteksi nomor tidak valid |
| 📸 **Screenshot on Error** | Capture browser saat nomor WA bermasalah |
| 🔁 **Retry Otomatis** | Ulangi pesan yang gagal secara otomatis |
| ↺ **Resume Mode** | Lanjut dari baris terakhir jika proses terhenti |
| 🧪 **Dry Run Mode** | Preview pesan tanpa benar-benar mengirim |
| 📊 **Dashboard Terminal** | Progress bar dan ringkasan berwarna (Rich) |
| 📋 **Laporan CSV** | Hasil kirim real-time, tersimpan di `data/reports/` |
| ⏱ **Rate Limiter** | Delay antar pesan, anti-banned WA |
| 📅 **Scheduler** | Kirim terjadwal via cron (nonaktif by default) |
| 🐳 **Docker** | Siap deploy dengan docker-compose |

---

## 🚀 Quick Start

### 🐳 Dengan Docker (Direkomendasikan)

> **Prasyarat:** Hanya [Docker Desktop](https://www.docker.com/products/docker-desktop/) — pastikan sudah **dibuka dan berjalan** sebelum menjalankan perintah di bawah.

```bash
# 1. Salin & edit konfigurasi
copy .env.example .env        # Windows
cp .env.example .env          # Linux/Mac

# 2. Edit data/input.csv (isi data peserta)

# 3. Build image (sekali saja)
docker-compose build

# 4. Validasi
docker-compose run --rm blast validate

# 5. Preview tanpa kirim
docker-compose run --rm blast run --dry-run

# 6. Kirim!
docker-compose run --rm blast run
```

### 🐍 Tanpa Docker (Python Langsung)

> **Prasyarat:** Python 3.10+ — [Download](https://www.python.org/downloads/)

```bash
# Setup virtual environment
python -m venv venv
venv\Scripts\activate       # Windows
source venv/bin/activate    # Linux/Mac

# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Konfigurasi & jalankan
copy .env.example .env
python src/main.py validate
python src/main.py run --dry-run
python src/main.py run
```

---

## 📁 Struktur Project

```
automation-blast-massages/
├── data/
│   ├── input.csv              ← ✏️ GANTI INI setiap run
│   └── reports/               ← Laporan otomatis tersimpan di sini
├── templates/
│   └── bpjs_message.txt       ← ✏️ Edit template pesan di sini
├── src/
│   ├── main.py                ← Entry point CLI
│   ├── config.py              ← Konfigurasi dari .env
│   ├── csv_handler.py         ← Baca & validasi CSV
│   ├── phone_validator.py     ← Normalisasi nomor HP
│   ├── template_engine.py     ← Render template Jinja2
│   ├── wa_sender.py           ← WA Web (Playwright)
│   ├── sms_sender.py          ← SMS via ADB
│   ├── reporter.py            ← Logging & laporan CSV
│   ├── dashboard.py           ← Terminal UI (Rich)
│   └── scheduler.py           ← Scheduler (APScheduler)
├── docs/
│   ├── SETUP.md               ← Panduan setup lengkap
│   └── USAGE.md               ← Panduan penggunaan
├── wa_profile/                ← Sesi WA tersimpan di sini
├── screenshots/               ← Screenshot error WA
├── .env.example               ← Template konfigurasi
├── Dockerfile
└── docker-compose.yml
```

---

## 📋 Format CSV

```csv
nomor,nama_peserta,nokapst,nohp,send_wa,send_sms
1,SUROTO,0002223480115,087771580543,TRUE,TRUE
2,SITI AMINAH,0001082332293,081234567890,TRUE,FALSE
```

---

## 💬 Perintah

Setiap perintah tersedia dalam dua versi:

| Aksi | 🐳 Docker | 🐍 Python |
|---|---|---|
| Kirim semua | `docker-compose run --rm blast run` | `python src/main.py run` |
| Dry run | `... run --dry-run` | `... run --dry-run` |
| Hanya WA | `... run --wa-only` | `... run --wa-only` |
| Hanya SMS | `... run --sms-only` | `... run --sms-only` |
| Reset & ulang | `... run --fresh` | `... run --fresh` |
| Validasi | `... validate` | `... validate` |
| Preview template | `... preview` | `... preview` |
| Lihat laporan | `... report` | `... report` |

---

## 📖 Dokumentasi Lengkap

- [📋 SETUP.md](docs/SETUP.md) — Panduan setup dari awal (Docker & Python)
- [📖 USAGE.md](docs/USAGE.md) — Panduan penggunaan lengkap

---

## 🛠 Tech Stack

- **Python 3.11** · **Playwright** · **ADB** · **Jinja2** · **Rich + Click** · **Pandas** · **APScheduler** · **Docker**

---

*Dibuat untuk BPJS Kesehatan Kantor Cabang Serang*
