# 🏥 BPJS Blast Message Automation

Sistem otomasi pengiriman pesan blast untuk **BPJS Kesehatan Kantor Cabang Serang**.
Mendukung pengiriman multi-channel: **WhatsApp Web** dan **SMS via HP Android (ADB/USB)**.

---

## 🚀 Cara Setup di Device / Komputer Baru

Jika Anda baru saja melakukan clone dari GitHub ke device baru, ikuti **1 langkah super mudah** ini:

Cukup klik ganda (jalankan) file **`setup.bat`** di folder project.
Atau buka PowerShell dan ketik:
```cmd
.\setup.bat
```
*(Script ajaib ini akan menginstall Python virtual environment, mengunduh Playwright + Chromium untuk WA Web, serta menyetel **Android Debug Bridge (ADB)** untuk SMS secara otomatis 100% siap pakai).*

---

## 📱 Cara Penggunaan (Daily Usage)

Setiap hari saat Anda ingin mengirim pesan, cukup:
1. Ganti isi file `data/input.csv` dengan data terbaru.
2. Edit pesan di `templates/bpjs_message.txt`.
3. Buka PowerShell di folder project, lalu masuk ke Virtual Environment:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

**Sangat disarankan** untuk menjalankan WhatsApp terlebih dahulu sampai selesai, baru kemudian menjalankan SMS untuk mereka yang gagal/tidak punya WA.

### Tahap 1: Mengirim WhatsApp
```powershell
# Jalankan simulasi (Dry Run) & Scan QR Code WA Web
python src/main.py run --wa-only --dry-run

# Jika QR sudah terscan dan siap, jalankan pengiriman sungguhan:
python src/main.py run --wa-only
```
*(Catatan: Sistem akan cerdas mencatat siapa saja yang "NOT ON WA" (tidak terdaftar di WhatsApp) di dalam log/laporan).*

### Tahap 2: Mengirim SMS (sebagai Backup)
Pastikan HP Android menyala, layar tidak terkunci, kabel USB terhubung, dan **USB Debugging** diizinkan di layar HP Anda.
*(Fitur canggih: Sistem otomatis memindai layar HP untuk mencari tombol "Kirim", terlepas dari merek HP Anda!)*

```powershell
# Jalankan simulasi (Dry Run) untuk mengetes koneksi HP:
python src/main.py run --sms-only --dry-run

# Mulai Blast SMS! (Otomatis hanya mengirim ke yang belum sukses WA)
python src/main.py run --sms-only
```

> **Tips:** Anda bisa melihat rekapan siapa saja yang berhasil dikirim di folder `data/reports/`.
> Jika ada masalah dan Anda ingin mengulang dari nomor 1, tambahkan parameter `--fresh`.

---

## ✨ Fitur Utama

| Fitur | Keterangan |
|---|---|
| 📱 **WA Web Automation** | Bekerja senatural manusia (Bebas Blokir) |
| 💬 **SMS Auto-Detect** | Kirim SMS via USB, *AI UI Scanning* otomatis cari tombol Send |
| ⚡ **Setup Instan** | `setup.bat` langsung siap pakai di Windows |
| 📄 **Template Jinja2** | Edit template pesan (termasuk baris baru) dengan mudah |
| ✅ **Validasi Nomor HP** | Normalisasi 08xx→628xx, deteksi nomor tidak valid |
| 🔁 **Retry Otomatis** | Ulangi pesan yang gagal secara otomatis |
| ↺ **Resume Mode** | Lanjut dari baris terakhir jika proses terhenti |
| 🧪 **Dry Run Mode** | Preview pesan tanpa benar-benar mengirim |
| 📊 **Dashboard Terminal** | Progress bar dan ringkasan berwarna (Rich) |
| 📋 **Laporan CSV** | Hasil kirim real-time, tersimpan di `data/reports/` |

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
```

## 📋 Format CSV

```csv
nomor,nama_peserta,nokapst,nohp,send_wa,send_sms
1,SUROTO,0002223480115,087771580543,TRUE,TRUE
2,SITI AMINAH,0001082332293,081234567890,TRUE,FALSE
```

---

## 💬 Daftar Perintah CLI

Pastikan selalu mengaktifkan environment (`.\venv\Scripts\Activate.ps1`) sebelum menjalankan ini:

| Aksi | Perintah Python |
|---|---|
| Kirim semua | `python src/main.py run` |
| Dry run | `python src/main.py run --dry-run` |
| Hanya WA | `python src/main.py run --wa-only` |
| Hanya SMS | `python src/main.py run --sms-only` |
| Reset & ulang | `python src/main.py run --fresh` |
| Validasi data | `python src/main.py validate` |
| Preview pesan | `python src/main.py preview` |

---

*Dibuat untuk BPJS Kesehatan Kantor Cabang Serang*
