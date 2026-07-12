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
echo   [4] Dry-run preview WA
echo   [5] Dry-run preview SMS
echo   [6] Validasi CSV + Config
echo   [7] Preview template pesan
echo   [8] Lihat laporan terakhir
echo   [9] Generate pesan blast WA
echo   [10] Generate pesan blast SMS
echo   [11] Generate pesan blast WA + SMS
echo   [12] Hapus Sesi WhatsApp (Log Out)
echo   [13] Bersihkan data log dan template (Cleanup)
echo   [0] Keluar
echo  ------------------------------------------------
echo.
set /p PILIHAN=  Masukkan pilihan: 

if "%PILIHAN%"=="1" goto RUN_ALL
if "%PILIHAN%"=="2" goto RUN_WA
if "%PILIHAN%"=="3" goto RUN_SMS
if "%PILIHAN%"=="4" goto DRY_RUN_WA
if "%PILIHAN%"=="5" goto DRY_RUN_SMS
if "%PILIHAN%"=="6" goto VALIDATE
if "%PILIHAN%"=="7" goto PREVIEW
if "%PILIHAN%"=="8" goto REPORT
if "%PILIHAN%"=="9" goto GENERATE_WA
if "%PILIHAN%"=="10" goto GENERATE_SMS
if "%PILIHAN%"=="11" goto GENERATE_ALL
if "%PILIHAN%"=="12" goto LOGOUT
if "%PILIHAN%"=="13" goto CLEANUP
if "%PILIHAN%"=="0" goto EXIT

echo.
echo  [!] Pilihan tidak valid. Masukkan angka pilihan yang benar.
goto MENU

:RUN_ALL
echo.
echo  [-^>] Mengirim semua pesan (WA + SMS)...
echo.
python src\main.py run
goto DONE

:RUN_WA
echo.
echo  [-^>] Mengirim via WhatsApp saja...
echo.
python src\main.py run --wa-only
goto DONE

:RUN_SMS
echo.
echo  [-^>] Mengirim via SMS saja...
echo.
python src\main.py run --sms-only
goto DONE

:DRY_RUN_WA
echo.
echo  [-^>] Mode DRY-RUN WA - preview visual tanpa kirim...
echo.
python src\main.py run --dry-run --wa-only
goto DONE

:DRY_RUN_SMS
echo.
echo  [-^>] Mode DRY-RUN SMS - preview di HP Android tanpa kirim...
echo.
python src\main.py run --dry-run --sms-only
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

:GENERATE_WA
echo.
echo  [-^>] Generate pesan blast WA per nomor dari CSV...
echo.
python src\main.py generate --channel wa
goto DONE

:GENERATE_SMS
echo.
echo  [-^>] Generate pesan blast SMS per nomor dari CSV...
echo.
python src\main.py generate --channel sms
goto DONE

:GENERATE_ALL
echo.
echo  [-^>] Generate pesan blast WA dan SMS per nomor dari CSV...
echo.
python src\main.py generate --channel all
goto DONE

:LOGOUT
echo.
echo  [-^>] Menghapus sesi WhatsApp Web (Log out)...
if exist "wa_profile" (
    rmdir /S /Q "wa_profile"
    echo  [OK] Sesi berhasil dihapus. Silakan pilih opsi 1, 2, atau 4 untuk login dengan nomor baru.
) else (
    echo  [INFO] Tidak ada sesi WhatsApp yang tersimpan.
)
goto DONE

:CLEANUP
echo.
echo  [-^>] Membersihkan file log laporan dan template pesan otomatis...
echo.
python src\main.py cleanup
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
