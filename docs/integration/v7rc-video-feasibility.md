# Microduck 頭部相機經 UDP 回傳 V7RC

查閱／實作日期：2026-11-06。已完成 Mac 發送端、相機 HUD、本機 UDP 收圖與既有 iOS SDK 重組測試；**一般 Wi-Fi 下手機影像顯示已由使用者確認正常**。使用者手機為 iOS V7RC 3.00.006。個人熱點模式相機訂閱未達；換成一般 Wi-Fi 後，手機有效訂閱及 EF02 回饋已到達，CAMERA ON、已送 91 張。使用者已確認「看得到，影像正常」，見 [網路對照測試](../validation/2026-11-06-udp8800-network.md)。此文件取代先前「格式尚未確認」的初步研究。

## 啟動與 APP 設定

在工作區終端機執行 `scripts/microduck-sim serve`，另開終端機執行 `scripts/v7rc-bridge`。模擬器預設啟用相機服務；`MICRODUCK_VIDEO=0 scripts/microduck-sim serve` 可關閉。不要同時設定上游 `DUCK_SIM_CAMERAS`，兩條相機路徑不可合併啟動。本路徑直接使用既有 MuJoCo 頭部相機，不需要另裝 mediad／GStreamer。

| 用途 | 設定 |
| --- | --- |
| SRT 四通道控制 | Mac Wi-Fi IPv4，UDP 6188 |
| APP 影像來源 | UDP |
| APP 相機 IP | Mac Wi-Fi IPv4，此次 172.20.10.2 |
| APP 相機 Port | 8800，儲存後開啟遙控頁的影像功能 |
| Mac 影像來源 Port | UDP 1234；不填入 APP 相機目的 Port |
| 手機接收 Port | APP 自動分配，主機回傳至其 UDP 來源 Port |

右上顯示 Mac `en0` IPv4（每 5 秒更新）、CONTROL UDP 6188、VIDEO UDP 8800。更換 Wi-Fi 後須同步修改 APP 的控制與相機 IP。重啟／失聯後四通道先回 1500。

左上顯示：控制 `V7RC RX` FPS、控制狀態、`CAMERA ON/OFF`、`TX FRAMES` 累計與影像送出 FPS，以及相機 `PEER` IP。有效訂閱 3 秒未更新即 OFF；狀態發布程序停止也會 OFF。累計數為本次程序已完整送出所有分片的影格數，重啟歸零；不表示手機已收到或顯示。`PEER 127.0.0.1` 為本機測試，手機此次應是 172.20.10.1。相機輸出為頭部第一人稱視角，不包含桌面第三人稱 HUD。

## 既有協定與封包

UDP 本身沒有建立連線的握手。既有 SDK 開相機後會自動送 `EF 00 04 00` 到相機 UDP 8800，主機取得來源 IP／Port 後，從 UDP 1234 回傳圖像；後續 `EF 02` 回饋亦延續訂閱。此處「探測／訂閱」是應用層封包，不是要求使用者另外建立連線。未收到任何 UDP 時，主機不能憑控制來源 IP 猜出相機接收 Port。

採用既有完整 JPEG 擴充 FF/45，實際像素與標頭均為 **640×360**，JPEG quality 70，目標上限約 10 FPS。每包 56 bytes 標頭加最多 1024 bytes JPEG，最大 UDP payload 1080 bytes；一個完整 JPEG 最多 256 KiB。

| Offset | 內容（多 bytes 欄位為 little-endian） |
| --- | --- |
| 0–1 | `93 01` |
| 2–3 | 此 datagram 長度，包含 56 bytes header |
| 4–7 | `02 02 00 01` |
| 8、16、24 | uint64 frame ID、相同 ID、前一個 ID |
| 32、36、40 | uint32 fragment index（從 0）、總分片數、完整 JPEG 長度 |
| 44、46 | uint16 width=640、height=360 |
| 48–49 | `FF 45`，完整 JPEG；不是原始 quality-50 scan 模板 |
| 50、52 | `01`；其他保留 bytes=0 |
| 56 起 | 該分片的 JPEG 資料；整張包含 SOI／EOI |

只維持一個相機接收端，3 秒過期後可換來源；發送採最新影格槽，不累積無限佇列。與既有 ESP32 範例相同，目前不依 EF02 內容重傳遺失分片。影像渲染採 portrait 360×640 後順時針旋轉為實際 640×360，使用上游 Camera 的安裝姿態修正；手機旋轉／鏡像觀感仍待驗收。

## 沒有影像時

- `CAMERA OFF` 且 `.runtime/v7rc-video.json` 的 `last_datagram` 沒有手機來源：先查目的 IP、8800、影像功能是否啟動、手機路由與主機防火牆；此時尚無影像格式解碼的證據。
- `CAMERA ON`、`PEER` 為手機且 TX FRAMES 增加：主機已送出，接著查回程路由、丟包與 APP 解碼。ON 本身不代表 APP 顯示成功。
- 本機 iOS 3.00.006 原始碼的 `Camera757UDPClient.swift` 使用 `IP_BOUND_IF` 強制 socket 綁定 `en0`。iPhone 作熱點主機時的回連路由可能受影響，**這是根據程式碼及未收封包的推測，尚非手機封包擷取證實**。下一步讓兩端連同一台 Wi-Fi 路由器，再填右上最新 IP 測試。

## 本機來源與版本

依使用者授權參考本地專案的協定事實，以 Python 獨立實作，沒有修改或搬移原專案韌體／APP。根目錄未發現 LICENSE，故未複製韌體實作進本工作區。

- `../../20260920 V7RC-TOY/V7RC-TOY-Android`，main `35f0f1e39a3ee4b51583a22649d2409f35032ad6`：ESP32 `apps/esp32-cam/camera757/Camera757ESP32/Protocol757.h`、Ameba `apps/ameba-pro2/camera757/Camera757/Protocol757.h`、`ios-v7rc-ble-toy-sdk/Sources/V7RCToySDK/Camera757Codec.swift`。
- `../../20260511V7RC-APP/V7RC%20IOS%20Version`，louis-test `aee429656a4f1d3d8740f7d2edfb3590814f537d`：`Vendor/V7RCToySDK/ios-v7rc-ble-toy-sdk/Sources/V7RCToySDK/Camera757{Codec,JpegHeaders,UDPClient}.swift`，`docs/UDP_CAMERA_INTEGRATION.md`。本地 project.pbxproj MARKETING_VERSION=3.00.006；不能據此保證手機 binary 完全相同。
- `../../20260511V7RC-APP/V7RC-APP-Research/android`，louis-dev `12a22bf2a56a527d180f6fdfc674f32198db4d53`：實際 APP 的 `UdpCameraReceiver.java` 使用相同 Camera757 接收路徑。
- Microduck main `98ce17e4868ba9370713c4d11f3d934e5a1b7687`；microduck_rl develop `bae39f5900b318f7e87fc485c30a31213cfa14eb`。相機原始碼入口：[上游 camera.py](https://github.com/pollen-robotics/microduck_rl/blob/bae39f5900b318f7e87fc485c30a31213cfa14eb/src/mjlab_microduck/sim/camera.py)。實際 Git remote 以倉庫登錄為準。

來源檔 SHA256 與該檔 Git 狀態見 [source-files.json](../validation/evidence/2026-11-06-video/source-files.json)；本機來源路徑以上層工作區為相對基準。測試細節見 [驗證紀錄](../validation/2026-11-06-v7rc-video.md)。
