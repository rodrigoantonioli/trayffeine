# MSIX packaging

This directory prepares Trayffeine for a future Microsoft Store submission. It does not replace
the existing PyInstaller + Inno Setup installer, GitHub Release, or WinGet flow.

`build.ps1` builds an x64 PyInstaller bundle in an MSIX-only output directory, stages a full-trust
desktop package, then uses `MakeAppx.exe` to create and unpack an unsigned `.msix` preflight
artifact. It intentionally does not upload, publish, sign, or submit anything.

Use [docs/msix.md](../../docs/msix.md) for the complete developer and Partner Center procedure.
