# ファンコンケース

**正本は [source/freecad_fan_controller.py](source/freecad_fan_controller.py) です。** 冒頭の寸法・設定と、それに続く形状コードを編集します。

| 用途 | ファイル |
|---|---|
| 寸法・形状の編集 | [freecad_fan_controller.py](source/freecad_fan_controller.py) |
| FreeCADで生成を実行 | [FanControllerCase.FCMacro](source/FanControllerCase.FCMacro) |
| FCStd・STEP・STL・検査結果の出力 | [build_fan_controller.py](source/build_fan_controller.py) |
| プレビュー画像の生成 | [render_preview.py](source/render_preview.py) |

FreeCADでマクロを実行すると、`build/fan-controller/<実行ID>/` に新規出力します。FCStdとSTEPは組立座標、STLは本体を底面下・蓋を天面下・独立押さえを平置きにして原点へ接地した座標です。`manifest.json` が成功状態であることを確認してください。出力はGit管理対象外です。

## 本体を骨格にするラック向けのねじ不要案

[本体骨格案](../spark-rack/docs/本体を骨格にする再設計.md)は、正本の `screwless_case_parts()` を使います。基板押さえ4か所を蓋と一体にし、本体・蓋のねじ穴を加工しない形状を返します。受け台と一緒に解除式結束バンド2本で留めます。基板と端子台の寸法は同じ正本を引き継ぎます。

`mise run body-frame:spark-rack` で組立参考形状と検査結果を生成します。ねじ不要案の造形用ファイルはまだ出力しません。参考形状では基板投入と蓋の差し込みを検査しています。実物のはめ合い、基板裏面の部品配置、バンドを通す操作は未検証です。以下の単独ケース用マクロ・生成手順と取付仕様は、従来のねじ式を維持したものです。

## 基板の固定：本体側のねじ留め押さえ

試作で折れた蓋の薄板（厚さ0.9mm・長さ15.07mm）は廃止しました。厚さ3mmの独立押さえを本体の着座ポケットにねじ留めし、基板の縁へ0.8mm掛けます。基板の受け位置・高さは従来どおりです。ねじの締付けは着座面で受け、基板上面には0.20mmの遊びを残します。基板への穴あけは不要です。

| 部品 | ケース1組の必要数 |
|---|---:|
| `CaseBody.stl` | 1 |
| `CaseLid.stl` | 1 |
| `PCBClamp.stl` | 4（同形。反対側は180度回転して組み付け） |
| M2×6mmなべ小ねじ（並目0.4mm） | 蓋4本＋押さえ4本＝8本 |

本体の下穴は印刷後に切削タップで加工します。[工具・試験片・加工手順](docs/タップ加工.md)を確認してください。

押さえ用ねじ頭は外径4mm以下・高さ1.6mm以下を想定しています。下穴1.6mmは仮値で、使用するねじと印刷材料で確認してください。M4ラック用ねじとは別です。

組立は、基板を受けまで入れる → 押さえ4個を着座面に置く → 各1本のねじで固定 → 蓋を取り付ける、の順です。蓋ねじの位置を変更しているため、本体・蓋は今回生成した組を使います。旧版との混用はできません。

CADでは単一ソリッド、基板・本体・蓋・端子台との干渉、着座面、ねじ頭・ドライバーの空間、上からの着脱を検査します。基板縁の部品・はんだと押さえの実物適合、折れにくさ、繰り返し締結の強度は未検証です。既定の3MF生成は各種類1個なので、押さえ4個を作る場合は `mise run 3mf:prototype:fan-controller -- --part PCBClamp --copies 4` を使います。

プレビューはFreeCAD対応Pythonとmatplotlib・numpyのある環境で `render_preview.py <今回の出力フォルダ>` を実行します。現在の正本から生成するため、同じ設計版の出力先を指定してください。画像は補助資料で、形状の正本ではありません。

元の `designs/fan-controller/FanControllerCase.FCMacro` の形状コードはそのままPythonへ移しました。元マクロ、既存プレビュー、過去の検査記録は [取り込み時のアーカイブ](../../archive/fan-controller-import/README.md) に保全しています。元worktreeは変更していません。今後の編集先はこの `source/` です。

USB-Cは今回の実測値に反映済みです。端子台の逃げ、ファン・温度センサー開口には未修正の箇所が残ります。実物の適合・操作性は未検証です。

## ラックへの取り付け

ケース底部の外側に取付耳を設け、M3穴ピッチ92mmで共通ドックへ固定します。箱本体81.4×39.4mmに対し、耳を含む長さは100mmです。本体ラックは `controller_dock.stl`、アダプターラックは `accessory_plate.stl` として同じドック形状を出力します。[取付方法と必要金具](docs/ラックへの取り付け.md)を参照してください。

## ライセンス

[Apache License 2.0](../../LICENSE)

Copyright 2026 IDEO PLUS LLC
