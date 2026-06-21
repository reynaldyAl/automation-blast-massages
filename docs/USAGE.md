# 📖 Panduan Penggunaan — BPJS Blast Message Automation

Sistem ini memiliki DUA versi yang bisa Anda gunakan:
1. **Versi BPJS (Folder `src`)** — Khusus untuk pesan yang wajib ada Nomor Kartu (`nokapst`).
2. **Versi Basic / Umum (Folder `src_basic`)** — Untuk undangan rapat, pengumuman, dll yang kolomnya bisa di-custom sebebas-bebasnya.

---

## ─────────────────────────────────────────
## 💼 VERSi 1 — BPJS KESEHATAN (`src`)
## ─────────────────────────────────────────

Digunakan untuk mem-blast peserta JKN. Wajib memiliki kolom `nokapst` di CSV.

### 1. Siapkan Data CSV (`data/input.csv`)
Pastikan kolom wajib ini ada: `nomor,nama_peserta,nokapst,nohp`
*Optional:* `send_wa,send_sms`

### 2. Siapkan Template Pesan (`templates/bpjs_message.txt`)
Gunakan tag `{{ nama_peserta }}` dan `{{ nokapst }}` di dalam file teks tersebut.

### 3. Jalankan Pengiriman
Buka PowerShell, aktifkan `.\venv\Scripts\Activate.ps1`, lalu jalankan:

```powershell
# Jalankan simulasi (Cek QR WA)
python src/main.py run --wa-only --dry-run

# Kirim via WhatsApp (Yang gagal akan di-skip)
python src/main.py run --wa-only

# Kirim via SMS (Untuk mem-backup yang WA-nya gagal)
python src/main.py run --sms-only
```

---

## ─────────────────────────────────────────
## 🎉 VERSi 2 — BASIC / UMUM (`src_basic`)
## ─────────────────────────────────────────

Sangat cocok untuk **Undangan, Pengumuman Kantor, Promosi, dll.**
Anda BEBAS menambahkan kolom apapun di Excel/CSV, dan memanggilnya di template!

### 1. Siapkan Data CSV (`data/input.csv`)
Kolom wajib HANYA 2: `nama_peserta,nohp`. 
Sisa kolomnya BEBAS (misal: acara, tanggal, waktu, meja, dsb).

**Contoh isi `input.csv`:**
```csv
nama_peserta,nohp,acara,tanggal,waktu
BUDI SANTOSO,0812345678,Rapat Paripurna,12 Desember 2026,09:00 WIB
SITI AMINAH,0898765432,Makan Siang Bersama,13 Desember 2026,12:00 WIB
```

### 2. Siapkan Template Pesan (`templates/basic_message.txt`)
Buat template Anda sebebas mungkin dan panggil kolom CSV menggunakan kurung kurawal ganda `{{ nama_kolom }}`.

**Contoh isi `templates/basic_message.txt`:**
```text
Halo kak {{ nama_peserta }},

Kami mengundang kakak untuk hadir di acara {{ acara }} yang akan diselenggarakan pada:
Tanggal: {{ tanggal }}
Waktu: {{ waktu }}

Kehadiran kakak sangat kami nantikan. Terima kasih!
```

### 3. Jalankan Pengiriman
Sama seperti versi BPJS, tapi ganti kata `src` menjadi `src_basic`!

```powershell
# Cek apakah template sudah benar tampilannya:
python src_basic/main.py preview --nama "BUDI SANTOSO"

# Kirim via WhatsApp
python src_basic/main.py run --wa-only

# Kirim via SMS Backup
python src_basic/main.py run --sms-only

# Paksa kirim ulang dari awal (mengabaikan riwayat yang sudah sukses)
python src_basic/main.py run --wa-only --fresh
```

---

## 💡 Perintah Bermanfaat Lainnya (Bisa untuk `src` atau `src_basic`)

```powershell
# Validasi apakah CSV dan konfigurasi sudah benar sebelum mulai
python src/main.py validate

# Lihat laporan pengiriman terakhir dalam bentuk tabel yang rapi
python src/main.py report
```
