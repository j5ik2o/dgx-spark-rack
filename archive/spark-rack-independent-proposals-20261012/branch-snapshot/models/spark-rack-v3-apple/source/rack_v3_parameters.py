# -*- coding: utf-8 -*-
"""DGX Spark 4台＋CRS812 DDQ 一体ラック 提案v3「Apple風」(案D) の寸法定義。
内部シャーシ(曲げ板)＋外装シェル(陽極酸化アルミ, 大R)。案A(v2)のコードは参照しない(複製して独立)。単位mm・kg。

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

# ---- 外装・内部シャーシ ----
SHELL_T = 2.0        # A5052 2mm 陽極酸化(スペースグレイ/シャンパンゴールド)
SHELL_R = 40.0       # 天面両肩の曲げR(大R曲げ。板金外注)
OUT_X0, OUT_X1 = -10.0, 500.0     # 外形幅 510
OUT_Y0, OUT_Y1 = -10.0, 472.0     # 外形奥行 482 (前面ラティス6mm+背面カバー2mm込み)
H = 530.0                          # 外形高さ(床から天面)
W = 490.0          # 内部基準幅(壁外面 X17..473 の基準。旧定義との互換用)
D = 440.0          # シャーシ奥行(Y6..440) 基準
WALL_T = 3.0       # 内部シャーシ側壁 A5052 3mm(構造)
WALL_X = [(17.0, 20.0), (470.0, 473.0)]
CHASSIS_Y0, CHASSIS_Y1 = 6.0, 440.0
BASE_Z0, BASE_Z1 = 25.0, 31.0      # 底板 A5052 6mm (構造の基礎)
PLINTH = dict(x0=30.0, x1=460.0, y0=30.0, y1=420.0, z0=4.0, z1=25.0)   # 奥まった台座(浮いて見える)
FOOT_H = 4.0
EXT = 20.0         # 梁(2mm曲げC形チャンネル 20x20)
INNER_X0, INNER_X1 = 20.0, 470.0
LATTICE = dict(t=6.0, hole_d=5.0, pitch=6.5)   # 前面ラティス: 千鳥丸穴 φ5 / P6.5 (Mac Pro風の見え方を2D穴で代替)
REAR_LATTICE = dict(t=2.0, hole_d=4.0, pitch=5.5)

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
TUNNEL = dict(x0=110.0, x1=380.0, y0=218.0, y1=348.0, z0=33.0, z1=163.0, wall=3.0)  # 前から吸気→後面120x2で背面排気
SIDE_PANEL_T = 2.0

PRINT_LIMIT = 246.0   # Bambu Lab X1C 256mm から余裕込み
