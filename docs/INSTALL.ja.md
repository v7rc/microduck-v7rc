# インストールガイド

[繁體中文](INSTALL.zh-TW.md) | [简体中文](INSTALL.zh-CN.md) | [English](INSTALL.en.md) | [日本語](INSTALL.ja.md)

macOS Apple Silicon ではシミュレーション、スマートフォン操作と映像表示を確認済みです。Linux ネイティブの導入・起動処理を実装し、分離コンテナーの試験結果は別途記録します。実機のデスクトップ、GPU、スマートフォン通信は対象 PC での確認が必要です。Windows 11 では WSL2 Ubuntu＋WSLg を使い、PowerShell 起動スクリプトを提供します。Windows ネイティブ版 robotd ではなく、Windows 実機での受け入れ確認は未実施です。

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

Mac：DMG 内の Microduck V7RC を開き、言語を選んで環境を確認します。必要な Apple 開発ツール、Homebrew／CMake／pkg-config、固定版上流、Rust、Python、依存関係を表示します。導入／修復を選び確認してから取得を開始します。端末でシステムの確認とパスワード入力を行ってください。全手順の成功後だけ完了状態を記録し、ユーザー Applications に App をコピーしてデスクトップアイコンを作成します。

Windows：EXE を開き、環境確認後に導入を承認します。WSL／Ubuntu がなければシステム導入を開始します。再起動を求められたら完了後に再度開いてください。Ubuntu で一般 Linux ユーザーの初期設定後、シミュレーターを導入します。Linux パッケージには sudo パスワードが必要な場合があります。成功後はアイコンから本体とブリッジを起動できます。他の WSL を停止したりファイアウォールを自動変更したりしません。スマートフォン通信には前述の mirrored networking と UDP 規則を設定してください。

導入済みならアイコンから自動起動し、端末に取得・ビルド・実行内容を表示します。初回導入時に runtime のビルドと方策取得を行います。6188／8800／1234 が使用中なら通知して停止し、他プロジェクトを自動停止しません。停止ボタンまたは実行端末を閉じて終了できます。

未署名／未公証プレビューのため、OS の信頼確認が表示される場合があります。本番配布には組織の署名を使用してください。Mac データは ~/Library/Application Support/MicroduckV7RC、Windows 本体は %LocalAppData%/Programs/MicroduckV7RC、シミュレーターは Ubuntu ~/.local/share/microduck-v7rc に置きます。バージョン別ディレクトリを使い、研究 Repo を移動・上書きしません。

## 前提条件

推奨環境は Ubuntu 24.04 デスクトップ／WSL2 Ubuntu-24.04、Linux x86_64 または aarch64 です。Git、curl、C/C++ ツールチェーン、CMake、pkg-config、OpenSSL／udev／ALSA 開発パッケージ、OpenGL／EGL が必要です。GUI にはドライバーと DISPLAY／Wayland、ヘッドレスのカメラ描画には動作する EGL 構成が必要です。単体シミュレーションと推論用であり、GPU 学習環境の導入ではありません。

## Linux への導入

以下のシステムパッケージには管理者権限が必要です。setup は sudo の実行やファイアウォール変更を自動では行いません。

```
sudo apt-get update
sudo apt-get install -y git curl python3 build-essential cmake pkg-config \
  libssl-dev libudev-dev libasound2-dev libgl1 libegl1 libgl1-mesa-dri libglfw3
```

## 新規環境への Repo 取得

setup はプロジェクト内に uv 0.13.7、Rust 1.94.1、Python 3.12.16 を導入し、上流 commit を取得してパッチを適用し、上流 uv.lock で依存関係を導入します。初回ダウンロードと Rust コンパイルには時間と数 GB の空き容量が必要です。既存の上流 HEAD が異なる場合は停止し、reset、ユーザー変更の上書き、他プロジェクトの停止は行いません。初回起動で公式方策をダウンロードするため、GitHub、Rust、PyPI、Hugging Face への接続が必要です。

```
git clone https://github.com/v7rc/microduck-v7rc.git
cd microduck-v7rc
scripts/setup --check
scripts/setup
```

## Windows 11／WSL2 への導入

Windows 11 22H2 以降で仮想化を有効にし、最新の WSL2 と GPU ドライバーを使用してください。管理者 PowerShell で Ubuntu-24.04 を導入し、必要なら再起動後、Ubuntu 端末で Linux の手順を実行します。Repo は Linux のホームに置き、/mnt/c 上での実行や Windows の Python .venv の共用は避けてください。WSLg が GUI を提供します。

```
wsl --install -d Ubuntu-24.04
wsl --update
```

## Windows のスマートフォン向け UDP 設定

スマートフォンから WSL への UDP 接続が必要です。既存の %UserProfile%\.wslconfig の [wsl2] に mirrored networking を追加し、他の設定を保持します。すべての WSL 作業を保存してから wsl --shutdown を実行（全ディストリビューションが停止）し、Ubuntu を開き直します。必要な場合だけ UDP 6188／8800 の規則を追加し、ファイアウォール全体を無効にしないでください。

```
[wsl2]
networkingMode=mirrored
```

## Windows のスマートフォン向け UDP 設定 / PowerShell

スマートフォンから WSL への UDP 接続が必要です。既存の %UserProfile%\.wslconfig の [wsl2] に mirrored networking を追加し、他の設定を保持します。すべての WSL 作業を保存してから wsl --shutdown を実行（全ディストリビューションが停止）し、Ubuntu を開き直します。必要な場合だけ UDP 6188／8800 の規則を追加し、ファイアウォール全体を無効にしないでください。

```
wsl --shutdown
```

## Windows のスマートフォン向け UDP 設定 / Firewall

Windows の規則は同等の規則がなく、信頼できる Private ネットワークの場合に管理者 PowerShell で手動実行します。WSL の Hyper-V 規則も別に示します。コマンドがない場合は Windows／WSL を更新してください。Linux は実際に有効なファイアウォールでスマートフォンから 6188／8800 への接続を許可します。

```
New-NetFirewallRule -DisplayName "Microduck V7RC UDP" -Direction Inbound -Action Allow -Protocol UDP -LocalPort 6188,8800 -Profile Private -RemoteAddress LocalSubnet
New-NetFirewallHyperVRule -Name "MicroduckV7RC" -DisplayName "Microduck V7RC WSL" -Direction Inbound -VMCreatorId '{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}' -Protocol UDP -LocalPorts 6188,8800 -Action Allow
```

## 任意の PowerShell 起動スクリプト

Windows から読める本 Repo の windows/ で実行できます。LinuxRepo は WSL 内の絶対パスで、既定は Linux ホーム直下の microduck-v7rc です。複数 NIC や VPN がある場合はスマートフォンから到達できる Windows LAN IPv4 を指定します。Ubuntu 端末で 2 つの Shell コマンドを直接実行する方法も使えます。

```
.\microduck-v7rc.ps1 -Action Serve -Distribution Ubuntu-24.04 -LinuxRepo /home/louis/microduck-v7rc -AdvertiseIP 192.168.1.20
.\microduck-v7rc.ps1 -Action Bridge -Distribution Ubuntu-24.04 -LinuxRepo /home/louis/microduck-v7rc -AdvertiseIP 192.168.1.20
```

## macOS の既存環境

導入済みツールと上流 Repo の場所を維持し、リンク後に setup --check を実行します。今回の変更のために環境全体を再インストールする必要はありません。新規 Mac は先に Xcode Command Line Tools を導入し、同じ setup を実行します。 新規 Mac には CMake と pkg-config も必要です。Homebrew 導入済みなら brew install cmake pkg-config を実行します。例の 192.168.1.20 と /home/louis は自分の IP とパスに置き換えてください。

```
scripts/link-workspace
scripts/setup --check
```

## 導入後の確認

doctor はプラットフォーム、公開用 IP、IPC socket、描画環境を表示します。VPN、複数 NIC、WSL で IP が適切でない場合は MICRODUCK_ADVERTISE_IP を指定します。表示先 IP だけが変わり、経路やファイアウォールは変更しません。IP 変更後はアプリの操作・カメラ両方を更新し、スマートフォンの送信元 IP 変更後はブリッジを再起動します。

```
scripts/microduck-sim doctor
microduck_rl/.venv/bin/python -m unittest discover -s tests -v

MICRODUCK_ADVERTISE_IP=192.168.1.20 scripts/microduck-sim serve
```

## 起動と接続 — 1

起動後にロボットが立ち、端末に healthy が表示されます。中立パケットの受信後は LIVE となり、スティックは生の入力を示します。アプリで映像を開くと CAMERA ON、スマートフォンの PEER、増加する TX FRAMES で PC の送信を確認できます。

```
scripts/microduck-sim serve
```

## 起動と接続 — 2

シミュレーターの端末を開いたまま、別の端末でブリッジを起動します。スマートフォンと PC を同じ Wi-Fi ルーターに接続し、アプリの操作とカメラの両方にシミュレーター右上の IPv4 を設定します。

```
scripts/v7rc-bridge
```

## アプリ設定とチャンネル

固定のサンプル IP ではなく現在の LAN IPv4 を使用します。操作は Wi-Fi UDP／SRT／6188、カメラは UDP／8800 です。1234 は PC の映像送信元 Port で、アプリに設定する宛先 Port ではありません。

CH1 は旋回、CH2 は前後、CH3 は頭部上下（反転）、CH4 は頭部左右です。範囲 1000–2000、中立 1500。起動、通信断、再接続後は全 4 チャンネルを中立に戻すまで操作を再開しません。

## 受け入れ確認

対象 PC で、起立／health → 全軸中立 → 前後・旋回 → 頭部上下・左右 → 映像と向き → 閉じて再開 → 入力停止後の中立保護を順に確認します。OS、アーキテクチャ、GPU、IP、上流 commit と結果を記録してください。Linux コンテナー試験は GUI／スマートフォン確認の代用ではなく、PowerShell 構文確認も実際の WSL 試験の代用ではありません。

## 参照先（確認日：2026-11-06）

- [WSL installation](https://learn.microsoft.com/en-us/windows/wsl/install)
- [WSLg](https://learn.microsoft.com/en-us/windows/wsl/tutorials/gui-apps)
- [WSL networking / mirrored](https://learn.microsoft.com/en-us/windows/wsl/networking)
- [Hyper-V firewall](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/hyper-v-firewall)
- [MuJoCo](https://github.com/google-deepmind/mujoco)
