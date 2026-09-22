# 設計コードと生成物

- 現行モデルは `models/spark-rack/`、`models/adapter-rack/`、`models/fan-controller/`。正本は各モデルの `source/` に限定する。
- 本体ラックの正本は `models/spark-rack/source/freecad_spark_rack.py` と `spark_rack_parameters.py`。旧FCStdは `archive/spark-rack-fcstd-v1/` に保全する。
- ファンコンケースの正本は `models/fan-controller/source/freecad_fan_controller.py`（冒頭に寸法定義）。`FanControllerCase.FCMacro` は実行入口。取り込み前の原本は `archive/fan-controller-import/`。ラックへの取付は未設計。
- アダプターラックの正本は `models/adapter-rack/source/freecad_adapter_rack.py` と `adapter_rack_parameters.py`。FCMacroは実行入口に限定する。
- 生成FCStdだけを変更して完成扱いにしない。各モデルの採用変更はPythonへ戻して再生成・検査する。
- 現行生成物は `build/<モデル名>/`、スライサー設定は `print-projects/<モデル名>/`。3MFは形状の正本ではない。
- 旧モデル・廃止した印刷配置・過去の生成結果は `archive/` に分ける。旧モデルの再生成も `archive/build-history/` へ出力する。
- 購入品の仕様・出典は各モデルの `reference/`、共通処理は `tools/cad/`。現行設計から旧版を暗黙に参照しない。
- 既存のCAD・STL・3MFを勝手に上書きしない。配布用生成物には同じ実行のmanifestと検査結果を添える。
- CAD上の検証と実物の適合・強度・冷却の確認を区別する。詳細は `docs/設計コードと生成物の管理.md` を参照する。
