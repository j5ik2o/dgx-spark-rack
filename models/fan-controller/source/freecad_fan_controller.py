# -*- coding: utf-8 -*-
"""ファンコントローラーケース / FreeCAD 1.0系 App・Part API。

要採寸の仮配置モデル。写真のピクセル比から寸法を推定していない。
原点=(PCB左下角, PCB下面)。X=全長方向、Y=幅方向、Z=上方向。
左短辺をX_MIN、右短辺をX_MAX、手前長辺をY_MIN、奥長辺をY_MAXとする。
PCBを上から置き、本体側の独立したねじ留め押さえ4個で抜けを防ぐ。
基板への穴あけは不要。押さえは着座面まで締め、基板を直接締め付けない。
蓋の固定は厚い側壁に樹脂用呼び径2mmの小ねじ4本。下穴径は試験片で調整。
初期状態は組立座標。印刷時は本体を底面下、蓋を天面下にする。
"""

# ===== 編集する寸法・設定（mm）: ここから =====
PCB_LENGTH = 76.0              # 最新の実測値（以前の75.43から更新）
PCB_WIDTH = 25.0               # 最新の実測値
PCB_THICKNESS = 1.60           # 要確認
TERMINAL_TOP_Z = 15.87        # 実測: 基板下面から端子台上端。基板厚を加算しない
TERMINAL_LEFT_PROTRUSION = 1.0 # 概測: 端子台本体が基板左端より外へ出る量
TERMINAL_LENGTH = 10.16       # 実測: 上から見た左右(X)方向の最大外形
TERMINAL_WIDTH = 10.02        # 実測: 上から見た上下(Y)方向の最大外形
TERMINAL_TOP_MARGIN = 0.0    # 実測: 基板上端と端子台上端は面一
TERMINAL_BODY_CLEARANCE = 0.25 # 設計値: 端子台最大外形に対する片側の余裕
TERMINAL_PORT_TOP_Z = 9.45    # 実測: 基板下面から差込口上端まで
TERMINAL_BOTTOM_OUTER_Z = 3.84 # 実測: 基板下面から下側樹脂壁の外縁まで
TERMINAL_PORT_OUTER_WIDTH = 10.48 # 実測: 配線側の外幅（本体外形10.02とは測定範囲要照合）
TERMINAL_PORT_SIDE_WALL = 1.0 # 概測: 差込口の左右外側の肉厚
TERMINAL_PORT_BOTTOM_WALL = 1.0 # 概測: 差込口の下側の肉厚
TERMINAL_PORT_DIVIDER = 1.8   # 概測: 2穴間の仕切り。ケース開口には仕切りを設けない
TERMINAL_PORT_BOTTOM_Z = TERMINAL_BOTTOM_OUTER_Z + TERMINAL_PORT_BOTTOM_WALL
TERMINAL_PORT_WIDTH = TERMINAL_PORT_OUTER_WIDTH - 2 * TERMINAL_PORT_SIDE_WALL
TERMINAL_PORT_HEIGHT = TERMINAL_PORT_TOP_Z - TERMINAL_PORT_BOTTOM_Z
# 端子台の下面高さに依存しないよう、床から蓋まで局所的に空洞を拡張する。
DISPLAY_TOP_Z = 8.16          # 実測訂正: 基板下面から表示器上端。基板厚を加算しない
UNDERSIDE_PROTRUSION = 5.0     # 実測: 基板下面からの最大突出量
KNOB_TOP_Z = 21.7             # 実測: 基板下面からつまみ先端。基板厚を加算しない
ENCODER_BASE_TOP_Z = 10.56    # 最新実測: 基板下面から土台上面（以前の8.2から更新）
ENCODER_BASE_LENGTH = 12.52  # 実測: 土台の左右(X)方向
ENCODER_BASE_WIDTH = 13.26   # 実測: 土台自体の縦(Y)方向
ENCODER_TOP_TO_BASE_BOTTOM = 16.16 # 注釈画像: 基板上端から土台下端まで
ENCODER_BASE_BOTTOM_Y = PCB_WIDTH - ENCODER_TOP_TO_BASE_BOTTOM # 左下原点で8.84mm
ENCODER_RIGHT_TO_BASE_LEFT = 18.09 # 実測: 基板右端から土台左端まで
ENCODER_BASE_TOP_MARGIN = ENCODER_TOP_TO_BASE_BOTTOM - ENCODER_BASE_WIDTH # 基板上端から2.90mm
SHAFT_DIAMETER = 6.0           # 要確認
KNOB_PASS_DIAMETER = 7.0       # 実測: つまみ径。蓋を通過する外径として使用
KNOB_HOLE_EXTRA = 1.0          # 径への加算。汎用開口余裕と重複加算しない
KNOB_TARGET_EXPOSED = 3.0      # 操作性の暫定目標。未達は警告し、形状の確認を可能にする

PCB_OUTLINE_EXTRA = 0.30       # 外形全体へ+0.3（片側0.15）。片側0.3なら0.60へ
OPENING_EXTRA = 0.50           # 開口の幅・高さ全体へ+0.5（片側0.25）
WALL = 2.0                    # 壁厚
FLOOR = 2.0                   # 底厚
LID_THICKNESS = 2.0           # 蓋厚
BOTTOM_CLEARANCE = 0.80        # 下面突起と床との隙間（USB開口下端より床を低くする）
TOP_CLEARANCE = 1.0           # 端子台等と蓋下面との隙間
OTHER_TOP_HEIGHT = 10.0       # 要確認: エンコーダ本体/JST等の最大高さ（軸除外）

# 表示窓は表示器の外形を覆う寸法とする。実測位置は基板左端・上端基準。
DISPLAY_LENGTH = 32.23        # 実測: 表示器外形の長辺
DISPLAY_WIDTH = 10.43         # 実測: 表示器外形の短辺
DISPLAY_X = 10.71             # 実測: 基板左端から表示器左端
DISPLAY_TOP_MARGIN = 0.0      # 実測: 基板上端から表示器上端
DISPLAY_Y = PCB_WIDTH - DISPLAY_TOP_MARGIN - DISPLAY_WIDTH  # 左下原点へ変換
ENCODER_X = PCB_LENGTH - ENCODER_RIGHT_TO_BASE_LEFT + ENCODER_BASE_LENGTH / 2
# 上式は軸が土台の左右中央にある前提。現寸法ではX=64.17mm。
ENCODER_Y = ENCODER_BASE_BOTTOM_Y + ENCODER_BASE_WIDTH / 2 # 軸中央の前提で15.47mm

# (面, 面上の中心位置, 中心Z, 実寸幅, 実寸高さ)
# X面の中心位置はY座標、Y面はX座標。Zは常にPCB下面基準。
# USB-Cは左短辺(X_MIN)。2026-09-23の実測値を採用。
# Y=0はUSB-Cに近い基板の長辺。9.72は金属枠の全幅を含む遠い端まで。
USB_OUTER_WIDTH = 8.91        # 写真2283: 金属枠の外幅（直接実測）
USB_INNER_HEIGHT = 2.65       # ユーザー実測: 口の内側高さ
USB_SHELL_WALL = 0.26        # ユーザー実測: 金属枠の肉厚
USB_TOP_Z = 4.80             # 写真2281: 基板下面から金属枠上端
USB_FAR_EDGE_Y = 9.72        # 基板長辺から金属枠の遠い端（全幅を含む）
USB_OUTER_HEIGHT = USB_INNER_HEIGHT + 2 * USB_SHELL_WALL  # 上下同じ肉厚として算出
USB_CENTER_Y = USB_FAR_EDGE_Y - USB_OUTER_WIDTH / 2
USB_CENTER_Z = USB_TOP_Z - USB_OUTER_HEIGHT / 2
# 電源には黒いねじ端子台を使用中。端子台の配線出口を確保し、USB開口も残す。
USB_PORT = ("X_MIN", USB_CENTER_Y, USB_CENTER_Z, USB_OUTER_WIDTH, USB_OUTER_HEIGHT)
TERMINAL_PORT = ("X_MIN", PCB_WIDTH - TERMINAL_TOP_MARGIN - TERMINAL_WIDTH / 2,
                 (TERMINAL_PORT_BOTTOM_Z + TERMINAL_PORT_TOP_Z) / 2,
                 TERMINAL_PORT_WIDTH, TERMINAL_PORT_HEIGHT)
# 差込口は端子台本体の幅方向中央にある前提。余裕加算後8.98x5.11mm。
NTC_PORT = ("X_MAX", 17.0, PCB_THICKNESS + 3.0, 5.0, 4.0)
FAN_PORT = ("X_MAX", 6.0, PCB_THICKNESS + 3.0, 9.0, 4.0)

SUPPORT_X_FRONT = (18.0, 57.0) # 要確認: 手前長辺の部品/ランドのない箇所
SUPPORT_X_BACK = (47.0, 57.0)  # 要確認: 奥長辺。実測した表示器の範囲を避けた仮位置
SUPPORT_LENGTH = 4.0          # 支え・押さえのX方向長さ
SUPPORT_EDGE_OVERLAP = 0.80   # PCB端から内側へ掛かる量。両面の部品と要照合
RETAINER_Z_GAP = 0.20         # PCB上面と独立押さえの上下遊び
CLAMP_THICKNESS = 3.0         # 旧0.9mm薄板を廃止。別部品を平置き造形する
CLAMP_LUG_WIDTH = 6.0         # ねじ周囲のX方向幅
CLAMP_LUG_LENGTH = 4.0        # ねじ周囲のY方向長さ
CLAMP_SCREW_OFFSET = 2.5      # 内壁から外側へねじ中心までの距離
CLAMP_POCKET_CLEARANCE = 0.30 # 着座用ポケットの片側隙間
CLAMP_PILOT_DIAMETER = 1.6   # 呼び径2mm樹脂用ねじの仮下穴
CLAMP_CLEAR_DIAMETER = 2.5
CLAMP_SCREW_LENGTH = 8.0     # 押さえ専用: 呼び径2mm×8mmを4本
CLAMP_PILOT_DEPTH = 6.0
CLAMP_HEAD_DIAMETER = 4.0    # 許容するねじ頭の外径上限（実物要確認）
CLAMP_HEAD_HEIGHT = 1.6      # 許容するねじ頭高さ上限
CLAMP_DRIVER_DIAMETER = 4.5  # 上からアクセスするドライバー軸の検査外径

SCREW_X = (9.0, 68.0)        # 蓋用。独立押さえの着座ポケットを避ける新版位置
SCREW_ZONE_LENGTH = 7.0      # ねじの周囲で配線開口を避けるX方向幅
SCREW_RAIL_WIDTH = 5.0       # 基本壁の外側に加えるねじ固定用側壁の幅
SCREW_PILOT_DIAMETER = 1.6   # 樹脂用呼び径2mmねじの仮下穴。材質ごとに要調整
SCREW_CLEAR_DIAMETER = 2.5   # 蓋側通し穴
SCREW_PILOT_DEPTH = 8.0      # 本体の止まり穴
SCREW_LENGTH = 8.0           # 設計用: なべ頭下からの長さ（別途購入）
SCREW_TIP_CLEARANCE = 1.0    # 止まり穴底の余裕

VENT_COUNT = 6               # 底面スリット数
VENT_FIRST_X = 25.0          # PCB原点から最初のスリット中心X
VENT_PITCH = 5.0             # X方向間隔
VENT_WIDTH = 2.0             # スリットのX幅
VENT_LENGTH = 10.0           # スリットのY長さ。PCB幅中央に配置
BOOLEAN_OVERLAP = 0.10       # 切断工具を貫通させる余長
VOLUME_TOLERANCE = 0.00001   # 干渉検査許容体積(mm^3)
MIN_LID_FRAME = 1.5          # 設計値: 表示窓と蓋外周の間に残す最小幅
OUTER_CORNER_RADIUS = 3.0    # 長方形外周の四隅の丸み
TOUCH_EDGE_RADIUS = 0.4      # 蓋天面・本体上下端・底面スリットの縁の丸み
PORT_EDGE_RADIUS = 0.3       # 配線開口の外側の縁の丸み
EDGE_TOLERANCE = 0.00001     # エッジ座標の比較許容差
CORNER_PROBE = 0.01         # 外周の凸角を判定する微小距離
DOCUMENT_NAME = "FanControllerCase"
# ===== 編集する寸法・設定: ここまで =====

import FreeCAD as App
import Part
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tools/cad'))
from controller_mount import case_ears
from edge_finishing import chamfer


def box(x, y, z, length, width, height):
    return Part.makeBox(length, width, height, App.Vector(x, y, z))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def valid_solid(shape, label):
    require(not shape.isNull() and shape.isValid()
            and len(shape.Solids) == 1 and shape.Volume > VOLUME_TOLERANCE,
            label + ": 単一の有効なソリッドになっていません。寸法を確認してください。")


gap = PCB_OUTLINE_EXTRA / 2.0
opening_gap = OPENING_EXTRA / 2.0
inner_x = -gap
inner_y = -gap
inner_length = PCB_LENGTH + PCB_OUTLINE_EXTRA
inner_width = PCB_WIDTH + PCB_OUTLINE_EXTRA
outer_x = inner_x - WALL
outer_y = inner_y - WALL
outer_length = inner_length + WALL * 2.0
outer_width = inner_width + WALL * 2.0
outer_right = outer_x + outer_length
outer_back = outer_y + outer_width
floor_top_z = -UNDERSIDE_PROTRUSION - BOTTOM_CLEARANCE
bottom_z = floor_top_z - FLOOR
lid_z = max(TERMINAL_TOP_Z,
            DISPLAY_TOP_Z,
            PCB_THICKNESS + OTHER_TOP_HEIGHT, ENCODER_BASE_TOP_Z) + TOP_CLEARANCE
body_height = lid_z - bottom_z
lid_top_z = lid_z + LID_THICKNESS
retainer_bottom_z = PCB_THICKNESS + RETAINER_Z_GAP
shaft_hole_diameter = max(SHAFT_DIAMETER, KNOB_PASS_DIAMETER) + KNOB_HOLE_EXTRA
terminal_x = -TERMINAL_LEFT_PROTRUSION
terminal_y = PCB_WIDTH - TERMINAL_TOP_MARGIN - TERMINAL_WIDTH
terminal_cavity_x = terminal_x - TERMINAL_BODY_CLEARANCE
terminal_cavity_y = terminal_y - TERMINAL_BODY_CLEARANCE
terminal_cavity_length = TERMINAL_LENGTH + 2 * TERMINAL_BODY_CLEARANCE
terminal_cavity_width = TERMINAL_WIDTH + 2 * TERMINAL_BODY_CLEARANCE
terminal_outer_x = terminal_cavity_x - WALL
terminal_outer_y = terminal_cavity_y - WALL
terminal_outer_length = terminal_cavity_length + 2 * WALL
terminal_outer_width = terminal_cavity_width + 2 * WALL
# 端子台の逃げ上側と外周を揃え、0.1mmの小段差を作らない。
outer_back = max(outer_back, terminal_outer_y + terminal_outer_width)
outer_width = outer_back - outer_y
envelope_x = min(outer_x, terminal_outer_x)
envelope_y = outer_y - SCREW_RAIL_WIDTH
envelope_back = outer_back + SCREW_RAIL_WIDTH
envelope_length = outer_right - envelope_x
envelope_width = envelope_back - envelope_y

require(min(PCB_LENGTH, PCB_WIDTH, PCB_THICKNESS, WALL, FLOOR, LID_THICKNESS,
            BOTTOM_CLEARANCE, SUPPORT_LENGTH, SUPPORT_EDGE_OVERLAP) > 0,
        "基板・壁・底・支持部の寸法は正値にしてください。")
require(lid_z > retainer_bottom_z + CLAMP_THICKNESS + CLAMP_HEAD_HEIGHT,
        "独立押さえとねじ頭が蓋の下に収まりません。")
require(RETAINER_Z_GAP >= 0 and CLAMP_THICKNESS >= 3.0, "押さえの上下隙間・厚さが不適切です。")
require(CLAMP_THICKNESS < CLAMP_SCREW_LENGTH
        <= CLAMP_THICKNESS + CLAMP_PILOT_DEPTH - SCREW_TIP_CLEARANCE,
        "基板押さえのねじ長さが下穴に適合しません。")
require(retainer_bottom_z - CLAMP_PILOT_DEPTH > bottom_z + FLOOR,
        "基板押さえの下穴が底の肉厚へ入り込みます。")
require(CLAMP_POCKET_CLEARANCE > 0
        and 0 < CLAMP_PILOT_DIAMETER < CLAMP_CLEAR_DIAMETER < CLAMP_LUG_WIDTH,
        "基板押さえの穴径・隙間が不適切です。")
knob_exposed = KNOB_TOP_Z - lid_top_z
require(KNOB_TOP_Z > ENCODER_BASE_TOP_Z >= PCB_THICKNESS,
        "つまみ先端・土台上面・基板上面の高さ関係を確認してください。")
require(knob_exposed > 0, "つまみ先端が蓋に埋もれます。蓋高さを見直してください。")
if knob_exposed < KNOB_TARGET_EXPOSED:
    App.Console.PrintWarning("つまみの露出は%.2fmmです（操作性目標%.2fmm）。"
                             "端子台高さを確認し、必要なら蓋に操作用のくぼみを設けてください。\n"
                             % (knob_exposed, KNOB_TARGET_EXPOSED))
require(LID_THICKNESS < SCREW_LENGTH <= LID_THICKNESS + SCREW_PILOT_DEPTH - SCREW_TIP_CLEARANCE,
        "ねじ長さが下穴深さに適合しません。")
require(SCREW_PILOT_DEPTH < body_height - FLOOR, "下穴が底を貫通します。")
require(0 < SCREW_PILOT_DIAMETER < SCREW_CLEAR_DIAMETER < min(SCREW_ZONE_LENGTH, SCREW_RAIL_WIDTH),
        "ねじ穴径と側壁内の固定領域が不適合です。")

# 本体: 外箱 - 内側空洞。内側は蓋面を越えて切り抜く。
body_outer = box(envelope_x, envelope_y, bottom_z,
                 envelope_length, envelope_width, body_height)
body_cavity = box(inner_x, inner_y, floor_top_z, inner_length, inner_width,
                  lid_z - floor_top_z + BOOLEAN_OVERLAP)
terminal_cavity = box(terminal_cavity_x, terminal_cavity_y, floor_top_z,
                      terminal_cavity_length, terminal_cavity_width,
                      lid_z - floor_top_z + BOOLEAN_OVERLAP)
body_cavity_expanded = body_cavity.fuse(terminal_cavity)
body_shell = body_outer.cut(body_cavity_expanded)
body_with_supports = body_shell
clamps = []
clamp_pockets = []
clamp_screw_centers = []
support_groups = (
    (SUPPORT_X_FRONT, inner_y - BOOLEAN_OVERLAP, SUPPORT_EDGE_OVERLAP),
    (SUPPORT_X_BACK, PCB_WIDTH - SUPPORT_EDGE_OVERLAP,
     PCB_WIDTH + gap + BOOLEAN_OVERLAP),
)
for positions, y_min, y_max in support_groups:
    for x in positions:
        require(SUPPORT_LENGTH / 2 < x < PCB_LENGTH - SUPPORT_LENGTH / 2,
                "支持位置が基板範囲外です。")
        support = box(x - SUPPORT_LENGTH / 2, y_min, floor_top_z,
                      SUPPORT_LENGTH, y_max - y_min, -floor_top_z)
        body_with_supports = body_with_supports.fuse(support)
        front = y_min < 0
        screw_y = inner_y - CLAMP_SCREW_OFFSET if front else PCB_WIDTH + gap + CLAMP_SCREW_OFFSET
        reach = CLAMP_SCREW_OFFSET + gap + SUPPORT_EDGE_OVERLAP
        clamp = box(-CLAMP_LUG_WIDTH/2, -CLAMP_LUG_LENGTH/2, 0,
                    CLAMP_LUG_WIDTH, CLAMP_LUG_LENGTH, CLAMP_THICKNESS)
        tongue = box(-SUPPORT_LENGTH/2, 0, 0, SUPPORT_LENGTH, reach, CLAMP_THICKNESS)
        clamp = clamp.fuse(tongue).cut(Part.makeCylinder(
            CLAMP_CLEAR_DIAMETER/2, CLAMP_THICKNESS + 2*BOOLEAN_OVERLAP,
            App.Vector(0, 0, -BOOLEAN_OVERLAP))).removeSplitter()
        clamp = chamfer(clamp,[('Z',CLAMP_THICKNESS)],size=0.2)
        if not front:
            clamp.rotate(App.Vector(), App.Vector(0, 0, 1), 180)
        clamp.translate(App.Vector(x, screw_y, retainer_bottom_z))
        clamps.append(clamp)
        clamp_screw_centers.append((x, screw_y))
        b = clamp.optimalBoundingBox(False)
        c = CLAMP_POCKET_CLEARANCE
        pocket = box(b.XMin-c, b.YMin-c, retainer_bottom_z,
                     b.XLength+2*c, b.YLength+2*c, lid_z-retainer_bottom_z+BOOLEAN_OVERLAP)
        clamp_pockets.append(pocket)

lid_plate = box(envelope_x, envelope_y, lid_z,
                envelope_length, envelope_width, LID_THICKNESS)

# ねじ固定部を長方形外枠の厚い側壁に内蔵する。外側への耳は設けない。
screw_centers = []
for x in SCREW_X:
    require(SCREW_ZONE_LENGTH / 2 < x < PCB_LENGTH - SCREW_ZONE_LENGTH / 2,
            "ねじのX位置が範囲外です。")
    for center_y in (outer_y - SCREW_RAIL_WIDTH / 2, outer_back + SCREW_RAIL_WIDTH / 2):
        screw_centers.append((x, center_y))


def port_cutter(spec):
    face, along, center_z, width, height = spec
    require(face in ("X_MIN", "X_MAX", "Y_MIN", "Y_MAX"), "開口面の指定が不正です。")
    require(width > 0 and height > 0, "開口寸法は正値にしてください。")
    span = PCB_WIDTH if face.startswith("X") else PCB_LENGTH
    if face == "X_MIN":
        span = max(span, terminal_cavity_y + terminal_cavity_width)
    full_width, full_height = width + OPENING_EXTRA, height + OPENING_EXTRA
    require(0 < along - full_width / 2 and along + full_width / 2 < span,
            "側面開口が角を越えます。座標・面・幅を確認してください。")
    low_z = center_z - full_height / 2
    require(floor_top_z < low_z and low_z + full_height < lid_z,
            "側面開口が床または蓋に接します。高さを調整してください。")
    depth = WALL + BOOLEAN_OVERLAP * 2
    if face.startswith("X"):
        x = envelope_x - BOOLEAN_OVERLAP if face == "X_MIN" else PCB_LENGTH + gap - BOOLEAN_OVERLAP
        if face == "X_MIN":
            depth = inner_x - x + BOOLEAN_OVERLAP
        return box(x, along - full_width / 2, low_z, depth, full_width, full_height)
    y = envelope_y - BOOLEAN_OVERLAP if face == "Y_MIN" else PCB_WIDTH + gap - BOOLEAN_OVERLAP
    depth = (inner_y - y + BOOLEAN_OVERLAP if face == "Y_MIN"
             else envelope_back - y + BOOLEAN_OVERLAP)
    return box(along - full_width / 2, y, low_z, full_width, depth, full_height)


body_with_ports = body_with_supports
port_cutters = []
for name, spec in (("USB-C", USB_PORT), ("端子台", TERMINAL_PORT),
                   ("NTC", NTC_PORT), ("ファン", FAN_PORT)):
    cutter = port_cutter(spec)
    # 長辺の開口が厚い側壁内のねじ固定領域に重なる配置を禁止。
    face, along, _, width, _ = spec
    if face.startswith("Y"):
        for screw_x in SCREW_X:
            require(abs(along - screw_x) >= (width + OPENING_EXTRA + SCREW_ZONE_LENGTH) / 2,
                    name + ": 配線開口とねじ固定領域が重なります。位置を変更してください。")
    require(body_with_supports.common(cutter).Volume > VOLUME_TOLERANCE,
            name + ": 工具が側壁と交差しません。")
    body_with_ports = body_with_ports.cut(cutter)
    port_cutters.append(cutter)

# 底面の細いスリット。受けリブの付け根を避ける。
body_with_vents = body_with_ports
require(isinstance(VENT_COUNT, int) and VENT_COUNT > 0 and VENT_PITCH > VENT_WIDTH > 0,
        "スリット数・ピッチ・幅が不正です。")
require(0 < VENT_LENGTH < PCB_WIDTH - 2 * SUPPORT_EDGE_OVERLAP,
        "通気スリットが支持部に重なります。")
for index in range(VENT_COUNT):
    center_x = VENT_FIRST_X + index * VENT_PITCH
    require(0 < center_x - VENT_WIDTH / 2 < center_x + VENT_WIDTH / 2 < PCB_LENGTH,
            "通気スリットが基板範囲外です。")
    vent = box(center_x - VENT_WIDTH / 2, (PCB_WIDTH - VENT_LENGTH) / 2,
               bottom_z - BOOLEAN_OVERLAP, VENT_WIDTH, VENT_LENGTH,
               FLOOR + BOOLEAN_OVERLAP * 2)
    body_with_vents = body_with_vents.cut(vent)

# 天面の表示窓と軸穴。独立押さえが表示器・軸の下へ入らないことも検査する。
window_x = DISPLAY_X - opening_gap
window_y = DISPLAY_Y - opening_gap
window_length = DISPLAY_LENGTH + OPENING_EXTRA
window_width = DISPLAY_WIDTH + OPENING_EXTRA
require(DISPLAY_X >= 0 and DISPLAY_X + DISPLAY_LENGTH <= PCB_LENGTH
        and DISPLAY_Y >= 0 and DISPLAY_TOP_MARGIN >= 0,
        "表示器外形が基板範囲を越えています。")
require(outer_x + MIN_LID_FRAME <= window_x
        and window_x + window_length <= outer_right - MIN_LID_FRAME
        and outer_y + MIN_LID_FRAME <= window_y
        and window_y + window_width <= outer_back - MIN_LID_FRAME,
        "表示窓の周囲に必要な蓋の枠幅が残りません。")
radius = shaft_hole_diameter / 2
require(radius < ENCODER_X < PCB_LENGTH - radius
        and radius < ENCODER_Y < PCB_WIDTH - radius, "軸穴が基板範囲を越えています。")
window_tool = box(window_x, window_y, retainer_bottom_z - BOOLEAN_OVERLAP,
                  window_length, window_width, lid_top_z - retainer_bottom_z + 2 * BOOLEAN_OVERLAP)
shaft_tool = Part.makeCylinder(radius, lid_top_z - retainer_bottom_z + 2 * BOOLEAN_OVERLAP,
                               App.Vector(ENCODER_X, ENCODER_Y, retainer_bottom_z - BOOLEAN_OVERLAP))
require(window_tool.common(shaft_tool).Volume < VOLUME_TOLERANCE, "表示窓と軸穴が重なっています。")
for retainer in clamps:
    for tool in (window_tool, shaft_tool):
        require(retainer.common(tool).Volume < VOLUME_TOLERANCE, "天面開口と基板押さえが重なっています。")
lid_with_window = lid_plate.cut(window_tool)
lid_with_openings = lid_with_window.cut(shaft_tool)

body_final = body_with_vents
lid_final = lid_with_openings
for x, y in screw_centers:
    pilot = Part.makeCylinder(SCREW_PILOT_DIAMETER / 2, SCREW_PILOT_DEPTH + BOOLEAN_OVERLAP,
                              App.Vector(x, y, lid_z - SCREW_PILOT_DEPTH))
    clearance = Part.makeCylinder(SCREW_CLEAR_DIAMETER / 2, LID_THICKNESS + 2 * BOOLEAN_OVERLAP,
                                  App.Vector(x, y, lid_z - BOOLEAN_OVERLAP))
    body_final = body_final.cut(pilot)
    lid_final = lid_final.cut(clearance)
body_final = body_final.removeSplitter()
lid_final = lid_final.removeSplitter()


def round_outer_corners(shape, height):
    """全高にわたる外周の凸角だけを丸め、基板受けや内側角を保持する。"""
    edges = []
    for edge in shape.Edges:
        bounds = edge.BoundBox
        if not (bounds.XLength < EDGE_TOLERANCE and bounds.YLength < EDGE_TOLERANCE
                and abs(bounds.ZLength - height) < EDGE_TOLERANCE):
            continue
        point = edge.CenterOfMass
        inside_count = sum(shape.isInside(point + App.Vector(dx, dy, 0) * CORNER_PROBE,
                                          EDGE_TOLERANCE, False)
                           for dx, dy in ((1, 1), (1, -1), (-1, 1), (-1, -1)))
        if inside_count == 1:
            edges.append(edge)
    require(bool(edges), "外周の丸め対象が見つかりません。")
    return shape.makeFillet(OUTER_CORNER_RADIUS, edges)


def round_horizontal_rims(shape, heights):
    edges = [edge for edge in shape.Edges
             if any(abs(edge.BoundBox.ZMin - z) < EDGE_TOLERANCE
                    and abs(edge.BoundBox.ZMax - z) < EDGE_TOLERANCE for z in heights)]
    require(bool(edges), "上下端の丸め対象が見つかりません。")
    return shape.makeFillet(TOUCH_EDGE_RADIUS, edges)


# makeFillet失敗時は停止する。角が残った形状を成功として出力しない。
body_with_corner_rounds = round_outer_corners(body_final, body_height)
lid_with_corner_rounds = round_outer_corners(lid_final, LID_THICKNESS)
body_with_rim_rounds = round_horizontal_rims(body_with_corner_rounds, (bottom_z, lid_z))
lid_with_rim_rounds = round_horizontal_rims(lid_with_corner_rounds, (lid_top_z,))
port_edges = []
for edge in body_with_rim_rounds.Edges:
    bounds = edge.BoundBox
    on_outer_face = (
        any(abs(bounds.XMin - x) < EDGE_TOLERANCE and bounds.XLength < EDGE_TOLERANCE
            for x in (envelope_x, outer_right))
        or any(abs(bounds.YMin - y) < EDGE_TOLERANCE and bounds.YLength < EDGE_TOLERANCE
               for y in (envelope_y, envelope_back)))
    if not on_outer_face or edge.Length <= 2 * TOUCH_EDGE_RADIUS:
        continue
    for cutter in port_cutters:
        cut_bounds = cutter.BoundBox
        if all(getattr(bounds, axis + "Min") >= getattr(cut_bounds, axis + "Min") - EDGE_TOLERANCE
               and getattr(bounds, axis + "Max") <= getattr(cut_bounds, axis + "Max") + EDGE_TOLERANCE
               for axis in "XYZ"):
            port_edges.append(edge)
            break
require(bool(port_edges), "配線開口の丸め対象が見つかりません。")
body_final = body_with_rim_rounds.makeFillet(PORT_EDGE_RADIUS, port_edges).removeSplitter()
lid_final = lid_with_rim_rounds.removeSplitter()
for pocket, (x, y) in zip(clamp_pockets, clamp_screw_centers):
    body_final = body_final.cut(pocket)
    body_final = body_final.cut(Part.makeCylinder(
        CLAMP_PILOT_DIAMETER/2, CLAMP_PILOT_DEPTH+BOOLEAN_OVERLAP,
        App.Vector(x, y, retainer_bottom_z-CLAMP_PILOT_DEPTH)))
body_final = body_final.removeSplitter()
body_final = case_ears(body_final, envelope_x, outer_right,
                       (envelope_y+envelope_back)/2, bottom_z)
valid_solid(body_final, "CaseBody")
valid_solid(lid_final, "CaseLid")
require(body_final.common(lid_final).Volume < VOLUME_TOLERANCE, "本体と蓋が干渉しています。")
pcb_envelope = box(0, 0, 0, PCB_LENGTH, PCB_WIDTH, PCB_THICKNESS)
require(body_final.common(pcb_envelope).Volume < VOLUME_TOLERANCE
        and lid_final.common(pcb_envelope).Volume < VOLUME_TOLERANCE, "基板外形とケースが干渉しています。")
terminal_envelope = box(terminal_x, terminal_y, PCB_THICKNESS,
                        TERMINAL_LENGTH, TERMINAL_WIDTH, TERMINAL_TOP_Z - PCB_THICKNESS)
require(body_final.common(terminal_envelope).Volume < VOLUME_TOLERANCE
        and lid_final.common(terminal_envelope).Volume < VOLUME_TOLERANCE,
        "端子台の最大外形とケースが干渉しています。")

clamp_validation = []
for index, (clamp, pocket, (x, y)) in enumerate(zip(clamps, clamp_pockets, clamp_screw_centers)):
    valid_solid(clamp, f"PCBClamp{index+1}")
    for shape, label in ((body_final, '本体'), (lid_final, '蓋'),
                         (pcb_envelope, '基板'), (terminal_envelope, '端子台')):
        require(clamp.common(shape).Volume < VOLUME_TOLERANCE, f'基板押さえと{label}が干渉しています。')
    head = Part.makeCylinder(CLAMP_HEAD_DIAMETER/2, CLAMP_HEAD_HEIGHT,
                            App.Vector(x, y, retainer_bottom_z+CLAMP_THICKNESS))
    driver = Part.makeCylinder(CLAMP_DRIVER_DIAMETER/2, lid_z-retainer_bottom_z-CLAMP_THICKNESS+1,
                              App.Vector(x, y, retainer_bottom_z+CLAMP_THICKNESS))
    require(head.common(body_final).Volume < VOLUME_TOLERANCE
            and head.common(lid_final).Volume < VOLUME_TOLERANCE, '基板押さえのねじ頭がケースに干渉しています。')
    require(driver.common(body_final).Volume < VOLUME_TOLERANCE,
            '基板押さえのねじへドライバーが届きません。')
    b = clamp.optimalBoundingBox(False)
    insertion = box(b.XMin, b.YMin, b.ZMin, b.XLength, b.YLength, lid_top_z-b.ZMin+1)
    require(insertion.common(body_final).Volume < VOLUME_TOLERANCE,
            '独立押さえを真上から着脱できません。')
    for sx, sy in screw_centers:
        lid_pilot = Part.makeCylinder(SCREW_PILOT_DIAMETER/2, SCREW_PILOT_DEPTH,
                                     App.Vector(sx, sy, lid_z-SCREW_PILOT_DEPTH))
        require(pocket.common(lid_pilot).Volume < VOLUME_TOLERANCE, '押さえポケットと蓋用ねじ穴が干渉しています。')
    # 押さえの下に着座面があること。基板ではなく側壁で締付けを受ける。
    seat_probe = box(x-CLAMP_LUG_WIDTH/2, y-CLAMP_LUG_LENGTH/2, retainer_bottom_z-0.1,
                     CLAMP_LUG_WIDTH, CLAMP_LUG_LENGTH, 0.1)
    seat_area = seat_probe.common(body_final).Volume/0.1
    require(seat_area > CLAMP_LUG_WIDTH*CLAMP_LUG_LENGTH*0.75, '押さえの着座面が不足しています。')
    clamp_validation.append({'seat_area_mm2': seat_area, 'pcb_gap_mm': RETAINER_Z_GAP,
                             'screw_engagement_mm': CLAMP_SCREW_LENGTH-CLAMP_THICKNESS,
                             'driver_access': True})
for i, clamp in enumerate(clamps):
    for other in clamps[i+1:]:
        require(clamp.common(other).Volume < VOLUME_TOLERANCE, '独立押さえ同士が干渉しています。')
require(abs(lid_final.optimalBoundingBox(False).ZLength-LID_THICKNESS) < EDGE_TOLERANCE,
        '蓋に長い押さえが残っています。')

# 組立は本体・蓋・独立押さえ4個。STLは同形の押さえを1種類だけ出力する。
doc = App.newDocument(DOCUMENT_NAME)
case_body = doc.addObject("Part::Feature", "CaseBody")
case_body.Shape = body_final
case_lid = doc.addObject("Part::Feature", "CaseLid")
case_lid.Shape = lid_final
clamp_objects = []
for index, shape in enumerate(clamps):
    obj = doc.addObject('Part::Feature', 'PCBClamp' if index == 0 else f'PCBClamp{index+1}')
    obj.Shape = shape
    clamp_objects.append(obj)
PRINT_PARTS = ('CaseBody', 'CaseLid', 'PCBClamp')
for obj in (case_body, case_lid):
    obj.addProperty("App::PropertyString", "MeasurementStatus", "Design")
    obj.MeasurementStatus = "要採寸: 仮配置モデル。実物との適合は未検証"
doc.recompute()
if App.GuiUp:
    import FreeCADGui as Gui
    case_body.ViewObject.ShapeColor = (0.25, 0.32, 0.40)
    case_lid.ViewObject.ShapeColor = (0.78, 0.83, 0.89)
    for obj in clamp_objects:
        obj.ViewObject.ShapeColor = (0.90, 0.58, 0.17)
    Gui.activeDocument().activeView().viewAxonometric()
    Gui.activeDocument().activeView().fitAll()
App.Console.PrintWarning("要採寸の仮配置モデルです。実物の部品・配線と支持部の干渉を確認してください。\n")
App.Console.PrintMessage("ケース箱外形（取付耳を除く）: %.2f x %.2f x %.2f mm\n" %
                        (envelope_length, envelope_width, lid_top_z - bottom_z))

# STLエクスポート例（組立座標。スライサーで各部品を個別に接地する）:
# import Mesh
# Mesh.export([case_body], "/absolute/output/CaseBody.stl")
# Mesh.export([case_lid], "/absolute/output/CaseLid.stl")
# 本体: 底面を下。蓋: 天面を下。独立押さえ: 広い下面を下。
# 任意で保存: doc.saveAs("/absolute/output/FanControllerCase.FCStd")
