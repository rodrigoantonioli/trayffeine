# Microsoft Store / MSIX pilot

Trayffeine is prepared for a future Microsoft Store submission as a full-trust MSIX desktop app.
This is preparation only: there is no Store listing, submission, GitHub Release upload, or WinGet
change in this repository state.

## What remains unchanged

- The public installer remains the per-user Inno Setup `.exe` built by
  `packaging/windows/build.ps1`.
- GitHub Release tags still publish only that installer and follow the existing WinGet update path.
- The new MSIX workflow never runs on tags and never creates a GitHub Release.
- No project version is changed just to create an MSIX package.

The MSIX route is intentionally an x64 pilot for Trayffeine. Add other architectures only after a
real Store acceptance test shows they are needed.

## Package design and behavior

`packaging/msix/build.ps1` creates an MSIX-only PyInstaller bundle under `dist/msix/`, stages it
with `AppxManifest.xml`, and uses the Windows SDK `MakeAppx.exe` to pack and unpack the result. The
unpack step verifies the identity, full-trust executable, declared startup task, and required tile
assets. The script does not sign, publish, install, or submit the package.

The manifest declares `Windows.FullTrustApplication` and `runFullTrust`, which keeps the existing
Win32 tray implementation, native dialogs, and keep-awake backends in their full-trust desktop
context. It also declares the `TrayffeineStartup` `windows.startupTask` extension.

Startup behavior is intentionally channel-aware:

- The existing EXE/Inno Setup/WinGet install continues to use the current-user `Run` key.
- When Trayffeine has an MSIX package identity, the same tray preference uses the declared Windows
  startup task instead. This avoids relying on a virtualized `Run` key inside the package.
- The task starts disabled. Turning on `Preferences > Start with Windows` requests its enablement.
  Windows exposes it in Task Manager's Startup tab. If the user disables it there, Windows does not
  allow the app to turn it back on programmatically; the next launch reconciles the tray preference
  to off.

Settings and logs continue to use the existing `%LOCALAPPDATA%\Trayffeine` code path. MSIX manages
that state per user and preserves it through package updates; a full uninstall can remove
package-managed state. Test any desired migration from an existing EXE install explicitly during
acceptance, rather than assuming that the two install channels share all state.

Do not run the legacy EXE and MSIX package as simultaneous acceptance targets: both deliberately use
the same single-instance mutex. Disable legacy autostart before testing MSIX autostart.

## Build an unsigned preflight package locally

Requirements:

- Windows with the Windows 10 or 11 SDK MSIX packaging tools (`MakeAppx.exe`)
- Python 3.13

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .[build,msix]
python scripts\generate_assets.py

powershell -ExecutionPolicy Bypass -File packaging\msix\build.ps1 `
  -IdentityName "Trayffeine.Preview" `
  -Publisher "CN=Trayffeine Preview" `
  -PublisherDisplayName "Trayffeine Preview" `
  -Clean
```

The command creates `dist/msix/Trayffeine-<version>-x64.msix`, plus the staged package at
`dist/msix/staging`. It is deliberately unsigned. The preview identity is only suitable for package
structure validation; do not upload it to Partner Center.

The staging and verification directories are recreated on every build, even without `-Clean`.
Passing `-Clean` additionally removes the previous PyInstaller work and all MSIX output first.

For an interactive local package-context smoke test, register the staged manifest from an appropriate
development-enabled Windows machine:

```powershell
Add-AppxPackage -Register (Resolve-Path .\dist\msix\staging\AppxManifest.xml)
```

This worktree's host intentionally did not perform that registration: Windows returned `0x80073CFF`
because it does not allow unsigned developer package registration. Do not enable Developer Mode or
change sideload/security policy solely for this pilot. This is the only unperformed local installation
test; run it later on a disposable, development-approved Windows profile.

Then launch Trayffeine from Start and verify tray appearance, a timed session, infinite restore,
settings persistence across relaunch, and the Startup task. Test package removal separately on a
non-production user profile. A signed package is only necessary for direct MSIX sideloading; it is
not needed for this preflight or a Microsoft Store MSIX submission.

## CI preflight

`MSIX Preview Build` runs for relevant pull requests and manual dispatches on `windows-latest`. It
uses a non-Store preview identity and uploads the unsigned `.msix` only as a workflow artifact. It
also rebuilds without `-Clean` after adding sentinel files, verifying that stale staging and
verification content is removed. It does not need Partner Center credentials, certificates, GitHub
Release permissions, or WinGet credentials.

## Partner Center values required later

Before the first real submission, use Partner Center to create an **MSIX/PWA** product and reserve
the Store name. Copy these exact package-identity values into the real build command:

- `Identity Name` / package identity name
- `Publisher` (the exact X.500 publisher string supplied by Partner Center)
- reserved display name and the publisher display name, if they differ from the defaults

The public display name is not a substitute for either identity field. Build the submission candidate
only after those values are known:

```powershell
powershell -ExecutionPolicy Bypass -File packaging\msix\build.ps1 `
  -IdentityName "<Partner Center identity name>" `
  -Publisher "<Partner Center publisher>" `
  -DisplayName "<Reserved Store name>" `
  -PublisherDisplayName "<Partner Center publisher display name>" `
  -Clean
```

The script reads `pyproject.toml` by default and maps the current semantic version, for example
`1.2.0`, to the four-part MSIX version `1.2.0.0`. A later Store update must increase that MSIX
version; this preparation does not require a version bump.

Before uploading the real submission candidate, run the current Windows App Certification Kit from
an elevated command prompt in an active user session. Use the package built with the exact Partner
Center identity, and review the generated report rather than assuming that a successful MakeAppx
pack/unpack is equivalent to Store certification:

```powershell
$appCert = "${env:ProgramFiles(x86)}\Windows Kits\10\App Certification Kit\appcert.exe"
& $appCert reset
& $appCert test `
  -appxpackagepath ".\dist\msix\Trayffeine-<version>-x64.msix" `
  -reportoutputpath ".\dist\msix\wack-report.xml"
```

Finish the required Partner Center metadata before submission: pricing and availability, category and
capability declarations, age rating, Store description, screenshots, Store listing artwork, support
details, and a privacy-policy URL if the published data practices require one. Explain the
`runFullTrust` declaration as the packaging requirement for this existing Win32 tray application.

For Microsoft Store MSIX distribution, Microsoft signs the submitted package after certification, so
no certificate, PFX, or signing secret belongs in this repository or workflow. For private signed
sideload tests, use a local test certificate whose subject exactly matches the manifest publisher and
trust it only on the test machine.

Useful official references:

- [Manual desktop MSIX packaging](https://learn.microsoft.com/windows/msix/desktop/desktop-to-uwp-manual-conversion)
- [Desktop startup task extension](https://learn.microsoft.com/windows/apps/desktop/modernize/desktop-to-uwp-extensions#start-an-executable-file-when-users-log-into-windows)
- [MakeAppx command-line packaging](https://learn.microsoft.com/windows/msix/package/create-app-package-with-makeappx-tool)
- [Windows App Certification Kit](https://learn.microsoft.com/windows/uwp/debug-test-perf/windows-app-certification-kit)
- [MSIX signing options](https://learn.microsoft.com/windows/msix/package/signing-package-overview)
- [Packaged desktop app state and AppData behavior](https://learn.microsoft.com/windows/msix/desktop/desktop-to-uwp-behind-the-scenes)
