# 跨平台啟動與四語文件：實作及驗證

本次以既有 `53699e4` 為開發基準，保留 upstream-revisions.json 的兩個上游 commit 與兩行 runtime 補丁。此次修改仍在整合 Repo，不修改模擬器核心或行走策略。

## 實作

- Linux 原生與 Windows 11／WSL2 Ubuntu 共用 POSIX 啟動。Windows 提供 `windows/microduck-v7rc.ps1`，不是原生 Windows robotd；上游仍依賴 Unix IPC。
- `bridge/platform_support.py` 統一路徑與 IP。既有 Mac 自己擁有的 `/tmp/microduck-m4-UID` 保留；其他 checkout 依絕對路徑 hash 建立短連結，禁止覆寫其他工作區。腳本與所有控制驗證工具使用同一 IPC socket 推導。
- Linux 使用 `ip -j`，Mac 使用 ipconfig；已有手機來源時依路由選本機 IP，也可用 `MICRODUCK_ADVERTISE_IP` 明確指定。這不變更實際網路路由。
- `scripts/setup` 安裝專案內工具、固定上游 commit、以保護檢查套用補丁及執行 locked uv sync。`--check` 不下載、不改 Git 或連結。不同 HEAD 會停止；patch 可重跑，不 reset 或覆寫既有工作。
- 四語 README、四語安裝指引及單一離線四語 `docs/how-to.html`；由 `scripts/generate-docs.py` 維護。語言為繁中、簡中、英文、日文。依使用者確認，本次不翻譯既有研究／歷史測試紀錄及原始輸出。

## 已執行的檢查

| 檢查 | 結果與範圍 |
| --- | --- |
| Mac Python 3.12 測試 | 23 項通過；包含 socket、相機 JPEG、失聯中立、路徑所有權、Linux NIC 選擇、安裝補丁重跑與不重設上游 |
| Linux 容器 | Docker Linux arm64、Python 3.12；23 項通過。MuJoCo 3.10.0、NumPy 2.4.1、Pillow 12.2.0；真實 UDP／Unix socket 在容器內運作 |
| PowerShell AST | 既有 PowerShell 7.4 Linux amd64 容器解析通過 |
| PowerShell 行為 | 模擬 wsl.exe 測試，含空白 Repo 路徑、發行版、對外 IPv4 與 Serve 參數邊界通過；未啟動真正 WSL |
| Shell／Python | sh -n、py_compile、setup --check 與 doctor 通過 |
| uv 固定安裝入口 | https://astral.sh/uv/0.13.7/install.sh 回覆 HTTP 200；沒有在既有 Mac 上重裝工具 |
| HTML | 瀏覽器實際切換四種語言，確認只顯示選定語言；1280 px 預設視窗無整頁水平溢出。內容不依賴外部字型／CDN，離線時複製按鈕有手動複製提示 |
| Mac 實際模擬器 | 新共用啟動流程起身成功、healthy、50/50 Hz、0 missed；即時倍率實測 1.00x。這次未重新跑完整行走方向及手機影像人工驗收 |

證據：[Mac 測試](evidence/cross-platform/macos-tests.txt)、[Linux 測試](evidence/cross-platform/linux-tests.txt)、[PowerShell 語法](evidence/cross-platform/powershell-parse.txt)、[參數測試](evidence/cross-platform/powershell-arguments.txt)、[HTML 預覽](evidence/cross-platform/how-to-preview.png)。

## 尚待目標機驗收

沒有可操作的 Windows 主機或 Linux 桌面，因此尚未在那些主機完成上游整套首次下載／Rust 編譯／GPU 視窗／手機 LAN 連線。Linux 容器只驗證隔離橋接與平台程式，不代表完整 robotd 堆疊或 GPU 行為通過；PowerShell 語法與假程序測試也不能代替真正 WSL。CI workflow 已加入 Linux／Mac 單元測試及 Windows 啟動器檢查，但未推送或觸發遠端 CI，不能稱為 CI 通過。

請在目標機依四語安裝與操作指引完成站立、行走／轉向、頭部、影像與 watchdog 驗收。Windows 必須另外確認 WSLg、mirrored networking、Windows／Hyper-V 的窄範圍 UDP 6188／8800 規則。實體 Microduck 與 GPU 訓練仍不在此範圍。

## 來源

- 上游 microduck robotd／robotctl 的 Unix IPC 與 duck-sim 的 Linux／Mac 啟動，commit 同 upstream-revisions.json。
- [Microsoft WSL networking](https://learn.microsoft.com/en-us/windows/wsl/networking)
- [WSLg](https://learn.microsoft.com/en-us/windows/wsl/tutorials/gui-apps)
- [Hyper-V firewall](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/hyper-v-firewall)
