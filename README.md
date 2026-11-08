# Microduck × V7RC 整合

[繁體中文](README.md) | [简体中文](README.zh-CN.md) | [English](README.en.md) | [日本語](README.ja.md)

透過 V7RC APP，以 Wi-Fi UDP 控制 Microduck 模擬器，並回傳 640×360 頭部相機影像。包含 SRT 四通道橋接、接收 FPS、雙搖桿、連線 IP／Port 與相機送出影格 HUD。

## 控制台與操作比較

從桌面圖示開啟控制台。選擇「自由練習」或「S 型迷宮」，再選鍵盤、V7RC APP 或自訂 UDP 控制程式。面板可啟動、停止、回到起點，也會顯示手機連線資訊與即時狀態。碼錶可開始、停止、歸零，時間以 `分:秒.毫秒` 同步顯示在面板和模擬器。

控制台從 GitHub Releases 查詢程式、場景、ONNX 步態模型和控制設定。支援 Schema 2 的版本可單獨更新控制設定；單軸和斜推使用各自的右轉曲線。

控制台新增「控制曲線」和「步態模型」選單。在同一場景可選內建曲線、線性曲線或先前下載的設定，也可切換相容的 ONNX 模型。選好後按「啟動」或「回到起點」，面板會顯示實際套用的組合。模擬器左下角會顯示程式版號。Mac 和 Windows 安裝器提供繁體中文、簡體中文、英文和日文選擇；安裝器會記住語言選擇。控制台改用獨立的 MuJoCo 內部連接埠，修正這台 Mac 上自由練習啟動後無法穩定轉向的問題。

## 九乘六格迷宮

使用 preview.8 控制台。先停止模擬器，再按「檢查更新」並安裝 preview.10 場景包。從場景選單選「九乘六格迷宮」，然後按「啟動」。

Microduck 從左下角橘色 START 格出發，右上角橘色 END 格是終點。場內地面為白色，左上角已補牆。格距為 300 mm（牆中心線到中心線），牆厚 3 mm、牆高 400 mm。場地外緣為 2703 × 1803 mm，約 4.87 m²，支架與底座另計。

[場景更新](https://github.com/v7rc/microduck-v7rc/releases/tag/v0.1.0-preview.10) · [施工尺寸與牆段座標（繁中）](docs/microduck/grid-maze-build.md)

## 授權與商用

- MuJoCo 引擎採 Apache-2.0，允許商用。現有安裝器在安裝時下載 MuJoCo。如果重新封裝或散布 MuJoCo，應隨附授權全文並保留適用的第三方聲明。 [MuJoCo LICENSE](https://raw.githubusercontent.com/google-deepmind/mujoco/3.10.0/LICENSE)
- Pollen Robotics 指定的 Microduck STL 網格採 CC BY-NC-SA 4.0。商用這些網格須另取得相應授權，或改用具商用授權的素材。 [LICENSE-MODELS.md](https://github.com/pollen-robotics/microduck_rl/blob/bae39f5900b318f7e87fc485c30a31213cfa14eb/LICENSE-MODELS.md)
- 安裝時下載的官方 ONNX 策略權重 microduck-policies v8 在上游標示為 Apache-2.0。其他權重依各自的授權。 [microduck-policies v8](https://huggingface.co/pollen-robotics/microduck-policies/tree/v8)
- 本 Repo 自有整合程式與場景的正式授權尚待決定。第三方授權只適用於各自涵蓋的內容。

## 下載與安裝

**目前版本: `0.1.0-preview.8`** · [GitHub Release](https://github.com/v7rc/microduck-v7rc/releases/tag/v0.1.0-preview.8)

| 平台 | 安裝包 | 校驗檔 |
| --- | --- | --- |
| macOS 13+ · Apple Silicon / Intel | [MicroduckV7RC-0.1.0-preview.8-macOS-universal.dmg](https://github.com/v7rc/microduck-v7rc/releases/download/v0.1.0-preview.8/MicroduckV7RC-0.1.0-preview.8-macOS-universal.dmg) | [SHA256](https://github.com/v7rc/microduck-v7rc/releases/download/v0.1.0-preview.8/MicroduckV7RC-0.1.0-preview.8-macOS-universal.dmg.sha256) |
| Windows 11 x64 · WSL2 Ubuntu | [MicroduckV7RC-0.1.0-preview.8-Windows-x64.exe](https://github.com/v7rc/microduck-v7rc/releases/download/v0.1.0-preview.8/MicroduckV7RC-0.1.0-preview.8-Windows-x64.exe) | [SHA256](https://github.com/v7rc/microduck-v7rc/releases/download/v0.1.0-preview.8/MicroduckV7RC-0.1.0-preview.8-Windows-x64.exe.sha256) |

下載後開啟安裝包，檢查環境並確認安裝；完成後從桌面圖示啟動。Repo 已公開，可直接下載 Release 安裝包，無須登入 GitHub。

preview.2 已完成 Mac 安裝、桌面啟動及 V7RC 控制與影像驗收。preview.3 的比例控制校正已完成 Mac 模擬器 54 輪量測。Windows 的完整 WSL2 安裝與手機操作仍待實機驗收。

## 圖形安裝包與桌面啟動

從 GitHub Release 下載目前版本的未簽署測試版。Mac 使用 macOS 13 以上的 universal DMG；Windows 使用 Windows 11 x64 EXE，內含 .NET 執行環境，模擬器仍在 WSL2 Ubuntu 執行。這是網路安裝程式，第一次需要網路與約 20 GB 可用空間，不是離線的完整模擬器。

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

個人熱點模式曾收不到 iOS 相機訂閱；同一 Wi-Fi 下已驗收正常。低速步行、速度追蹤及直線精度有上游限制，不能以收到 UDP 推定動作精度。CAMERA ON 與 TX FRAMES 代表訂閱有效／主機送出，仍須實際確認 APP 顯示。

## 文件與測試

- [安裝指引](docs/INSTALL.zh-TW.md)
- [操作指引 — HTML](docs/how-to.html#zh-TW)
- [Validation](docs/validation/2026-11-06-cross-platform.md)

```sh
microduck_rl/.venv/bin/python -m unittest discover -s tests -v
```
