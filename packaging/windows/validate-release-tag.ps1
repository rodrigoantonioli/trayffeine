param(
    [Parameter(Mandatory = $true)]
    [string]$Tag
)

$ErrorActionPreference = "Stop"

$ReleaseTagPattern = '^v(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)(?:-beta(?:[.-]?(?:0|[1-9]\d*))?)?$'

if ($Tag -cnotmatch $ReleaseTagPattern) {
    throw "Unsupported release tag: $Tag"
}

Write-Host "Validated release tag: $Tag"
