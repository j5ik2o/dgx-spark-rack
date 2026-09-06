# DGX Spark Rack

DGX Sparkを最初は2台、最終的に2段×2列で4台置く、3Dプリント用ラックの設計です。電源アダプターは別置きとし、各ユニットに140mmファンを取り付けます。

**設計の正本は [DGX-SPARK-RACK-FUSION-v1.f3d](DGX-SPARK-RACK-FUSION-v1.f3d) だけです。** Fusionで寸法・形状を編集し、STEP・STL・画像は正本から書き出します。実物の適合・耐荷重・冷却性能は試作で確認します。

## 始める

1. F3DをAutodesk Fusionで開きます。
2. [Fusion版の操作](docs/Fusion版の操作.md)でパラメーターと書き出し方法を確認します。
3. [接合用の試験片](exports/fusion/stl)を印刷し、[試作ガイド](docs/試作ガイド.md)に沿って1台分から組み立てます。

## データの役割

| 場所 | 役割 |
|---|---|
| `DGX-SPARK-RACK-FUSION-v1.f3d` | 唯一の設計マスター |
| `exports/fusion/` | STEP・STL・プレビュー・検査記録 |
| `scripts/fusion_rack_cli.py` | アクティブな正本の検査・書き出し |
| `scripts/fusion_mcp.py` | Fusion組み込みMCPへの接続 |
| `scripts/check_stl.py` | 書き出したSTLの形状検査 |

旧モデルと初期生成用データは削除しました。比較用のCADデータを作る場合も、設計マスターとは分けて扱います。

## 変更を記録する

変更時には、対象部品・パラメーター・検査結果を記録し、正本と派生データを一緒にGitへコミットします。FreeCADへの移行試験中も、Fusionの正本を保持します。
