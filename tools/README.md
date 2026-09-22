# 共通ツール

モデル固有の形状や寸法はここに置きません。現行モデルの設計は [../models/](../models/) を参照してください。

- `cad/freecad_features.py`：拘束付きスケッチと加工の共通処理。
- `cad/check_stl.py`：バイナリSTLの閉じた形状、接続成分、体積、造形寸法を検査。
- `cad/freecad_mcp.py`：FreeCAD MCPへPythonコードを渡す補助ツール。

- `tasks/cad.py`：miseから呼ぶCAD・3MF生成タスク。
- `tasks/cad_worker.py`：FreeCAD専用プロセスの実行入口。

## ライセンス

[Apache License 2.0](../LICENSE)

Copyright 2026 IDEO PLUS LLC
