# DGX Spark Rack

DGX Spark本体とACアダプターを置く、3Dプリント用ラックです。**現行モデルは3つです。編集する正本は `models/` にあります。**

## 何を編集するか

| 現行モデル | 正本（SSoT） | 最初に開く案内 |
|---|---|---|
| Spark本体ラック | [source内のPythonコードと寸法定義](models/spark-rack/source/) | [本体ラック](models/spark-rack/README.md) |
| ACアダプターラック | [source内のPythonコードと寸法定義](models/adapter-rack/source/) | [アダプターラック](models/adapter-rack/README.md) |
| ファンコンケース | [source内のPythonコード（冒頭に寸法定義）](models/fan-controller/source/freecad_fan_controller.py) | [ファンコンケース](models/fan-controller/README.md) |

3モデルともPythonを正本とし、FCMacroを実行入口にします。ファンコンケースの設計データは統合済みですが、ラックへの機械的な取り付けは未設計です。

## フォルダは用途で分ける

| フォルダ | 入れるもの | 正本として編集するか |
|---|---|---|
| `models/` | 現行モデルの設計コード・CAD正本、参照仕様、モデル別の説明 | `source/`を編集する。`reference/`は購入品の根拠資料 |
| `build/` | 現行モデルから作ったFCStd・STEP・STL・画像・検査結果 | 編集しない。正本から出力する |
| `print-projects/` | スライサーの3MF。配置、材料、ブリム等の印刷設定 | 印刷条件の変更先。形状の正本ではない |
| `archive/` | 旧アダプタースタンド、採用をやめた印刷配置、過去の生成結果 | 現行設計には使わない |
| `tools/` | 複数モデルで使うCAD補助・検査ツール | 共通処理を変更するときだけ編集 |
| `docs/` | リポジトリ全体の運用ルール | 運用を変更するときに編集 |

`exports/`、`design/`、`scripts/`と直下のFCStdは廃止し、上の用途に応じて移動しました。旧スタンドは[archive/adapter-stand-v1](archive/adapter-stand-v1/README.md)にまとめています。

## コマンドで生成する

```sh
mise trust
mise run doctor
mise run build                 # 全モデルのCAD・STL・検査結果
mise run 3mf:fan-controller     # ケースのCADから、部品別3MFまで生成
```

全モデルの3MFは `mise run 3mf`。部品・個数の指定と生成先は[タスクランナーの案内](docs/タスクランナー.md)を参照してください。3MFはX1C向けPLA試作設定で、スライス前の状態です。

## レビューを始める

1. 上の表で対象モデルを選び、その案内を開く。
2. `source/`で設計を確認する。各モデルの案内に記載した生成マクロをFreeCADで実行する。
3. `build/<モデル名>/`で形状と検査結果を確認する。印刷設定を確認するときだけ[print-projects](print-projects/README.md)を開く。

生成物は各モデルとも `build/<モデル名>/<実行ID>/` に保存し、Gitには含めません。詳細は[正本と生成物の管理](docs/設計コードと生成物の管理.md)を参照してください。
