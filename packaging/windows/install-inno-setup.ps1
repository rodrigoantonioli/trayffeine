$ErrorActionPreference = "Stop"

$InnoSetupVersion = "6.7.1"
$PackageUrl = "https://community.chocolatey.org/api/v2/package/innosetup/$InnoSetupVersion"
$ExpectedPackageSha512 = "431A9F0A8D40D95F8A04C8D98617D2F6E88AC08B65A01BE1F272D6978C3F726AE118F9D7DC04C2B52A429DDEC3D491358A1C8BF2F77DEEE0ABDA8606A975EB61"
$ExpectedInstallerSha256 = "4D11E8050B6185E0D49BD9E8CC661A7A59F44959A621D31D11033124C4E8A7B0"
$ExpectedSignerSubject = "Pyrsys B.V."
$ValidExitCodes = @(0, 3010, 1641)

$workDir = Join-Path ([System.IO.Path]::GetTempPath()) "trayffeine-innosetup-$([guid]::NewGuid())"
$packagePath = Join-Path $workDir "innosetup.$InnoSetupVersion.nupkg"
$packageZipPath = Join-Path $workDir "innosetup.$InnoSetupVersion.zip"
$extractPath = Join-Path $workDir "package"
$installerPath = Join-Path $extractPath "tools\innosetup-$InnoSetupVersion.exe"

New-Item -ItemType Directory -Path $workDir | Out-Null

try {
    $downloadArgs = @{
        Uri = $PackageUrl
        OutFile = $packagePath
    }
    if ($PSVersionTable.PSEdition -eq "Desktop") {
        $downloadArgs.UseBasicParsing = $true
    }
    Invoke-WebRequest @downloadArgs

    $packageHash = (Get-FileHash -Path $packagePath -Algorithm SHA512).Hash
    if ($packageHash -ne $ExpectedPackageSha512) {
        throw "Inno Setup package SHA512 mismatch. Expected $ExpectedPackageSha512, got $packageHash."
    }

    Copy-Item -LiteralPath $packagePath -Destination $packageZipPath
    Expand-Archive -LiteralPath $packageZipPath -DestinationPath $extractPath

    if (-not (Test-Path -LiteralPath $installerPath)) {
        throw "Inno Setup installer was not found in the pinned package."
    }

    $installerHash = (Get-FileHash -Path $installerPath -Algorithm SHA256).Hash
    if ($installerHash -ne $ExpectedInstallerSha256) {
        throw "Inno Setup installer SHA256 mismatch. Expected $ExpectedInstallerSha256, got $installerHash."
    }

    $signature = Get-AuthenticodeSignature -FilePath $installerPath
    if ($signature.Status.ToString() -ne "Valid") {
        throw "Inno Setup installer signature is not valid. Status: $($signature.Status)."
    }
    if (
        $null -eq $signature.SignerCertificate -or
        $signature.SignerCertificate.Subject -notlike "*$ExpectedSignerSubject*"
    ) {
        throw "Inno Setup installer signer is not trusted. Subject: $($signature.SignerCertificate.Subject)."
    }

    $installArgs = @("/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-")
    $process = Start-Process -FilePath $installerPath -ArgumentList $installArgs -Wait -PassThru
    if ($process.ExitCode -notin $ValidExitCodes) {
        throw "Inno Setup installer failed with exit code $($process.ExitCode)."
    }
}
finally {
    Remove-Item -LiteralPath $workDir -Recurse -Force -ErrorAction SilentlyContinue
}
