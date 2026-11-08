# Installation guide

[繁體中文](INSTALL.zh-TW.md) | [简体中文](INSTALL.zh-CN.md) | [English](INSTALL.en.md) | [日本語](INSTALL.ja.md)

macOS Apple Silicon has passed local simulation and phone control/video acceptance. Native Linux setup and launch paths are implemented; isolated container results are reported separately. Desktop graphics, GPU drivers and phone networking still require target-host acceptance. Windows 11 runs the Unix robot stack in WSL2 Ubuntu with WSLg and a PowerShell frontend. This is not native Windows robotd support; real Windows acceptance is pending.

## Download and install

**Current version: `0.1.0-preview.11`** · [GitHub Release](https://github.com/v7rc/microduck-v7rc/releases/tag/v0.1.0-preview.11)

| Platform | Installer | Checksum |
| --- | --- | --- |
| macOS 13+ · Apple Silicon / Intel | [MicroduckV7RC-0.1.0-preview.11-macOS-universal.dmg](https://github.com/v7rc/microduck-v7rc/releases/download/v0.1.0-preview.11/MicroduckV7RC-0.1.0-preview.11-macOS-universal.dmg) | [SHA256](https://github.com/v7rc/microduck-v7rc/releases/download/v0.1.0-preview.11/MicroduckV7RC-0.1.0-preview.11-macOS-universal.dmg.sha256) |
| Windows 11 x64 · WSL2 Ubuntu | [MicroduckV7RC-0.1.0-preview.11-Windows-x64.exe](https://github.com/v7rc/microduck-v7rc/releases/download/v0.1.0-preview.11/MicroduckV7RC-0.1.0-preview.11-Windows-x64.exe) | [SHA256](https://github.com/v7rc/microduck-v7rc/releases/download/v0.1.0-preview.11/MicroduckV7RC-0.1.0-preview.11-Windows-x64.exe.sha256) |

Open the downloaded installer, check prerequisites and confirm installation. Launch from the desktop icon after setup completes. This repository is public; Release installers can be downloaded without signing in to GitHub.

Mac installation, desktop launch, and V7RC control and video were verified on preview.2. The preview.3 drive calibration completed 54 simulator trials on Mac. Full WSL2 installation and phone operation still need validation on a Windows machine.

## Graphical installers and desktop launcher

Download the current unsigned preview from GitHub Releases. Use the universal DMG on macOS 13+, or the self-contained EXE on Windows 11 x64. Windows includes its .NET runtime; the simulator runs inside WSL2 Ubuntu. This is an online installer: initial downloads need internet and roughly 20 GB of free space, not a complete offline simulator bundle.

Mac: open Microduck V7RC inside the DMG, select a language and check the environment. The plan lists missing Apple developer tools, Homebrew/CMake/pkg-config, pinned upstreams, Rust, Python and dependencies. Installation starts only after confirming Install / repair. Complete system dialogs and password requests in the terminal. Only successful completion writes a ready receipt, copies the app to the user Applications directory and creates the desktop icon.

Windows: open the EXE, inspect the environment and confirm installation. Missing WSL/Ubuntu triggers system installation; if Windows requests a reboot, complete it and reopen the installer. Initialize a normal Linux user in Ubuntu first, then install the simulator; Linux packages may require your sudo password. The desktop icon starts the simulator and bridge after success. The installer does not shut down unrelated WSL distributions or change firewall rules. Configure mirrored networking and the specific UDP rules described above for phone access.

The desktop icon automatically launches a completed installation and leaves a terminal showing download/build/runtime output. Initial setup prebuilds the runtime and downloads policies. Ports 6188/8800/1234 are checked before launch: another application using them causes a clear stop, never automatic termination of another project. Use Stop simulator or close the session terminal to stop.

This preview has no publisher signature/notarization, so the OS may display trust prompts. Use organizational signing for production deployment. Mac data defaults to ~/Library/Application Support/MicroduckV7RC; the Windows frontend lives in %LocalAppData%/Programs/MicroduckV7RC and simulator data in Ubuntu ~/.local/share/microduck-v7rc. Installations use separate version directories and do not move or overwrite the research workspace.

## Prerequisites

Recommended target: Ubuntu 24.04 desktop or WSL2 Ubuntu-24.04; Linux x86_64 or aarch64. Requires Git, curl, a C/C++ toolchain, CMake, pkg-config, OpenSSL/udev/ALSA development packages and OpenGL/EGL. Desktop use requires graphics drivers and DISPLAY/Wayland. Headless camera rendering requires a working EGL configuration. This installs single-robot simulation and inference, not a GPU training environment.

## Linux installation

Install these system packages with administrator privileges. The setup program does not run sudo or modify firewall settings.

```
sudo apt-get update
sudo apt-get install -y git curl python3 build-essential cmake pkg-config \
  libssl-dev libudev-dev libasound2-dev libgl1 libegl1 libgl1-mesa-dri libglfw3
```

## Get the integration repository

Setup installs project-local uv 0.13.7, Rust 1.94.1 and Python 3.12.16, checks out the upstream commits, applies the launch patch and installs dependencies using the upstream uv.lock. Initial downloads and Rust compilation may take time and several GB. A mismatched existing upstream HEAD stops setup; it never resets a checkout, overwrites user work or stops another project. The first simulator launch downloads official policies. Allow network access to GitHub, Rust, PyPI and Hugging Face.

```
git clone https://github.com/v7rc/microduck-v7rc.git
cd microduck-v7rc
scripts/setup --check
scripts/setup
```

## Windows 11 / WSL2 installation

Use Windows 11 22H2 or later with virtualization enabled, current WSL2 and GPU drivers. Install Ubuntu-24.04 from an administrator PowerShell, reboot if requested, then follow the Linux steps in the Ubuntu terminal. Keep the repository in the Linux home directory, not /mnt/c, and do not reuse a Windows Python .venv. WSLg provides the simulator window.

```
wsl --install -d Ubuntu-24.04
wsl --update
```

## Phone UDP access to Windows

The phone must initiate UDP traffic into WSL. Enable mirrored networking by adding the setting to the existing [wsl2] section of %UserProfile%\.wslconfig, preserving other settings. Save all WSL work before wsl --shutdown (it stops every distribution), then reopen Ubuntu. If necessary, add rules only for UDP 6188/8800; do not disable the firewall.

```
[wsl2]
networkingMode=mirrored
```

## Phone UDP access to Windows / PowerShell

The phone must initiate UDP traffic into WSL. Enable mirrored networking by adding the setting to the existing [wsl2] section of %UserProfile%\.wslconfig, preserving other settings. Save all WSL work before wsl --shutdown (it stops every distribution), then reopen Ubuntu. If necessary, add rules only for UDP 6188/8800; do not disable the firewall.

```
wsl --shutdown
```

## Phone UDP access to Windows / Firewall

Run Windows firewall commands manually in administrator PowerShell only if equivalent rules do not exist and the current network is a trusted Private profile. A separate WSL Hyper-V rule is included. Update Windows/WSL if its cmdlet is unavailable. On Linux, allow the phone to reach 6188/8800 through whichever firewall is actually enabled.

```
New-NetFirewallRule -DisplayName "Microduck V7RC UDP" -Direction Inbound -Action Allow -Protocol UDP -LocalPort 6188,8800 -Profile Private -RemoteAddress LocalSubnet
New-NetFirewallHyperVRule -Name "MicroduckV7RC" -DisplayName "Microduck V7RC WSL" -Direction Inbound -VMCreatorId '{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}' -Protocol UDP -LocalPorts 6188,8800 -Action Allow
```

## Optional PowerShell frontend

Run it from a Windows-accessible copy of this repository’s windows/ directory. LinuxRepo is an absolute path inside WSL; the default is microduck-v7rc in the Linux home directory. With multiple NICs or VPNs, specify the Windows LAN IPv4 address reachable by the phone. You may instead run both shell launch commands directly in Ubuntu.

```
.\microduck-v7rc.ps1 -Action Serve -Distribution Ubuntu-24.04 -LinuxRepo /home/louis/microduck-v7rc -AdvertiseIP 192.168.1.20
.\microduck-v7rc.ps1 -Action Bridge -Distribution Ubuntu-24.04 -LinuxRepo /home/louis/microduck-v7rc -AdvertiseIP 192.168.1.20
```

## Existing macOS environment

Keep the installed tools and upstream locations. Link them and run setup --check; reinstalling the environment is unnecessary for this update. On a new Mac, install Xcode Command Line Tools before running the same setup. A new Mac also needs CMake and pkg-config; with Homebrew installed, use brew install cmake pkg-config. Replace example 192.168.1.20 and /home/louis with your own IP and path.

```
scripts/link-workspace
scripts/setup --check
```

## Post-install checks

Doctor reports the platform, advertised IP, IPC socket and display environment. If a VPN, multiple NICs or WSL cause an unsuitable address, set MICRODUCK_ADVERTISE_IP. This changes the address displayed for the app, not routing or firewall rules. Update both app endpoints after an address change. Restart the bridge after the phone’s source IP changes.

```
scripts/microduck-sim doctor
microduck_rl/.venv/bin/python -m unittest discover -s tests -v

MICRODUCK_ADVERTISE_IP=192.168.1.20 scripts/microduck-sim serve
```

## Start and connect — 1

The duck should stand up and the console should report healthy. After a valid neutral packet, the overlay shows LIVE and raw joystick movement. Open the app camera: CAMERA ON, a phone PEER address and increasing TX FRAMES indicate host transmission.

```
scripts/microduck-sim serve
```

## Start and connect — 2

Leave the simulator terminal running and open a second terminal for the bridge. Connect the phone and computer to the same Wi-Fi router. Use the IPv4 address shown in the simulator for both app endpoints.

```
scripts/v7rc-bridge
```

## App settings and channels

Use the current LAN IPv4 address, not a fixed example address. Control: Wi-Fi UDP / SRT / 6188. Camera: UDP / 8800. Port 1234 is the computer’s outgoing video source port, not the camera destination configured in the app.

CH1 steering; CH2 forward/reverse; CH3 head pitch (inverted); CH4 head yaw. Range 1000–2000, neutral 1500. All four channels must return to neutral after startup, timeout or reconnection before control is armed again.

## Acceptance checklist

On the target computer check, in order: standing/health, four-channel neutral, forward/reverse and turns, head pitch/yaw, picture/orientation, close/reopen, and neutral protection after input stops. Record OS, architecture, GPU, IP, upstream commits and observed results. Linux container checks do not replace desktop/phone acceptance; PowerShell parsing does not replace a real WSL run.

## Sources (checked 2026-11-06)

- [WSL installation](https://learn.microsoft.com/en-us/windows/wsl/install)
- [WSLg](https://learn.microsoft.com/en-us/windows/wsl/tutorials/gui-apps)
- [WSL networking / mirrored](https://learn.microsoft.com/en-us/windows/wsl/networking)
- [Hyper-V firewall](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/hyper-v-firewall)
- [MuJoCo](https://github.com/google-deepmind/mujoco)
