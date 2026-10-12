# -*- coding: utf-8 -*-
"""案D 印刷部品の造形形状(PAHT-CF前提)。各関数は造形向き(Z=積層方向, 原点=外形の最小角)の実体を返す。
実測前の仮寸法。荷重を受ける板金シャーシは含めない。
インサート穴: 熱圧入ナット(M3: φ4.0×5, M4: φ5.6×6, M5: φ6.4×8)前提。下穴径は試し印刷で調整。
"""
import math
import FreeCAD as App, Part
from rack_v3_parameters import *

V = App.Vector
INS = {'M3': (4.0/2, 5.0), 'M4': (5.6/2, 6.0), 'M5': (6.4/2, 8.0)}

def box(x, y, z, dx, dy, dz): return Part.makeBox(dx, dy, dz, V(x, y, z))
def cyl(x, y, z, r, h, d=V(0, 0, 1)): return Part.makeCylinder(r, h, V(x, y, z), d)
def insert(s, x, y, z, size, down=False):
    r, h = INS[size]
    return s.cut(cyl(x, y, z-h if down else z, r, h+0.01) if not down else cyl(x, y, z-h, r, h+0.01))
def insert_from_bottom(s, x, y, size):
    r, h = INS[size]; return s.cut(cyl(x, y, -0.01, r, h))
def through(s, x, y, z0, h, d): return s.cut(cyl(x, y, z0-0.01, d/2, h+0.02))

def spark_tray():
    """160×150×4 + 外側リップ。平置き(荷重は面外=積層面に平行な曲げ)。工具不要の引出し: 下面にプランジャー受け窪み、前端つまみ。"""
    w, d, t = SPARK['w']+10, SPARK['d'], TRAY_T
    s = box(0, 0, 0, w, d, t)
    s = s.fuse(box(0, 0, 0, 2.5, d, t+6)).fuse(box(w-2.5, 0, 0, 2.5, d, t+6))     # 横ずれ止めリップ
    s = s.fuse(box(w/2-20, -14, 0, 40, 14, t))                                   # 前つまみ
    s = s.cut(box(w/2-14, -10, -1, 28, 6, t+2))                                  # 指掛け穴
    for x in (25, w-25):
        s = s.cut(Part.makeSphere(2.2, V(x, 10, 0)))                             # ボールプランジャー受け(前梁位置)
        s = s.cut(Part.makeSphere(2.2, V(x, d-10, 0)))
    for x in range(30, int(w)-20, 25):                                           # 通風スリット(Spark底面の熱)
        s = s.cut(box(x, 30, -1, 8, d-60, t+2))
    return s.removeSplitter()

def duct():
    """ファン側フランジを下(Z=0)、Spark側を上。140角ファンM4インサート4・梁固定タブ(つまみねじM4インサート)。"""
    H0 = SPARK_Y0-DUCT_Y0
    def rect(z, w, h):
        return Part.makePolygon([V(71-w/2, 71-h/2, z), V(71+w/2, 71-h/2, z), V(71+w/2, 71+h/2, z), V(71-w/2, 71+h/2, z), V(71-w/2, 71-h/2, z)])
    outer = Part.makeLoft([rect(5, 142, 142), rect(H0, 150, 52)], True)
    inner = Part.makeLoft([rect(4.9, 134, 134), rect(H0+0.1, 144, 44)], True)
    fl = box(0, 0, 0, 142, 142, 5).cut(cyl(71, 71, -1, 66, 7))
    s = fl.fuse(outer.cut(inner))
    for dx in (-1, 1):
        for dy in (-1, 1):
            s = insert(s, 71+dx*FAN140['pitch']/2, 71+dy*FAN140['pitch']/2, 5.0-INS['M4'][1]+0.01, 'M4') if False else \
                s.cut(cyl(71+dx*FAN140['pitch']/2, 71+dy*FAN140['pitch']/2, -0.01, INS['M4'][0], 5.02))
    # 下側の梁固定タブ(Spark側端の下面に沿う)
    tab = box(71-20, 71-26-12, H0-10, 40, 12, 10)
    s = s.fuse(tab).cut(cyl(71, 71-26-6, H0-10-0.01, INS['M4'][0], 6))
    return s.removeSplitter()

def tunnel(half):
    """135×130×130角筒の半分。筒軸を縦(Z)にして造形。前面格子は一体、後面は開口(120ファン側)。
    half=0 は+X端に段差はめ合いの雄、half=1 は雌。底フランジにM4インサート2(下面から板金底板へ)。"""
    L = (TUNNEL['x1']-TUNNEL['x0'])/2; Y = TUNNEL['y1']-TUNNEL['y0']; Zh = TUNNEL['z1']-TUNNEL['z0']; w = TUNNEL['wall']
    # 造形座標: X=トンネル長手(L), Y=奥行(Y), Z=高さ(Zh)を、筒軸(Y:前後)を縦にする → 造形Z=Y
    s = box(0, 0, 0, L, Zh, Y).cut(box(-1 if half else w, w, -1, L+1-w if half else L+1-w, Zh-2*w, Y+2))
    if half == 0:
        for zz in (6, Y-9):   # 雄舌(壁に掛かる全幅の段差, 前後2か所)
            s = s.fuse(box(L-0.01, 1.5, zz, 6.01, Zh-3, 3))
    else:
        for zz in (6, Y-9):
            s = s.cut(box(-0.01, 1.2, zz-0.2, 6.3, Zh-2.4, 3.4))
    # 前面(造形Z=0側)の格子: 底面に一体の格子板 2mm
    grid = box(0 if half else w, w, 0, L-w if not half else L, Zh-2*w, 2)
    for i in range(int(L//9)):
        for j in range(int((Zh-2*w)//9)):
            grid = grid.cut(box((0 if half else w)+2+i*9, w+2+j*9, -1, 6, 6, 4))
    s = s.fuse(grid)
    # 底板への固定フランジ(トンネル下面=造形のY=0面)にM4インサート
    for z in (25, Y-25):
        s = s.cut(cyl(L/2, -0.01, z, INS['M4'][0], INS['M4'][1], V(0, 1, 0)))
    # 内部棚受けリブ(アダプター上段用)
    s = s.fuse(box(0 if half else w, w+42, 8, L-w if not half else L, 3, Y-16))
    return s.removeSplitter()

def ctrl_bracket():
    """L字: ドック面(44×100, M4通し穴ピッチ28)と側壁面(25×100, M4インサート2)。
    L字の折れを造形XY面内に置き(横倒し)、曲げ荷重が層間剥離方向に掛からない向き。高さ100=Z。"""
    s = box(0, 0, 0, 44, 5, 100).fuse(box(0, 0, 0, 5, 25, 100))
    for z in (36, 64):
        s = s.cut(cyl(8, 25, z, 2.25, 30, V(0, -1, 0)) if False else cyl(22-14+7, 5.01, z, 2.25, 6, V(0, -1, 0)))
    for x0 in (8+14, 8+14+28):
        pass
    s = box(0, 0, 0, 44, 5, 100).fuse(box(0, 0, 0, 5, 25, 100))
    for xh in (22-14, 22+14):   # ドックのラック側M4ピッチ28(ドック幅方向)
        s = s.cut(cyl(xh+0, 5.01, 50, 2.25, 6, V(0, -1, 0)))
    for z in (25, 75):          # 側壁へ: M4インサート(板金側からねじ)
        s = s.cut(cyl(-0.01, 16, z, INS['M4'][0], INS['M4'][1], V(1, 0, 0)))
    s = s.fuse(box(5, 5, 0, 8, 8, 100).cut(cyl(13, 13, -1, 8, 102)))   # 内隅R補強
    return s.removeSplitter()

def switch_retainer():
    """150×30×3.4板+下フランジ。立てず平置き。後部支持耳の穴位置未確定のため長穴2本(M4)。下面フランジにM5インサート2。"""
    s = box(0, 0, 0, 150, 30, 3.4).fuse(box(0, 0, 0, 150, 12, 10))
    for x in (35, 115):
        s = s.cut(box(x-12, 18, -1, 24, 4.5, 6)).cut(cyl(x-12, 20.25, -1, 2.25, 6)).cut(cyl(x+12, 20.25, -1, 2.25, 6))
        s = s.cut(cyl(x, 6, 10.01, INS['M5'][0], INS['M5'][1], V(0, 0, -1)))
    return s.removeSplitter()

def slack_tray():
    """205×112×38 トレー(壁2.4)。R42以上の8の字が入る内のり。吊りタブ2(M4インサート)。底面を下。"""
    s = box(0, 0, 0, 205, 112, 38).cut(box(2.4, 2.4, 2.4, 200.2, 107.2, 40))
    s = s.cut(box(-1, 30, 20, 4, 52, 20)).cut(box(202, 30, 20, 4, 52, 20))      # ケーブル出入口
    for x in (40, 165):
        s = s.fuse(box(x-12, 112, 26, 24, 12, 12).cut(cyl(x, 118, 38.01, INS['M4'][0], INS['M4'][1], V(0, 0, -1))))
    for i in range(6):
        s = s.cut(box(20+i*30, 20, -1, 15, 72, 4))                                # 軽量・通風穴
    return s.removeSplitter()

def window_frame():
    """表示窓枠 44×30×4。透明PC 1mm(36×22)を内側から落とし込む段。前面パネルへ接着またはM2(要選定)。"""
    s = box(0, 0, 0, 44, 30, 4).cut(box(6, 6, -1, 32, 18, 6)).cut(box(4, 4, 2.6, 36, 22, 2))
    return s.removeSplitter()

PARTS = [
    # name, func, qty, orientation_note, support, critical(先に試す)
    ('spark_tray', spark_tray, 4, '平置き(底面下)。リップ・つまみ上向き', '不要', True),
    ('fan_duct', duct, 4, 'ファン側フランジを下。ロフト壁は約45°以内', '不要(斜面は外向き45°以内。タブ下のみ要確認)', True),
    ('adapter_tunnel_A', lambda: tunnel(0), 1, '前面格子を下、筒軸を縦', '不要', False),
    ('adapter_tunnel_B', lambda: tunnel(1), 1, '前面格子を下、筒軸を縦', '不要', False),
    ('controller_bracket', ctrl_bracket, 6, 'L字を横倒し(高さ100が積層方向)。L字の曲げ面は層内', '不要', True),
    ('switch_retainer', switch_retainer, 2, '平置き(フランジ下)', '不要', False),
    ('cable_slack_tray', slack_tray, 2, '底面を下', 'タブ下にサポート(ビルドプレートから)', False),
    ('display_window_frame', window_frame, 6, '前面を下', '不要', True),
]
