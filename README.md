# DGX Spark Rack

DGX Sparkを最初は2台、最終的に2段×2列で4台置く、3Dプリント用ラックの設計です。電源アダプターは別置きとし、各ユニットに140mmファンを取り付けます。

**FreeCADで開くファイルは [DGX-SPARK-RACK-FREECAD-v1.FCStd](DGX-SPARK-RACK-FREECAD-v1.FCStd) です。** 4台の組立と印刷部品12種類を含みます。形状と配置を引き継いだもので、Fusionの設計履歴は含みません。

変換元の正本 [DGX-SPARK-RACK-FUSION-v1.f3d](DGX-SPARK-RACK-FUSION-v1.f3d) は保持しています。実物の適合・耐荷重・冷却性能は試作で確認します。

## 始める

1. FCStdをFreeCADで開きます。
2. [FreeCAD版の操作](docs/FreeCAD版の操作.md)で組立と個別部品の表示方法を確認します。
3. [接合用の試験片](exports/fusion/stl)を印刷し、[試作ガイド](docs/試作ガイド.md)に沿って1台分から組み立てます。

## データの役割

| 場所 | 役割 |
|---|---|
| `DGX-SPARK-RACK-FUSION-v1.f3d` | 変換元・元の設計履歴を保持 |
| `DGX-SPARK-RACK-FREECAD-v1.FCStd` | Fusionから生成した全体形状と印刷部品 |
| `DGX-SPARK-ADAPTER-STAND-v1.FCStd` | ACアダプター用の開放スタンド。実寸確認待ち |
| `exports/fusion/` | STEP・STL・プレビュー・検査記録 |
| `exports/freecad/` | 変換用STEP・全体画像・変換記録 |
| `scripts/fusion_rack_cli.py` | アクティブな正本の検査・書き出し |
| `scripts/fusion_mcp.py` | Fusion組み込みMCPへの接続 |
| `scripts/check_stl.py` | 書き出したSTLの形状検査 |
| `comparison/freecad/` | FreeCADへの移行試験用データと比較結果 |
| `comparison/freecad-native-crossbar/` | FreeCADで作り直した履歴付き支持棒と検査記録 |
| `comparison/freecad-native-sideplate/` | FreeCADで作り直した履歴付き左側板と検査記録 |

旧モデルと初期生成用データは削除しました。比較用のCADデータを作る場合も、設計マスターとは分けて扱います。

## 変更を記録する

変更時には、対象部品・パラメーター・検査結果を記録し、CADファイルと派生データを一緒にGitへコミットします。CAD比較は終了し、Fusionの正本を保持したままFreeCADファイルを生成しています。Fusionで履歴を編集する場合は[操作ガイド](docs/Fusion版の操作.md)を参照してください。

[CAD比較](docs/CAD比較.md)に、形状の一致、引き継げない設計履歴、読み込み時間、macOSのクラッシュをまとめています。

[FreeCAD支持棒の評価](docs/FreeCAD支持棒の評価.md)では、支持棒1種類を履歴付きで作り直し、寸法変更と保存後の再編集を確認しています。

[FreeCAD側板の評価](docs/FreeCAD側板の評価.md)では、窓・差込口・固定穴・丸みを含む左側板を再構築し、7種類の寸法変更と再編集を確認しています。

[ACアダプタースタンド](docs/ACアダプタースタンド.md)は、本体ラックと分けて横に置く開放型です。2台から4台へ増設でき、ファン用ブラケットの取付部を用意しています。アダプターの実寸は未確認です。
