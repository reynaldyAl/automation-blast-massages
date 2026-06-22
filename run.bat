@echo off
title BPJS Blast Message Automation

echo.
echo  ================================================
echo   BPJS BLAST MESSAGE AUTOMATION SYSTEM
echo   BPJS Kesehatan - Kantor Cabang Serang
echo  ================================================
echo.

:: === Navigasi ke direktori script ===
cd /d "%~dp0"

:: === Cek apakah venv ada ===
if not exist "venv\Scripts\activate.bat" (
    echo  [ERROR] Virtual environment tidak ditemukan!
    echo  Jalankan setup.bat terlebih dahulu.
    echo.
    pause
    exit /b 1
)

:: === Aktifkan virtual environment ===
call venv\Scripts\activate.bat

:MENU
echo.
echo  ------------------------------------------------
echo   Pilih mode pengiriman:
echo  ------------------------------------------------
echo   [1] Kirim semua pesan  (WA + SMS)
echo   [2] WhatsApp only
echo   [3] SMS only
echo   [4] Dry-run preview    (tidak ada yg terkirim)
echo   [5] Validasi CSV + Config
echo   [6] Preview template pesan
echo   [7] Lihat laporan terakhir
echo   [0] Keluar
echo  ------------------------------------------------
echo.
set /p PILIHAN=  Masukkan pilihan [0-7]: 

if "%PILIHAN%"=="1" goto RUN_ALL
if "%PILIHAN%"=="2" goto RUN_WA
if "%PILIHAN%"=="3" goto RUN_SMS
if "%PILIHAN%"=="4" goto DRY_RUN
if "%PILIHAN%"=="5" goto VALIDATE
if "%PILIHAN%"=="6" goto PREVIEW
if "%PILIHAN%"=="7" goto REPORT
if "%PILIHAN%"=="0" goto EXIT

echo.
echo  [!] Pilihan tidak valid. Masukkan angka 0 sampai 7.
goto MENU

:RUN_ALL
echo.
echo  [->] Mengirim semua pesan (WA + SMS)...
echo.
python src\main.py run
goto DONE

:RUN_WA
echo.
echo  [->] Mengirim via WhatsApp saja...
echo.
python src\main.py run --wa-only
goto DONE

:RUN_SMS
echo.
echo  [->] Mengirim via SMS saja...
echo.
python src\main.py run --sms-only
goto DONE

:DRY_RUN
echo.
echo  [->] Mode DRY-RUN - preview visual tanpa kirim...
echo.
python src\main.py run --dry-run --wa-only
goto DONE

:VALIDATE
echo.
python src\main.py validate
goto DONE

:PREVIEW
echo.
python src\main.py preview
goto DONE

:REPORT
echo.
python src\main.py report
goto DONE

:DONE
:: Beri jeda agar output Python selesai ditulis ke terminal sebelum prompt muncul
timeout /t 1 /nobreak > nul

:ASK_MENU
echo.
echo  ------------------------------------------------
set /p LAGI=  Kembali ke menu? (y=ya, n/0=keluar): 

if /i "%LAGI%"=="y" (
    cls
    echo.
    echo  ================================================
    echo   BPJS BLAST MESSAGE AUTOMATION SYSTEM
    echo   BPJS Kesehatan - Kantor Cabang Serang
    echo  ================================================
    goto MENU
)
if /i "%LAGI%"=="n" goto EXIT
if    "%LAGI%"=="0" goto EXIT

:: Input tidak dikenal - minta lagi (forgive)
echo  [!] Ketik  y  untuk kembali ke menu, atau  n  /  0  untuk keluar.
goto ASK_MENU
:EXIT
echo.
echo  Sampai jumpa!
echo.
pause
