# Spark本体＋CRS812 一体ラック 提案v3「Apple風」（案D）

内部シャーシ（曲げ板）と陽極酸化アルミ外装（大R・前面ラティス・背面格子）の構成です。案A（`models/spark-rack-v2/`）とは独立しており、既存ファイルは変更していません。

| 用途 | ファイル |
|---|---|
| 寸法定義 | source/rack_v3_parameters.py |
| 部品配置 | source/rack_v3_layout.py |
| 検査（干渉・経路・質量・リング・圧損） | source/rack_v3_checks.py |
| 図・レンダリング風画像 | source/draw_rack_v3.py |
| 生成入口 | source/build_rack_v3.py, source/run_rack_v3.FCMacro |
| 仕様・出典 | reference/specs_v3.json |
| 提案書・比較 | docs/設計提案.md |
| 数量表 | docs/数量表.csv |

生成（FreeCAD 1.0系）:

```sh
freecadcmd -c "import os;os.environ['RACK_V3_SRC']='$PWD/models/spark-rack-v3-apple/source';exec(open('models/spark-rack-v3-apple/source/build_rack_v3.py').read(),{'__name__':'__main__'})"
```

出力先は `build/spark-rack-v3-apple/<実行ID>/` です。
- FreeCAD文書（完成形・リング運用）とSTEP
- 正面・側面・背面・上面図（PNG/SVG）、レンダリング風画像（全体スペースグレイ／ゴールド、前面パネルを外した状態）
- 3D HTML、parts.json、validation.json、manifest.json

造形用のSTL/3MFは出力しません。
