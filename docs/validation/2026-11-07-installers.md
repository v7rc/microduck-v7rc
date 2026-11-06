# 2026-11-07：圖形安裝包與桌面啟動器

版本：0.1.0-preview.1。使用者確認先製作未簽署測試版。Mac 是原生 AppKit universal App／DMG；Windows 是 WPF／.NET 10 自含執行環境的 x64 EXE，模擬器仍在 WSL2 Ubuntu-24.04。

## 行為

- GUI 先列環境、缺少的系統套件、下載清單與版本化安裝位置，使用者確認才開始。取消不啟動安裝。
- 獨立安裝資料不覆寫現有研究工作區。已有不同版本或非安裝程式擁有的目錄會停止並報告，不 reset 上游或覆蓋使用者修改。
- Mac 系統工具或 Homebrew 缺少時在終端機引導，Windows 缺 WSL／Ubuntu 時啟動 Windows 系統安裝。重新開機與 Ubuntu 一般帳號初始化由使用者完成。密碼由使用者在系統／sudo 提示輸入，安裝程式不儲存。
- setup --prepare-simulator 先下載上游、固定工具及 locked 依賴，編譯 runtime 並取得策略；檔案校驗與整個流程成功後才寫入 ready receipt。失敗時不能產生成功收據。
- 成功後建立桌面圖示。啟動器同時管理模擬器與橋接，拒絕占用中的 6188／8800／1234／7801；中斷／關閉終端機時先要求橋接中立，再停止自己的模擬器。
- 不自動修改 Windows mirrored networking 或防火牆，也不停止其他 WSL 發行版；手機網路設定依四語安裝指引完成。
- 圖示為本 Repo 自行繪製的機器鴨圖樣，沒有複製上游模型／Logo。

## 打包

- packaging/make_payload.py 僅納入執行程式、補丁、版本清單與公開操作文件。排除上游 clone、.tools、.runtime、Git 資料、金鑰及測試快取。
- ZIP 路徑固定 POSIX 格式、文字固定 LF 換行、權限固定 Unix executable bits，因此 Windows 打出的 payload 也可在 Linux 解壓後執行。來源 manifest 列出各檔 SHA256。
- Mac binary 使用 arm64／x86_64 合併；本機為 ad-hoc code signature，沒有 Developer ID 或 Apple 公證。Windows EXE 沒有發行者簽章。這是需網路的 bootstrap installer，不是完整離線模擬器。
- Preview installers workflow 會產生 DMG／EXE／SHA256，artifact 保存 30 天並需 GitHub 登入下載；本次沒有發布正式 GitHub Release。

## 已驗證與待驗收

- Mac 本機 28 項測試通過，其中 Linux 專用安裝 transaction 在 Mac 略過；另有既有快取的 runtime 預編譯／策略檢查通過。
- 原生 Mac App 可開啟，顯示完整計畫、確認對話框；按取消回到未安裝狀態、Launch 保持停用。沒有因此執行安裝或寫入使用者的實際安裝目錄。
- 本機 universal App 編譯、啟動 self-test、codesign 結構校驗與 DMG checksum 驗證通過。
- Linux transaction 測試以假的 dpkg／id 及隔離 payload 檢查失敗不寫 success、成功後 receipt 正確；桌面 session 測試檢查 SIGHUP 後中立與程序清理。這些不是乾淨主機完整下載安裝的證據。
- Windows 的真實編譯、嵌入 payload／四語／參數 self-test 以 installer workflow 結果為準。完整 Windows WSL、UAC、重開機、Ubuntu 初始化與桌面捷徑操作仍需 Windows 目標機人工驗收。
- Mac 未在這台已有研究環境的機器重複下載整套依賴；乾淨 Mac 的系統套件安裝及最後桌面圖示啟動仍需目標機驗收。

證據：[Mac 測試](evidence/installers/macos-tests.txt)、[Mac 安裝計畫畫面](evidence/installers/macos-installer-preview.png)。下載與最新建置狀態見 [Preview installers](https://github.com/v7rc/microduck-v7rc/actions/workflows/installers.yml)。
