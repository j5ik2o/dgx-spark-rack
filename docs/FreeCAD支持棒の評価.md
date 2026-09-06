# FreeCADで支持棒を履歴付きモデルとして評価する

**支持棒1種類について、寸法式・完全拘束スケッチ・押し出し・貫通穴を備えたFreeCADモデルを作成し、編集と再読込を確認しました。** Fusionの正本は保持しています。ラック全体の移行はまだ行っていません。

検証日：2026年9月6日。FreeCAD 1.1.3、Apple M4 Max、macOS 26.5.1で、ローカルMCPから実行しました。

## 開いて寸法を変える

[crossbar-native.FCStd](../comparison/freecad-native-crossbar/crossbar-native.FCStd)をFreeCADで開きます。初期寸法は長さ204 × 幅20 × 厚さ8 mm、穴径4.6 mm、穴中心は左右97 mmです。

1. モデルツリーの「寸法表_青が入力値」を開きます。
2. 青いセルを編集します。たとえばB2の`ModuleWidth`を`210 mm`から`214 mm`へ変更すると、支持棒が208 mmに伸び、穴中心が左右99 mmへ動きます。
3. 再計算後のモデルを確認します。自動で更新されない場合は再計算を実行してください。
4. 評価を終えたら元の寸法へ戻します。今回保存したファイルは全て初期寸法です。

| セル | 入力値 | 初期値 | 意味 |
|---|---|---:|---|
| B2 | ModuleWidth | 210 mm | ラック幅 |
| B3 | SideThickness | 12 mm | 側板厚さ |
| B4 | TenonLength | 9 mm | 側板内側より先へ伸びる長さ |
| B5 | BeamWidth | 20 mm | 支持棒の幅 |
| B6 | BeamThickness | 8 mm | 支持棒の厚さ |
| B7 | PinDiameter | 4 mm | 固定ピン径 |
| B8 | FitClearance | 0.3 mm | ピン穴の片側の隙間 |
| B9 | PinInset | 4 mm | 側板内側から穴中心までの距離 |

灰色のB10〜B13は計算値です。`BeamLength = 2 × (InnerX + TenonLength)`、`PinX = InnerX + PinInset`、`HoleDiameter = PinDiameter + 2 × FitClearance`で連動します。`InnerX = ModuleWidth / 2 − SideThickness`です。

これは単体の評価用文書です。ここでラック幅を変えても、既存の4台構成やFusionの部品は更新されません。

## 設計履歴の構成

寸法表は8個の入力値と4個の計算値を持ちます。支持棒のBodyには次の4項目があります。

| 項目 | FreeCADの機能 | 内容 |
|---|---|---|
| 01_輪郭_完全拘束 | Sketcher | 長方形の位置と寸法を拘束 |
| 02_厚さ_押し出し | PartDesign Pad | 寸法表の厚さで押し出し |
| 03_ピン穴_完全拘束 | Sketcher | 左右の穴位置と穴径を拘束 |
| 04_ピン穴_貫通 | PartDesign Pocket | 2穴をまとめて貫通加工 |

穴スケッチは特定の面番号へ貼り付けず、高さを`BeamThickness`の式で指定しています。厚さを変えても上面の高さへ移動し、貫通加工を維持します。2つのスケッチは検証した全条件で完全拘束でした。

Fusionの履歴を自動変換したものではありません。元の寸法式を調べ、FreeCADの機能で作り直しました。Fusionでは左右の穴が別の加工履歴ですが、ここでは1枚のスケッチと1回のPocketにまとめています。

## 確認結果

| 試験 | 期待した変化 | 結果 |
|---|---|---|
| ModuleWidth：210 → 214 mm | 全長204 → 208 mm、穴中心±97 → ±99 mm | 一致 |
| FitClearance：0.3 → 0.4 mm | 穴径4.6 → 4.8 mm、位置は維持 | 一致 |
| BeamThickness：8 → 10 mm | 厚さ10 mm、2穴が貫通 | 一致 |
| 各変更から初期値へ復元 | 初期形状へ戻る | 一致 |
| FCStd保存・再読込 | 履歴・拘束・寸法式が残る | 成功 |
| 再読込後の幅変更・復元 | 全長と穴位置が再び追随 | 成功 |
| Fusionの支持棒との形状比較 | 余分な部分・欠けた部分がない | 差分体積は両方向とも0 mm³ |
| STLの独立検査 | 閉じた形状、接続成分1個、正の体積 | 合格 |

形状比較では、Fusionから書き出した支持棒のSTEPと、FreeCADで作り直したソリッドを相互に引き算しました。許容値は差分体積0.00001 mm³です。寸法と体積だけの比較より踏み込んで確認していますが、造形精度や実物の接合を保証する試験ではありません。

変更から再計算までの測定値は約12〜15 ms、保存後の幅変更は約11 msでした。各条件1回の測定で、描画、MCP通信、検査時間は含みません。小さな支持棒1個の結果であり、4台構成の再計算速度や長時間の安定性は未確認です。

今回のMCP経由の作成・編集ではクラッシュは発生していません。前の試験で確認したmacOS・Qtの問題が修正されたという意味ではありません。[CAD比較のクラッシュ記録](CAD比較.md#macosで発生したクラッシュ)を参照してください。

## 成果物と再実行

- [FreeCADモデル](../comparison/freecad-native-crossbar/crossbar-native.FCStd)：履歴付きの評価用文書。
- [STEP](../comparison/freecad-native-crossbar/crossbar-native.step)：初期寸法のソリッド。
- [STL](../comparison/freecad-native-crossbar/crossbar-native.stl)：単位mm、平置き、XYZ最小値0。外寸204 × 20 × 8 mm。
- [プレビュー](../comparison/freecad-native-crossbar/crossbar-native.png)：外観の確認。
- [CAD検査記録](../comparison/freecad-native-crossbar/validation.json)／[STL検査記録](../comparison/freecad-native-crossbar/stl_validation.json)：変更条件、拘束、形状、出力ハッシュ。

STLは692三角形で、線形偏差0.02 mm、角度偏差0.15 radを指定しています。元のFusion STLと三角形の分割は異なります。造形や部品とのはめ合いは未実施なので、印刷部品一式の正本は引き続きFusion側です。

作成処理は[scripts/freecad_crossbar.py](../scripts/freecad_crossbar.py)、検査・保存・出力は[scripts/check_freecad_crossbar.py](../scripts/check_freecad_crossbar.py)です。GUIのFreeCADで[scripts/run_native_crossbar.FCMacro](../scripts/run_native_crossbar.FCMacro)を実行すると、両方を続けて実行します。MCPからこのマクロを渡して実行することもできます。

検査用の出力先に既にFCStdがあると停止します。再評価するときは出力先を分けてください。既存のFusion正本、4台構成のSTEP取り込み文書は変更しません。

## 次の判断

1. **推奨：側板1枚を履歴付きで再構築する。** 窓、支持棒の差込口、固定穴、丸みが追随するかを確認し、支持棒より複雑な部品でも扱えるかを判断します。
2. **CADの比較をいったん終え、製作試験を進める。** Fusionの正本を使い、まず接合用の試験片を印刷します。

支持棒1個の成功をもって、ラック全体の移行完了とはしません。
