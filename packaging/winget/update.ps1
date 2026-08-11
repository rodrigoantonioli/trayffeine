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

$WingetCreateVersion = "v1.12.8.0"
$WingetCreateUrl = "https://github.com/microsoft/winget-create/releases/download/$WingetCreateVersion/wingetcreate.exe"
$ExpectedWingetCreateSha256 = "8BD738851B524885410112678E3771B341C5C716DE60FBBECB88AB0A363ED85D"
$ExpectedSignerSubject = "Microsoft Corporation"

$toolDir = Join-Path ([System.IO.Path]::GetTempPath()) "trayffeine-wingetcreate-$([guid]::NewGuid())"
$toolPath = Join-Path $toolDir "wingetcreate-$WingetCreateVersion.exe"

New-Item -ItemType Directory -Path $toolDir | Out-Null

try {
    $downloadArgs = @{
        Uri = $WingetCreateUrl
        OutFile = $toolPath
    }
    if ($PSVersionTable.PSEdition -eq "Desktop") {
        $downloadArgs.UseBasicParsing = $true
    }
    Invoke-WebRequest @downloadArgs

    $toolHash = (Get-FileHash -Path $toolPath -Algorithm SHA256).Hash
    if ($toolHash -ne $ExpectedWingetCreateSha256) {
        throw "wingetcreate SHA256 mismatch. Expected $ExpectedWingetCreateSha256, got $toolHash."
    }

    $signature = Get-AuthenticodeSignature -FilePath $toolPath
    if ($signature.Status.ToString() -ne "Valid") {
        throw "wingetcreate signature is not valid. Status: $($signature.Status)."
    }
    if (
        $null -eq $signature.SignerCertificate -or
        $signature.SignerCertificate.Subject -notlike "*$ExpectedSignerSubject*"
    ) {
        throw "wingetcreate signer is not trusted. Subject: $($signature.SignerCertificate.Subject)."
    }

    & $toolPath update $PackageIdentifier -u $InstallerUrl -v $PackageVersion -t $GitHubToken --submit
    if ($LASTEXITCODE -ne 0) {
        throw "wingetcreate failed with exit code $LASTEXITCODE."
    }
}
finally {
    Remove-Item -LiteralPath $toolDir -Recurse -Force -ErrorAction SilentlyContinue
}
