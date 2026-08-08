[CmdletBinding()]
param(
    [string]$Version = "",
    [Parameter(Mandatory = $true)]
    [string]$IdentityName,
    [Parameter(Mandatory = $true)]
    [string]$Publisher,
    [string]$DisplayName = "Trayffeine",
    [string]$PublisherDisplayName = "Rodrigo Antonioli",
    [ValidateSet("x64")]
    [string]$Architecture = "x64",
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$SpecFile = Join-Path $Root "packaging\windows\trayffeine.spec"
$ManifestTemplate = Join-Path $PSScriptRoot "AppxManifest.xml.template"
$MsixAssets = Join-Path $PSScriptRoot "assets"
$BuildRoot = Join-Path $Root "build\msix"
$OutputRoot = Join-Path $Root "dist\msix"
$BundleRoot = Join-Path $OutputRoot "bundle"
$StagingRoot = Join-Path $OutputRoot "staging"
$VerificationRoot = Join-Path $OutputRoot "verification"

function Get-ProjectVersion {
    $pyproject = Get-Content -LiteralPath (Join-Path $Root "pyproject.toml") -Raw
    $match = [regex]::Match($pyproject, '(?m)^version\s*=\s*"([^"]+)"\s*$')
    if (-not $match.Success) {
        throw "Could not read the project version from pyproject.toml."
    }
    return $match.Groups[1].Value
}

function ConvertTo-MsixVersion([string]$RawVersion) {
    $normalized = $RawVersion.Trim()
    if ($normalized.StartsWith("v")) {
        $normalized = $normalized.Substring(1)
    }
    if ($normalized -notmatch '^\d+(?:\.\d+){1,3}$') {
        throw "MSIX versions must have two to four numeric components: $RawVersion"
    }

    $numbers = @()
    foreach ($part in $normalized.Split(".")) {
        $number = [int]$part
        if ($number -lt 0 -or $number -gt 65535) {
            throw "MSIX version components must be between 0 and 65535: $RawVersion"
        }
        $numbers += $number
    }
    while ($numbers.Count -lt 4) {
        $numbers += 0
    }
    return $numbers -join "."
}

function Resolve-MakeAppxPath {
    $command = Get-Command "makeappx.exe" -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Path
    }

    $sdkBin = Join-Path ${env:ProgramFiles(x86)} "Windows Kits\10\bin"
    $candidates = @(
        Get-ChildItem -Path $sdkBin -Filter "makeappx.exe" -File -Recurse -ErrorAction SilentlyContinue |
            Where-Object { $_.Directory.Name -eq "x64" } |
            Sort-Object -Property FullName -Descending
    )
    if ($candidates.Count -gt 0) {
        return $candidates[0].FullName
    }

    throw "MakeAppx.exe not found. Install the Windows 10/11 SDK with MSIX packaging tools."
}

function Escape-Xml([string]$Value) {
    return [System.Security.SecurityElement]::Escape($Value)
}

if ([string]::IsNullOrWhiteSpace($Version)) {
    $Version = Get-ProjectVersion
}
$MsixVersion = ConvertTo-MsixVersion $Version

foreach ($path in @($SpecFile, $ManifestTemplate, $MsixAssets)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Required MSIX input not found: $path. Run python scripts\\generate_assets.py first."
    }
}

if ($Clean) {
    foreach ($path in @($BuildRoot, $OutputRoot)) {
        if (Test-Path -LiteralPath $path) {
            Remove-Item -LiteralPath $path -Recurse -Force
        }
    }
}

# These directories must be fresh on every build so removed payload files cannot leak into the
# package and MakeAppx never prompts while unpacking over a previous verification result.
foreach ($path in @($StagingRoot, $VerificationRoot)) {
    if (Test-Path -LiteralPath $path) {
        Remove-Item -LiteralPath $path -Recurse -Force
    }
}

New-Item -ItemType Directory -Force -Path $BuildRoot, $BundleRoot, $StagingRoot, $VerificationRoot |
    Out-Null

python -m PyInstaller $SpecFile --noconfirm --clean --distpath $BundleRoot --workpath $BuildRoot
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed while creating the MSIX bundle."
}

$BundleDirectory = Join-Path $BundleRoot "Trayffeine"
if (-not (Test-Path -LiteralPath (Join-Path $BundleDirectory "Trayffeine.exe"))) {
    throw "PyInstaller output not found: $(Join-Path $BundleDirectory 'Trayffeine.exe')"
}

Copy-Item -Path (Join-Path $BundleDirectory "*") -Destination $StagingRoot -Recurse -Force
$VisualAssets = Join-Path $StagingRoot "Assets"
New-Item -ItemType Directory -Force -Path $VisualAssets | Out-Null
Copy-Item -Path (Join-Path $MsixAssets "*") -Destination $VisualAssets -Force

$manifest = Get-Content -LiteralPath $ManifestTemplate -Raw
$replacements = @{
    "__IDENTITY_NAME__" = $IdentityName
    "__PUBLISHER__" = $Publisher
    "__PACKAGE_VERSION__" = $MsixVersion
    "__ARCHITECTURE__" = $Architecture
    "__DISPLAY_NAME__" = $DisplayName
    "__PUBLISHER_DISPLAY_NAME__" = $PublisherDisplayName
}
foreach ($token in $replacements.Keys) {
    $manifest = $manifest.Replace($token, (Escape-Xml $replacements[$token]))
}
Set-Content -LiteralPath (Join-Path $StagingRoot "AppxManifest.xml") -Value $manifest -Encoding utf8

$MakeAppx = Resolve-MakeAppxPath
$PackagePath = Join-Path $OutputRoot "Trayffeine-$MsixVersion-$Architecture.msix"
& $MakeAppx pack /o /d $StagingRoot /p $PackagePath
if ($LASTEXITCODE -ne 0) {
    throw "MakeAppx failed while creating $PackagePath"
}

& $MakeAppx unpack /p $PackagePath /d $VerificationRoot
if ($LASTEXITCODE -ne 0) {
    throw "MakeAppx failed while validating $PackagePath"
}

foreach ($relativePath in @(
    "AppxManifest.xml",
    "Trayffeine.exe",
    "Assets\Square44x44Logo.png",
    "Assets\Square150x150Logo.png",
    "Assets\Wide310x150Logo.png",
    "Assets\StoreLogo.png"
)) {
    if (-not (Test-Path -LiteralPath (Join-Path $VerificationRoot $relativePath))) {
        throw "MSIX validation did not find required package content: $relativePath"
    }
}

[xml]$verifiedManifest = Get-Content -LiteralPath (Join-Path $VerificationRoot "AppxManifest.xml")
$identity = $verifiedManifest.DocumentElement.SelectSingleNode("*[local-name()='Identity']")
if (
    $identity.GetAttribute("Name") -ne $IdentityName -or
    $identity.GetAttribute("Publisher") -ne $Publisher -or
    $identity.GetAttribute("Version") -ne $MsixVersion -or
    $identity.GetAttribute("ProcessorArchitecture") -ne $Architecture
) {
    throw "MSIX validation found an unexpected package identity."
}

$application = $verifiedManifest.DocumentElement.SelectSingleNode(
    "*[local-name()='Applications']/*[local-name()='Application']"
)
if ($null -eq $application -or $application.GetAttribute("Executable") -ne "Trayffeine.exe") {
    throw "MSIX validation did not find the Trayffeine full-trust application entry."
}

$startupTask = $application.SelectSingleNode(".//*[local-name()='StartupTask']")
if ($null -eq $startupTask -or $startupTask.GetAttribute("TaskId") -ne "TrayffeineStartup") {
    throw "MSIX validation did not find the Trayffeine startup task declaration."
}

Write-Host "Created unsigned MSIX preflight package: $PackagePath"
Write-Host "Staged package files remain available for local registration: $StagingRoot"
