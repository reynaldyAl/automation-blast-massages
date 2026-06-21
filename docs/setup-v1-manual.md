# 📋 Panduan Setup Manual — BPJS Blast Message Automation

Jika Anda tidak bisa (atau tidak ingin) menggunakan `setup.bat`, Anda bisa melakukan setup secara manual. Berikut adalah langkah-langkah *pure manual* untuk menjalankan sistem ini pertama kali:

### Tahap 1: Setup Lingkungan Python (Buka PowerShell)

**1. Buka PowerShell di dalam folder project Anda, lalu buat rumah khusus (Virtual Environment) untuk aplikasinya:**
```powershell
python -m venv venv
```

**2. Aktifkan rumah khusus tersebut:**
```powershell
.\venv\Scripts\Activate.ps1
```
*(Ciri berhasil: Akan muncul tulisan `(venv)` warna hijau di sebelah kiri teks terminal Anda).*

**3. Install semua *library* pendukung (Robotnya):**
```powershell
pip install -r requirements.txt
```

**4. Install Otak WhatsApp Web (Playwright & Chromium):**
```powershell
pip install playwright
playwright install chromium
```

---

### Tahap 2: Setup Komunikasi HP (ADB)
Agar komputer Anda bisa "ngobrol" dan "menyuruh" HP Anda mengetik SMS, komputer Anda butuh *driver* bahasa HP bernama ADB (Android Debug Bridge).

**1. Cara Paling Gampang (Gunakan PowerShell mode Administrator):**
```powershell
winget install Google.PlatformTools --accept-source-agreements --accept-package-agreements
```
*(Setelah instalasi selesai, **tutup lalu buka ulang** PowerShell Anda agar komputer mereset ingatannya).*

---

### Tahap 3: Pemakaian Pertama Kali (First Run)

Semua instalasi sudah selesai! Anda sekarang masuk ke tahap pemakaian sehari-hari:

**1. Login WhatsApp Web (Hanya perlu sekali seumur hidup):**
Pastikan Anda sudah mengaktifkan venv (`.\venv\Scripts\Activate.ps1`), lalu jalankan simulasi:
```powershell
python src/main.py run --wa-only --dry-run
```
*(Browser akan terbuka, silakan scan QR Code dengan HP Anda. Kalau sudah terscan, browser otomatis menyimpan datanya).*

**2. Hubungkan HP untuk SMS:**
Colokkan HP Anda pakai kabel USB, lalu pastikan **USB Debugging** di Pengaturan HP Anda sudah menyala. Tekan **"Izinkan"** jika muncul konfirmasi di layar HP Anda.

Untuk mengecek apakah HP sudah terhubung:
```powershell
adb devices
```
*(Kalau muncul tulisan `device`, berarti sukses!)*

**3. Mulai Blast!**
Isi file `data/input.csv`, lalu jalankan sesuai urutan terbaik:
```powershell
# 1. Kirim WA dulu (yang gagal akan di-skip)
python src/main.py run --wa-only

# 2. Kirim SMS (otomatis menyasar orang yang tadinya gagal di WA)
python src/main.py run --sms-only
```

> **Tips:** Selesai! Langkah instalasi (Tahap 1 & 2) hanya dilakukan **sekali seumur hidup** di komputer tersebut. Besok-besoknya Anda cukup mengulang langkah Tahap 3 saja!
