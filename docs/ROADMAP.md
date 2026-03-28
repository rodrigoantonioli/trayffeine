# Roadmap

This file is a maintainer-facing backlog, not a product commitment.

## v1.1.0

Current release bucket:

- add `Start with Windows` in tray preferences
- add public contributor guidance
- refresh release and WinGet docs for the current repository state

## v1.2

Next product and repo improvements under consideration:

- show which keep-awake method is actually active when `Smart` falls back
- add a `Copy diagnostics` tray action with version, language, active method, and log path
- add issue templates plus a screenshot or GIF to the public repo
- document better when Trayffeine helps with sleep prevention versus app-presence expectations

## v2.0

Larger reliability and packaging ideas:

- add a lightweight diagnostics flow to test `Windows API`, `F15`, and `Shift`
- surface a discreet notification when every keep-awake backend fails
- expand automated coverage around settings, logging, packaging, and release wiring
- review Start Menu folder organization and future packaging polish

## Not Planned For Now

- code signing is intentionally out of scope because of cost
- custom popup UI instead of the native tray menu
- arbitrary key selection
- online telemetry
