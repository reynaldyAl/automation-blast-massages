# 🏥 BPJS Blast Message Automation

Sistem otomasi pengiriman pesan blast untuk **BPJS Kesehatan Kantor Cabang Serang**.  
Mendukung pengiriman multi-channel: **WhatsApp Web** dan **SMS via HP Android (ADB/USB)**.

---

##  Cara Setup (Pertama Kali / Device Baru)

Lakukan langkah ini **sekali saja** saat pertama kali menggunakan di komputer baru.

### Cara A: Via File Explorer (Tanpa Coding)

1. Buka folder project di **File Explorer** (Windows Explorer)
2. **Klik kanan** file `setup.bat` → pilih **"Run as administrator"**

> ⚠️ Klik kanan lalu "Run as administrator" — BUKAN double-click biasa — karena setup membutuhkan izin instalasi.

### Cara B: Via Terminal di IDE (VS Code, dll)

Buka terminal di IDE kamu (tekan **Ctrl + `**), lalu ketik:

```cmd
.\setup.bat
```

### Apa yang Dilakukan `setup.bat` Secara Otomatis?

| Langkah | Keterangan |
|---|---|
| ✅ Cek Python | Memastikan Python terdeteksi di PATH |
| ✅ Install ADB | Menginstall Android Platform Tools via `winget` |
| ✅ Buat Virtual Environment | Membuat folder `venv/` agar library terisolasi |
| ✅ Install Dependencies | `pip install -r requirements.txt` |
| ✅ Install Playwright + Chromium | Browser otomatis untuk WhatsApp Web |
| ✅ Cek Koneksi HP Android | Memvalidasi ADB device untuk SMS |

---

## 📱 Cara Penggunaan Harian (Daily Usage)

Setiap kali ingin mengirim pesan, lakukan ini:

1. **Ganti data** di file `data/input.csv` dengan data peserta terbaru
2. **Cek template** pesan di `templates/bpjs_message.txt`
3. **Jalankan** menggunakan salah satu cara di bawah

---

## ▶️ Cara Menjalankan `run.bat`

### Cara A: Via File Explorer (Untuk Staf Non-Teknis)

1. Buka folder project di **File Explorer**
2. **Double-click** file `run.bat`
3. Jendela Command Prompt akan terbuka dan menampilkan menu:

```
================================================
 BPJS BLAST MESSAGE AUTOMATION SYSTEM
 BPJS Kesehatan - Kantor Cabang Serang
================================================

------------------------------------------------
 Pilih mode pengiriman:
------------------------------------------------
 [1] Kirim semua pesan  (WA + SMS)
 [2] WhatsApp only
 [3] SMS only
 [4] Dry-run preview    (tidak ada yg terkirim)
 [5] Validasi CSV + Config
 [6] Preview template pesan
 [7] Lihat laporan terakhir
 [0] Keluar
------------------------------------------------

  Masukkan pilihan [0-7]:
```

4. Ketik angka pilihan lalu tekan **Enter**

> 💡 Setelah selesai, program akan tanya `Kembali ke menu? [y/n]:` — ketik `y` untuk pilih mode lain atau `n` untuk keluar.

---

### Cara B: Via Terminal di IDE (VS Code, dll)

Buka terminal di IDE kamu (**Ctrl + `**), pastikan sudah di folder project, lalu:

```cmd
.\run.bat
```

Atau jalankan langsung perintah Python-nya tanpa menu (lebih cepat untuk developer):

```powershell
# Aktifkan virtual environment dulu
venv\Scripts\python.exe src\main.py run --wa-only
```

---

## 📋 Alur Pengiriman yang Disarankan

### Tahap 1 — Preview (Dry Run)

Selalu jalankan dry-run terlebih dahulu untuk memastikan data dan pesan sudah benar.

**Via `run.bat`:** Pilih menu **[4]**

**Via terminal:**
```powershell
venv\Scripts\python.exe src\main.py run --dry-run --wa-only
```

Saat dry-run berjalan:
- Browser WhatsApp Web akan terbuka otomatis
- Sistem **membuka chat** tiap peserta satu per satu
- **Mengetik pesan** di kotak input (terlihat di browser)
- **Menunggu ±2.5 detik** agar kamu bisa melihat isi pesan
- **Menghapus** teks tanpa menekan tombol Send
- Lanjut ke peserta berikutnya

> ✅ Tidak ada pesan yang terkirim. Aman untuk dicoba kapan saja.

---

### Tahap 2 — Kirim WhatsApp

Jika dry-run sudah oke, kirim via WhatsApp.

**Via `run.bat`:** Pilih menu **[2]**

**Via terminal:**
```powershell
venv\Scripts\python.exe src\main.py run --wa-only
```

Catatan:
- Scan QR Code sekali saja (sesi tersimpan otomatis di folder `wa_profile/`)
- Login berikutnya langsung masuk tanpa QR
- Nomor yang tidak terdaftar di WA otomatis dicatat di laporan

---

### Tahap 3 — Kirim SMS (Backup)

Untuk peserta yang gagal WA atau tidak punya WhatsApp.

**Syarat:** HP Android terhubung via USB, USB Debugging aktif, layar tidak terkunci.

**Via `run.bat`:** Pilih menu **[3]**

**Via terminal:**
```powershell
venv\Scripts\python.exe src\main.py run --sms-only
```

---

### Tahap 4 — Kirim Semua Sekaligus (WA + SMS)

**Via `run.bat`:** Pilih menu **[1]**

**Via terminal:**
```powershell
venv\Scripts\python.exe src\main.py run
```

---

## 💬 Daftar Lengkap Perintah CLI

| Menu | Perintah Python | Keterangan |
|---|---|---|
| [1] | `python src/main.py run` | Kirim WA + SMS sekaligus |
| [2] | `python src/main.py run --wa-only` | Hanya WhatsApp |
| [3] | `python src/main.py run --sms-only` | Hanya SMS |
| [4] | `python src/main.py run --dry-run` | Preview visual, tidak kirim |
| [5] | `python src/main.py validate` | Validasi CSV & config |
| [6] | `python src/main.py preview` | Preview template pesan |
| [7] | `python src/main.py report` | Lihat laporan terakhir |
| — | `python src/main.py run --fresh` | Reset & mulai dari awal |

> 💡 Saat menggunakan terminal di IDE, ganti `python` dengan `venv\Scripts\python.exe` agar menggunakan versi yang benar.

---

## ✨ Fitur Utama

| Fitur | Keterangan |
|---|---|
|  **WA Web Automation** | Bekerja senatural manusia, minim risiko banned |
|  **SMS Auto-Detect** | Kirim SMS via USB, otomatis cari tombol Send di HP |
|  **Visual Dry Run** | Buka chat, ketik pesan di browser — tidak kirim |
|  **Setup Instan** | `setup.bat` sekali klik, langsung siap pakai |
|  **Template Jinja2** | Edit pesan dengan variabel `{{ nama_peserta }}` dll |
|  **Validasi Nomor HP** | Normalisasi `08xx` → `628xx`, deteksi nomor invalid |
|  **Retry Otomatis** | Ulangi pengiriman yang gagal secara otomatis |
|  **Resume Mode** | Lanjut dari baris terakhir jika proses terhenti |
|  **Dashboard Terminal** | Progress bar dan ringkasan berwarna (Rich) |
|  **Laporan CSV + Log** | Hasil kirim real-time + kolom `failure_reason` |

---

## 📁 Struktur Project

```
automation-blast-massages/
├── data/
│   ├── input.csv              ← ✏️ GANTI INI setiap run
│   └── reports/               ← Laporan CSV & log otomatis tersimpan di sini
├── templates/
│   ├── bpjs_message.txt       ← ✏️ Edit template pesan utama di sini
│   └── basic_message.txt      ← Template alternatif
├── src/
│   ├── main.py                ← Entry point CLI
│   ├── wa_sender.py           ← Pengiriman WA via Playwright
│   ├── sms_sender.py          ← Pengiriman SMS via ADB
│   ├── csv_handler.py         ← Baca & validasi data CSV
│   ├── phone_validator.py     ← Normalisasi nomor HP Indonesia
│   ├── template_engine.py     ← Render pesan Jinja2
│   ├── reporter.py            ← Laporan CSV & log
│   ├── dashboard.py           ← Terminal UI (Rich)
│   ├── scheduler.py           ← Penjadwalan otomatis (opsional)
│   └── config.py              ← Konfigurasi dari .env
├── wa_profile/                ← Sesi login WA tersimpan di sini (jangan dihapus)
├── setup.bat                  ← Setup otomatis (jalankan sekali)
├── run.bat                    ← Menu pengiriman harian
├── .env                       ← Konfigurasi lokal (tidak di-commit ke Git)
└── requirements.txt           ← Daftar library Python
```

---

## 📋 Format CSV Input

```csv
nomor,nama_peserta,nokapst,nohp,send_wa,send_sms
1,SUROTO,0002223480115,087771580543,TRUE,TRUE
2,SITI AMINAH,0001082332293,081234567890,TRUE,FALSE
3,BUDI SANTOSO,0003345678901,082198765432,FALSE,TRUE
```

| Kolom | Wajib | Keterangan |
|---|---|---|
| `nomor` | Opsional | Nomor urut baris |
| `nama_peserta` | ✅ | Nama peserta (akan dikapitalkan otomatis) |
| `nokapst` | ✅ | Nomor kartu JKN-KIS |
| `nohp` | ✅ | Nomor HP (format bebas: 08xx / 628xx / +628xx) |
| `send_wa` | Opsional | `TRUE`/`FALSE` — kirim WA? (default: TRUE) |
| `send_sms` | Opsional | `TRUE`/`FALSE` — kirim SMS? (default: TRUE) |

---

## 📊 Laporan Hasil Pengiriman

Setiap run menghasilkan 2 file di folder `data/reports/`:

- **`report_YYYYMMDD_HHMMSS.csv`** — Rekap hasil per peserta, termasuk kolom `failure_reason` yang menjelaskan mengapa pengiriman gagal
- **`blast_YYYYMMDD_HHMMSS.log`** — Log detail seluruh proses

Contoh kolom `failure_reason` di CSV:
```
[WA] Nomor tidak terdaftar di WhatsApp
[WA] Gagal kirim: Playwright timeout | [SMS] Perangkat Android tidak terdeteksi
[WA] Nomor tidak valid: format salah
```

---

## ❓ Troubleshooting

| Masalah | Solusi |
|---|---|
| `run.bat` tidak bereaksi saat double-click | Klik kanan → **Open** atau jalankan via terminal IDE |
| Error `venv tidak ditemukan` | Jalankan `setup.bat` terlebih dahulu |
| QR Code tidak muncul | Jalankan dry-run dulu: menu [4], scan QR di browser |
| Pesan WA tidak terkirim (timeout) | Naikkan `WA_TIMEOUT_SECONDS` di file `.env` |
| HP tidak terdeteksi ADB | Cek USB Debugging aktif, cabut-pasang kabel USB |
| Pesan gagal semua | Cek koneksi internet, pastikan WA Web bisa dibuka manual |

---

*Dibuat untuk seseorang di BPJS Kesehatan Kantor Cabang Serang*
*with love, R*