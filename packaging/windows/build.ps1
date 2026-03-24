param(
    [string]$Version = "0.3.4",
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$SpecFile = Join-Path $PSScriptRoot "trayffeine.spec"
$InstallerScript = Join-Path $PSScriptRoot "Trayffeine.iss"
$NormalizedVersion = $Version.Trim()

if ($NormalizedVersion.StartsWith("v")) {
    $NormalizedVersion = $NormalizedVersion.Substring(1)
}

if ($Clean) {
    Remove-Item -Recurse -Force (Join-Path $Root "build") -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force (Join-Path $Root "dist\Trayffeine") -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force (Join-Path $Root "dist\installer") -ErrorAction SilentlyContinue
}

python -m PyInstaller $SpecFile --noconfirm --clean

$ExePath = Join-Path $Root "dist\Trayffeine\Trayffeine.exe"
if (-not (Test-Path $ExePath)) {
    throw "PyInstaller output not found: $ExePath"
}

$InstallerOutput = Join-Path $Root "dist\installer"
New-Item -ItemType Directory -Force -Path $InstallerOutput | Out-Null

$ISCC = (Get-Command iscc.exe -ErrorAction Stop).Path
& $ISCC "/DAppVersion=$NormalizedVersion" "/DSourceRoot=$Root" "/DOutputDir=$InstallerOutput" $InstallerScript
