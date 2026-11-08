# Microduck × V7RC 連携

[繁體中文](README.md) | [简体中文](README.zh-CN.md) | [English](README.en.md) | [日本語](README.ja.md)

V7RC アプリから Wi-Fi UDP で Microduck シミュレーターを操作し、640×360 の頭部カメラ映像を受信します。SRT 4 チャンネルブリッジ、受信 FPS、左右スティック、接続先 IP／Port、送信フレーム数の HUD を含みます。

## 操作パネルと操作感の比較

デスクトップのショートカットから操作パネルを開き、自由練習または S 字迷路を選びます。キーボード、V7RC アプリ、自作の UDP プログラムを使えます。起動・停止・スタート地点への復帰、接続状況、シミュレーターと同期するストップウォッチ（`分:秒.ミリ秒`）を利用できます。アプリ、シーン、ONNX モデル、制御設定の更新には GitHub Releases を使用します。Schema 2 対応版では制御設定だけを更新できます。

操作パネルでは、制御カーブと歩行モデルを個別に選べます。内蔵カーブ、線形カーブ、ダウンロードした設定、対応する ONNX モデルを選び、起動またはスタート地点への復帰を押して同じシーンで比較できます。シミュレーターの左下にアプリのバージョンを表示します。Mac と Windows のインストーラーは繁体字中国語、簡体字中国語、英語、日本語に対応し、選択を記憶します。操作パネルの MuJoCo 内部ポートを分け、検証した Mac で自由練習の旋回が不安定になる問題を解消しました。

## ダウンロードと導入

**現在のバージョン: `0.1.0-preview.8`** · [GitHub Release](https://github.com/v7rc/microduck-v7rc/releases/tag/v0.1.0-preview.8)

| プラットフォーム | インストーラー | チェックサム |
| --- | --- | --- |
| macOS 13+ · Apple Silicon / Intel | [MicroduckV7RC-0.1.0-preview.8-macOS-universal.dmg](https://github.com/v7rc/microduck-v7rc/releases/download/v0.1.0-preview.8/MicroduckV7RC-0.1.0-preview.8-macOS-universal.dmg) | [SHA256](https://github.com/v7rc/microduck-v7rc/releases/download/v0.1.0-preview.8/MicroduckV7RC-0.1.0-preview.8-macOS-universal.dmg.sha256) |
| Windows 11 x64 · WSL2 Ubuntu | [MicroduckV7RC-0.1.0-preview.8-Windows-x64.exe](https://github.com/v7rc/microduck-v7rc/releases/download/v0.1.0-preview.8/MicroduckV7RC-0.1.0-preview.8-Windows-x64.exe) | [SHA256](https://github.com/v7rc/microduck-v7rc/releases/download/v0.1.0-preview.8/MicroduckV7RC-0.1.0-preview.8-Windows-x64.exe.sha256) |

取得したインストーラーを開き、環境を確認して導入を承認してください。完了後はデスクトップアイコンから起動できます。この Repo は公開されており、GitHub にログインせずに Release のインストーラーを取得できます。

preview.2 では Mac での導入、デスクトップ起動、V7RC 制御・映像を確認済みです。preview.3 の走行制御の調整は Mac のシミュレーターで 54 試行を完了しました。Windows の WSL2 導入とスマートフォン操作は実機での確認が必要です。

## GUI インストーラーと起動アイコン

GitHub Release から現在の未署名プレビューを取得します。macOS 13 以降は universal DMG、Windows 11 x64 は .NET 同梱 EXE を使用します。Windows のシミュレーターは WSL2 Ubuntu 内で動作します。初回にネット接続と約 20 GB の空き容量が必要なオンライン導入版で、完全なオフライン配布ではありません。

## 対応環境と検証範囲

macOS Apple Silicon ではシミュレーション、スマートフォン操作と映像表示を確認済みです。Linux ネイティブの導入・起動処理を実装し、分離コンテナーの試験結果は別途記録します。実機のデスクトップ、GPU、スマートフォン通信は対象 PC での確認が必要です。Windows 11 では WSL2 Ubuntu＋WSLg を使い、PowerShell 起動スクリプトを提供します。Windows ネイティブ版 robotd ではなく、Windows 実機での受け入れ確認は未実施です。

## クイックスタート

新しい環境では先にインストールガイドを実行してください。Louis の既存 Mac 環境では scripts/link-workspace で同階層の上流 Repo とツールを再利用できます。このコマンドだけでは新規環境を導入できません。以下の相対コマンドは連携 Repo のルートで実行します。

```
scripts/microduck-sim serve
```

シミュレーターの端末を開いたまま、別の端末でブリッジを起動します。スマートフォンと PC を同じ Wi-Fi ルーターに接続し、アプリの操作とカメラの両方にシミュレーター右上の IPv4 を設定します。

```sh
scripts/v7rc-bridge
```

## アプリ設定とチャンネル

固定のサンプル IP ではなく現在の LAN IPv4 を使用します。操作は Wi-Fi UDP／SRT／6188、カメラは UDP／8800 です。1234 は PC の映像送信元 Port で、アプリに設定する宛先 Port ではありません。

CH1 は旋回、CH2 は前後、CH3 は頭部上下（反転）、CH4 は頭部左右です。範囲 1000–2000、中立 1500。起動、通信断、再接続後は全 4 チャンネルを中立に戻すまで操作を再開しません。

## ソースと上流プロジェクト

bridge/ は操作・カメラ・HUD・共通処理、scripts/ は導入と起動、windows/ は WSL フロントエンド、tests/ は試験です。upstream-revisions.json で上流 commit を固定します。上流 Repo、.venv、.tools、.runtime は Git に含めません。依存先は Repo 内の clone または既存環境への symlink です。上流 runtime の起動部分 2 行のみを変更し、物理モデルや歩行方策は変更しません。

## 既知の制限

受信側 iPhone 自身がインターネット共有を提供する構成ではカメラ購読が届かず、共通 Wi-Fi では映像表示を確認済みです。低速歩行、速度追従、直進精度には上流の制限があります。UDP 受信だけで動作精度は保証できません。CAMERA ON と TX FRAMES は購読と PC の送信を示し、アプリ表示は別途確認します。モデルのライセンスは上流 LICENSE-MODELS.md（CC BY-NC-SA 4.0 を含む）を確認してください。

## 資料とテスト

- [インストールガイド](docs/INSTALL.ja.md)
- [操作ガイド — HTML](docs/how-to.html#ja)
- [Validation](docs/validation/2026-11-06-cross-platform.md)

```sh
microduck_rl/.venv/bin/python -m unittest discover -s tests -v
```
