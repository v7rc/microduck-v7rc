# 用 V7RC 操作 Microduck 迷宮

第一版在平地上配置約 0.95 公尺淨寬的 S 型走道。第一個路口直走會到紅牆死巷。正確路線依序左轉、右轉、右轉、左轉，從橘色箱子右側繞過，再穿過綠色拱門及地上的終點線。藍色牆面和箱子有碰撞，綠色拱門及終點線是視覺標記。

## 啟動

在 `microduck-v7rc/` 開兩個終端機，各執行一條命令並保持運行。

```sh
scripts/microduck-sim serve --maze
```

```sh
scripts/v7rc-bridge
```

手機和 Mac 連同一個 Wi-Fi。控制模式選 SRT 四通道，目的 IP 填模擬器 HUD 顯示的 Mac IPv4，Port 填 `6188`。相機來源選 UDP，填同一個 IP、Port `8800`，回遙控頁開啟影像。

四通道先回到 `1500`，等橋接顯示已接管。左搖桿前後控制移動、左右控制轉向。右搖桿調整頭部相機方向，畫面若偏向地面可抬頭看轉角和標記。要從起點重來，在模擬器終端按 Ctrl+C，重新執行第一條命令，搖桿回中後再控制。

操作細節見 [SRT 控制](v7rc-wifi-udp.md) 與 [相機設定](v7rc-video-feasibility.md)。

## 場景與驗證

場景在 [scenes/maze.xml](../../scenes/maze.xml)，引用既有 `scene_backlash.xml`，保留機器人模型、SIT 起始姿勢、地面和頭部相機。啟動選項使用工作區短路徑傳遞 XML，讓含空白的 Mac 工作區可用。

2026-11-08 於 MacBook Pro M4、MuJoCo 3.10.0 驗證。有視窗啟動後 robotd 為 healthy、Microduck 站立。沿設計路線與四個轉角取樣 691 個靜態站姿，均未接觸迷宮障礙物，另驗證橘色箱子和死巷紅牆可產生碰撞。本機送 SRT 前進封包使軀幹前移 0.187 公尺。相機本機 UDP 接收端約四秒成功解碼 25 張 640×360 JPEG。重新啟動橋接後，另觀測到手機送出 SRT 回中封包，以及相機訂閱和回饋。手機畫面顯示與完整操控通關待使用者確認。

來源為 [Microduck main 98ce17e](https://github.com/pollen-robotics/microduck/blob/98ce17e4868ba9370713c4d11f3d934e5a1b7687/docs/robot/simulation.md) 與 [microduck_rl develop bae39f5](https://github.com/pollen-robotics/microduck_rl/blob/bae39f5900b318f7e87fc485c30a31213cfa14eb/src/mjlab_microduck/robot/microduck/scene_backlash.xml)，整合 repo 基準為 main `f5bbafe`。
