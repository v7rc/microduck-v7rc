# Microduck × V7RC Integration

[繁體中文](README.md) | [简体中文](README.zh-CN.md) | [English](README.en.md) | [日本語](README.ja.md)

Control the Microduck simulator with the V7RC app over Wi-Fi UDP and stream its 640×360 head camera. Includes a four-channel SRT bridge and an overlay showing input FPS, two joysticks, connection addresses, and camera frame counts.

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
