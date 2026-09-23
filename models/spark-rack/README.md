# Spark本体ラック

**正本は `source/` のPython設計コードと寸法定義です。**

| 用途 | ファイル |
|---|---|
| 寸法・隙間 | [spark_rack_parameters.py](source/spark_rack_parameters.py) |
| 部品形状・組立配置 | [freecad_spark_rack.py](source/freecad_spark_rack.py) |
| FreeCADで生成 | [run_spark_rack.FCMacro](source/run_spark_rack.FCMacro) |
| 検査 | [validate_spark_rack.py](source/validate_spark_rack.py) |

出力先は `build/spark-rack/<実行ID>/`。FCStd・STEP・STL・画像・検査結果・manifestを保存します。旧FCStdを読み込まず、Pythonの形状定義から生成します。生成FCStdの寸法表は生成時の記録で、編集によって形状が連動するものではありません。変更はPythonへ反映して再生成してください。

現在の接合隙間は0.30mm、ファンは140mmです。0.20mmへの変更は今回のコード移行に含みません。実物の強度・冷却は別途確認が必要です。

[印刷設定](../../print-projects/README.md) と [移行前データ](../../archive/spark-rack-fcstd-v1/README.md) は別管理です。

新版の側板にはファンコン用M4穴を追加しています。`controller_dock.stl` を介して、各ファンのケースをラック外側へ固定します。[取付位置と金具](../fan-controller/docs/ラックへの取り付け.md)を参照してください。旧側板を使用する場合は追加穴加工または新版への交換が必要です。

前面は幅210mmのフレームと外形を揃え、側枠と同じ幅12mmの外周をファン保持部へ一体化しています。高さ162mmの前面枠は、170mmの側枠に対して上下4mmずつ内側です。ファン取付穴・送風開口・保持部の接合位置は維持しています。

## ライセンス

[Apache License 2.0](../../LICENSE)

Copyright 2026 IDEO PLUS LLC
