# DGX Spark Rack

DGX Sparkを最初は2台、最終的に2段×2列で4台置く、3Dプリント用ラックの設計です。電源アダプターは別置きとし、各ユニットに140mmファンを取り付けます。

**CADはFreeCADで管理します。** [DGX-SPARK-RACK-FREECAD-v1.FCStd](DGX-SPARK-RACK-FREECAD-v1.FCStd)に4台の組立と印刷部品12種類を収録しています。全体モデルは取り込んだソリッドで、参考用の寸法表は形状に連動しません。実物の適合・耐荷重・冷却性能は試作で確認します。

## 始める

1. FCStdをFreeCADで開きます。
2. [FreeCAD版の操作](docs/FreeCAD版の操作.md)で組立と個別部品の表示方法を確認します。
3. [接合用の試験片](exports/freecad/stl)を印刷し、[試作ガイド](docs/試作ガイド.md)に沿って1台分から組み立てます。

## データの役割

| 場所 | 役割 |
|---|---|
| `DGX-SPARK-RACK-FREECAD-v1.FCStd` | ラック全体と印刷部品を保持する基準ファイル |
| `DGX-SPARK-ADAPTER-STAND-v1.FCStd` | 履歴付きのACアダプタースタンド。実寸確認待ち |
| `exports/freecad/stl/` | 印刷部品12種類。単位mm |
| `exports/freecad/parts/` | 個別部品を他のCADへ渡す汎用STEP |
| `exports/freecad/` | 組立STEP、配置画像、ファイル一覧、STL検査記録 |
| `scripts/freecad_mcp.py` | FreeCAD MCPへの接続 |
| `scripts/check_stl.py` | 印刷用STLの形状検査 |
| `exports/adapter-stand/` | アダプタースタンドの試作用STL・画像・検査記録 |
| `scripts/freecad_adapter_stand.py` | 履歴付きアダプタースタンドの作成 |

[ACアダプタースタンド](docs/ACアダプタースタンド.md)は寸法表で編集でき、2台から4台へ横に増設できます。現在は電源の実寸確認待ちです。

## 変更を記録する

変更したFCStdと派生データを、検査結果と一緒にGitへコミットします。以前のCAD専用ファイル、変換スクリプト、比較用のモデル・スクリプト・資料は削除しました。現在のラックのファイル一覧とハッシュは[manifest.json](exports/freecad/manifest.json)に記録しています。
