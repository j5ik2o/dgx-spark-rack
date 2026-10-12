# Spark本体＋CRS812 一体ラック 提案v2（案A）

DGX Spark 4台・CRS812 DDQ・電源アダプター4個・ファン6個・コントローラー6個とその電源・電源タップを一つのラックへ収める独立提案です。既存の `models/spark-rack/` には依存せず、既存ファイルも変更していません。

| 用途 | ファイル |
|---|---|
| 寸法定義 | [source/rack_v2_parameters.py](source/rack_v2_parameters.py) |
| 部品配置 | [source/rack_v2_layout.py](source/rack_v2_layout.py) |
| 検査 | [source/rack_v2_checks.py](source/rack_v2_checks.py) |
| 図 | [source/draw_rack_v2.py](source/draw_rack_v2.py) |
| 生成入口 | [source/build_rack_v2.py](source/build_rack_v2.py), [source/run_rack_v2.FCMacro](source/run_rack_v2.FCMacro) |
| 仕様・出典 | [reference/specs_v2.json](reference/specs_v2.json) |
| 提案書 | [docs/設計提案.md](docs/設計提案.md) |
| 数量表 | [docs/数量表.csv](docs/数量表.csv) |

生成（FreeCAD 1.0系）:

```sh
freecadcmd -c "import os;os.environ['RACK_V2_SRC']='$PWD/models/spark-rack-v2/source';exec(open('models/spark-rack-v2/source/build_rack_v2.py').read(),{'__name__':'__main__'})"
```

出力は `build/spark-rack-v2/<実行ID>/`（FCStd×2、STEP、図PNG/SVG、3D HTML、parts.json、validation.json、manifest.json）。造形用STL/3MFは実測前のため出力しません。
