# microduck-v7rc

Microduck 與 V7RC APP 的整合程式：SRT 四通道 Wi-Fi UDP 控制、頭部相機 UDP 影像傳輸，以及模擬器 HUD。

目前已在 MacBook Pro M4 Pro 驗證本機模擬、手機控制與一般 Wi-Fi 下 iOS V7RC 影像顯示。Windows 尚未移植，iPhone 個人熱點的相機通訊仍有已知限制。

## 目錄

```text
microduck-v7rc/
├── bridge/                 # UDP 控制、Camera757 相機與 HUD
├── scripts/                # 啟動、連結既有環境與驗證
├── patches/                # 上游 runtime 啟動入口的兩行補丁
├── tests/                  # 隔離測試與既有 iOS 接收器互通檢查
├── docs/                   # 研究、安裝、操作與驗證證據
└── upstream-revisions.json # 上游來源、驗證 commit 與補丁
```

上游 `microduck`、`microduck_rl` 各自保留獨立 Git 歷史，沒有直接收進此 Repo。本機可以在此目錄 clone 指定版本，或以忽略的 symlink 連到工作區內既有 Repo；工具 `.tools/` 與執行資料 `.runtime/` 也不提交。版本清單不是 submodule，不會自動下載依賴；安裝步驟見下方文件。

## 既有 Mac 環境啟動

Louis 的研究工作區已安裝工具與上游 Repo，進入本 Repo 後執行：

```sh
scripts/link-workspace
scripts/microduck-sim serve
```

保留模擬器終端機，另開終端機在此 Repo 執行：

```sh
scripts/v7rc-bridge
```

V7RC 控制使用 SRT、四通道、UDP 6188；相機來源選 UDP、Port 8800。IP 填模擬器右上顯示的 Mac Wi-Fi IPv4，四通道先回到 1500。CH1 轉向、CH2 前後、CH3 頭部上下（反相）、CH4 頭部左右。

左上顯示控制接收 FPS、相機 ON/OFF、送出影格數與相機接收端 IP，並疊加兩個搖桿。相機提供 640×360 頭部視角；CAMERA ON 或送出影格數本身不表示手機已顯示，須分開驗收。

停止模擬器使用 `scripts/microduck-sim down`；橋接終端機按 Ctrl-C。

## 安裝與驗證

- [從空環境安裝／Mac 操作](docs/microduck/local-simulator-macos.md)
- [SRT 四通道操作](docs/integration/v7rc-wifi-udp.md)
- [Camera757 相機設定與協定](docs/integration/v7rc-video-feasibility.md)
- [相機手機驗收](docs/validation/2026-11-06-v7rc-video.md)
- [個人熱點與一般 Wi-Fi 對照](docs/validation/2026-11-06-udp8800-network.md)
- [本次獨立 Repo 整理](docs/repositories/microduck-v7rc-layout.md)
- [完整文件索引](docs/README.md)

隔離測試：`microduck_rl/.venv/bin/python -m unittest discover -s tests -v`。真實模擬器測試另見操作文件，不要與手機同時送控制或訂閱相機。

上游程式與模型的授權各自適用；尤其 STL 模型的 CC BY-NC-SA 4.0 限制請見上游 LICENSE-MODELS.md。本 Repo 不包含模型、策略、上游程式副本或其授權轉授權。
