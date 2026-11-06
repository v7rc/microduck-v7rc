# Microduck 初步資料

查閱日期：2026-11-06。狀態：官方 README 初步研究，尚未固定 commit、建置或連接設備。

後續進度：本機已固定版本並安裝，見 [Mac 模擬器操作](local-simulator-macos.md) 與 [實測結果](../validation/2026-11-06-macos-simulator.md)；本頁以下保留最初研究脈絡。

## 已確認的來源內容

官方 [microduck README](https://github.com/pollen-robotics/microduck) 說明：`robotd` 負責控制迴圈及馬達匯流排，`btd` 提供手機的 Bluetooth 路徑，`padd` 接收遊戲手把輸入；元件之間使用 Unix socket 上的 JSON-RPC 契約。這些元件是後續追查外部遙控入口的起點。

## 後續原始碼研究

- 確認外部速度、轉向、動作切換的實際方法、參數、範圍及回覆。
- 查看 `btd`／`duck-ble` 的 GATT 定義及寫入語意，確認是否與 V7RC 相容。
- 查看手把輸入如何進入機器人控制狀態，確認控制權競爭與斷線處理。
- 查閱模擬器啟動條件及本機支援平台，先進行不接實機的橋接驗證。

公開軟體倉庫與通訊介面的存在，不代表已確認 V7RC 可以直接連線；實際行為應以固定 commit 與測試結果為準。
