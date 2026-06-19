# Changelog

## 1.2.0

Usability and support release for Trayffeine.

Highlights:

- adds persistent presence compatibility mode using F15 as the effective keep-awake method
- shows configured and effective keep-awake method status in the tray menu
- adds `Copy diagnostics` for support details such as version, language, session, methods, settings path, and log path
- reorganizes the native tray menu with compact status, preferences, and support sections
- documents how presence compatibility, diagnostics, and support reporting should be used
- clarifies that Teams and similar presence indicators are best effort, not guaranteed

## 1.1.2

Maintenance release for Trayffeine.

Highlights:

- moves local development, CI, preview builds, and release builds to Python 3.13
- fixes the entrypoint smoke test so it does not launch the real tray app on Windows
- makes the Windows build script find per-user Inno Setup installations outside `PATH`
- refreshes generated tray assets and fixes stale README links

## 1.1.1

Hotfix release for Trayffeine.

Highlights:

- reapplies the persisted `Start with Windows` preference during app launch
- keeps startup registration and the tray checkbox from drifting apart when the Windows `Run` key is removed externally
- continues launching normally if startup-registration sync fails

## 1.1.0

Second stable release of Trayffeine.

Highlights:

- added a persistent `Start with Windows` preference backed by the current-user `Run` key
- kept the auto-start option in the tray `Preferences` menu without adding a main window
- added `CONTRIBUTING.md` and an internal `docs/ROADMAP.md`
- refreshed public docs to reflect WinGet availability and the unsigned-installer caveat
- bumped project, packaging, and WinGet metadata to `1.1.0`

## 1.0.0

First stable release of Trayffeine.

Highlights:

- Windows tray-only app with no main window
- timed presets and infinite mode
- automatic return to inactive mode when timers end
- localized runtime UI in `pt-BR`, `en`, and `es`
- persistent language, keep-awake method, and detailed logging preferences
- persistent restore of infinite mode
- configurable keep-awake methods: `Smart`, `Windows API`, `F15`, and `Shift`
- double-click toggle for infinite mode
- grouped `Preferences` and `Support` tray menus
- support actions for help, logs folder, and log cleanup
- rotating log files and crash dialog with log-path guidance
- Windows installer and GitHub Actions release pipeline

## Pre-1.0.0 History

### 0.7.x

- Added configurable keep-awake methods and smart fallback order.
- Added support/help dialog and first-run defaults.
- Fixed help dialog closing behavior.
- Reduced heavy tray redraws while keeping the tooltip live.

### 0.6.x

- Reworked the tray menu into grouped `Preferences` and `Support` sections.
- Added persistent detailed logging control.
- Added `Open Logs Folder` and `Clear Logs`.
- Fixed dialog behavior and reduced noisy detailed logs.

### 0.5.0 beta

- Hardened the app for beta testing.
- Added crash boundary logging and support flow improvements.
- Added prerelease handling in the release workflow.

### 0.4.x

- Refined tray UX and status summaries.
- Restored correct accented localized text.

### 0.3.x

- Added persistence for language and infinite-mode restore.
- Added live tray status and Windows double-click toggle.
- Added runtime log rotation and multiple tray/runtime hotfixes.

### 0.2.0

- Added runtime localization and project documentation.

### 0.1.x

- Initial scaffold, packaging pipeline, and early Windows runtime fixes.
