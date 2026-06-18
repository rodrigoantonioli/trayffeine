param(
    [string]$Version = "1.1.2",
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$SpecFile = Join-Path $PSScriptRoot "trayffeine.spec"
$InstallerScript = Join-Path $PSScriptRoot "Trayffeine.iss"
$NormalizedVersion = $Version.Trim()

function Resolve-IsccPath {
    $Command = Get-Command iscc.exe -ErrorAction SilentlyContinue
    if ($Command) {
        return $Command.Path
    }

    $Candidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
        (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe")
    )

    foreach ($Candidate in $Candidates) {
        if ($Candidate -and (Test-Path $Candidate)) {
            return (Resolve-Path $Candidate).Path
        }
    }

    throw "ISCC.exe not found. Install Inno Setup 6 or add it to PATH."
}

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

$ISCC = Resolve-IsccPath
& $ISCC "/DAppVersion=$NormalizedVersion" "/DSourceRoot=$Root" "/DOutputDir=$InstallerOutput" $InstallerScript
