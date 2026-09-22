# FreeCADでの生成と確認

1. [run_spark_rack.FCMacro](../source/run_spark_rack.FCMacro) をFreeCADで実行します。
2. `build/spark-rack/<実行ID>/` の `manifest.json` と検査結果が成功していることを確認します。
3. 同じフォルダの `DGX-SPARK-RACK.FCStd` と配置画像で形状を確認します。
4. 印刷には同じ実行の `stl/` 内の個別部品を使います。購入部品の参照形状を含む組立全体は印刷しません。

寸法変更は [spark_rack_parameters.py](../source/spark_rack_parameters.py)、形状変更は [freecad_spark_rack.py](../source/freecad_spark_rack.py) に反映して再生成します。生成FCStdの寸法表は記録用で、形状と連動しません。

STLの閉じた形状などのCAD検査と、実物の適合・強度・冷却は別です。[試作ガイド](試作ガイド.md) も参照してください。
