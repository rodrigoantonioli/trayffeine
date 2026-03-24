param(
    [Parameter(Mandatory = $true)]
    [string]$PackageIdentifier,

    [Parameter(Mandatory = $true)]
    [string]$PackageVersion,

    [Parameter(Mandatory = $true)]
    [string]$InstallerUrl,

    [Parameter(Mandatory = $true)]
    [string]$GitHubToken
)

$ErrorActionPreference = "Stop"

$toolPath = Join-Path $env:TEMP "wingetcreate.exe"

Invoke-WebRequest "https://aka.ms/wingetcreate/latest" -OutFile $toolPath

& $toolPath update $PackageIdentifier -u $InstallerUrl -v $PackageVersion -t $GitHubToken --submit
