# 設計コードと生成物

- アダプタースタンドの設計の正本はPythonコードと `scripts/adapter_stand_parameters.py`。FCMacroは実行入口に限定する。
- 生成FCStdだけを変更して完成扱いにしない。採用する変更はコードへ反映し、再生成・検査する。
- 本体ラックv1はコード移行前の例外。ルートのFCStdと既存STLを保全し、全モデルがコードから再生成できるとは説明しない。
- 生成先は `build/`。既存の `exports/`、FCStd、ユーザーの3MFを勝手に上書きしない。
- 配布用生成物には同じ実行のmanifestと検査結果を添える。CAD上の検証と実物の適合・強度・冷却の確認を区別する。
- 詳細は `docs/設計コードと生成物の管理.md` を参照する。
- アダプターラックv2は `scripts/freecad_adapter_rack.py` と `scripts/adapter_rack_parameters.py` が正本。`run_adapter_rack.FCMacro` で `build/adapter-rack/` へ生成する。旧スタンドv1の正本とは分けて保全する。
