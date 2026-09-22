# ファンコンケース

**正本は [source/freecad_fan_controller.py](source/freecad_fan_controller.py) です。** 冒頭の寸法・設定と、それに続く形状コードを編集します。

| 用途 | ファイル |
|---|---|
| 寸法・形状の編集 | [freecad_fan_controller.py](source/freecad_fan_controller.py) |
| FreeCADで生成を実行 | [FanControllerCase.FCMacro](source/FanControllerCase.FCMacro) |
| FCStd・STEP・STL・検査結果の出力 | [build_fan_controller.py](source/build_fan_controller.py) |
| プレビュー画像の生成 | [render_preview.py](source/render_preview.py) |

FreeCADでマクロを実行すると、`build/fan-controller/<実行ID>/` に新規出力します。FCStdとSTEPは組立座標、STLは本体を底面下・蓋を天面下にして原点へ接地した座標です。`manifest.json` が成功状態であることを確認してください。出力はGit管理対象外です。

プレビューはFreeCAD対応Pythonとmatplotlib・numpyのある環境で `render_preview.py <今回の出力フォルダ>` を実行します。現在の正本から生成するため、同じ設計版の出力先を指定してください。画像は補助資料で、形状の正本ではありません。

元の `designs/fan-controller/FanControllerCase.FCMacro` の形状コードはそのままPythonへ移しました。元マクロ、既存プレビュー、過去の検査記録は [取り込み時のアーカイブ](../../archive/fan-controller-import/README.md) に保全しています。元worktreeは変更していません。今後の編集先はこの `source/` です。

USB/JST開口などに仮寸法が残ります。実物の適合・操作性、およびアダプターラックとの取付は未検証・未設計です。データの統合と機械的な一体化は別作業です。

## ライセンス

[Apache License 2.0](../../LICENSE)

Copyright 2026 IDEO PLUS LLC
