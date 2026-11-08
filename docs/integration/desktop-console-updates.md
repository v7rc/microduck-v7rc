# 控制台與 GitHub Releases

在 Windows 或 Mac 啟動器按「開啟控制台」。從 Git 工作區開發時，可執行 `scripts/console`。控制台在本機瀏覽器執行，Windows 透過 WSL2 的 localhost 轉發開啟。手機使用面板所列的 UDP 連接埠。

## 發布更新

控制台查詢 `v7rc/microduck-v7rc` 的已發布 Releases。預覽版接受更新的預覽版和穩定版，穩定版接受更新的穩定版。使用版本號比較，並要求同一個 Release 同時提供檔案和其 `.sha256` 校驗檔。Actions 建置的 artifacts 須附到公開的 Release 才能提供更新。

| 類別 | Release 資產 |
| --- | --- |
| Mac | `MicroduckV7RC-<version>-macOS-universal.dmg` 和同名 `.sha256` |
| Windows | `MicroduckV7RC-<version>-Windows-x64.exe` 和同名 `.sha256` |
| 場景包 | `microduck-scenes.zip` 和同名 `.sha256` |
| 模型 | `velstand.onnx` 和同名 `.sha256` |

場景 ZIP 的根目錄放 `scenes.json` 以及每個場景的 `<id>.xml`。JSON 範例為 `{"schema":1,"scenes":[{"id":"corridor","title":"直線走廊"}]}`。XML 根元素為 `worldbody`，只放置靜態基本形狀的 `geom`。控制台會套上目前安裝的 Microduck、地面與相機，再用 MuJoCo 檢查每個場景。每版場景包應包含當版完整的自訂場景清單。

ONNX 資產目前使用既有 VelStand 步態格式，輸入 `obs[1,61]`，輸出 `actions[1,14]`，兩者皆為 float32。控制台會用 CPU 推論驗證格式和有限值，再於下次啟動時交給 robotd。發布前仍應完成站立和走路驗收。場景與模型在校驗成功前使用既有版本。

安裝器下載驗證完成後，Windows 開啟新版 EXE，Mac 掛載新版 DMG，由使用者完成安裝。安裝資料依版本隔離，下載的場景及模型由兩個版本共用。操作和驗收項目見 [HTML 驗收清單](desktop-console-todo.html)。

## 獨立控制設定

從 `0.1.0-preview.5` 起，可以把 `control-profile.json` 和 `control-profile.json.sha256` 附到版本號更高的 GitHub Release。這個 Release 可以只放控制設定資產。控制台會把它列為「控制設定」更新，下載並驗證後在下次啟動橋接時套用。

以 [內建設定](../../bridge/control-profile.json) 為範本。Schema 1 包含轉向死區、四條比例曲線，以及起步輔助的幅度與時間。曲線使用扣除死區後的 0–1 正規化輸入及輸出。更新程式會先校驗 SHA256，再檢查欄位、曲線與數值範圍，驗證完成後才切換設定。版本標籤採同一套預覽版版本號規則。
