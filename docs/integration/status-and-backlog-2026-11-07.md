# Microduck V7RC 工作盤點

日期：2026-11-07。main：`2aff421668ddad2bdb552f26bd9d5d4c04802094`；公開 preview：`0.1.0-preview.2`；安裝包來源：`827905a260f52d0e5606ebf136a1cf6cb52890eb`。

## 已完成

- Mac M4 模擬器：既有官方策略的基本站立、前進、左右轉向；未宣稱精確速度追蹤。
- Wi-Fi UDP SRT 四通道、CH3／CH4 調整與反相、失聯回中、FPS／雙搖桿／IP 與 Port HUD。
- 一般 Wi-Fi 下，iOS V7RC 3.00.006 控制與 640×360 UDP 相機顯示，使用者已確認成功。
- Mac preview.2 實際下載安裝與桌面圖示啟動，使用者確認控制／影像正常；安裝版另有 14 階段隔離控制與 39 幀解碼證據。
- Mac DMG、Windows EXE、SHA256 已上傳公開 [Release](https://github.com/v7rc/microduck-v7rc/releases/tag/v0.1.0-preview.2)，未登入下載 HTTP 200 已確認。仍為未簽署測試版。
- 四語 README、安裝指引及 How-To；[最新 main CI](https://github.com/v7rc/microduck-v7rc/actions/runs/42325347905) 與 [兩平台安裝包建置](https://github.com/v7rc/microduck-v7rc/actions/runs/42323508633) 成功。CI 不代替目標機完整驗收。

## 未完成與建議順序

| 順序 | 工作 | 現況與完成條件 |
| --- | --- | --- |
| 1 | Windows 11 完整實機驗收 | EXE 已編譯及 self-test。需要 Windows 目標機實測 WSL2／Ubuntu 初始化、必要重開機、套件安裝、桌面圖示、WSLg 視窗、SRT 控制、相機與停止／再次啟動。 |
| 2 | 穩定性與例外驗收 | 建議連續操作至少 30 分鐘；測試鎖屏、切換 APP、Wi-Fi 斷線重連、關閉程序及控制來源切換。確認失聯停止、重新回中解鎖、無殘留服務。曾有一次 MuJoCo SIGSEGV，使用者亦說明有關閉視窗；原因未確認，後續隔離測試通過，尚不能宣稱已修復或長時間穩定。 |
| 3 | 文件現況與內嵌文件同步 | 初期 plan、validation 索引及部分筆記仍有未選通訊／手機未驗收／CI 未推送等舊敘述。應保留歷史並加入現況入口。現有 Release 內嵌指南早於公開下載說明更新，仍提 artifact 保留 30 天；下版需重新內嵌並驗證連結。 |
| 4 | 第三階段：RTX 5090 訓練 | 尚未在使用者伺服器訓練。取得主機後核對 driver／PyTorch／CUDA／Warp，完成 GPU 計算、小規模訓練、checkpoint 保存與恢復、ONNX 匯出，記錄可重現環境與吞吐量。不能預先承諾訓練時間。 |
| 5 | 第四階段：新策略接回 V7RC | 目前是官方既有策略，尚無新訓練策略的控制驗收。核對 observation／action、normalizer、關節順序、命令與時序，將 ONNX 回載模擬器，以同一套控制／失聯測試驗收並保留官方策略回退。 |
| 6 | Linux 桌面驗收 | 已有平台支援及隔離測試，未完整測試 Linux 首次安裝、圖形環境、GPU／渲染及手機控制／影像。需要指定發行版與可操作目標機。 |
| 7 | iPhone 個人熱點影像 | 一般 Wi-Fi 已成功；iPhone 自己提供熱點時相機訂閱未達 Mac 的問題未修復。需在 APP 相機路徑記錄介面綁定、路由及 sendto errno，再確認修正。不能認定 Mac 防火牆或 en0 是唯一根因。 |
| 8 | 行走品質 | 校正後完成同樣 54 輪，四個方向達到持續運動門檻的輪次由 23／48 增至 48／48。仍待驗證起步瞬態、低於 25% 的細幅、混合軸與手機操作感。[校正前後對照](../validation/2026-11-07-proportional-control-calibrated.md) |

原始四階段目標中，第一、二階段已有 Mac 基線驗收；第三、四階段尚未交付。上述排序是建議，不代表已取得 Windows／Linux／GPU 主機存取權。

## 可選擴充

- 安裝器升級、修復重試、解除安裝及資料保留流程；中斷下載、磁碟不足、Port 衝突的目標機測試。已有部分保護不等於完整生命週期管理。
- Apple Developer ID／公證與 Windows 簽章：目前使用者接受未簽署 preview，簽章不是這次交付欠件。
- 真實 Microduck 部署與 sim-to-real：需要實體機器人，與模擬器成功分開驗收。
- BLE、多影像接收端與分片重傳：屬新增功能，不列為目前必要欠件。

## 依據

- [Mac 模擬量測](../validation/2026-11-06-macos-simulator.md)
- [SRT 測試](../validation/2026-11-06-v7rc-udp.md)
- [Wi-Fi／熱點對照](../validation/2026-11-06-udp8800-network.md)
- [跨平台驗收界線](../validation/2026-11-06-cross-platform.md)
- [安裝包與 Mac 實際驗收](../validation/2026-11-07-installers.md)
- [原始計畫](plan.md)、[訓練與新策略研究](feasibility-2026-11-06.md)

本次僅盤點，未啟動訓練、修改 APP 或安裝遠端主機。
