# 旧アダプタースタンドv1

横連結だけに対応した旧モデルです。現行は [アダプターラック](../../models/adapter-rack/README.md) を参照してください。

- `source/`：当時のPython設計コードと寸法定義。配置変更に伴う参照パスのみ更新。
- `reference/`：旧版が参照する電源仕様のスナップショット。
- `generated/`：保存済みFCStd・STL・画像・検査記録。
- [docs/設計と組立.md](docs/設計と組立.md)：旧版の説明。

旧版を再生成する場合だけ `source/run_adapter_stand.FCMacro` を使います。出力は `archive/build-history/adapter-stand/<実行ID>/` に作成し、保存済み生成物は上書きしません。
