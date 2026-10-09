# 17:21の136部品案は不採用として保全する

この案は不採用です。

ユーザーレビューの対象は`build/spark-rack/four-node-structure/20261009-172152-7b36234b`です。136部品、288本の締結経路を持つ案は採用せず、[保存パッケージ](four-node-structure-20261009-172152-not-adopted.zip)へ保全しました。指定実行の文書・立体データ・画像・検査結果・元manifestは変更していません。

`generated/`は指定実行の生成物、`working-source-at-rejection/`はレビューを受領した時点の作業コードです。当時の入力コードを生成時に複製していなかったため、後者が元manifestの入力と一致するとは限りません。一致した入力と、ここに保存できていない当時の入力版は[preservation-manifest.json](preservation-manifest.json)に区別して記録しました。

旧案のM4×45などの金具一覧、横梁を45度に置く印刷向きは、この履歴に保持します。136部品案を印刷せず、次は部材の凹凸と段差を持つ短い試験片で検討します。

## 履歴確認用の実装

不採用の実装は`source/`へ移しました。元の保存パッケージと内容照合記録は変更していません。再生成する場合は、リポジトリのルートから次を実行します。

```sh
python3 archive/spark-rack-structure-rejected-20261009-172152/source/build_four_node_structure.py --historical
```

出力は`archive/build-history/four-node-structure-not-adopted/<実行ID>/`です。この実装が利用する現在の配置・共通基準・ドックのコードも、同じ実行の生成記録へ含めます。保存パッケージをそのまま復元することと、現在の共通処理で履歴形状を再生成することは区別してください。
