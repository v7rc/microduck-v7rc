# Microduck × V7RC 整合

[繁體中文](README.md) | [简体中文](README.zh-CN.md) | [English](README.en.md) | [日本語](README.ja.md)

透過 V7RC APP，以 Wi-Fi UDP 控制 Microduck 模擬器，並回傳 640×360 頭部相機影像。包含 SRT 四通道橋接、接收 FPS、雙搖桿、連線 IP／Port 與相機送出影格 HUD。

## 圖形安裝包與桌面啟動

從安裝包 workflow 下載未簽署測試版（GitHub artifact 需登入，保留 30 天）。Mac 使用 macOS 13 以上的 universal DMG；Windows 使用 Windows 11 x64 EXE，內含 .NET 執行環境，模擬器仍在 WSL2 Ubuntu 執行。這是網路安裝程式，第一次需要網路與約 20 GB 可用空間，不是離線的完整模擬器。

[Installer downloads](https://github.com/v7rc/microduck-v7rc/actions/workflows/installers.yml)

## 平台與驗證範圍

macOS Apple Silicon 已完成本機與手機控制／影像驗收。Linux 提供原生安裝與啟動，隔離容器測試另列於驗證紀錄；實際桌面、GPU 與手機網路仍待目標機驗收。Windows 11 使用 WSL2 Ubuntu＋WSLg，提供 PowerShell 啟動器；不是原生 Windows robotd，Windows 目標機仍待驗收。

## 快速開始

新環境先完成安裝指引。既有 Louis Mac 環境可執行 scripts/link-workspace 重用同層上游與工具；此命令不適用尚未安裝的全新機器。所有下列相對命令均從整合 Repo 根目錄執行。

```
scripts/microduck-sim serve
```

保留模擬器終端機，另開第二個終端機啟動橋接。手機與電腦使用同一台 Wi-Fi 路由器；APP 的控制與相機 IP 都填模擬器右上顯示的 IPv4。

```sh
scripts/v7rc-bridge
```

## APP 設定與通道

IP 使用目前的 LAN IPv4，不使用固定範例 IP。控制：Wi-Fi UDP／SRT／6188；相機：UDP／8800。1234 是電腦的影像送出來源 Port，不是 APP 設定的目的 Port。

CH1 左右轉向；CH2 前後；CH3 頭部上下（反相）；CH4 頭部左右。範圍 1000–2000，中立 1500。啟動、失聯或重連後，四通道先回中才會重新啟用控制。

## 原始碼與上游

bridge/ 為控制、相機、HUD 與平台共用程式；scripts/ 為安裝及啟動；windows/ 為 WSL 啟動器；tests/ 為測試。upstream-revisions.json 固定上游 commit。上游 Repo、.venv、.tools、.runtime 均不提交；本機依賴可以是 Repo 內的 clone 或連到既有環境的 symlink。上游 runtime 只有兩行啟動補丁；不修改模擬物理或行走策略。

## 已知限制

個人熱點模式曾收不到 iOS 相機訂閱；同一 Wi-Fi 下已驗收正常。低速步行、速度追蹤及直線精度有上游限制，不能以收到 UDP 推定動作精度。CAMERA ON 與 TX FRAMES 代表訂閱有效／主機送出，仍須實際確認 APP 顯示。模型授權請閱讀上游 LICENSE-MODELS.md（含 CC BY-NC-SA 4.0）。

## 文件與測試

- [安裝指引](docs/INSTALL.zh-TW.md)
- [操作指引 — HTML](docs/how-to.html#zh-TW)
- [Validation](docs/validation/2026-11-06-cross-platform.md)

```sh
microduck_rl/.venv/bin/python -m unittest discover -s tests -v
```
