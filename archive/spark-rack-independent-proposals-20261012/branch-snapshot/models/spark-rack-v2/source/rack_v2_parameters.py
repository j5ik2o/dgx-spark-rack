# -*- coding: utf-8 -*-
"""DGX Spark 4台＋CRS812 DDQ 一体ラック 提案v2 (案A) の寸法定義。単位mm・kg。

座標: X=幅(左→右), Y=奥行(正面Y=0→背面), Z=高さ(床Z=0)。
値の区分: C=確認済み仕様, P=公開資料の参考値, A=仮定, M=実測待ち(仮値で配置)。
旧案(512x520x420, 28mm角材, CRS804, 中央段スイッチ)の寸法は参照しない。
"""

# ---- 購入品 ----
SPARK = dict(w=150.0, d=150.0, h=50.5, mass=1.2)            # P: NVIDIA公開外形/質量。足・端子位置はM
ADAPTER = dict(w=99.05, d=98.99, h=35.17, mass=0.5423)      # P: ChargerLab計測
SWITCH = dict(w=443.0, d=268.0, h=44.0, mass=4.0)           # P: 443x268x44(GETIC/製品資料)。旧取説156mmと要照合(M)。質量はA
SWITCH_FEET = 2.0                                            # A
FAN140 = dict(s=140.0, t=27.0, pitch=124.5, mass=0.20)      # P(外形/ピッチ: Noctua) 質量A
FAN120 = dict(s=120.0, t=27.0, pitch=105.0, mass=0.17)      # P 質量A
CTRL_ENVELOPE = dict(l=100.0, w=44.0, h=43.0, mass=0.08)    # 既存資料の収容目安(ケース+共通ドック)
CTRL_PSU = dict(l=110.0, w=50.0, h=35.0, mass=0.20)         # A: 12V3A据置型の仮収容範囲(M)
POWER_STRIP = dict(l=420.0, w=45.0, h=45.0, mass=0.7)       # A: 10口以上・上向き口の仮外形(M)
PLUG_KEEPOUT_H = 75.0                                        # A: プラグ高さ+コード曲げ
BEND_R_BREAKOUT = 42.0                                       # 商品ページ 37-42mm → 2m型未確定のため上限42mmを仮条件
RING_CABLE_LEN = 400.0                                       # ユーザー所有。測定基準はM
RING_BEND_R = 40.0                                           # A: 未確認のため仮40mm (M)
QSFP_STRAIGHT = 70.0                                          # A: コネクタ+ブーツ+ラッチ引き代の直線長 (M)

# ---- フレーム(2020アルミ押出材, 6mmスロット) ----
EXT = 20.0
W = 490.0          # 外形幅(側板を除く)
D = 400.0          # 外形奥行
H = 540.0          # 床から天枠上面(足8mm込み)
FOOT_H = 8.0
INNER_X0, INNER_X1 = EXT, W - EXT     # 450mm内のり

# ---- 段構成 ----
BAY_Z0, BAY_Z1 = FOOT_H + EXT + 3.0, 165.0       # 下段: 電源アダプター/コントローラー電源/タップ
TIER_BEAM_Z = [165.0, 309.0]                      # Spark段の受け梁下面 (段ピッチ144=ファン140+4)
TRAY_T = 4.0
SPARK_X = [80.0, 260.0]                            # 左右列のSpark X始点 (列間30mm: リング横渡しの40cm制約から詰める)
SPARK_Y0 = 95.0                                    # Spark前面
FAN_Y0 = 22.0                                      # ファン前面
DUCT_Y0 = FAN_Y0 + FAN140['t']                     # 49
SWITCH_SHELF_Z = 440.0                             # 側面受け梁下面
SWITCH_PLATE_T = 3.0                               # A5052 3mm
SWITCH_Y0 = 110.0                                  # スイッチ非端子側(ファン/電源側)前端。端子面は背面向き
TUNNEL = dict(y0=218.0, y1=348.0, z0=33.0, z1=163.0, wall=3.0)   # 内のり124角: 120ファンを端部に内装
SIDE_PANEL_T = 2.0

PRINT_LIMIT = 246.0   # Bambu Lab X1C 256mm から余裕込み
