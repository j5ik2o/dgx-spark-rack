# ACアダプターラック

**正本は `source/` のPython設計コードと寸法定義です。** 生成したFCStdやSTLを編集して正本にはしません。縦横連結・120mmファン対応のv2が現行の設計試作です。

| 変更したいもの | 編集・実行するファイル |
|---|---|
| 寸法と隙間 | [source/adapter_rack_parameters.py](source/adapter_rack_parameters.py) |
| 部品形状と組立配置 | [source/freecad_adapter_rack.py](source/freecad_adapter_rack.py) |
| CAD検査 | [source/validate_adapter_rack.py](source/validate_adapter_rack.py) |
| 出力処理 | [source/build_adapter_rack.py](source/build_adapter_rack.py) |
| 生成を実行 | [source/run_adapter_rack.FCMacro](source/run_adapter_rack.FCMacro) をFreeCADで実行 |
| 購入品の根拠 | [reference/](reference/)の仕様・出典資料 |

出力先はリポジトリ直下の `build/adapter-rack/<実行ID>/` です。実行ごとに新しいフォルダを作り、FCStd・STEP・STL・画像・検査結果・manifestを保存します。正本を選ぶ際に、この出力フォルダからファイルを選ぶ必要はありません。

[設計と組立](docs/設計と組立.md)で構成・部品表・試作手順を確認できます。実物の適合・耐荷重・冷却は未検証です。旧スタンドは[アーカイブ](../../archive/adapter-stand-v1/README.md)に退避しています。

## ライセンス

[Apache License 2.0](../../LICENSE)

Copyright 2026 IDEO PLUS LLC
