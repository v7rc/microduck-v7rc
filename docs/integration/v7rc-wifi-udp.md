# V7RC SRT 四通道 → Mac Microduck 模擬器

日期：2026-11-06。橋接程式：根目錄 `bridge/v7rc_udp.py`，啟動入口 `scripts/v7rc-bridge`。只使用 Python 標準函式庫；不需額外硬體、DB 或 GPU。

## APP 要設定的值

本次查得 Mac 的 Wi-Fi 介面 en0：

| APP 項目 | 設定 |
| --- | --- |
| 連線方式 | Wi-Fi／UDP |
| 目的 IP | **172.20.10.2** |
| 目的 Port | **6188** |
| Protocol | **SRT** |
| Channel 數 | **4** |
| 各通道範圍 | **1000–2000** |
| 各通道中立 | **1500** |
| 封包頻率 | 建議 10–20 Hz，連續有效封包間隔須小於 300 ms |

手機與 Mac 必須能在同一區域網路互通。IP 是此次介面查詢結果，換 Wi-Fi／熱點後可能改變；在 Mac 執行 `/usr/sbin/ipconfig getifaddr en0` 重新確認。若 Mac 改用其他介面，查該介面的 IPv4。不要在手機填 `127.0.0.1` 或 `0.0.0.0`；橋接的 `0.0.0.0` 是接收端綁定設定。

目前尚未讀取／操作使用者手機的 APP，因此上述是需要填入的欄位值，不宣稱已驗證特定 APP 版本的選單名稱。若 iOS 提示本機網路權限，需允許 V7RC 存取本機網路；若 macOS 提示 Python 入站連線，需允許此橋接接收。尚未修改防火牆或系統網路設定。

## 四通道映射

SRT 在此作為四個原始通道的封包格式；本橋接將 CH1／CH2 解讀為轉向／前後移動，不產生左右履帶 PWM。

| 通道 | 1000 | 1500 | 2000 | 送給 Microduck |
| --- | --- | --- | --- | --- |
| CH1 | 左轉 | 不轉向 | 右轉 | `vyaw` +0.8 至 −0.8 rad/s |
| CH2 | 後退請求 | 不前後移動 | 前進 | `vx` −0.3 至 +0.3 m/s |
| CH3 | 頭部向下 | 名義頭部姿態 | 頭部向上 | `head_pitch` +0.25 至 −0.25 rad（依使用者要求反相） |
| CH4 | 頭部向左 | 名義頭部姿態 | 頭部向右 | `head_yaw` +0.4 至 −0.4 rad |

CH3 已依手機操作回饋設定上下反相；CH4 維持左右方向。`vy`、`neck_pitch`、`head_roll` 固定為 0。頭部數值進入既有策略的命令觀測，由策略控制關節；不直接寫馬達或關節 PWM，因此實際角度不等於請求值。

每軸設 8% 死區（1460–1540 視為中立），死區外線性重映射至完整輸出。各軸可反向，例如 `scripts/v7rc-bridge --invert 1 4` 會反轉 CH1、CH4；若 APP 已反向，避免兩側重複反向。

目前設定是四通道的初版操作配置。前後／轉向及頭部控制的可用程度，以 [本次測試結果](../validation/2026-11-06-v7rc-udp.md) 為準；第一階段的低速／精度限制依然存在。

## 啟動與手機操作

在工作區根目錄的第一個終端機啟動模擬器，保持執行：

```sh
scripts/microduck-sim serve
```

看到 healthy、standing 後，在第二個終端機執行：

```sh
scripts/v7rc-bridge
```

橋接接收 `0.0.0.0:6188/UDP`，控制端只連到本機 `.runtime/duck-sim/duck-a.sock` 的短路徑。需讓兩個程序持續執行；不要同時開兩個使用相同 Port 的橋接，第二個會回報位址已使用。

手機依上表設定後，先將 **四個通道全部回到 1500** 並持續送出。主控台應出現 `armed sender=<手機 IP> after neutral SRT frame`；此時再推動搖桿。每 5 秒的 status 會顯示 accepted、invalid、foreign、waiting_neutral 等計數。

若先前機器人在自主看向四周，收到回中後頭部約需 1.5 秒淡出，建議等待約 2 秒再觀察中立姿態。長時間失聯後自主看向四周可能恢復；這不是橋接重播舊輸入。

測試順序：先小量操作 CH3／CH4 並回中，再測 CH1 轉向與 CH2 前進。由於已知低速可能不起步，基本動作可先觀察較大輸入；不要因為搖桿小幅度時沒有位移就推論 UDP 沒收到。以主控台四通道、`robot.state` 與畫面三者一起判斷。

若斷線或停止送包超過 300 ms，橋接歸零並解除輸入；重新連線後再次四通道回中。未回中時，waiting_neutral 計數會上升且不接受運動命令。

停止：在橋接終端機 Ctrl-C，送出移動與頭部歸零請求；若也要停止模擬器，再執行 `scripts/microduck-sim down`。歸零是收斂到名義姿態，不代表立即煞停、坐下或卸力。

## 封包契約與運作方式

每個 UDP datagram 必須剛好是 20 bytes ASCII：`SRT` + 四個四位十進位欄位 + `#`。不接受其他 Protocol、尾隨換行／NUL、黏合多筆、缺字或超出設定範圍的通道。

```text
SRT1500150015001500#  四軸回中
SRT1500200015001500#  前進
SRT1000150015001500#  左轉
SRT2000150015001500#  右轉
SRT1500150020001500#  頭部向上請求
SRT1500150015002000#  頭部向右請求
```

橋接最多以 20 Hz 將最新且仍新鮮的通道送成 `robot.move`、`robot.head` JSON-RPC notifications。錯誤封包及其他來源 IP 都不刷新 watchdog。首次有效回中封包的來源 IP 取得本次程序控制權，來源 UDP port 可改變；換另一台手機需重啟橋接，或啟動時用 `--source-ip <手機 IP>` 明確指定。UDP 無登入驗證，此實作供可信本機網路的模擬操作使用。

逾時時主動送一次歸零，不會持續重播最後一筆移動。robotd 自己約 500 ms 的 intent deadman 仍有效。robotd 斷線會丟棄輸入，每秒嘗試重連；成功後同樣需要新的回中封包。橋接不呼叫 robot.enable，需先依第一階段方式啟動並確認模擬器站立。

連線後另有手把、CLI 或其他程式送命令時，上游可能採最後寫入者為準；測試時請只保留一個控制來源。

## 本機檢查與複驗

```sh
# 查 IP、接收程序與模擬器健康
/usr/sbin/ipconfig getifaddr en0
/usr/sbin/lsof -nP -iUDP:6188
scripts/microduck-sim ctl health

# 協定／watchdog／重新連線測試（不操作真實模擬器）
microduck_rl/.venv/bin/python -m unittest discover -s tests -v

# 使用本機 Python sender 送 UDP 並量測真實模擬器；先重啟橋接清除來源鎖定
microduck_rl/.venv/bin/python scripts/verify-v7rc-udp.py \
  --host 172.20.10.2 --output .runtime/udp-validation-new-run
```

端到端複驗會取得本機 sender IP 的控制權；測完務必重啟橋接，才能讓手機取得控制權。手機與本機 Python sender 不可同時測試。

CLI 可調 `--port`、`--timeout`（0.1–0.5 秒）、`--hz`（5–50）、PWM 端點、死區、各軸反向與最大命令；用 `scripts/v7rc-bridge --help` 查看。命令增益變更後須重新驗證模擬效果，不能以第一階段結果替代。

## 待使用者手機確認

- 手機送出的封包確實是 SRT 四通道、1000–2000／1500，且沒有額外尾碼。
- 手機與 Mac 在目前 Wi-Fi／熱點上可直達，APP accepted 計數持續增加。
- 四通道實際方向、回中、持續更新頻率符合操作習慣；CH2 後退仍需單獨驗證。
- 鎖屏、切換 APP、Wi-Fi 中斷後確實歸零；回到 APP 先回中才恢復控制。

## 來源

- [V7RC 官方 SRT 格式](https://github.com/v7rc/V7RC-Protocol/blob/main/protocol.zh-TW.md)，2026-11-06 重新查閱。
- [V7RC 官方 Wi-Fi UDP 範例](https://github.com/v7rc/V7RC-ESP32-WIFI-LIB/blob/main/src/V7RC_WIFI.cpp)，同日確認使用 UDP 6188。
- 本機 microduck main `98ce17e4868ba9370713c4d11f3d934e5a1b7687` 的 `duck-ipc-proto/src/lib.rs`、`duck-control/src/obs.rs`，確認 move／head 參數與方向。HUD 的本機啟動擴充另見下節。
- V7RC Protocol main 查閱版本 `f9c17b85b2c24bc0581a8c2fb36788ff9f1abedf`；Wi-Fi LIB main `fd4b679f60209838d6e4c53c39144aba599e9cc6`。


## 左上方接收 FPS 與雙搖桿 HUD

啟動 `scripts/microduck-sim serve` 會載入 `bridge/microduck_hud.py`，以 MuJoCo 原生文字／線圖疊在視窗左上方。左搖桿 X=CH1、Y=CH2；右搖桿 X=CH4、Y=CH3。搖桿顯示原始接收位置，不套用命令死區或方向反相。

`V7RC RX` 是最近 1 秒有效 SRT 封包數（FPS），不是畫面渲染 FPS。錯誤／外來來源封包不計入；尚未回中但格式正確的封包仍算接收。HUD 每秒約更新 10 次，資料由橋接原子寫入 `.runtime/v7rc-input.json`。

LIVE 表示新鮮且已取得控制權；CENTER TO ARM 表示須回中；INPUT EXPIRED 表示失聯；WAITING FOR INPUT 表示無新鮮發送端。失聯保留最後原始搖桿位置並改色；橋接仍會把實際命令歸零。

本機 runtime `scripts/duck-sim` 有兩行啟動／停止模組擴充，補丁保存在 `patches/microduck-body-module.patch`；RL 倉庫與物理／策略程式未修改。全新 clone 重建時，先在根目錄執行 `git -C microduck apply ../patches/microduck-body-module.patch`（現有環境已套用，不需重複），再用本專案啟動入口。

## 相機與連線 HUD

右上顯示當前 Mac Wi-Fi IP、控制 UDP 6188、相機 UDP 8800；相機須另於 APP 影像設定選 UDP。左上 CAMERA ON/OFF、TX FRAMES 與 PEER 是獨立影像狀態，不是 SRT 控制接收率。詳見 [影像操作與未收圖排查](v7rc-video-feasibility.md)。
