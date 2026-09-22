# 印刷設定

このフォルダの3MFはBambu Studioの印刷設定です。**形状の正本は [../models/](../models/) にあります。** 設計変更を3MFだけで完結させません。

| 本体ラック用ファイル | 用途 |
|---|---|
| [pla-fit-tests.3mf](spark-rack/pla-fit-tests.3mf) | 接合と金具の試験片 |
| [pla-frame-without-pins.3mf](spark-rack/pla-frame-without-pins.3mf) | 側板2枚・支持棒3本。ピンは別印刷 |
| [pla-pin-trial-brim5.3mf](spark-rack/pla-pin-trial-brim5.3mf) | 固定ピン2本、外側5mmブリム |
| [pla-pins-3-brim5.3mf](spark-rack/pla-pins-3-brim5.3mf) | 追加ピン3本、外側5mmブリム |
| [pla-fan-cassette.3mf](spark-rack/pla-fan-cassette.3mf) | 140mmファン用保持部1個 |

いずれもPLA仮組み用の記録です。現在のプリンター・プレート・素材割り当てを確認してから印刷します。旧混在配置とバックアップは [../archive/print-projects/](../archive/print-projects/) に分けました。この一覧は手調整済みの保存ファイルです。3モデルの自動生成3MFは下記の別フォルダに出力します。

## 自動生成する

`mise run 3mf:<モデル名>` でCADから再生成し、部品別3MFを `<モデル名>/generated/<実行ID>/` に出力します。既存の手調整済み3MFは上書きしません。生成物はGit管理対象外、共通の設定は `profiles/` で管理します。[操作と検査の範囲](../docs/タスクランナー.md)を参照してください。

## ライセンス

[Apache License 2.0](../LICENSE)

Copyright 2026 IDEO PLUS LLC
