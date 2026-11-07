# 安裝指引

[繁體中文](INSTALL.zh-TW.md) | [简体中文](INSTALL.zh-CN.md) | [English](INSTALL.en.md) | [日本語](INSTALL.ja.md)

macOS Apple Silicon 已完成本機與手機控制／影像驗收。Linux 提供原生安裝與啟動，隔離容器測試另列於驗證紀錄；實際桌面、GPU 與手機網路仍待目標機驗收。Windows 11 使用 WSL2 Ubuntu＋WSLg，提供 PowerShell 啟動器；不是原生 Windows robotd，Windows 目標機仍待驗收。

## 下載與安裝

**目前版本: `0.1.0-preview.2`** · [GitHub Release](https://github.com/v7rc/microduck-v7rc/releases/tag/v0.1.0-preview.2)

| 平台 | 安裝包 | 校驗檔 |
| --- | --- | --- |
| macOS 13+ · Apple Silicon / Intel | [MicroduckV7RC-0.1.0-preview.2-macOS-universal.dmg](https://github.com/v7rc/microduck-v7rc/releases/download/v0.1.0-preview.2/MicroduckV7RC-0.1.0-preview.2-macOS-universal.dmg) | [SHA256](https://github.com/v7rc/microduck-v7rc/releases/download/v0.1.0-preview.2/MicroduckV7RC-0.1.0-preview.2-macOS-universal.dmg.sha256) |
| Windows 11 x64 · WSL2 Ubuntu | [MicroduckV7RC-0.1.0-preview.2-Windows-x64.exe](https://github.com/v7rc/microduck-v7rc/releases/download/v0.1.0-preview.2/MicroduckV7RC-0.1.0-preview.2-Windows-x64.exe) | [SHA256](https://github.com/v7rc/microduck-v7rc/releases/download/v0.1.0-preview.2/MicroduckV7RC-0.1.0-preview.2-Windows-x64.exe.sha256) |

下載後開啟安裝包，檢查環境並確認安裝；完成後從桌面圖示啟動。Repo 已公開，可直接下載 Release 安裝包，無須登入 GitHub。

Mac 已完成本機安裝、桌面啟動及 V7RC 控制／影像驗收；Windows 已通過建置與自我檢查，完整 WSL2 安裝與手機操作仍待 Windows 實機驗收。

## 圖形安裝包與桌面啟動

從 GitHub Release 下載目前版本的未簽署測試版。Mac 使用 macOS 13 以上的 universal DMG；Windows 使用 Windows 11 x64 EXE，內含 .NET 執行環境，模擬器仍在 WSL2 Ubuntu 執行。這是網路安裝程式，第一次需要網路與約 20 GB 可用空間，不是離線的完整模擬器。

Mac：開啟 DMG 裡的 Microduck V7RC App，選擇語言並按「檢查環境」。安裝計畫會列出缺少的 Apple 開發工具、Homebrew／CMake／pkg-config，以及固定版本的上游、Rust、Python 與依賴。按「安裝／修復」並確認後才開始下載，請跟著終端機完成系統對話框與密碼操作。程式只在所有步驟成功後寫入完成狀態，並複製 App 到使用者 Applications、建立桌面啟動圖示。

Windows：開啟 EXE，先檢查環境並確認安裝。若缺少 WSL／Ubuntu，會請求系統安裝；需要重新開機時請完成後重開安裝程式。先在 Ubuntu 完成一般 Linux 使用者初始化，再按安裝；Linux 系統套件安裝可能要求 sudo 密碼。成功後桌面圖示會啟動模擬器與橋接，不會自動關閉其他 WSL 發行版或修改防火牆。手機連線仍須依前述 mirrored networking 與窄範圍 UDP 規則設定。

桌面圖示會自動啟動已完成的安裝，並保留終端機顯示下載、編譯與執行訊息。初次安裝會先編譯 runtime 並取得策略；之後可由同一圖示啟動。若研究版或其他程式占用 6188／8800／1234／7801，會停止並提示，不會自動停止別的專案。停止可使用視窗中的「停止模擬器」或關閉啟動終端機。

目前是未簽署／未公證測試版，系統可能顯示發行者或信任提示；正式部署應使用組織簽章。Mac 預設資料位於 ~/Library/Application Support/MicroduckV7RC；Windows 啟動器位於 %LocalAppData%/Programs/MicroduckV7RC，模擬資料位於 Ubuntu 的 ~/.local/share/microduck-v7rc。版本目錄彼此分開，既有研究 Repo 不會被搬移或覆寫。

## 前置條件

建議 Ubuntu 24.04 桌面／WSL2 Ubuntu-24.04；Linux x86_64 或 aarch64。需 Git、curl、C/C++ 工具鏈、CMake、pkg-config、OpenSSL／udev／ALSA 開發套件與 OpenGL／EGL。桌面需要可用的圖形驅動與 DISPLAY／Wayland；無視窗運算仍須依相機需求配置 EGL。這是單機模擬與推論安裝，不是 GPU 訓練環境。

## Linux 安裝

以下系統套件安裝需管理員權限；setup 不會自行執行 sudo，也不會調整防火牆。

```
sudo apt-get update
sudo apt-get install -y git curl python3 build-essential cmake pkg-config \
  libssl-dev libudev-dev libasound2-dev libgl1 libegl1 libgl1-mesa-dri libglfw3
```

## 從空環境取得整合 Repo

setup 下載專案內 uv 0.13.7、Rust 1.94.1 與 Python 3.12.16，依版本清單 clone 上游並套用補丁，再以上游 uv.lock 安裝依賴。第一次下載與 Rust 編譯可能需較長時間及數 GB 空間。若現有上游 HEAD 不符會停止，不會 reset、覆寫使用者變更或停止其他專案。首次啟動會下載官方策略；網路需能存取 GitHub、Rust、PyPI 與 Hugging Face。

```
git clone https://github.com/v7rc/microduck-v7rc.git
cd microduck-v7rc
scripts/setup --check
scripts/setup
```

## Windows 11／WSL2 安裝

建議 Windows 11 22H2 以上，啟用虛擬化，使用最新 WSL2 與 GPU 驅動。先在管理員 PowerShell 安裝 Ubuntu-24.04，依提示重新啟動，再於 Ubuntu 終端機依 Linux 步驟安裝。Repo 放在 Linux 家目錄，不要共用 Windows 的 Python .venv 或從 /mnt/c 執行。WSLg 提供模擬器視窗。

```
wsl --install -d Ubuntu-24.04
wsl --update
```

## Windows 手機 UDP 網路

手機需要能主動連進 WSL。使用 mirrored networking，並在既有 %UserProfile%\.wslconfig 的 [wsl2] 區段加入設定，保留其他設定。先儲存所有 WSL 工作再執行 wsl --shutdown（會停止所有發行版），然後重開 Ubuntu。若仍被擋，只新增 UDP 6188／8800 的必要規則；不要關閉整個防火牆。

```
[wsl2]
networkingMode=mirrored
```

## Windows 手機 UDP 網路 / PowerShell

手機需要能主動連進 WSL。使用 mirrored networking，並在既有 %UserProfile%\.wslconfig 的 [wsl2] 區段加入設定，保留其他設定。先儲存所有 WSL 工作再執行 wsl --shutdown（會停止所有發行版），然後重開 Ubuntu。若仍被擋，只新增 UDP 6188／8800 的必要規則；不要關閉整個防火牆。

```
wsl --shutdown
```

## Windows 手機 UDP 網路 / Firewall

Windows 防火牆命令需在管理員 PowerShell 手動執行，僅於尚未有等效規則且目前網路為可信任的 Private profile 時使用。Hyper-V 的 WSL 規則另列；命令不存在時先更新 Windows／WSL。Linux 則依實際啟用的防火牆放行手機到 6188／8800。

```
New-NetFirewallRule -DisplayName "Microduck V7RC UDP" -Direction Inbound -Action Allow -Protocol UDP -LocalPort 6188,8800 -Profile Private -RemoteAddress LocalSubnet
New-NetFirewallHyperVRule -Name "MicroduckV7RC" -DisplayName "Microduck V7RC WSL" -Direction Inbound -VMCreatorId '{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}' -Protocol UDP -LocalPorts 6188,8800 -Action Allow
```

## 可選的 PowerShell 啟動器

可從 Windows 可讀到的本 Repo windows/ 目錄執行；LinuxRepo 是 WSL 內的絕對路徑。預設路徑為 Linux 家目錄下的 microduck-v7rc。若多張網卡或 VPN，明確指定手機可達的 Windows LAN IPv4。主要使用方式仍可直接在 Ubuntu 終端機執行兩個 Shell 啟動命令。

```
.\microduck-v7rc.ps1 -Action Serve -Distribution Ubuntu-24.04 -LinuxRepo /home/louis/microduck-v7rc -AdvertiseIP 192.168.1.20
.\microduck-v7rc.ps1 -Action Bridge -Distribution Ubuntu-24.04 -LinuxRepo /home/louis/microduck-v7rc -AdvertiseIP 192.168.1.20
```

## macOS 既有環境

保留既有工具和上游位置，先連結再執行 setup --check；不需要為本次更新重裝整個環境。空白 Mac 需先安裝 Xcode Command Line Tools，再執行相同 setup。 新 Mac 也需要 CMake 與 pkg-config；可在已安裝的 Homebrew 使用 brew install cmake pkg-config。範例 192.168.1.20 與 /home/louis 必須改成自己的 IP 與路徑。

```
scripts/link-workspace
scripts/setup --check
```

## 安裝後檢查

doctor 顯示平台、對外 IP、IPC socket 與圖形環境。多網卡、VPN 或 WSL 顯示錯誤 IP 時，指定 MICRODUCK_ADVERTISE_IP；這只調整顯示給 APP 的 IP，不會修改路由或防火牆。更換 IP 後，APP 控制與相機都要更新；換手機來源 IP 後重啟橋接。

```
scripts/microduck-sim doctor
microduck_rl/.venv/bin/python -m unittest discover -s tests -v

MICRODUCK_ADVERTISE_IP=192.168.1.20 scripts/microduck-sim serve
```

## 啟動與連線 — 1

開啟模擬器後應站起，主控台顯示 healthy。控制橋接收到有效回中封包後，左上變 LIVE，搖桿反映原始輸入。開啟 APP 相機後 CAMERA ON、PEER 為手機 IP，TX FRAMES 增加。

```
scripts/microduck-sim serve
```

## 啟動與連線 — 2

保留模擬器終端機，另開第二個終端機啟動橋接。手機與電腦使用同一台 Wi-Fi 路由器；APP 的控制與相機 IP 都填模擬器右上顯示的 IPv4。

```
scripts/v7rc-bridge
```

## APP 設定與通道

IP 使用目前的 LAN IPv4，不使用固定範例 IP。控制：Wi-Fi UDP／SRT／6188；相機：UDP／8800。1234 是電腦的影像送出來源 Port，不是 APP 設定的目的 Port。

CH1 左右轉向；CH2 前後；CH3 頭部上下（反相）；CH4 頭部左右。範圍 1000–2000，中立 1500。啟動、失聯或重連後，四通道先回中才會重新啟用控制。

## 驗收清單

在目標電腦依序確認：站立／健康 → 四通道回中 → 前後與轉向 → 頭部上下／左右 → 影像與方向 → 關閉再開 → 停止封包後中立保護。記錄 OS、架構、GPU、IP、上游 commit 與實測結果。Linux 容器測試不能替代桌面或手機驗收；Windows 啟動器語法檢查也不能替代真實 WSL 測試。

## 來源（查閱日期：2026-11-06）

- [WSL installation](https://learn.microsoft.com/en-us/windows/wsl/install)
- [WSLg](https://learn.microsoft.com/en-us/windows/wsl/tutorials/gui-apps)
- [WSL networking / mirrored](https://learn.microsoft.com/en-us/windows/wsl/networking)
- [Hyper-V firewall](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/hyper-v-firewall)
- [MuJoCo](https://github.com/google-deepmind/mujoco)
