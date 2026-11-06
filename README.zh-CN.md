# Microduck × V7RC 集成

[繁體中文](README.md) | [简体中文](README.zh-CN.md) | [English](README.en.md) | [日本語](README.ja.md)

通过 V7RC APP，以 Wi-Fi UDP 控制 Microduck 模拟器，并回传 640×360 头部相机图像。包含 SRT 四通道桥接、接收 FPS、双摇杆、连接 IP／Port 与相机发送帧 HUD。

## 图形安装包与桌面启动

从安装包 workflow 下载未签名测试版（GitHub artifact 需要登录，保留 30 天）。Mac 使用 macOS 13 以上的 universal DMG，Windows 使用 Windows 11 x64 EXE，内含 .NET 运行时；模拟器仍在 WSL2 Ubuntu 中执行。这是联网安装程序，首次需要网络及约 20 GB 空间，并非完整离线模拟器。

[Installer downloads](https://github.com/v7rc/microduck-v7rc/actions/workflows/installers.yml)

## 平台与验证范围

macOS Apple Silicon 已完成本机与手机控制／图像验收。Linux 提供原生安装与启动，隔离容器测试见验证记录；实际桌面、GPU 与手机网络仍待目标机验收。Windows 11 使用 WSL2 Ubuntu＋WSLg，提供 PowerShell 启动器；并非原生 Windows robotd，Windows 目标机仍待验收。

## 快速开始

新环境请先完成安装指南。Louis 现有 Mac 环境可执行 scripts/link-workspace 复用同级上游与工具；此命令不适用于尚未安装的新机器。以下相对命令均从集成 Repo 根目录执行。

```
scripts/microduck-sim serve
```

保持模拟器终端运行，另开第二个终端启动桥接。手机与电脑连接同一台 Wi-Fi 路由器；APP 的控制和相机 IP 均填写模拟器右上显示的 IPv4。

```sh
scripts/v7rc-bridge
```

## APP 设置与通道

IP 使用当前 LAN IPv4，不使用固定示例 IP。控制：Wi-Fi UDP／SRT／6188；相机：UDP／8800。1234 是电脑发送图像的源 Port，不是 APP 设置的目标 Port。

CH1 左右转向；CH2 前后；CH3 头部上下（反相）；CH4 头部左右。范围 1000–2000，中立 1500。启动、失联或重连后，四通道先回中才能重新启用控制。

## 源代码与上游

bridge/ 包含控制、相机、HUD 和平台公共程序；scripts/ 包含安装和启动；windows/ 包含 WSL 启动器；tests/ 包含测试。upstream-revisions.json 固定上游 commit。上游 Repo、.venv、.tools、.runtime 均不提交；本机依赖可为 Repo 内 clone 或指向现有环境的 symlink。上游 runtime 只有两行启动补丁，不修改模拟物理或行走策略。

## 已知限制

个人热点模式曾无法收到 iOS 相机订阅；同一 Wi-Fi 下已验收正常。低速步行、速度跟踪和直线精度有上游限制，不能以收到 UDP 推断动作精度。CAMERA ON 和 TX FRAMES 表示订阅有效／主机发送，仍须实际确认 APP 显示。模型许可证请阅读上游 LICENSE-MODELS.md（含 CC BY-NC-SA 4.0）。

## 文档与测试

- [安装指南](docs/INSTALL.zh-CN.md)
- [操作指南 — HTML](docs/how-to.html#zh-CN)
- [Validation](docs/validation/2026-11-06-cross-platform.md)

```sh
microduck_rl/.venv/bin/python -m unittest discover -s tests -v
```
