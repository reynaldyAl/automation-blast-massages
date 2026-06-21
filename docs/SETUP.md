# 📋 Panduan Setup — BPJS Blast Message Automation

Sistem ini didesain agar sangat mudah diinstal dan dijalankan murni menggunakan OS Windows Anda secara lokal (tanpa Docker/VM).

---

## 🚀 Instalasi Super Cepat (Direkomendasikan)

Jika Anda menggunakan Windows, seluruh proses instalasi bisa dilakukan dengan **1 kali klik**:

1. Pastikan Anda sudah menginstall [Python 3.10+](https://www.python.org/downloads/) dan **mencentang "Add Python to PATH"** saat instalasi.
2. Buka folder project ini.
3. Klik ganda (jalankan) file **`setup.bat`**.

Script `setup.bat` akan secara otomatis:
- Membuat Virtual Environment Python (`venv`)
- Mendownload dan menginstall semua *library* (Jinja2, Pandas, dll)
- Mendownload dan menginstall Playwright beserta browser Chromium (untuk WhatsApp)
- Mendownload dan mengkonfigurasi Android Debug Bridge / ADB (untuk SMS)

---

## 🛠 Instalasi Manual (Jika setup.bat gagal)

Jika Anda ingin melakukan instalasi tahap demi tahap:

### 1. Buat & Aktifkan Virtual Environment
Buka PowerShell/Terminal di folder project:
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2. Install Dependencies (WA & SMS)
```powershell
pip install -r requirements.txt
pip install playwright
playwright install chromium
```

### 3. Install ADB (Khusus SMS)
Buka PowerShell baru **sebagai Administrator**:
```powershell
winget install Google.PlatformTools --accept-source-agreements --accept-package-agreements
```
*(Lalu tutup dan buka ulang PowerShell Anda agar sistem mengenali perintah `adb`)*

---

## 📱 Tahap 1: Setup WhatsApp Web (Sekali Saja)

1. Aktifkan Virtual Environment:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```
2. Jalankan perintah *dry run* pertama kali:
   ```powershell
   python src/main.py run --wa-only --dry-run
   ```
3. Sebuah browser Chrome akan terbuka menampilkan QR Code WhatsApp Web.
4. Di HP Anda: Buka **WhatsApp → Titik Tiga (Opsi) → Perangkat Tertaut → Tautkan Perangkat**.
5. Scan QR code di layar monitor Anda.
6. Tunggu sampai daftar chat Anda muncul. Selesai! Sesi Anda telah tersimpan dengan aman di folder `wa_profile/` dan Anda **tidak perlu scan QR lagi** ke depannya.

---

## 💬 Tahap 2: Setup HP Android (Untuk Backup SMS)

Sistem akan menggunakan kabel USB untuk mengirimkan perintah pengetikan langsung ke HP Android Anda, persis seperti robot yang mengetik di HP.

1. Buka HP Android Anda.
2. Masuk ke **Pengaturan → Tentang Ponsel** → ketuk **Nomor Versi (Build Number)** sebanyak **7 kali** (sampai muncul notif *"Mode Pengembang aktif"*).
3. Masuk ke **Pengaturan → Opsi Pengembang (Developer Options)**.
4. Aktifkan fitur **USB Debugging** ✓.
5. Sambungkan HP ke komputer menggunakan kabel USB data yang bagus.
6. **SANGAT PENTING:** Lihat layar HP Anda! Jika muncul *popup* *"Izinkan debugging USB?"*, centang opsi *"Selalu izinkan dari komputer ini"* lalu ketuk **Izinkan (OK)**.

Untuk memastikan komputer Anda sudah terkoneksi ke HP, jalankan:
```powershell
adb devices
```
Output yang benar:
```
List of devices attached
R5CX12345678    device    ← ✅ Berhasil (bukan "unauthorized")
```

---

## 📁 Struktur Folder Penting

```
automation-blast-massages/
├── data/
│   ├── input.csv           ← ✏️ GANTI INI setiap kali mau blast baru
│   └── reports/            ← Laporan hasil kirim otomatis (Excel/CSV)
├── templates/
│   └── bpjs_message.txt    ← ✏️ Template isi pesan (bisa diganti)
├── wa_profile/             ← Sesi WA Web tersimpan (jangan dihapus)
├── .env                    ← Konfigurasi setting (opsional)
└── setup.bat               ← Script Instalasi
```

---

## 🔧 Troubleshooting (Penyelesaian Masalah)

### 🟡 WA: Browser selalu minta scan QR padahal sudah scan?
```powershell
# Hapus folder wa_profile secara manual (hapus seluruh isinya)
rmdir /s /q wa_profile

# Jalankan ulang dan scan QR yang baru
python src/main.py run --wa-only --dry-run
```

### 🟡 SMS: "Tidak ada HP yang terdeteksi"
- Cek kabel USB (jangan gunakan kabel yang hanya untuk *charging*).
- Pastikan popup *USB Debugging* di HP sudah ditekan "Izinkan".
- Jika ADB macet, restart layanan ADB dengan perintah:
  ```powershell
  adb kill-server
  adb start-server
  ```

### 🟡 WA/SMS: Script berjalan tapi "Timeout / Error"
- Untuk WhatsApp: Pastikan internet komputer Anda stabil karena browser *headless* membutuhkan waktu *loading*.
- Untuk SMS: Pastikan layar HP dalam keadaan **menyala (tidak terkunci / password)** selama proses pengiriman berlangsung! Robot kita tidak bisa mengetik jika HP terkunci.

---
*Dibuat untuk BPJS Kesehatan Kantor Cabang Serang*
