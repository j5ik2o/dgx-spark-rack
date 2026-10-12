# 旧枠のスイッチ受け板案は採用せず保管する

この案は採用しません。

2026年10月11日に`codex/switch-support-design`ブランチで作った案です。柱と梁の枠（外形512×520×420mm）へ、アルミの受け板と梁でスイッチを支える構造を組み込んでいました。翌12日に、左右の構造面で支える固定段ラック（[PR #12](https://github.com/j5ik2o/dgx-spark-rack/pull/12)）へ設計が置き換わりました。前提の枠が違うため、mainへはマージしていません。ブランチを削除する前に、内容をここへ移しました。

| 場所 | 保管するもの |
|---|---|
| `branch-snapshot/` | ブランチで新しく追加したファイル。リポジトリ内の元の位置を保っている |
| `patches/` | 2コミット分の差分。既存ファイルへの変更はここにだけ残る |
| [preservation-manifest.json](preservation-manifest.json) | ブランチ名、基点と先端のコミット、各ファイルのハッシュ |

## mainへ引き継いだのは注文の記録だけ

ブランチには「CRS812を1台、2mの分岐ケーブルを注文した」というユーザーの報告が記録されていました。mainでは「購入は未確認」のままだったため、2026年10月12日に注文済み・未着をユーザーへ再確認しました。その結果を[選定記録](../../models/spark-rack/reference/selected-network-20261012/configuration.json)と[最終接続構成](../../models/spark-rack/docs/最終接続構成.md)へ反映しています。分岐ケーブルの注文本数は、まだ提示されていません。

元の記録は[ordered-network-equipment-20261011.json](branch-snapshot/models/spark-rack/reference/ordered-network-equipment-20261011.json)です。

受け板・梁・柱の寸法と生成コードは引き継いでいません。説明は[スイッチ支持部と交換経路](branch-snapshot/models/spark-rack/docs/スイッチ支持部と交換経路.md)に残っています。

## 別エージェントへの依頼文は独立案の出発点

[別エージェント向け設計プロンプト](branch-snapshot/models/spark-rack/docs/別エージェント向け設計プロンプト-20261011.md)は、既存案の寸法に縛られない設計を別のエージェントへ依頼した文です。この依頼から生まれた2案は[独立案の保管先](../spark-rack-independent-proposals-20261012/README.md)にあります。

## 履歴を復元する

基点のコミット`0806d37`へ`patches/`を順に適用すると、ブランチ先端と同じ内容に戻ります。2026年10月12日に、適用後のファイル一式がブランチ先端と一致することを確認しました。基点にはこのフォルダがないため、別の作業ツリーで適用します。リポジトリのルートから実行してください。

```sh
git worktree add --detach ../switch-support-restore 0806d37
git -C ../switch-support-restore am "$PWD"/archive/spark-rack-switch-support-20261011/patches/*.patch
```

この復元手順は履歴の確認用です。保管したコードが現在のmainの上で動くかは確認していません。現行の`models/spark-rack/`からこのコードを参照しないでください。
