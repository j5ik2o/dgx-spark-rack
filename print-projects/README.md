# 印刷設定

このフォルダの3MFはBambu Studioの印刷設定です。**形状の正本は [../models/](../models/) にあります。** 設計変更を3MFだけで完結させません。

本体ラックの保存ファイルには`modular-spark-rack-`を付け、従来の連結式ラック用と分かる名前にしました。内容は変更していません。[4台専用ラック](../models/spark-rack/docs/4台専用ラックの設計条件.md)用の印刷設定は、形状を決めてから作成します。

| 本体ラック用ファイル | 用途 |
|---|---|
| [modular-spark-rack-pla-fit-tests.3mf](spark-rack/prototype/modular-spark-rack-pla-fit-tests.3mf) | 接合と金具の試験片 |
| [modular-spark-rack-pla-frame-without-pins.3mf](spark-rack/prototype/modular-spark-rack-pla-frame-without-pins.3mf) | 側板2枚・支持棒3本。ピンは別印刷 |
| [modular-spark-rack-pla-pin-trial-brim5.3mf](spark-rack/prototype/modular-spark-rack-pla-pin-trial-brim5.3mf) | 固定ピン2本、外側5mmブリム |
| [modular-spark-rack-pla-pins-3-brim5.3mf](spark-rack/prototype/modular-spark-rack-pla-pins-3-brim5.3mf) | 追加ピン3本、外側5mmブリム |
| [modular-spark-rack-pla-fan-cassette.3mf](spark-rack/prototype/modular-spark-rack-pla-fan-cassette.3mf) | 140mmファン用保持部1個 |

いずれもPLA仮組み用の記録です。現在のプリンター・プレート・素材割り当てを確認してから印刷します。旧混在配置とバックアップは [../archive/print-projects/](../archive/print-projects/) に分けました。この一覧は手調整済みの保存ファイルです。3モデルの自動生成3MFは下記の別フォルダに出力します。

## 試作と本番の区分

各モデルの `prototype/` が試作用、`production/` が本番用です。既存3MFはすべてPLA試作用へ移動しました。本番用3MFはまだありません。自動生成履歴も `prototype/generated/` に移しています。アーカイブ内の過去データは履歴として保全します。

## 本番の素材はPAHT-CFの黒

2026年10月12日のユーザー指定で、本番の印刷素材をPAHT-CF（炭素繊維入りの耐熱ナイロン）の黒に決めました。試作は引き続きPLAです。積層の厚さ、壁の数、充填率、乾燥の手順などの本番の印刷条件はまだ決めていないため、`profiles/production/`の設定ファイルは作っていません。条件が決まるまで、本番用の生成は停止したままです。

Bambu Labの技術資料の値は次のとおりです。メーカーのページは取得できず、[販売店の掲載](https://shop3duniverse.com/collections/filament/products/bambu-lab-paht-cf-high-temperature-nylon-carbon-fiber-1-75mm-black)で確認しました（2026年10月12日）。本番の設定を作るときに、メーカーの最新資料で確認し直します。

| 項目 | 値 |
|---|---|
| 荷重たわみ温度 | 194℃（0.45MPa、ISO 75） |
| 乾燥 | 80℃で8〜12時間 |
| 保管 | 湿度20%未満。乾燥剤を入れて密封する |
| ノズル | 焼入れ鋼の0.4・0.6・0.8mm。ステンレスと0.2mmは非推奨 |
| ノズル温度 | 260〜290℃ |
| 造形台の温度 | 80〜100℃ |
| 造形板 | 高温用か技術用の板。低温用の板は非推奨 |
| プリンター | 密閉型が必要 |

PLAの試作で確かめたはめあい、ねじ穴、強度の結果を、PAHT-CFの結果として扱いません。収縮や吸湿で寸法が変わるため、本番の素材で試験片を印刷して確かめます。

## 自動生成する

`mise run 3mf:prototype:<モデル名>` でCADから再生成し、部品別3MFを `<モデル名>/<用途>/generated/<実行ID>/` に出力します。既存の手調整済み3MFは上書きしません。生成物はGit管理対象外、用途は `prototype` または `production` です。本番用は `mise run 3mf:production:<モデル名>` で生成しますが、素材・条件が未設定なら停止します。共通の設定は `profiles/` で管理します。[操作と検査の範囲](../docs/タスクランナー.md)を参照してください。

## ライセンス

[Apache License 2.0](../LICENSE)

Copyright 2026 IDEO PLUS LLC
