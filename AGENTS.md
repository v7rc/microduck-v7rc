# microduck-v7rc 整合 Repo 規則

## 用途與目錄

- 本 Repo 用於 Microduck 與 V7RC APP 整合；父目錄為多 Repo 研究工作區。
- 上游以獨立 Repo 維護，本機 microduck、microduck_rl、.tools 可連結至父工作區。這些目錄及 .runtime 不提交；相容版本記錄於 upstream-revisions.json。不得將上游完整內容誤加為本 Repo 檔案。
- 尊重子專案的 AGENTS.md、授權、建置方式與既有變更。跨專案修改應分別說明，不在不相關倉庫提交研究文件。
- 共用研究資料放在根目錄 `docs/`，按內容分類：`repositories/`、`microduck/`、`v7rc/`、`integration/`、`validation/`；新主題可新增類別並更新 `docs/README.md`。
- 文件預設使用繁體中文，保留原始 API、命令與程式識別名稱。
- 技術研究標註查閱日期、來源 URL；涉及程式行為時記錄倉庫、branch/tag 與 commit。區分已確認事實、設計提案與待驗證假設。
- 複製上游程式或資產前檢查授權。模擬成功、程式可建置及實機驗收應分開記錄。
- 密碼、Token、私鑰、含憑證設定與資料庫備份不可提交或輸出到聊天／公開文件。

## 本機模擬器

- 使用 `scripts/microduck-sim serve` 啟動有視窗模擬器並保留前景程序，`scripts/microduck-sim down` 只停止本專案模擬程序。
- `.tools/` 保存專案工具與快取，`.runtime/` 保存本機執行資料；均不提交。兩個上游倉庫保留獨立 Git 歷史。
- 包裝腳本以 `/tmp/microduck-m4-<UID>` 連結本工作區，解決中文／空白路徑與 Unix socket 長度問題；不要覆寫屬於其他工作區的連結。
- 版本、安裝方法及動作限制見 `docs/microduck/local-simulator-macos.md`；修改或更新版本後，先重新檢查資料再驗證，不能沿用舊測試宣稱通過。

## V7RC UDP 橋接

- `scripts/v7rc-bridge` 啟動標準函式庫的 `bridge/v7rc_udp.py`，預設 UDP 6188、SRT 四通道；CH1 轉向、CH2 前後、CH3 頭部上下（反相）、CH4 頭部左右。
- 啟動／失聯／robotd 重連後需要新的四通道中立封包。不要無限重播最後的非中立封包；無效封包及非控制來源不能刷新 watchdog。
- 用 `microduck_rl/.venv/bin/python -m unittest discover -s tests -v` 執行隔離測試；操作真實模擬器的端到端測試另用 `scripts/verify-v7rc-udp.py`，不要同時由手機操控。
- 本機 sender 測試後需重啟橋接清除來源 IP 鎖定，才能讓手機取得控制權。操作與驗收界線見 `docs/integration/v7rc-wifi-udp.md`。

## MacBook Pro M4 本機共用資料庫

以下僅適用 Louis 這台 MacBook Pro M4 本機，不自動套用遠端、正式環境或 CI。若子專案已使用外部 DB，先確認用途，不逕自切換。目前本工作區未選用或建立資料庫。

- 本機 Docker 專案需要 MariaDB／PostgreSQL 時優先使用既有共用服務，不另建專案專屬 DB container。
- 調整前先閱讀 `/Users/louischuang/CompanyStorage/嵐奕科技有限公司/第四處 技術處/Louis-Mac-Book-ProM4-Setting/README.md` 與同目錄 `shared-databases/project.example.yaml`，並確認服務現況。
- 應用 Compose 宣告 external network `mac-shared-db` 並加入；共用 DB 不納入應用 service 生命週期。
- Docker 內連線：MariaDB `shared-mariadb:3306`；PostgreSQL `shared-postgres:5432`。Mac 原生程式使用 `127.0.0.1:3306`／`127.0.0.1:5432`；容器 localhost 指容器本身。
- 每個專案使用獨立 DB 與專案帳號，不使用共用管理員帳號；先確認既有資源，避免重複建立或覆寫。
- 新建時在共用目錄執行 `python3 scripts/db.py provision mariadb <project_name>` 或 `python3 scripts/db.py provision postgres <project_name>`。名稱須以小寫英文字母開頭，後續僅小寫字母、數字、底線，總長不超過 40 字元。
- 憑證由 provisioning 寫入共用目錄 `.secrets/<engine>-<project_name>.env`，依應用支援的環境變數或 DATABASE_URL 接入，不假設範例變數通用。使用本機忽略檔或既有 secret 注入，不提交憑證。
- 檢查 Compose 及覆寫檔，移除舊本機 DB services 與其 depends_on，保留 Redis、MQTT、應用間依賴及其他設定。舊 DB 容器、volume、資料不得直接刪除，先備份、搬移並驗證。
- 選用 DB 後，在對應專案 AGENTS.md 與操作文件記錄引擎、DB 名稱、專案帳號、network、啟動方式，不記錄密碼。
- 驗證 Compose 可解析且不意外啟動舊 DB；用專案帳號實際驗證共用網路連線。設定可解析不等於完整應用驗收。
- 清空／重建資料測試僅使用明確隔離的測試 DB 或暫用容器，不對共用開發資料或其他專案資料清空、重建或重匯 bootstrap。
- 共用 DB 啟動、備份、管理使用共用目錄 `scripts/db.py`。先確認狀態，不因單一應用重建而停止、刪除或重設其他專案使用的服務。

- HUD 入口為 `bridge/microduck_hud.py`，接收 FPS 是最近一秒有效 SRT 數；兩個原始搖桿軸為左 CH1/CH2、右 CH4/CH3。runtime 的啟動擴充補丁保存在 `patches/microduck-body-module.patch`。

- 影像服務 `bridge/camera757.py` 隨模擬器啟動，640×360 完整 JPEG FF/45；UDP 8800 接收、1234 送出至相機訂閱來源 Port。`MICRODUCK_VIDEO=0` 可停用，勿與 `DUCK_SIM_CAMERAS` 同時啟用。HUD ON 與 TX FRAMES 不是手機解碼成功；查看 PEER，127.0.0.1 是本機測試。

## 跨平台與四語入口

- 共用路徑／IP 在 bridge/platform_support.py；既有 Mac 短路徑保留，其餘預設依 Repo hash 產生。不要另寫平台專用 IPC 預設路徑。
- Linux 為原生 POSIX，Windows 為 WSL2 Ubuntu＋PowerShell 前端，不宣稱原生 Windows robotd 支援。
- 公開 README／安裝／How-To 以 scripts/generate-docs.py 產生四語版本；修改文字後重新產生。歷史研究與原始驗證資料保留原文。
- tests/linux.Dockerfile 的容器測試不代表完整 Linux GUI／WSL 驗收；目前的驗證界線見 docs/validation/2026-11-06-cross-platform.md。

## 圖形安裝包

- packaging/version.txt 固定 preview 版本；packaging/make_payload.py 以允許清單建立 payload，必須保留 POSIX 路徑與 Unix executable bits。dist/、Windows bin/obj/ 不提交。
- 發行前以 Preview installers workflow 編譯兩平台並取 SHA256。沒有憑證時只能標示未具發行者簽章的測試版，不宣稱已公證／Windows 實機驗收。
- GUI 取得同意後才開始下載與套件安裝；ready receipt 必須等整個流程與校驗成功後才寫 true。桌面啟動器不可為排除 Port 衝突而停止其他工作區。
