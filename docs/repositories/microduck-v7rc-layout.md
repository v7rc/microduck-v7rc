# microduck-v7rc 獨立整合 Repo

整理日期：2026-11-06（Asia/Taipei）。使用者指定 remote：`git@github.com:v7rc/microduck-v7rc.git`。

## 配置與版本

工作區根目錄保持多 Repo 容器；新增 `microduck-v7rc/` 獨立管理 bridge、scripts、patches、tests、docs。原 root README／AGENTS 保留工作區規則與新入口；root docs 的分類連結至此 Repo 的同一份文件。

現有兩個上游 Repo、Python .venv 與工具保留原位置，避免破壞已安裝環境中的絕對路徑。整合 Repo 內的 `microduck`、`microduck_rl`、`.tools` 是不提交的本機 symlink，可執行 `scripts/link-workspace` 重建。`.runtime` 實際移入整合 Repo、被 Git 忽略，工作區原 `.runtime` 保留相容連結。

上游不作為本 Repo 的檔案或 Git submodule；來源與驗證 commit 明確列於 `upstream-revisions.json`。從空環境可依安裝文件 clone 指定版本至整合 Repo 內，或另在同層 clone 後連結。這與 Git submodule 的差別是 clone 整合 Repo 不會自動取得上游，必須依文件安裝。選擇此方式是為了保持目前多個獨立 Repo 的目錄與本機依賴位置。

短路徑 `/tmp/microduck-m4-<UID>` 經確認屬於本工作區後，改指向整合 Repo；兩個上游與工具透過 symlink 解析至原位置。歷史測試中的 workspace-root 命令，現在須先進入 `microduck-v7rc` 再執行；歷史 JSON 的來源路徑／時間保留原始紀錄，不代表新 checkout 的相對路徑。

上游仍為 microduck main `98ce17e4868ba9370713c4d11f3d934e5a1b7687`、microduck_rl develop `bae39f5900b318f7e87fc485c30a31213cfa14eb`。runtime 仍只保留 `patches/microduck-body-module.patch` 的兩行本機修改；本次未修改模擬器核心或行走策略。

## 本次檢查

目錄移動後的測試、模擬器啟動與 Git 發佈結果在整理完成後補記。工具／策略／venv／socket／快取及執行日誌不納入 Git；docs/validation/evidence 中的選定驗證證據則保留供研究追溯。

## 移動後驗證

- `scripts/link-workspace` 重跑確認三個連結皆指向既有來源，沒有覆寫上游目錄。
- 18 項隔離測試全部通過，包含真實暫用 UDP／Unix socket 與相機 JPEG 測試，紀錄見 [tests.txt](../validation/evidence/2026-11-06-repo-layout/tests.txt)。
- 從新 Repo 啟動模擬器與控制橋接，robotd healthy、50/50 Hz、0 missed，起身站立成功；原生視窗已帶到前台，確認右上 IP=192.168.52.77、UDP 6188／8800，左上 FPS／相機／搖桿 HUD 正常。
- 移動後尚未重新執行走路／轉向或手機影像驗收；先前一般 Wi-Fi 下手機驗收是歷史紀錄，與本次啟動檢查分開。
- Git 忽略檢查確認 microduck、microduck_rl、.tools、.runtime 不納入首次發佈；根目錄工作區不建立 Git Repo。
