# Script PowerShell para iniciar emulador con ventana visible y lanzar AsisTech
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "          INICIANDO EMULADOR Y ASISTECH            " -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

$adb = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"
$emulator = "$env:LOCALAPPDATA\Android\Sdk\emulator\emulator.exe"
$apkPath = "$PSScriptRoot\aplicativo-movil-registro-de-camaras--main\mobile_app\build\app\outputs\flutter-apk\app-debug.apk"

# 1. Comprobar si el emulador esta encendido
$activeDevice = & $adb devices | Select-String "emulator-"
if (-not $activeDevice) {
    Write-Host "[1/3] Iniciando ventana del emulador Medium_Phone..." -ForegroundColor Yellow
    Start-Process -FilePath $emulator -ArgumentList "-avd", "Medium_Phone"
    Write-Host "Esperando a que el emulador encienda por completo..." -ForegroundColor Gray
    & $adb wait-for-device
    while ((& $adb shell getprop sys.boot_completed 2>$null).Trim() -ne "1") {
        Start-Sleep -Seconds 3
    }
} else {
    Write-Host "[1/3] El emulador ya esta en ejecucion." -ForegroundColor Green
}

# 2. Instalar el APK
Write-Host "[2/3] Instalando AsisTech..." -ForegroundColor Yellow
& $adb install -r $apkPath

# 3. Lanzar la aplicación
Write-Host "[3/3] Abriendo AsisTech en pantalla..." -ForegroundColor Green
& $adb shell monkey -p com.upec.asistech -c android.intent.category.LAUNCHER 1

Write-Host "`nListo! AsisTech esta corriendo en la ventana de tu emulador." -ForegroundColor Cyan
