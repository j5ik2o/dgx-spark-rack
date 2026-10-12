# Spark本体ラック

**印刷部品を主構造とする再設計を進めています。** [固定段と独立電源区画の形状候補](docs/固定段ラックの再設計.md)は`mise run redesign:spark-rack`で生成します。本体の段位置は208／428mmに固定し、電源4個は下部へ平置きします。左右の構造面と内側のリブへ支持構造を改め、ファンと制御器の前面をそろえました。支持梁30部品は固定棚・支持床12部品へ統合しています。造形範囲、干渉、交換予約、支持面と操作面を検査します。固定機構と実測は未完成で、造形用のファイルは生成しません。

スイッチの中央・上部・下部は[専用段の配置比較](docs/スイッチ専用段の配置比較.md)で確認できます。`mise run compare-switch:spark-rack`は外形と交換空間の比較を生成します。固定段を保つ条件では上部追加を推奨候補とし、中央の詳細形状は比較基準として維持しています。

最終接続は[CRS812 1台と2m分岐ケーブル](docs/最終接続構成.md)です。136部品案は不採用です。`mise run overview:spark-rack`は[再設計前の全体構想](docs/凹凸の接合試験片と次案.md)の比較画面です。最終配線の実経路を示したものではありません。試験片の印刷は後回しです。`joint:spark-rack`または`structure:spark-rack`は短い試験片だけを生成します。

[設計条件](docs/4台専用ラックの設計条件.md)と[配置参考](docs/仮配置の確認.md)を参照してください。配置参考の下段高さと制御ケース位置は次案の共通定義へそろえ、未測定の横ずれは製造穴に採用しません。

以下は従来の連結式ラックの操作案内です。[従来データは一式保全済み](../../archive/spark-rack-modular-20261009/README.md)です。

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
