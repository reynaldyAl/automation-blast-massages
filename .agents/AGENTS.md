# Automation Blast Messages - Panduan Utama untuk AI Agents

## 📌 Project Overview
Proyek ini adalah sistem otomatisasi pengiriman pesan blast (tagihan/informasi) BPJS Kesehatan Kantor Cabang Serang. Sistem mengirimkan pesan melalui dua jalur utama:
1. **WhatsApp Web** (diotomatisasi menggunakan browser `Playwright`)
2. **SMS** (diotomatisasi menggunakan perintah `Android Debug Bridge / ADB`)

Proyek ini menggunakan arsitektur CLI interaktif yang dibangun menggunakan framework `click` (untuk struktur argument/command) dan dipercantik secara visual di terminal menggunakan pustaka `rich`.

## 📁 Struktur Direktori & Arsitektur
Proyek ini memisahkan konfigurasi, antarmuka UI, pemroses data (parser), dan engine pengirim (sender) secara ketat.

### Direktori Utama
- `data/` : Tempat menyimpan file input (`input.csv`) dan laporan log (`reports/`).
- `templates/` : Folder untuk menyimpan format pesan teks (`bpjs_message.txt`).
  - `templates/messages/` : Folder output tempat sistem menyimpan hasil *Generate Pesan* (WA & SMS) yang bisa dibaca sebelum dikirim manual.
- `src/` : Seluruh *source code* utama aplikasi.
- `run.bat` : Entry point untuk pengguna Windows. Skrip ini berisi menu interaktif yang memanggil command di `src/main.py`.
- `.env` : Konfigurasi lokal sensitif dan nilai *default* (timeout, min/max delay).
- `wa_profile/` : Folder profil Chromium Playwright. **Penting:** Direktori ini menyimpan sesi login WhatsApp Web, sehingga user tidak perlu scan QR tiap kali aplikasi dijalankan.

### Modul-Modul Utama di `src/`
- **`main.py`** : Core entry point untuk Python. Mengatur semua fungsi eksekusi: `run` (blast sesungguhnya), `generate`, `cleanup`, `validate`, dsb.
- **`config.py`** : Mengambil env variables (dari `.env`) dan mendeklarasikan *path* atau konstanta agar terpusat. Termasuk mengatur delay minimum/maksimum untuk anti-ban WA & SMS.
- **`csv_handler.py`** : Membaca `input.csv` menggunakan `pandas`. Melakukan validasi kolom wajib (nama_peserta, nokapst, nohp) dan memasukkan semua *sisa kolom tambahan* ke dalam dictionary `extra_data` sebagai variabel template dinamis.
- **`phone_validator.py`** : Membersihkan dan menormalisasi nomor HP (mengubah `08x` menjadi format internasional `628x` atau `+628x`) agar valid digunakan dalam URL WhatsApp dan SMS ADB.
- **`template_engine.py`** : Memproses teks template dengan variabel dari CSV. Memiliki kemampuan menghapus sintaks Markdown (seperti `*teks tebal*` di WhatsApp) agar polos saat dikirim sebagai SMS.
- **`wa_sender.py`** : Kelas yang membungkus logika `playwright`. Berisi interaksi spesifik dengan HTML/DOM WhatsApp Web (mencari kotak chat, menempel teks, dan mendeteksi notifikasi "Nomor tidak terdaftar").
- **`sms_sender.py`** : Kelas interaksi berbasis *shell* (`adb shell`). Mengirim intent Android untuk membuka aplikasi SMS, menyuntikkan teks, dan menekan kordinat layar untuk tombol "Kirim".
- **`reporter.py`** : Modul logger yang membuat dua jenis file per sesi di `data/reports/`: sebuah CSV (`report_*.csv`) yang berisi rekap detail (sukses/gagal, alasan error), dan log teks (`blast_*.log`).
- **`dashboard.py`** : Bertanggung jawab menyajikan UI Terminal yang modern dan dinamis menggunakan `rich` (Progress bars, Live status panel, Tabel).

---

## 🔑 Key Features & Logic Rules

### 1. Placeholder Dinamis (Kolom Bebas di CSV)
Sistem template bersifat dinamis. AI Agents harus menyadari bahwa sistem *TIDAK* hanya mendukung field hardcoded.
- **Logika:** Di `csv_handler.py`, semua kolom CSV yang *bukan* merupakan bagian dari field bawaan `Peserta` akan ditampung di `extra_data: dict`.
- Saat `main.py` atau `wa_sender.py` memanggil `TemplateEngine.render()`, argumen `**peserta.extra_data` akan dilempar (*unpacked*).
- **Aturan AI:** Saat pengguna meminta agar pesan bisa memuat data spesifik baru (misal: "Kelas BPJS"), **jangan menambahkan variabel baru ke class `Peserta`** atau me-rewrite logika parser. Cukup instruksikan pengguna untuk membuat judul kolom "Kelas_BPJS" di CSV, dan menaruh kode `{Kelas_BPJS}` di file `bpjs_message.txt`.

### 2. Batching Generate & Custom Salam
Fungsi `generate` (`[11] Generate pesan blast WA + SMS`) memiliki alur logika pemisahan data (*batching*).
- Pengguna dapat membagi total baris CSV menjadi beberapa rentang (contoh: Data 1-50 untuk pagi hari dengan salam "Selamat Pagi", lalu Data 51-100 untuk siang hari dengan salam "Selamat Siang").
- Semua pesan WA dan SMS di-render dan direkap ke dalam *satu file output teks* yang sama, dengan penanda blok `===========================` agar mudah dibaca/di-*copy*.

### 3. Random Delay (Mekanisme Anti-Ban)
Mengirim pesan secara masif dalam tempo yang sangat konstan (misal tepat 5 detik) akan memicu sistem anti-spam WhatsApp dan menyebabkan akun terblokir (banned).
- **Logika:** Terdapat rentang jeda acak di `config.py` (seperti `WA_DELAY_MIN` & `WA_DELAY_MAX`). 
- Saat loop pengiriman berjalan di `main.py`, durasi jeda didapat dengan `random.uniform(MIN, MAX)`.
- **Aturan AI:** **Dilarang** menggunakan `time.sleep()` dengan angka konstan/statis (misal `time.sleep(5)`) untuk jeda pengiriman utama antar peserta. Selalu gunakan mekanisme random ini.

### 4. Sistem State Recovery (Resume Mode)
Aplikasi harus tangguh terhadap interupsi mendadak (seperti mati lampu atau proses ditutup paksa).
- **Logika:** Saat aplikasi berjalan, status pengiriman per baris CSV dicatat secara *real-time* ke file JSON tersembunyi (`.state.json`).
- Jika aplikasi ditutup dan dijalankan ulang, aplikasi akan mengecek `.state.json` dan otomatis melompati (skip) baris data yang sudah sukses terkirim. Mode `--fresh` dapat dipakai untuk mereset *state* ini.

### 5. Cleanup Otomatis
Perintah `cleanup` di `main.py` (`[13]` di `run.bat`) bertugas membersihkan memori lokal.
- Akan menghapus seluruh file `.txt` di `templates/messages/`.
- Akan menghapus seluruh log laporan (`.csv` dan `.json`) di `data/reports/`.
- Dilengkapi dengan konfirmasi Y/N. File-file vital sistem tidak akan terhapus.

---

## ⚠️ STRICT GUIDELINES FOR ALL AI AGENTS (Wajib Dipatuhi AI)

1. **JANGAN MERUSAK MENU CLI & `run.bat`**
   - Jika Anda (AI) menambahkan/memodifikasi sebuah command di `main.py` (`@cli.command()`), Anda **WAJIB** memperbarui antarmuka menu yang ada di file `run.bat`.
   - Karena `run.bat` merupakan script Windows Batch jadul yang mengandalkan statemen percabangan `goto`, pastikan penomoran menu sinkron. Jika menambah opsi `[14]`, tambahkan `if "%PILIHAN%"=="14" goto NAMA_LABEL`, dan implementasikan block `:NAMA_LABEL` yang memanggil perintah Python-nya.

2. **JANGAN MERUSAK STRUKTUR UI TERMINAL (`rich`)**
   - Proyek ini dirancang agar tampilan di CLI terlihat *premium*, estetik, dan informatif.
   - **DILARANG** menggunakan statemen `print()` bawaan Python secara langsung jika Anda merombak UI. Selalu impor dan gunakan instance `console.print()`, `Panel`, atau `Table` dari library `rich` agar sejalan dengan *codebase* lain.

3. **UTAMAKAN STABILITAS PLAYWRIGHT DIBANDING KECEPATAN**
   - Aplikasi web modern seperti WhatsApp sering mengalami perlambatan *render* DOM.
   - Saat mengubah interaksi di `wa_sender.py`, gunakan `page.wait_for_selector()` dengan benar. Berikan jeda toleransi dengan `time.sleep()` (sekitar 0.5 hingga 1 detik) sebelum dan sesudah *mengetik teks panjang* atau *menekan tombol send*. Pengiriman yang dipaksa instan akan menyebabkan Playwright gagal mendeteksi elemen input.

4. **KONSISTENSI TEMPLATE PYTHON FORMATTER**
   - Proyek ini me-render pesan `.txt` dengan fitur substitusi string dasar dan metode `str.format()` atau format mapping, serta sedikit ekstensi Jinja2. Pastikan Anda tidak membocorkan implementasi *reserved keyword* yang bisa bentrok dengan *built-in methods* Python.

5. **PERTAHANKAN SEPARATION OF CONCERNS (SoC)**
   - Jika Anda disuruh menambahkan "fitur statistik laporan", jangan menaruh kodenya di `wa_sender.py`. Taruh di `reporter.py` atau `dashboard.py`.
   - Modifikasi sistem harus bersifat modular sesuai peran file di dalam folder `src/`.
