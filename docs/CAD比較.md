# FusionとFreeCAD：ラックの移行試験

**形状の移行は確認できました。設計履歴の移行と、日常利用の安定性は確認できていません。** 現段階ではFusionを正本として保持し、FreeCAD版を評価用に扱います。検証日は2026年9月6日です。

追加試験として、[支持棒1種類を履歴付きで再構築](FreeCAD支持棒の評価.md)し、寸法変更・復元・保存後の再編集を確認しました。以下は4台構成をSTEPで取り込んだ際の記録です。

共有された[移行記事](https://zenn.dev/mattak/articles/b6ada01d5d16fd)を参考に、既存のSTEPをFreeCADへ読み込みました。記事が紹介するのもSTEP・STLによる形状の受け渡しで、Fusionのパラメーターや設計履歴を復元する方法ではありません。

## 今回のデータで確認できたこと

| 項目 | Fusion正本 | FreeCADへのSTEP取り込み |
|---|---:|---:|
| 4台構成の外寸 | 434 × 235 × 347.5 mm | 一致 |
| 組立ソリッド数 | 128 | 128、全て閉じた有効な形状 |
| 各ソリッドの面数 | 比較元 | 全て一致 |
| 各ソリッドの外形範囲・重心 | 比較元 | 最大誤差0.000001 mm未満 |
| 各ソリッドの体積・表面積 | 比較元 | 最大相対誤差0.000001%未満 |
| 名前付きパラメーター | 33 | 元の寸法式を引き継がない |
| 設計履歴 | 440項目 | 元のスケッチ・押し出し・ジョイントを引き継がない |
| 部品の階層・配置 | ネイティブの組立 | 13個の`App::Part`と128個の`Part::Feature`として保持 |
| 保存して開き直す | F3Dで確認済み | FCStdで形状保持を確認 |

128個にはDGX本体、ファン、ガード、ねじなどの参照形状も含みます。Fusionで行った干渉検査の80個とは、対象範囲が異なります。

比較ではソリッドを外形範囲で一対一に対応させ、寸法、重心、体積、表面積、面数を照合しました。座標の許容差は0.001 mm、体積・表面積の相対許容差は0.002%です。Fusion側は高精度の物性計算を使い、FreeCAD側は表示用メッシュを除いた形状を測っています。全ての曲面上の点の一致や、熱・強度まで証明する検査ではありません。

検査記録は[変換検査](../comparison/freecad/validation.json)、[Fusion側の基準値](../comparison/freecad/fusion_baseline.json)、[GUIでの確認](../comparison/freecad/freecad_gui_check.json)、[最終保存後の再読込](../comparison/freecad/final_reopen.json)です。

## 編集能力への影響

FreeCAD版は寸法を測定できるソリッドです。三角形のメッシュへ置き換えたモデルではありません。ただし、取り込んだ文書にはSketcherのスケッチ、Spreadsheet、PartDesignの履歴フィーチャーがありません。

たとえばFusionでは`ModuleWidth`を210から214 mmにすると、支持棒が204から208 mmへ、4台構成の幅が434から442 mmへ連動します。今回のSTEP取り込みでは、この連動関係を編集できません。同じ操作性が必要なら、FreeCADの寸法式・スケッチ・部品配置として再構築し、変更試験を行う必要があります。

したがって、今回確認できたのは「完成形状を保持して開ける」ことです。**設計を継続できる状態への完全移行は未完了です。**

## 読み込み時間の測定

Apple M4 Max、macOS 26.5.1上で、同じ442,536バイトのSTEPを読み込みました。Fusionは2704.1.53、FreeCADは1.1.3、FreeCADの形状計算ライブラリーOpen CASCADEは7.8.1です。

| 処理 | 1回目 | 2回目 | 3回目 | 中央値 |
|---|---:|---:|---:|---:|
| FusionのGUIプロセスでSTEPを読み込み | 1.941秒 | 1.230秒 | 1.194秒 | 1.230秒 |
| FreeCADのGUIプロセスでSTEPを読み込み・再計算 | 1.045秒 | 1.071秒 | 1.225秒 | 1.071秒 |

このモデルの読み込みで、FreeCADに目立つ速度低下は見られませんでした。ただし、実行順とOSキャッシュは制御していません。どちらも起動・MCP通信・明示的な描画更新を計測から除外しています。Fusionは新規文書作成を含むAPI、FreeCADは文書作成後の取り込みAPIであり、全く同じ処理範囲でもありません。この差だけでCAD全体の速度の優劣は決められません。

FreeCADのCLI単独では、STEP読み込み・再計算0.141秒、FCStd保存0.048秒、再読込・再計算0.032秒でした。こちらは単一試行で、GUIの測定とは分けて扱います。元の440項目の履歴を持つFreeCADモデルは作っていないため、寸法変更時の再計算速度は未比較です。

測定値は[Fusion](../comparison/freecad/fusion_step_timing.json)と[FreeCAD](../comparison/freecad/freecad_gui_check.json)にあります。

## macOSで発生したクラッシュ

画面操作を使った検証中に、FreeCADが2回終了しました。ユーザーから共有されたレポートは、そのうち11時28分の終了と一致します。

- `EXC_BAD_ACCESS (SIGSEGV)`がメインスレッドで発生。
- `objc_release`から`QMacAccessibilityElement dealloc`へ続くスタック。
- 読み込まれていたGUIライブラリーはQt 6.8.3。

macOS 26.5.1とQt 6.8.3で同じスタックが報告されている[FreeCAD Issue #30720](https://github.com/FreeCAD/FreeCAD/issues/30720)は、確認時点で未解決です。今回も同じアクセシビリティ処理の問題に該当する可能性が高く、Computer Useによる画面情報の取得が誘発した可能性があります。完全な原因確定やFreeCAD本体の修正はしていません。

その後、別の比較用プロファイルで起動し、画面情報の取得を介さず、ローカルMCPとCLIから読み込み・表示・保存を確認しました。この検証中に同じ終了は再発していませんが、長時間利用の安定性を保証する結果ではありません。OSの権限やセキュリティ設定は変更していません。

また、macOSの起動ラッパーが継承した環境変数を標準出力へ出す挙動を確認しました。以後の比較用起動では、必要最小限の環境変数だけを渡しています。起動ログとクラッシュレポート全文はリポジトリに含めていません。

## 費用とMCPの違い

| 項目 | Fusion | FreeCAD |
|---|---|---|
| 商用利用 | 有料契約または適用条件を満たす制度を検討 | 商用利用も無償 |
| 個人向け無償版 | 自宅での非商用利用などの条件あり | 用途による有料版への切替なし |
| 設計の保存 | 今回はローカルF3DをGitへ記録 | ローカルFCStdをGitへ記録 |
| 今回のMCP | Fusion組み込みのHTTPサーバー | コミュニティ製`neka-nat/freecad-mcp`を使用 |
| 接続経路 | HTTP → Fusion API | stdio MCP → ローカルXML-RPC → FreeCAD API |
| このラックの編集 | 既存の寸法式・履歴を使用可能 | STEP取り込み後に編集関係を再構築する必要あり |

日本のFusion公式ページは、年払いの月額換算で8,434円と表示しています。12倍すると概算で年約10.1万円ですが、これは月額換算値からの計算です。正式な請求額・税・契約条件は購入画面で確認します。[Fusion公式価格](https://www.autodesk.com/jp/products/fusion-360/overview)

個人向け無償版は非商用向けです。「年間売上1,000米ドル未満」だけで商用利用できる条件にはなっていません。[個人利用の公式条件](https://www.autodesk.com/products/fusion-360/personal)

スタートアップ向け制度もありますが、法人、独自の物理製品の設計・製造、過去のFusion契約がないことなどの審査条件があります。利用資格は未確認です。[スタートアップ向け公式条件](https://www.autodesk.com/products/fusion-360/startups)

FreeCADはLGPLのオープンソースソフトウェアで、商用の作業にも無償で使用できます。[FreeCAD公式FAQ](https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/Frequently_asked_questions.md)

Fusionの接続は[公式MCP](https://help.autodesk.com/view/fusion360/ENU/?guid=FMCP-OVERVIEW)です。FreeCADは[コミュニティ実装](https://github.com/neka-nat/freecad-mcp)のコミット`3da6db5f71a7b74d1b69d295d1ba89233ad622b5`、バージョン0.1.22を使いました。比較用の一時起動であり、ユーザーのグローバルMCP設定や常駐アドオン設定は変更していません。

専用スキルの公開例に[freecad-engineering](https://github.com/V0v1kkk/freecad-engineering)があります。MCP接続診断、履歴付きモデリング、形状検証など13個のスキルをまとめた実験的なプロジェクトです。今回の環境には未導入で、内容全体の評価はしていません。

## ファイルを開く・検証を再実行する

[FreeCAD評価ファイル](../comparison/freecad/DGX-SPARK-RACK-STEP-evaluation.FCStd)をFreeCADで開きます。[表示画像](../comparison/freecad/freecad_preview.png)も参照できます。このファイルには購入部品の参照形状を含むため、組立全体をそのまま印刷しないでください。印刷には引き続き[Fusionの部品別STL](../exports/fusion/stl)を使います。

CLIでの変換は`scripts/run_freecad_evaluation.FCMacro`、GUI内での確認は`scripts/freecad_gui_check.py`です。変換スクリプトは既存の評価用FCStdがあると停止します。別の試験をする場合は出力先を分けます。Fusionの正本は読み取り専用で扱います。

Fusion側の基準値は、正本をアクティブにした状態で取得します。

```sh
python3 scripts/fusion_mcp.py script scripts/fusion_evaluation_baseline.py
python3 scripts/fusion_mcp.py script scripts/fusion_step_benchmark.py
```

FreeCADの変換は、通常のPythonではなくFreeCAD付属の`freecadcmd`でマクロを実行します。macOSで起動する場合の例です。

```sh
env -i HOME="$HOME" USER="$USER" PATH=/usr/bin:/bin LANG=en_US.UTF-8 \
  /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd \
  scripts/run_freecad_evaluation.FCMacro
```

FreeCAD MCPへは、MCP SDKがあるPythonから`scripts/freecad_mcp.py`を実行します。`--server`には使用する`freecad-mcp`実行ファイルの絶対パスを渡します。一時的なMCP起動環境は再起動後の永続接続を保証しません。

## 次の判断

1. **推奨：Fusionを正本に保ち、側板1枚の履歴付き再構築へ進む。** 支持棒の追加試験は完了したので、差込口や丸みを含む部品へ評価範囲を広げます。
2. **FreeCADへの移行を保留し、Fusionで製作試験を進める。** 現在の履歴と検査済みSTLを使います。

どちらの場合も、今回の試験を理由にFusionデータを削除しません。
