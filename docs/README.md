# 研究文件索引

| 分類 | 內容 | 入口 |
| --- | --- | --- |
| repositories | 倉庫來源、用途、版本與本機位置 | [倉庫登錄](repositories/README.md) |
| microduck | 機器人架構、控制介面、硬體與模擬研究 | [初步資料](microduck/overview.md) |
| v7rc | APP 通訊、封包、控制模式與相容性 | [協定筆記](v7rc/protocol-notes.md) |
| integration | 橋接設計、控制映射與開發階段 | [整合計畫](integration/plan.md) |
| validation | 測試方法、環境、結果與問題紀錄 | [驗證規範](validation/README.md) |

新文件以內容分類；單次實驗可使用 `YYYY-MM-DD-主題.md` 命名，持續維護的設計使用穩定檔名。每份技術研究應註記日期、來源、已確認事項及待驗證事項；實驗另外記錄 commit 與環境。內容跨類別時放在主要類別，其他文件以連結引用。

最新研究：[四階段需求可行性評估（含 M4 本機模擬與 RTX 5090 訓練配置）](integration/feasibility-2026-11-06.md)。

本機實作：[安裝與操作](microduck/local-simulator-macos.md)、[實測結果與限制](validation/2026-11-06-macos-simulator.md)。

第二階段：[V7RC SRT 四通道 UDP 操作](integration/v7rc-wifi-udp.md)、[橋接測試結果與手機驗收範圍](validation/2026-11-06-v7rc-udp.md)。

影像橋接：[相機操作與 Camera757 協定](integration/v7rc-video-feasibility.md)、[實際封包／iOS 接收器驗證與手機未收圖紀錄](validation/2026-11-06-v7rc-video.md)。

相機未連線排查：[Mac 防火牆、UDP 8800 與 iPhone 個人熱點診斷](validation/2026-11-06-udp8800-network.md)。

Repo 結構：[microduck-v7rc 獨立整合 Repo 與本機依賴配置](repositories/microduck-v7rc-layout.md)。
