# 📋 Panduan Setup — BPJS Blast Message Automation

Ada dua cara menjalankan project ini. Pilih salah satu:

| | 🐳 Dengan Docker | 🐍 Tanpa Docker (Python Langsung) |
|---|---|---|
| **Prasyarat** | Docker Desktop saja | Python 3.10+, ADB |
| **Setup awal** | Lebih mudah | Perlu install manual |
| **Rekomendasi** | ✅ Disarankan | Untuk development |

---

## 🐳 OPSI A — Dengan Docker (Direkomendasikan)

### Prasyarat

| Kebutuhan | Link |
|---|---|
| 🐳 **Docker Desktop** | [Download](https://www.docker.com/products/docker-desktop/) |

> Tidak perlu install Python, pip, playwright, atau ADB secara manual —
> semuanya sudah dibundel di dalam Docker image.

### A1. Pastikan Docker Desktop Berjalan

Sebelum menjalankan perintah Docker apapun, **buka Docker Desktop** dan tunggu sampai statusnya **"Docker Desktop is running"** (icon whale di system tray).

> ⚠️ Error `failed to connect to docker API` artinya Docker Desktop belum dibuka.

### A2. Clone & Konfigurasi

```bash
git clone <repo-url>
cd automation-blast-massages

# Salin file konfigurasi
copy .env.example .env    # Windows
cp .env.example .env      # Linux/Mac
```

Edit `.env` sesuai kebutuhan (buka dengan teks editor biasa).

### A3. Build Image (Sekali Saja)

```bash
docker-compose build
```

> Build ulang hanya diperlukan jika ada perubahan kode atau `requirements.txt`.

### A4. Validasi Setup

```bash
docker-compose run --rm blast validate
```

### A5. Scan QR WhatsApp (Pertama Kali)

```bash
# Buka browser untuk scan QR
docker-compose run --rm blast run --dry-run
```

1. Browser Chromium terbuka otomatis
2. Di HP: **WhatsApp → Titik Tiga → Perangkat Tertaut → Tautkan Perangkat**
3. Scan QR code di browser
4. ✅ Sesi tersimpan di `wa_profile/` — tidak perlu scan ulang

### A6. Jalankan

```bash
docker-compose run --rm blast run
```

---

## 🐍 OPSI B — Tanpa Docker (Python Langsung)

### Prasyarat

| Kebutuhan | Link / Cara Install |
|---|---|
| **Python 3.10+** | [Download](https://www.python.org/downloads/) |
| **ADB** (untuk SMS) | Lihat langkah B3 |

### B1. Clone & Virtual Environment

```bash
git clone <repo-url>
cd automation-blast-massages

# Buat & aktifkan virtual environment
python -m venv venv

# Windows:
venv\Scripts\activate

# Linux/Mac:
source venv/bin/activate
```

### B2. Install Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### B3. Install ADB (untuk SMS)

**Windows** — unduh [Android SDK Platform Tools](https://developer.android.com/studio/releases/platform-tools), ekstrak, lalu tambahkan ke PATH.

Atau via winget:
```powershell
winget install Google.PlatformTools
```

**Linux:**
```bash
sudo apt install android-tools-adb
```

Verifikasi:
```bash
adb version
# Android Debug Bridge version 1.0.xx
```

### B4. Konfigurasi

```bash
copy .env.example .env   # Windows
cp .env.example .env     # Linux/Mac
```

Edit `.env` sesuai kebutuhan.

### B5. Aktifkan USB Debugging di HP Android

1. **Pengaturan → Tentang Ponsel** → ketuk **Nomor Versi** 7 kali
2. **Pengaturan → Opsi Pengembang** → aktifkan **USB Debugging**
3. Sambungkan HP via USB → izinkan di popup HP
4. Verifikasi: `adb devices` → harus muncul device dengan status `device`

### B6. Validasi

```bash
python src/main.py validate
```

### B7. Scan QR WhatsApp (Pertama Kali)

```bash
python src/main.py run --dry-run
```

Scan QR code yang muncul di browser Chromium.

### B8. Jalankan

```bash
python src/main.py run
```

---

## 📁 Struktur Folder Penting

```
automation-blast-massages/
├── data/
│   ├── input.csv           ← ✏️ GANTI INI setiap run (data peserta)
│   └── reports/            ← Laporan hasil kirim (otomatis dibuat)
├── templates/
│   └── bpjs_message.txt    ← ✏️ Edit template pesan di sini
├── wa_profile/             ← Sesi WA Web tersimpan (jangan dihapus)
├── screenshots/            ← Screenshot error WA (otomatis)
└── .env                    ← ✏️ Konfigurasi (dari .env.example)
```

---

## Troubleshooting

### 🟡 Docker: `failed to connect to docker API`
→ **Docker Desktop belum dibuka.** Buka Docker Desktop, tunggu hingga status "running", lalu coba lagi.

### 🟡 Docker: warning `version is obsolete`
→ Sudah diperbaiki (baris `version` dihapus dari `docker-compose.yml`).

### 🟡 WA: QR expired / harus scan ulang
```bash
# Hapus sesi lama
rmdir /s /q wa_profile   # Windows
rm -rf wa_profile/       # Linux/Mac

# Jalankan ulang
docker-compose run --rm blast run --dry-run   # Docker
python src/main.py run --dry-run              # Non-Docker
```

### 🟡 SMS: "Tidak ada HP yang terdeteksi"
- Cek kabel USB
- Pastikan USB Debugging aktif
- Jalankan `adb kill-server && adb start-server`
- Di Docker Windows: ADB via USB memerlukan konfigurasi tambahan (disarankan pakai non-Docker untuk SMS)

### 🟡 SMS: Pesan tidak terkirim otomatis
- Naikkan `ADB_SEND_WAIT` di `.env` (coba nilai 5 atau 7)
- Pastikan layar HP tidak terkunci saat proses berjalan
