@echo off
title Lanzador AsisTech
echo ===================================================
echo           INICIANDO EMULADOR Y ASISTECH
echo ===================================================

set ADB="%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"
set EMULATOR="%LOCALAPPDATA%\Android\Sdk\emulator\emulator.exe"
set APK_PATH="%~dp0aplicativo-movil-registro-de-camaras--main\mobile_app\build\app\outputs\flutter-apk\app-debug.apk"

echo [1/3] Verificando emulador...
%ADB% devices | findstr "emulator-" >nul
if %errorlevel% neq 0 (
    echo Iniciando ventana del emulador Medium_Phone...
    start "" %EMULATOR% -avd Medium_Phone
    echo Esperando a que el emulador encienda por completo...
    %ADB% wait-for-device
    :wait_boot
    timeout /t 3 /nobreak >nul
    for /f "tokens=*" %%a in ('%ADB% shell getprop sys.boot_completed 2^>nul') do set BOOT=%%a
    if not "%BOOT%"=="1" goto wait_boot
) else (
    echo El emulador ya esta en ejecucion.
)

echo [2/3] Instalando AsisTech...
%ADB% install -r %APK_PATH%

echo [3/3] Abriendo AsisTech en pantalla...
%ADB% shell monkey -p com.upec.asistech -c android.intent.category.LAUNCHER 1

echo ===================================================
echo     Listo! AsisTech esta abierto en tu emulador.
echo ===================================================
pause
