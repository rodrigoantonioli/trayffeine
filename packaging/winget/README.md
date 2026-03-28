# WinGet Packaging Notes

Trayffeine is already published to the Windows Package Manager community
repository (`microsoft/winget-pkgs`) under
`RodrigoAntonioli.Trayffeine`.

This folder keeps the publisher metadata and update notes aligned with the
GitHub release workflow.

## Current Status

- package identifier: `RodrigoAntonioli.Trayffeine`
- current stable version tracked here: `1.1.1`
- stable releases can submit WinGet updates automatically from GitHub Actions
- beta tags do not submit WinGet updates

## Metadata File

[`metadata.json`](./metadata.json) stores the package identity and the expected
GitHub release URL pattern for the current stable version.

The installer SHA is not stored here ahead of time because it depends on the
actual Windows release artifact that gets built for that version.

## GitHub Actions Automation

The release workflow can submit WinGet updates automatically after stable tag
releases.

Conditions:

- the tag must be a stable tag such as `v1.1.1`
- beta tags such as `v1.2.0-beta1` skip WinGet submission
- the repository must define the Actions secret `WINGET_GITHUB_PAT`

Required secret:

- `WINGET_GITHUB_PAT`
  - value: a GitHub classic PAT with `public_repo`

The workflow derives:

- package id: `RodrigoAntonioli.Trayffeine`
- version: from the tag without the leading `v`
- installer URL: from the GitHub release asset naming convention

The helper script for that path is [`update.ps1`](./update.ps1).

## Manual Fallback

If automation is unavailable, run `wingetcreate update ... --submit` from a
real Windows shell after the GitHub release asset is published.

Useful references:

- https://learn.microsoft.com/en-us/windows/package-manager/package/manifest
- https://learn.microsoft.com/en-us/windows/package-manager/package/repository
- https://github.com/microsoft/winget-create
- https://github.com/microsoft/winget-pkgs

## Notes About SmartScreen

Publishing to WinGet improves discoverability and installation convenience. The
project still ships an unsigned installer, so direct installer downloads can
still show Windows or SmartScreen warnings and `Unknown publisher` prompts.
