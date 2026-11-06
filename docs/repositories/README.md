# 倉庫登錄

查閱／取得日期：2026-11-06。以下保留各自獨立 Git 歷史；本機模擬使用已記錄的 commit。

| 上游來源 | 用途 | 建議子目錄 | 本機狀態 |
| --- | --- | --- | --- |
| [pollen-robotics/microduck](https://github.com/pollen-robotics/microduck) | 機器人控制與通訊架構、真實 daemons | `microduck/` | 已 clone、編譯，本機 main |
| [pollen-robotics/microduck_rl](https://github.com/pollen-robotics/microduck_rl) | CPU MuJoCo body／ONNX 推論；後續 GPU 訓練 | `microduck_rl/` | 已 clone、安裝，本機 develop |
| [v7rc/V7RC-Protocol](https://github.com/v7rc/V7RC-Protocol) | V7RC 公開命令協定 | `V7RC-Protocol/` | 未 clone |

新增／拉取後，記錄實際相對路徑、remote URL、branch/tag、完整 commit SHA、取得日期及 LICENSE／資產授權。子目錄名稱若重複，可採 `owner-repo`，避免覆蓋既有目錄。整合程式的倉庫與名稱待實作時決定。

## 已安裝的版本與授權

- `microduck`：remote `https://github.com/pollen-robotics/microduck.git`；main HEAD `98ce17e4868ba9370713c4d11f3d934e5a1b7687`；Apache-2.0。
- `microduck_rl`：remote `https://github.com/pollen-robotics/microduck_rl.git`；develop HEAD `bae39f5900b318f7e87fc485c30a31213cfa14eb`；程式及 XML 為 Apache-2.0，STL 模型為 CC BY-NC-SA 4.0，依 `LICENSE-MODELS.md`。
- 第一階段兩個倉庫追蹤檔案皆未修改；第二階段 HUD 在 runtime scripts/duck-sim 加入兩行可選啟動／停止模組擴充，補丁見根目錄 patches/microduck-body-module.patch。RL 倉庫保持未修改。本機包裝／驗證腳本位於工作區根目錄 `scripts/`。
- 安裝與啟動參考 [Mac 本機模擬器](../microduck/local-simulator-macos.md)，實際套件與策略 SHA-256 見 [環境證據](../validation/evidence/2026-11-06/environment.json)。
