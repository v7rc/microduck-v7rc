# Microduck × V7RC Integration

[繁體中文](README.md) | [简体中文](README.zh-CN.md) | [English](README.en.md) | [日本語](README.ja.md)

Control the Microduck simulator with the V7RC app over Wi-Fi UDP and stream its 640×360 head camera. Includes a four-channel SRT bridge and an overlay showing input FPS, two joysticks, connection addresses, and camera frame counts.

## Download and install

**Current version: `0.1.0-preview.5`** · [GitHub Release](https://github.com/v7rc/microduck-v7rc/releases/tag/v0.1.0-preview.5)

| Platform | Installer | Checksum |
| --- | --- | --- |
| macOS 13+ · Apple Silicon / Intel | [MicroduckV7RC-0.1.0-preview.5-macOS-universal.dmg](https://github.com/v7rc/microduck-v7rc/releases/download/v0.1.0-preview.5/MicroduckV7RC-0.1.0-preview.5-macOS-universal.dmg) | [SHA256](https://github.com/v7rc/microduck-v7rc/releases/download/v0.1.0-preview.5/MicroduckV7RC-0.1.0-preview.5-macOS-universal.dmg.sha256) |
| Windows 11 x64 · WSL2 Ubuntu | [MicroduckV7RC-0.1.0-preview.5-Windows-x64.exe](https://github.com/v7rc/microduck-v7rc/releases/download/v0.1.0-preview.5/MicroduckV7RC-0.1.0-preview.5-Windows-x64.exe) | [SHA256](https://github.com/v7rc/microduck-v7rc/releases/download/v0.1.0-preview.5/MicroduckV7RC-0.1.0-preview.5-Windows-x64.exe.sha256) |

Open the downloaded installer, check prerequisites and confirm installation. Launch from the desktop icon after setup completes. This repository is public; Release installers can be downloaded without signing in to GitHub.

Mac installation, desktop launch, and V7RC control and video were verified on preview.2. The preview.3 drive calibration completed 54 simulator trials on Mac. Full WSL2 installation and phone operation still need validation on a Windows machine.

## Graphical installers and desktop launcher

Download the current unsigned preview from GitHub Releases. Use the universal DMG on macOS 13+, or the self-contained EXE on Windows 11 x64. Windows includes its .NET runtime; the simulator runs inside WSL2 Ubuntu. This is an online installer: initial downloads need internet and roughly 20 GB of free space, not a complete offline simulator bundle.

## Platforms and validation

macOS Apple Silicon has passed local simulation and phone control/video acceptance. Native Linux setup and launch paths are implemented; isolated container results are reported separately. Desktop graphics, GPU drivers and phone networking still require target-host acceptance. Windows 11 runs the Unix robot stack in WSL2 Ubuntu with WSLg and a PowerShell frontend. This is not native Windows robotd support; real Windows acceptance is pending.

## Quick start

Complete the installation guide on a new machine. The existing Louis Mac workspace can reuse sibling checkouts and tools with scripts/link-workspace; that command does not install a fresh machine. Run all relative commands below from the integration repository root.

```
scripts/microduck-sim serve
```

Leave the simulator terminal running and open a second terminal for the bridge. Connect the phone and computer to the same Wi-Fi router. Use the IPv4 address shown in the simulator for both app endpoints.

```sh
scripts/v7rc-bridge
```

## App settings and channels

Use the current LAN IPv4 address, not a fixed example address. Control: Wi-Fi UDP / SRT / 6188. Camera: UDP / 8800. Port 1234 is the computer’s outgoing video source port, not the camera destination configured in the app.

CH1 steering; CH2 forward/reverse; CH3 head pitch (inverted); CH4 head yaw. Range 1000–2000, neutral 1500. All four channels must return to neutral after startup, timeout or reconnection before control is armed again.

## Source and upstream projects

bridge/ contains control, camera, HUD and platform helpers; scripts/ contains setup and launch commands; windows/ contains the WSL frontend; tests/ contains checks. upstream-revisions.json pins upstream commits. Upstream repositories, .venv, .tools and .runtime are excluded from Git. Dependencies may be local clones or symlinks to existing checkouts. Only two upstream runtime launch lines are patched; physics and walking policies are unchanged.

## Known limitations

iOS camera subscriptions failed when the same iPhone provided Personal Hotspot; video passed on a shared Wi-Fi router. Low-speed walking, velocity tracking and straight-line accuracy have upstream limitations. Receiving UDP does not establish motion accuracy. CAMERA ON and TX FRAMES indicate an active subscription and host transmission; confirm the app display separately. Read upstream LICENSE-MODELS.md for model licensing, including CC BY-NC-SA 4.0.

## Guides and tests

- [Installation guide](docs/INSTALL.en.md)
- [How to use — HTML](docs/how-to.html#en)
- [Validation](docs/validation/2026-11-06-cross-platform.md)

```sh
microduck_rl/.venv/bin/python -m unittest discover -s tests -v
```
