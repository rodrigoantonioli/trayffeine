# WinGet Packaging Notes

This folder prepares Trayffeine for submission to the Windows Package Manager
community repository (`microsoft/winget-pkgs`).

## Current Status

- Trayffeine is not yet submitted to WinGet.
- Recommended package identifier: `RodrigoAntonioli.Trayffeine`
- Current stable version prepared here: `1.0.0`

## Why The First Submission Should Be Manual

The first submission is easier to do from a real Windows session, not from WSL,
for two reasons:

1. `wingetcreate` is a Windows tool.
2. The submission target is not this repository. The final pull request goes to
   `microsoft/winget-pkgs`, so the first run is best treated as a reviewed,
   one-time onboarding step.

You do not need to clone this repository into a Windows path just to submit the
package. For the first submission, a Windows shell plus the GitHub release URL
is enough if you use `wingetcreate new`.

## Recommended First Submission Flow

From Windows PowerShell:

```powershell
winget install wingetcreate
wingetcreate new
```

When prompted, use the values in [`metadata.json`](./metadata.json).

Important points from the official WinGet docs:

- the installer must use HTTPS
- the installer must support non-interactive modes
- the installer should come directly from the publisher release location
- the package will be validated through automation after the PR is submitted

References:

- https://learn.microsoft.com/en-us/windows/package-manager/package/manifest
- https://learn.microsoft.com/en-us/windows/package-manager/package/repository
- https://github.com/microsoft/winget-create
- https://github.com/microsoft/winget-pkgs

## Suggested Metadata For Trayffeine

- `PackageIdentifier`: `RodrigoAntonioli.Trayffeine`
- `Publisher`: `Rodrigo Antonioli`
- `PackageName`: `Trayffeine`
- `Moniker`: `trayffeine`
- `License`: `MIT`
- `InstallerType`: `inno`

## First Submission Vs. Future Updates

### First submission

Do this manually from Windows so you can inspect the generated manifest and the
resulting pull request to `microsoft/winget-pkgs`.

### Future updates

After the first package is accepted, updates can be automated from the existing
Windows GitHub Actions release environment. The release runner can call
`wingetcreate update ... --submit` with a GitHub PAT stored as a repository
secret.

The helper script for that path is [`update.ps1`](./update.ps1).

## GitHub Actions Automation

The repository release workflow is now prepared to submit WinGet updates
automatically after stable releases.

Conditions:

- the tag must be a stable tag like `v1.0.1`
- beta tags such as `v1.1.0-beta1` do not submit to WinGet
- the repository must define the Actions secret `WINGET_GITHUB_PAT`

Required secret:

- `WINGET_GITHUB_PAT`
  - value: a GitHub classic PAT with `public_repo`

The workflow derives:

- package id: `RodrigoAntonioli.Trayffeine`
- version: from the tag without the leading `v`
- installer URL: from the GitHub release asset naming convention

## Notes About SmartScreen

Publishing to WinGet improves discoverability and installation convenience. It
does not remove SmartScreen warnings for the unsigned installer and does not
change the `Unknown publisher` status shown by Windows.
