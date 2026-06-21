@echo off
:: ============================================================
:: setup.bat — Setup otomatis BPJS Blast di komputer baru
:: Jalankan: klik kanan → "Run as Administrator"
:: ============================================================
echo.
echo  ============================================
echo   BPJS Blast Message — Setup Otomatis
echo  ============================================
echo.

:: 1. Cek Python
echo [1/5] Mengecek Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  Python tidak ditemukan. Install Python dulu dari:
    echo  https://www.python.org/downloads/
    echo  Pastikan centang "Add Python to PATH" saat install!
    pause
    exit /b 1
)
python --version
echo  OK: Python terdeteksi.
echo.

:: 2. Install ADB via winget
echo [2/5] Menginstall ADB (Android Platform Tools)...
winget install Google.PlatformTools --accept-source-agreements --accept-package-agreements
echo  OK: ADB terinstall.
echo.

:: 3. Buat virtual environment
echo [3/5] Membuat virtual environment...
if exist venv (
    echo  venv sudah ada, skip.
) else (
    python -m venv venv
    echo  OK: venv dibuat.
)
echo.

:: 4. Install dependencies WA dan SMS
echo [4/5] Menginstall Python dependencies...
call venv\Scripts\activate.bat

:: Install semua library dasar
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Gagal menginstall requirements.txt!
    pause
    exit /b %errorlevel%
)

:: Install Playwright dan Chromium untuk WA
echo.
echo Menginstall Playwright untuk WhatsApp Web...
pip install playwright
playwright install chromium
if %errorlevel% neq 0 (
    echo [ERROR] Gagal menginstall browser Chromium!
    pause
    exit /b %errorlevel%
)

echo  OK: Dependencies terinstall.
echo.

:: 5. Cek ADB
echo [5/5] Mengecek koneksi ADB...
echo  Sambungkan HP Android via USB dan izinkan USB Debugging jika ada popup.
echo  (Tekan Enter setelah HP terhubung)
pause
adb devices
echo.

echo  ============================================
echo   Setup selesai!
echo.
echo   Cara Menjalankan:
echo     1. Buka PowerShell atau Command Prompt
echo     2. Aktifkan venv: .\venv\Scripts\Activate.ps1
echo     3. Kirim WA: python src\main.py run --wa-only
echo     4. Kirim SMS: python src\main.py run --sms-only
echo  ============================================
echo.
pause
