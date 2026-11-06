# 安装指南

[繁體中文](INSTALL.zh-TW.md) | [简体中文](INSTALL.zh-CN.md) | [English](INSTALL.en.md) | [日本語](INSTALL.ja.md)

macOS Apple Silicon 已完成本机与手机控制／图像验收。Linux 提供原生安装与启动，隔离容器测试见验证记录；实际桌面、GPU 与手机网络仍待目标机验收。Windows 11 使用 WSL2 Ubuntu＋WSLg，提供 PowerShell 启动器；并非原生 Windows robotd，Windows 目标机仍待验收。

## 前置条件

建议 Ubuntu 24.04 桌面／WSL2 Ubuntu-24.04；Linux x86_64 或 aarch64。需要 Git、curl、C/C++ 工具链、CMake、pkg-config、OpenSSL／udev／ALSA 开发包及 OpenGL／EGL。桌面需要可用的图形驱动和 DISPLAY／Wayland；无窗口计算仍须按相机需求配置 EGL。本安装用于单机模拟与推理，并非 GPU 训练环境。

## Linux 安装

以下系统软件包安装需要管理员权限；setup 不会自行执行 sudo，也不会调整防火墙。

```
sudo apt-get update
sudo apt-get install -y git curl python3 build-essential cmake pkg-config \
  libssl-dev libudev-dev libasound2-dev libgl1 libegl1 libgl1-mesa-dri libglfw3
```

## 从新环境获取集成 Repo

setup 下载项目内 uv 0.13.7、Rust 1.94.1 和 Python 3.12.16，按版本清单 clone 上游并应用补丁，再按上游 uv.lock 安装依赖。首次下载和 Rust 编译可能耗时较长并占用数 GB。现有上游 HEAD 不匹配时会停止，不会 reset、覆盖用户修改或停止其他项目。首次启动会下载官方策略；网络需能访问 GitHub、Rust、PyPI 和 Hugging Face。

```
git clone https://github.com/v7rc/microduck-v7rc.git
cd microduck-v7rc
scripts/setup --check
scripts/setup
```

## Windows 11／WSL2 安装

建议 Windows 11 22H2 以上，启用虚拟化，使用最新 WSL2 和 GPU 驱动。先在管理员 PowerShell 安装 Ubuntu-24.04，按提示重启，再于 Ubuntu 终端按 Linux 步骤安装。Repo 放在 Linux 家目录，不要共用 Windows Python .venv 或从 /mnt/c 执行。WSLg 提供模拟器窗口。

```
wsl --install -d Ubuntu-24.04
wsl --update
```

## Windows 手机 UDP 网络

手机需要能主动连入 WSL。使用 mirrored networking，在现有 %UserProfile%\.wslconfig 的 [wsl2] 区段加入设置并保留其他配置。先保存所有 WSL 工作，再执行 wsl --shutdown（会停止全部发行版），然后重开 Ubuntu。若仍被阻挡，只添加 UDP 6188／8800 的必要规则，不要关闭整个防火墙。

```
[wsl2]
networkingMode=mirrored
```

## Windows 手机 UDP 网络 / PowerShell

手机需要能主动连入 WSL。使用 mirrored networking，在现有 %UserProfile%\.wslconfig 的 [wsl2] 区段加入设置并保留其他配置。先保存所有 WSL 工作，再执行 wsl --shutdown（会停止全部发行版），然后重开 Ubuntu。若仍被阻挡，只添加 UDP 6188／8800 的必要规则，不要关闭整个防火墙。

```
wsl --shutdown
```

## Windows 手机 UDP 网络 / Firewall

Windows 防火墙命令需在管理员 PowerShell 手动执行，仅在没有等效规则且当前网络是可信任 Private profile 时使用。Hyper-V 的 WSL 规则另列；命令不存在时先更新 Windows／WSL。Linux 则按实际启用的防火墙放行手机至 6188／8800。

```
New-NetFirewallRule -DisplayName "Microduck V7RC UDP" -Direction Inbound -Action Allow -Protocol UDP -LocalPort 6188,8800 -Profile Private -RemoteAddress LocalSubnet
New-NetFirewallHyperVRule -Name "MicroduckV7RC" -DisplayName "Microduck V7RC WSL" -Direction Inbound -VMCreatorId '{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}' -Protocol UDP -LocalPorts 6188,8800 -Action Allow
```

## 可选 PowerShell 启动器

可从 Windows 可读的本 Repo windows/ 目录执行；LinuxRepo 是 WSL 内的绝对路径。默认是 Linux 家目录下的 microduck-v7rc。多网卡或 VPN 时请明确指定手机可达的 Windows LAN IPv4。也可直接在 Ubuntu 终端执行两个 Shell 启动命令。

```
.\microduck-v7rc.ps1 -Action Serve -Distribution Ubuntu-24.04 -LinuxRepo /home/louis/microduck-v7rc -AdvertiseIP 192.168.1.20
.\microduck-v7rc.ps1 -Action Bridge -Distribution Ubuntu-24.04 -LinuxRepo /home/louis/microduck-v7rc -AdvertiseIP 192.168.1.20
```

## macOS 现有环境

保留现有工具和上游位置，先连接再执行 setup --check；本次更新不需要重装环境。新 Mac 需先安装 Xcode Command Line Tools，再执行同一 setup。 新 Mac 还需要 CMake 和 pkg-config，可用已安装的 Homebrew 执行 brew install cmake pkg-config。示例 192.168.1.20 和 /home/louis 必须替换成自己的 IP 与路径。

```
scripts/link-workspace
scripts/setup --check
```

## 安装后检查

doctor 显示平台、对外 IP、IPC socket 和图形环境。多网卡、VPN 或 WSL 显示错误 IP 时指定 MICRODUCK_ADVERTISE_IP；这只修改给 APP 的显示 IP，不修改路由或防火墙。更换 IP 后，APP 控制和相机都需更新；更换手机来源 IP 后重启桥接。

```
scripts/microduck-sim doctor
microduck_rl/.venv/bin/python -m unittest discover -s tests -v

MICRODUCK_ADVERTISE_IP=192.168.1.20 scripts/microduck-sim serve
```

## 启动与连接 — 1

模拟器开启后应站起，控制台显示 healthy。桥接收到有效回中封包后，左上显示 LIVE，摇杆反映原始输入。开启 APP 相机后 CAMERA ON、PEER 是手机 IP，TX FRAMES 增加。

```
scripts/microduck-sim serve
```

## 启动与连接 — 2

保持模拟器终端运行，另开第二个终端启动桥接。手机与电脑连接同一台 Wi-Fi 路由器；APP 的控制和相机 IP 均填写模拟器右上显示的 IPv4。

```
scripts/v7rc-bridge
```

## APP 设置与通道

IP 使用当前 LAN IPv4，不使用固定示例 IP。控制：Wi-Fi UDP／SRT／6188；相机：UDP／8800。1234 是电脑发送图像的源 Port，不是 APP 设置的目标 Port。

CH1 左右转向；CH2 前后；CH3 头部上下（反相）；CH4 头部左右。范围 1000–2000，中立 1500。启动、失联或重连后，四通道先回中才能重新启用控制。

## 验收清单

在目标电脑依次确认：站立／健康 → 四通道回中 → 前后和转向 → 头部上下／左右 → 图像与方向 → 关闭后重开 → 停止封包后的中立保护。记录 OS、架构、GPU、IP、上游 commit 和实测结果。Linux 容器测试不替代桌面或手机验收，Windows 启动器语法检查也不替代真实 WSL 测试。

## 来源（查询日期：2026-11-06）

- [WSL installation](https://learn.microsoft.com/en-us/windows/wsl/install)
- [WSLg](https://learn.microsoft.com/en-us/windows/wsl/tutorials/gui-apps)
- [WSL networking / mirrored](https://learn.microsoft.com/en-us/windows/wsl/networking)
- [Hyper-V firewall](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/hyper-v-firewall)
- [MuJoCo](https://github.com/google-deepmind/mujoco)
