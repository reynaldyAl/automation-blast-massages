# 📖 Panduan Penggunaan — BPJS Blast Message Automation

> **Arsitektur yang digunakan:**
> - 📱 **WhatsApp** → 🐳 **Docker** (tidak perlu install Python/Playwright)
> - 💬 **SMS** → 🐍 **Python langsung** (karena ADB butuh akses USB ke Windows)

---

## ─────────────────────────────────────────
## 📱 BAGIAN 1 — WHATSAPP (via Docker)
## ─────────────────────────────────────────

### Prasyarat
- ✅ **Docker Desktop** sudah terinstall dan **sedang berjalan** (icon whale di taskbar)

---

### Step WA-1 — Siapkan Data & Config

**Edit `data/input.csv`** — isi dengan data peserta nyata:
```csv
nomor,nama_peserta,nokapst,nohp,send_wa,send_sms
1,SUROTO,0002223480115,087771580543,TRUE,TRUE
2,SITI AMINAH,0001082332293,081234567890,TRUE,TRUE
```

**Edit `.env`** — pastikan setting ini:
```ini
SEND_WA=true
SEND_SMS=false      ← set false untuk WA-only run
WA_HEADLESS=false   ← false agar browser muncul (wajib untuk scan QR)
WA_DELAY_SECONDS=5
```

---

### Step WA-2 — Validasi

```bash
docker-compose run --rm blast validate
```

Pastikan output:
```
✓ Konfigurasi valid
✓ CSV valid: X peserta ditemukan
```

> ⚠ Warning ADB "tidak ada HP" di sini normal — kita pakai Docker untuk WA saja.

---

### Step WA-3 — Scan QR WhatsApp (HANYA PERTAMA KALI)

```bash
docker-compose run --rm blast run --dry-run
```

1. Browser Chromium terbuka otomatis
2. Di HP: **WhatsApp → ⋮ Titik Tiga → Perangkat Tertaut → Tautkan Perangkat**
3. Scan QR code yang muncul di browser
4. Tunggu sampai WA Web menampilkan daftar chat
5. ✅ Sesi tersimpan di folder `wa_profile/` — **tidak perlu scan QR lagi**

> Sesi WA biasanya bertahan 14–30 hari.
> Jika expired: hapus folder `wa_profile/` dan ulangi step ini.

---

### Step WA-4 — Kirim WhatsApp

```bash
docker-compose run --rm blast run --wa-only
```

Output yang berjalan normal:
```
✓ WhatsApp Web siap!
  SUROTO          08777...   WA: ✅ SUCCESS   SMS: —
  SITI AMINAH     08123...   WA: ✅ SUCCESS   SMS: —
  ...
```

---

### Perintah WA Lainnya

```bash
# Preview pesan (cek template dulu)
docker-compose run --rm blast preview

# Dry run (test tanpa kirim sungguhan)
docker-compose run --rm blast run --wa-only --dry-run

# Lanjut dari yang belum terkirim (jika terhenti di tengah)
docker-compose run --rm blast run --wa-only

# Mulai ulang dari awal
docker-compose run --rm blast run --wa-only --fresh

# Lihat laporan hasil
docker-compose run --rm blast report
```

---

## ─────────────────────────────────────────
## 💬 BAGIAN 2 — SMS (via Python Langsung)
## ─────────────────────────────────────────

### Prasyarat
- ✅ Python 3.10+ (cek: `python --version`)
- ✅ ADB terinstall (cek: `adb version`)
- ✅ HP Android tersambung USB dengan USB Debugging aktif
- ✅ Virtual environment sudah dibuat (`venv/`)
- ✅ Dependencies terinstall (`requirements-sms.txt`)

> Jika belum setup: jalankan `setup.bat` sebagai Administrator.

---

### Step SMS-1 — Buka Terminal & Aktifkan venv

Buka **Command Prompt** atau **PowerShell**, lalu:

```powershell
# Pindah ke folder project
cd "D:\04 Grinding\02_Github\automation-blast-massages"

# Aktifkan virtual environment
.\venv\Scripts\Activate.ps1        # PowerShell
# ATAU
venv\Scripts\activate.bat          # Command Prompt
```

Tanda venv aktif: ada `(venv)` di awal baris terminal.

---

### Step SMS-2 — Sambungkan HP Android

1. Pastikan **USB Debugging** aktif di HP:
   ```
   Pengaturan → Tentang Ponsel → ketuk Nomor Versi 7x
   Pengaturan → Opsi Pengembang → USB Debugging → ON
   ```

2. Sambungkan HP via kabel USB ke komputer

3. Di HP: tap **"Izinkan"** pada popup USB Debugging

4. Verifikasi koneksi:
   ```powershell
   adb devices
   ```
   Output harus:
   ```
   List of devices attached
   e41d1fee    device   ← ✅ HP terdeteksi
   ```

> Jika `unauthorized`: cabut-pasang kabel, cek popup di HP.

---

### Step SMS-3 — Siapkan Data & Config

**Edit `data/input.csv`:**
```csv
nomor,nama_peserta,nokapst,nohp,send_wa,send_sms
1,SUROTO,0002223480115,087771580543,TRUE,TRUE
```

**Edit `.env`:**
```ini
SEND_SMS=true
SEND_WA=false       ← set false untuk SMS-only run
SMS_DELAY_SECONDS=10
ADB_SEND_WAIT=3     ← naikkan ke 5-7 jika SMS tidak terkirim otomatis
```

> ⚠ **Penting:** Layar HP harus **menyala (tidak terkunci)** saat pengiriman SMS.

---

### Step SMS-4 — Validasi

```powershell
python src/main.py validate
```

Output yang diharapkan:
```
✓ Konfigurasi valid
✓ CSV valid: X peserta ditemukan
✓ ADB: HP terdeteksi — e41d1fee   ← HP harus muncul di sini
```

---

### Step SMS-5 — Dry Run (Test Tanpa Kirim)

```powershell
python src/main.py run --sms-only --dry-run
```

Ini akan menampilkan preview tanpa benar-benar membuka aplikasi SMS di HP.

---

### Step SMS-6 — Kirim SMS

```powershell
python src/main.py run --sms-only
```

Yang terjadi di HP:
1. Aplikasi SMS terbuka otomatis
2. Nomor tujuan terisi otomatis
3. Isi pesan terisi otomatis
4. Tombol Kirim ditekan otomatis
5. Lanjut ke peserta berikutnya

> **Layar HP harus menyala selama proses berlangsung!**

---

### Perintah SMS Lainnya

```powershell
# Preview pesan
python src/main.py preview

# Dry run (test tanpa kirim)
python src/main.py run --sms-only --dry-run

# Lanjut dari yang belum terkirim (resume)
python src/main.py run --sms-only

# Mulai ulang dari awal
python src/main.py run --sms-only --fresh

# Lihat laporan
python src/main.py report
```

---

## ─────────────────────────────────────────
## 🔄 BAGIAN 3 — WA + SMS BERSAMAAN
## ─────────────────────────────────────────

Karena WA pakai Docker dan SMS pakai Python, keduanya **tidak bisa dijalankan dalam satu perintah** secara bersamaan di setup ini.

**Cara yang disarankan — jalankan secara urut:**

```bash
# Step 1: Kirim WA dulu via Docker
docker-compose run --rm blast run --wa-only

# Step 2: Setelah WA selesai, kirim SMS via Python
.\venv\Scripts\Activate.ps1
python src/main.py run --sms-only
```

> Laporan CSV akan mencatat kedua channel secara terpisah di `data/reports/`.

---

## 📊 Memahami Status di Laporan

| Status | Arti |
|---|---|
| `SUCCESS` | ✅ Pesan berhasil terkirim |
| `FAILED` | ❌ Gagal kirim (error teknis, akan di-retry) |
| `INVALID_PHONE` | ⚠ Nomor HP tidak valid / format salah |
| `NOT_ON_WA` | ⚠ Nomor tidak terdaftar di WhatsApp |
| `NO_DEVICE` | ⚠ HP tidak terdeteksi ADB |
| `SKIPPED` | — Channel dinonaktifkan untuk baris ini |

---

## ❓ Troubleshooting

### WA: Browser tidak muncul
→ Pastikan `WA_HEADLESS=false` di `.env`

### WA: QR expired / harus scan ulang
```bash
rmdir /s /q wa_profile
docker-compose run --rm blast run --dry-run
```

### SMS: HP tidak terdeteksi
```powershell
adb kill-server
adb start-server
adb devices
```

### SMS: Pesan terbuka tapi tidak terkirim otomatis
→ Naikkan `ADB_SEND_WAIT=5` (atau 7) di `.env`

### SMS: Layar HP mati di tengah proses
→ Atur **"Jangan matikan layar"** di Opsi Pengembang HP, atau naikkan timeout layar HP ke maksimum
