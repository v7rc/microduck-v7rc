# Microduck × V7RC 集成

[繁體中文](README.md) | [简体中文](README.zh-CN.md) | [English](README.en.md) | [日本語](README.ja.md)

通过 V7RC APP，以 Wi-Fi UDP 控制 Microduck 模拟器，并回传 640×360 头部相机图像。包含 SRT 四通道桥接、接收 FPS、双摇杆、连接 IP／Port 与相机发送帧 HUD。

## 控制台与操作对比

从桌面图标打开控制台，选择自由练习或 S 型迷宫，再使用键盘、V7RC APP 或自定义 UDP 程序控制。面板支持启动、停止、回到起点、连接状态和同步秒表（`分:秒.毫秒`）。程序、场景、ONNX 模型与控制配置通过 GitHub Releases 更新；支持 Schema 2 的版本可单独更新控制配置。

控制台加入了控制曲线和步态模型下拉菜单。选择后按启动或回到起点，可在同一场景对比内置曲线、线性曲线、已下载配置和兼容的 ONNX 模型。模拟器左下角显示程序版本。Mac 和 Windows 安装程序可切换繁体中文、简体中文、英文和日文，并记住选择。控制台改用独立的 MuJoCo 内部端口，解决在受测 Mac 上自由练习启动后转向不稳定的问题。

## 九乘六格迷宫

使用 preview.8 控制台。先停止模拟器，再点击「检查更新」并安装 preview.10 场景包。从场景列表选择「九乘六格迷宫」，然后点击「启动」。

Microduck 从左下角橙色 START 格出发，右上角橙色 END 格是终点。场地地面为白色，左上角已补墙。格距为 300 mm（按墙体中心线计算），墙厚 3 mm、墙高 400 mm。场地外缘为 2703 × 1803 mm，约 4.87 m²，支架与底座另计。

[场景更新](https://github.com/v7rc/microduck-v7rc/releases/tag/v0.1.0-preview.10) · [施工尺寸与墙段坐标（繁体中文）](docs/microduck/grid-maze-build.md)

## 授权与商用

- MuJoCo 引擎采用 Apache-2.0，允许商用。现有安装程序在安装时下载 MuJoCo。如果重新打包或分发 MuJoCo，应附上许可证全文并保留适用的第三方声明。 [MuJoCo LICENSE](https://raw.githubusercontent.com/google-deepmind/mujoco/3.10.0/LICENSE)
- Pollen Robotics 指定的 Microduck STL 网格采用 CC BY-NC-SA 4.0。商用这些网格须另行取得相应授权，或使用具有商用许可的替代素材。 [LICENSE-MODELS.md](https://github.com/pollen-robotics/microduck_rl/blob/bae39f5900b318f7e87fc485c30a31213cfa14eb/LICENSE-MODELS.md)
- 安装时下载的官方 ONNX 策略权重 microduck-policies v8 在上游标注为 Apache-2.0。其他权重遵循各自的许可。 [microduck-policies v8](https://huggingface.co/pollen-robotics/microduck-policies/tree/v8)
- 本仓库自有集成代码和场景的正式许可证尚待确定。第三方许可仅适用于各自涵盖的内容。

## 下载与安装

**当前版本: `0.1.0-preview.11`** · [GitHub Release](https://github.com/v7rc/microduck-v7rc/releases/tag/v0.1.0-preview.11)

| 平台 | 安装包 | 校验文件 |
| --- | --- | --- |
| macOS 13+ · Apple Silicon / Intel | [MicroduckV7RC-0.1.0-preview.11-macOS-universal.dmg](https://github.com/v7rc/microduck-v7rc/releases/download/v0.1.0-preview.11/MicroduckV7RC-0.1.0-preview.11-macOS-universal.dmg) | [SHA256](https://github.com/v7rc/microduck-v7rc/releases/download/v0.1.0-preview.11/MicroduckV7RC-0.1.0-preview.11-macOS-universal.dmg.sha256) |
| Windows 11 x64 · WSL2 Ubuntu | [MicroduckV7RC-0.1.0-preview.11-Windows-x64.exe](https://github.com/v7rc/microduck-v7rc/releases/download/v0.1.0-preview.11/MicroduckV7RC-0.1.0-preview.11-Windows-x64.exe) | [SHA256](https://github.com/v7rc/microduck-v7rc/releases/download/v0.1.0-preview.11/MicroduckV7RC-0.1.0-preview.11-Windows-x64.exe.sha256) |

下载后打开安装包，检查环境并确认安装；完成后从桌面图标启动。Repo 已公开，可直接下载 Release 安装包，无需登录 GitHub。

preview.2 已完成 Mac 安装、桌面启动及 V7RC 控制与影像验收。preview.3 的比例控制校正已完成 Mac 模拟器 54 轮测量。Windows 的完整 WSL2 安装与手机操作仍待实机验收。

## 图形安装包与桌面启动

从 GitHub Release 下载当前版本的未签名测试版。Mac 使用 macOS 13 以上的 universal DMG，Windows 使用 Windows 11 x64 EXE，内含 .NET 运行时；模拟器仍在 WSL2 Ubuntu 中执行。这是联网安装程序，首次需要网络及约 20 GB 空间，并非完整离线模拟器。

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

个人热点模式曾无法收到 iOS 相机订阅；同一 Wi-Fi 下已验收正常。低速步行、速度跟踪和直线精度有上游限制，不能以收到 UDP 推断动作精度。CAMERA ON 和 TX FRAMES 表示订阅有效／主机发送，仍须实际确认 APP 显示。

## 文档与测试

- [安装指南](docs/INSTALL.zh-CN.md)
- [操作指南 — HTML](docs/how-to.html#zh-CN)
- [Validation](docs/validation/2026-11-06-cross-platform.md)

```sh
microduck_rl/.venv/bin/python -m unittest discover -s tests -v
```
