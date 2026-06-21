# 🎉 Blast Message — Edisi Basic (Umum)

Ini adalah versi **Dinamis dan Fleksibel** dari sistem *Blast Message Automation*.
Berbeda dengan versi BPJS yang mewajibkan kolom Nomor Kartu, versi `src_basic` ini dirancang agar Anda bisa menggunakannya untuk kebutuhan apapun:
- Mengirim undangan pernikahan/acara
- Menyebarkan pengumuman kantor
- Mengirim tagihan / *invoice* massal
- Mengirim pesan promosi

## ✨ Fitur Utama: Kolom Tak Terbatas (Custom Columns)

Sistem di dalam folder ini memiliki kemampuan untuk membaca **kolom apapun** yang Anda tulis di file Excel/CSV, dan menyalurkannya langsung ke dalam *Template Pesan*!

### 📝 Contoh Skenario Penggunaan

Katakanlah Anda ingin mengundang rapat.

**1. Buat Header CSV Sesuka Hati (`data/input.csv`)**
Anda bebas membuat kolom tambahan di samping kolom wajib.
*(Kolom wajib hanyalah `nama_peserta` dan `nohp`)*

```csv
nama_peserta,nohp,acara,tanggal,waktu,meja_vip
BUDI SANTOSO,0812345678,Rapat Paripurna,12 Desember 2026,09:00 WIB,VIP-01
SITI AMINAH,0898765432,Makan Siang Bersama,13 Desember 2026,12:00 WIB,REG-12
```

**2. Panggil di Template (`templates/basic_message.txt`)**
Buka file teks tersebut, lalu ketik pesan Anda dan panggil nama kolom CSV tadi dengan **kurung kurawal ganda**.

```text
Halo kak {{ nama_peserta }},

Kami mengundang kakak untuk hadir di acara {{ acara }} yang akan diselenggarakan pada:
Tanggal: {{ tanggal }}
Waktu: {{ waktu }}
Lokasi Meja: {{ meja_vip }}

Kehadiran kakak sangat kami nantikan. Terima kasih!
```

Script akan otomatis mengganti kurung kurawal tersebut dengan data dari masing-masing baris CSV! Ajaib bukan?

---

## 🚀 Cara Menjalankan

Buka terminal/PowerShell dari folder utama (*root*), pastikan *Virtual Environment* sudah aktif (`.\venv\Scripts\Activate.ps1`).

**Melihat Hasil Template (Preview):**
*Sangat disarankan untuk mengecek tampilan pesan sebelum mengirim!*
```powershell
python src_basic/main.py preview --nama "BUDI SANTOSO"
```

**Kirim Lewat WhatsApp:**
```powershell
python src_basic/main.py run --wa-only
```

**Kirim Lewat SMS (Biasanya untuk mereka yang WA-nya gagal):**
```powershell
python src_basic/main.py run --sms-only
```

**Kirim Ulang dari Awal (Reset Riwayat):**
```powershell
python src_basic/main.py run --wa-only --fresh
```

## 📂 Kenapa Ada Folder Ini?
Folder `src_basic/` adalah sistem tersendiri (memiliki `main.py` sendiri) agar kode BPJS Anda di dalam folder `src/` tidak tercampur. Dengan begini, *repository* Anda dapat melayani dua tujuan yang benar-benar berbeda tanpa saling merusak kode satu sama lain!
