# DGX Spark Rack

DGX Sparkを最初は2台、最終的に2段×2列で4台置く、3Dプリント用ラックの設計です。電源アダプターは別置きとし、各ユニットに140mmファンを取り付けます。

**設計の正本はPythonコードと寸法定義、FCMacroは生成の入口とします。** この方式はアダプタースタンドで実装済みです。本体ラックv1はまだコードへ移行していないため、[既存FCStd](DGX-SPARK-RACK-FREECAD-v1.FCStd)を形状の基準として保持します。実物の適合・耐荷重・冷却性能は試作で確認します。

電源用の次版は[アダプターラックv2](docs/ACアダプターラックv2.md)です。1台単位で縦横に連結し、120mmファンを列ごとに取り付けます。ファンコン用の着脱式取り付け面も含めています。

## 始める

1. FCStdをFreeCADで開きます。
2. [FreeCAD版の操作](docs/FreeCAD版の操作.md)で組立と個別部品の表示方法を確認します。
3. [接合用の試験片](exports/freecad/stl)を印刷し、[試作ガイド](docs/試作ガイド.md)に沿って1台分から組み立てます。

## データの役割

| 場所 | 役割 |
|---|---|
| `DGX-SPARK-RACK-FREECAD-v1.FCStd` | コード移行前のラックv1の形状基準。寸法表は形状に非連動 |
| `DGX-SPARK-ADAPTER-STAND-v1.FCStd` | 既存スタンドv1の保存済み生成物 |
| `exports/freecad/stl/` | 印刷部品12種類。単位mm |
| `exports/freecad/parts/` | 個別部品を他のCADへ渡す汎用STEP |
| `exports/freecad/` | 組立STEP、配置画像、ファイル一覧、STL検査記録 |
| `scripts/freecad_mcp.py` | FreeCAD MCPへの接続 |
| `scripts/check_stl.py` | 印刷用STLの形状検査 |
| `exports/adapter-stand/` | 既存スタンドv1の保存済みSTL・画像・検査記録 |
| `scripts/freecad_adapter_stand.py` / `freecad_features.py` | 履歴付きモデルを定義する設計コード |
| `scripts/adapter_stand_parameters.py` | 設計寸法と派生式の正本 |
| `design/adapter-stand/adapter_spec.json` | 参照する電源の実測値・出典。生成物から独立した入力資料 |
| `scripts/run_adapter_stand.FCMacro` | FreeCADで実行する生成入口 |
| `build/adapter-stand/` | 実行ごとのFCStd・STEP・STL・検査結果。Git管理対象外 |
| `scripts/freecad_adapter_rack.py` / `adapter_rack_parameters.py` | 縦横連結アダプターラックv2の形状・寸法の正本 |
| `scripts/run_adapter_rack.FCMacro` | v2の生成入口。`build/adapter-rack/` へ出力 |

[ACアダプタースタンド](docs/ACアダプタースタンド.md)は寸法表で試行でき、2台から4台へ横に増設できます。採用する寸法は設計コードへ戻します。

## 設計から生成する

1. FreeCAD GUIで `scripts/run_adapter_stand.FCMacro` を開き、実行します。
2. レポートビューに表示された `build/adapter-stand/<実行ID>/` を確認します。
3. `manifest.json` の成功記録と検査結果を確認し、そのフォルダのSTLを試作に使います。

再実行時も別のフォルダへ生成するため、既存FCStdや印刷用3MFを上書きしません。詳細は[設計コードと生成物の管理](docs/設計コードと生成物の管理.md)を参照してください。

縦横連結と120mmファンを備えるv2は、上の手順のマクロを `scripts/run_adapter_rack.FCMacro` に替えて生成します。旧スタンドとは別フォルダに出力します。

## 変更を記録する

設計コード・寸法定義・参照資料をGitで管理します。採用した生成物を保存するときは、同じ実行の検査結果とmanifestも一緒に保存します。スライサーの3MFは配置・材料・印刷設定の記録で、形状設計の正本とは分けます。既存ラックv1のファイル一覧とハッシュは[manifest.json](exports/freecad/manifest.json)に記録しています。
