# 四階段需求可行性評估

日期：2026-11-06。依據：上游文件與原始碼查閱；尚未安裝、啟動或完成 APP／GPU／實機測試。

後續進度：第一階段已實作，詳見 [本機模擬驗證結果與限制](../validation/2026-11-06-macos-simulator.md)。本篇以下保留搭建前的可行性評估，實際安裝狀態以後續驗證為準。

## 結論

四階段具備可執行的技術路徑。配置採 MacBook Pro M4 進行本機模擬與 V7RC 控制驗證，使用者日後提供的 RTX 5090 伺服器負責強化學習訓練。需要自行開發 V7RC 到 Microduck 的橋接程式；目前沒有已確認可直接使用的整合成品。

| 使用者需求 | 評估 | 首次通過條件 |
| --- | --- | --- |
| 本地搭建 Microduck 模擬器 | 官方有 CPU MuJoCo 與 daemon 模擬路徑，腳本有 macOS 處理 | 能載入既有策略、站立、前進、轉向，且模擬達到即時速度 |
| V7RC 控制模擬器 | 可開發；優先驗證同網段 Wi-Fi UDP 橋接 | APP 封包實際抵達 Mac，操控與回中符合預期，失聯輸入會逾時 |
| 訓練 Microduck | 官方 mjlab／MuJoCo Warp／PPO 流程需要 CUDA GPU | RTX 5090 上小規模訓練、checkpoint、恢復與 ONNX 匯出成功 |
| 訓練完成後由 V7RC 控制 | 可行，前提是策略保留對應命令契約 | 新策略在模擬中接受相同橋接輸入；實機另行部署及驗收 |

## 本地模擬路徑

官方 runtime 的 `scripts/duck-sim` 以真正的 `robotd` 連接 MuJoCo body，可經既有 JSON-RPC 控制介面操作。macOS 視窗由 `mjpython` 啟動；第一階段採一隻 duck、不啟用相機、非容器模式，減少依賴與負載。`boot` 的 systemd-nspawn 路徑屬 Linux，不能視為 macOS 原生啟動方法。

另一條較輕的基準路徑是 RL 倉庫 `scripts/infer_policy.py`，在 CPU MuJoCo 中載入 ONNX 並以鍵盤操控。可用來區分策略問題與 daemon 橋接問題，但其本身不等於完整機器人通訊環境。

重要版本差異：查閱時 RL `main` 的 pyproject 沒有 `duck-body` entry point；`develop` 有。因此完整 daemon 模擬應配對 runtime 與 RL develop 的已記錄版本，不能只 clone 兩個 main 就假設可啟動。RL 專案要求 Python 3.12，並包含額外相依套件，仍須在本機實際解依賴及啟動驗證。

macOS issue #498 曾有「選到走路策略但不移動」問題。後續留言指出舊策略配置是原因，回報修正後 M1 能走路；目前查閱的腳本也已選用 `velstand.onnx`。這是上游案例，尚未建立本機 M4 驗收證據。

## V7RC 控制路徑

V7RC 官方 Wi-Fi 範例使用 UDP 6188；範例 APP 目的地是 ESP32 AP 的廣播位址。本機方案提案改由手機與 Mac 位於相同 LAN，APP 目的位址設為 Mac LAN IP，橋接程式接收並解析控制封包。

APP 是否允許該版本的目的 IP／port 設定、單播是否送達、Wi-Fi client isolation 與系統網路權限仍需實測。若此路徑受限，再評估 BLE 接收端或外接相容接收板。模擬器不模擬實體 BLE radio，不能因為有模擬器就假設 APP 會直接發現裝置。

```text
手機 V7RC → Wi-Fi UDP → Mac 橋接程式
                         ↓ 解析、死區、限幅、輸入逾時
                       robot.move(vx, vy, vyaw)
                         ↓
                       robotd → ONNX 策略 → MuJoCo
```

`robot.move` 的方法及參數可在官方 `duck-sim` 的 drive 範例確認。該版本範例每秒重送 10 次，註解說明 intent 在 500 ms 後逾時。這些是特定上游版本行為，不代表 APP 實際封包頻率。橋接只能在收到新鮮 APP 輸入時維持命令，不能無限重送最後一筆封包，否則會抵銷 runtime 的逾時機制。

## 訓練與後續控制

訓練目標應先選「可追蹤速度命令的平地行走」。使用既有策略完成階段 1、2 後，再重訓同一類任務，比先訓練未知動作更容易驗證。

V7RC 提供高階控制意圖；策略依姿態、關節狀態及命令計算馬達動作。重新訓練須保留 observation／action layout、命令單位與範圍、策略時序、關節對應及正規化方式，才能沿用橋接。並非每個策略都接受速度命令；起身或踢球等策略需要對應的觸發與狀態管理。

官方建議透過 `scripts/export.py` 匯出 ONNX，將 observation normalizer 納入模型。匯出後先下載至 Mac 載入驗證，再進行實體機器人的 sim-to-real 驗收。模擬成功不自動代表實機穩定。

RTX 5090 伺服器可作為訓練端。建議使用 Linux、相容 NVIDIA driver、CUDA 版 PyTorch 與 MuJoCo Warp。PyTorch 已提供 Blackwell 支援，但必須實際確認所選 wheel、Warp 與 driver 組合，不能只以 `nvidia-smi` 成功作為訓練驗收。後續先檢查 GPU kernel、Warp 模擬、少量並行環境及 checkpoint／ONNX 全流程，再依顯存及吞吐量增加環境數，不預先承諾訓練時間。

## 來源與查閱版本

- Runtime `main`：`98ce17e4868ba9370713c4d11f3d934e5a1b7687`。
  - [模擬器文件](https://github.com/pollen-robotics/microduck/blob/98ce17e4868ba9370713c4d11f3d934e5a1b7687/docs/robot/simulation.md)
  - [啟動與 drive 原始碼](https://github.com/pollen-robotics/microduck/blob/98ce17e4868ba9370713c4d11f3d934e5a1b7687/scripts/duck-sim)
  - [macOS issue #498 與後續留言](https://github.com/pollen-robotics/microduck/issues/498)
- RL `main`：`1e79c29c97d8b38aee9eefde77a545860ba7658e`。
  - [訓練、推論、匯出說明](https://github.com/pollen-robotics/microduck_rl/blob/1e79c29c97d8b38aee9eefde77a545860ba7658e/README.md)
- RL `develop`：`bae39f5900b318f7e87fc485c30a31213cfa14eb`。
  - [依賴與 duck-body entry point](https://github.com/pollen-robotics/microduck_rl/blob/bae39f5900b318f7e87fc485c30a31213cfa14eb/pyproject.toml)
- V7RC Wi-Fi `main`：`fd4b679f60209838d6e4c53c39144aba599e9cc6`。
  - [Wi-Fi 範例](https://github.com/v7rc/V7RC-ESP32-WIFI-LIB/blob/fd4b679f60209838d6e4c53c39144aba599e9cc6/examples/V7RC_WIFI/V7RC_WIFI.ino)
  - [UDP 接收實作](https://github.com/v7rc/V7RC-ESP32-WIFI-LIB/blob/fd4b679f60209838d6e4c53c39144aba599e9cc6/src/V7RC_WIFI.cpp)
- [PyTorch 官方 Blackwell／CUDA 12.8 支援公告](https://pytorch.org/blog/pytorch-2-7/)。這是支援背景，不是建議將專案降版至 2.7。
- [Warp 1.12 安裝文件](https://nvidia.github.io/warp/v1.12/user_guide/installation.html)。實際 driver 要求仍須依鎖定的 wheel 與 RTX 5090 核對。
