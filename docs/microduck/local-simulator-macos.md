# MacBook Pro M4 本機模擬器安裝與操作

安裝日期：2026-11-06。適用本工作區、macOS Apple Silicon。使用原生 CPU MuJoCo 與官方 robotd，不需要 Docker、資料庫或 CUDA GPU。

## 安裝版本

| 項目 | 本次版本 |
| --- | --- |
| microduck | main，`98ce17e4868ba9370713c4d11f3d934e5a1b7687`，daemon 0.18.6 |
| microduck_rl | develop，`bae39f5900b318f7e87fc485c30a31213cfa14eb` |
| uv | 0.13.7，工作區 `.tools/bin/` |
| Rust | 1.94.1，工作區 `.tools/cargo/`、`.tools/rustup/` |
| Python | 3.12.16，由 uv 安裝至 `.tools/python/` |
| MuJoCo／ONNX Runtime | 3.10.0／1.24.4 |
| 官方策略組 | `pollen-robotics/microduck-policies`，v8 |

`microduck_rl/.venv` 依上游 `uv.lock` 安裝；本機只使用模擬與推論部分，不進行 GPU 訓練。此版本的 `duck-body` 在 develop，不能直接換成 RL main。

## 現有環境的啟動與操作

在 `microduck-v7rc` Repo 根目錄開啟終端機，執行：

```sh
scripts/microduck-sim serve
```

保持該終端機執行。MuJoCo 視窗會開啟，機器人從坐姿起身；輸出應有 `robot healthy` 與 `standing`。這是被動觀察視窗，移動命令從控制端送入。

另開終端機，切至相同 Repo 根目錄：

```sh
scripts/microduck-sim status
scripts/microduck-sim realtime
scripts/microduck-sim drive 0.3 0
scripts/microduck-sim drive 0 0.8
scripts/microduck-sim drive 0 -0.8
```

`drive` 每次持續 8 秒；第一個參數為前進速度 m/s，第二個為偏航角速度 rad/s。上列依序為前進、左轉、右轉。這是速度請求，實際位移及轉角應以量測為準。

低速存在已知限制：本機 `0.15 m/s` 前進及 `0.5 rad/s` 左轉曾未達動作門檻；即使使用較大命令，速度追蹤與直線精度仍不是本次通過項目。上方命令為優先操作基準，詳見測試結果，不保證所有初始狀態均成功。

停止本專案模擬器：

```sh
scripts/microduck-sim down
```

也可在 `serve` 終端機按 Ctrl-C。不要使用名稱匹配的全域 pkill，以免停止其他研究工作。

無視窗模式可使用 `DUCK_SIM_VIEWER=0 scripts/microduck-sim serve`；本次驗收使用有視窗模式。

## 從空環境重建的步驟

以下是本次安裝的可重現步驟。既有環境不必重跑 clone 或安裝；若重建，保留現有倉庫與資料，在新的工作目錄操作，並帶入本專案的 scripts。

### 1. 拉取官方倉庫並固定版本

```sh
git clone https://github.com/pollen-robotics/microduck.git microduck
git -C microduck checkout 98ce17e4868ba9370713c4d11f3d934e5a1b7687
git clone --branch develop https://github.com/pollen-robotics/microduck_rl.git microduck_rl
git -C microduck_rl checkout bae39f5900b318f7e87fc485c30a31213cfa14eb
```

本次實際 checkout 分別為 main／develop，HEAD 是上表 SHA；上述 checkout 指令用來重現同一版本。修改前閱讀各倉庫 AGENTS.md；runtime 軟體為 Apache-2.0，RL 的 STL 模型另受 CC BY-NC-SA 4.0 約束，見 RL `LICENSE-MODELS.md`。

### 2. 建立短路徑與專案工具

本工作區路徑含中文與空白，且超過 Unix socket 路徑長度上限。使用 `/tmp/microduck-m4-<UID>` 連結至工作區；真正工具、策略及執行資料仍保存在工作區。

```sh
mkdir -p .tools .runtime
task_short="/tmp/microduck-m4-$(id -u)"
# 若路徑已存在，先確認 readlink 指向目前工作區；不要覆寫其他工作區。
test -e "$task_short" || ln -s "$PWD" "$task_short"

curl -fL https://astral.sh/uv/install.sh -o .tools/install-uv.sh
UV_INSTALL_DIR="$PWD/.tools/bin" UV_NO_MODIFY_PATH=1 sh .tools/install-uv.sh

curl -fL https://sh.rustup.rs -o .tools/install-rustup.sh
CARGO_HOME="$task_short/.tools/cargo" RUSTUP_HOME="$task_short/.tools/rustup" \
    sh .tools/install-rustup.sh -y --no-modify-path --profile minimal --default-toolchain 1.94.1
```

本次 uv 官方安裝器下載版本為 0.13.7；未修改使用者 shell 設定或全域 Python。首次網路下載需允許 GitHub、Rust、PyPI 與 Hugging Face 等官方來源。

### 3. 安裝鎖定的 Python 依賴

```sh
(
    cd microduck_rl
    UV_CACHE_DIR="$PWD/../.tools/uv-cache" \
    UV_PYTHON_INSTALL_DIR="$PWD/../.tools/python" \
        ../.tools/bin/uv sync --python 3.12 --locked
)
```

此步驟也會依 lock 取得 BAM Git 相依套件。不要拿 macOS 的 MPS 當成官方 CUDA 訓練環境。

### 4. 編譯與下載既有策略

```sh
task_short="/tmp/microduck-m4-$(id -u)"
CARGO_HOME="$task_short/.tools/cargo" \
RUSTUP_HOME="$task_short/.tools/rustup" \
CARGO_TARGET_DIR="$task_short/microduck/target" \
    "$task_short/.tools/cargo/bin/cargo" build --locked \
    --manifest-path "$task_short/microduck/Cargo.toml" \
    -p robotd -p robotctl -p tof -p sounds -p configd -p updater

sh microduck/scripts/seed-policies.sh "$PWD/.runtime/duck-sim/policies"
```

下載完成後確認 `.runtime/duck-sim/policies/current/velstand.onnx` 存在。本次使用 `scene_backlash.xml` 與 v8 `velstand.onnx`，其餘參數由官方啟動腳本產生。

### 5. 啟動並驗證

使用上方 `serve` 指令；另開終端機執行：

```sh
microduck_rl/.venv/bin/python scripts/verify-simulator.py \
    --output .runtime/validation-new-run
```

輸出包含 `summary.json`、逐筆 `samples.jsonl` 與 `health.jsonl`。站立 10 秒、前進 8 秒、左右各轉 6 秒，中間各留 3 秒不送移動命令，整體約 39 秒。失敗以非零 exit code 回報，並保留已取得證據。不要覆蓋已存檔的驗收結果。

目前測試預設為前進 `0.3 m/s`、轉向 `±0.8 rad/s`；可用 `--walking-speed`、`--turning-speed` 指定其他測試點。前進門檻為至少 0.30 m 且至少命令理想距離的 25%，不是完整速度追蹤驗收。

## 本次排除的環境問題

- **中文工具鏈路徑**：直接用完整中文 CARGO_HOME 建置時，`aws-lc-rs` build script 出現非 UTF-8 環境值 panic。將 CARGO_HOME、RUSTUP_HOME、CARGO_TARGET_DIR 設為短連結路徑後建置通過。
- **空白場景路徑**：上游腳本將 scene 參數存成字串後展開，含空白可能被拆開。包裝腳本將 DUCK_SIM_RL 指向不含空白的短連結，並保護既有連結不被覆寫。
- **背景程序生命週期**：工具執行環境會回收啟動命令遺留的子程序。新增 `serve` 保持前景擁有者；首次測試中斷紀錄保留，不列為完整通過。
- **socket 路徑長度**：DUCK_SIM_STATE 使用短連結下的 `.runtime/duck-sim`，避免完整中文路徑超過系統限制。重開機若清除 `/tmp`，包裝腳本會重新建立連結。
- **未涵蓋功能**：拾起偵測模型未安裝，上游會記錄警告；相機串流、實體 BLE、NPU、真實馬達與實機 sim-to-real 均未驗收。

第一階段未修改兩個上游倉庫的追蹤檔案。後續第二階段 HUD 在 runtime 啟動腳本加入兩行可選模組擴充；新 clone 需先套用根目錄 patches/microduck-body-module.patch。參考 docs/integration/v7rc-wifi-udp.md。工具、快取與執行資料在根目錄 `.gitignore` 排除；不使用 DB。

## 參考

- [官方模擬器文件](https://github.com/pollen-robotics/microduck/blob/98ce17e4868ba9370713c4d11f3d934e5a1b7687/docs/robot/simulation.md)
- [官方啟動腳本](https://github.com/pollen-robotics/microduck/blob/98ce17e4868ba9370713c4d11f3d934e5a1b7687/scripts/duck-sim)
- [RL develop 依賴與 duck-body](https://github.com/pollen-robotics/microduck_rl/blob/bae39f5900b318f7e87fc485c30a31213cfa14eb/pyproject.toml)
- [本機測試結果](../validation/2026-11-06-macos-simulator.md)
