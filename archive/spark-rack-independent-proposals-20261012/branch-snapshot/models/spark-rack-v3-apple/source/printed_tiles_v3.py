# -*- coding: utf-8 -*-
"""オプション: 外装を板金の代わりにPAHT-CF/ASAタイルで印刷する場合の形状(非構造)。造形向き済み。
側面2×3、天面2×2、肩R40(軸を縦に造形)2×2、前面ラティス3×3、背面格子3×3。裏面にM3インサートボス。"""
import math
import FreeCAD as App, Part
from rack_v3_parameters import *
V = App.Vector

def _boss(s, pts, t):
    for x, y in pts:
        s = s.fuse(Part.makeCylinder(4.5, 6, V(x, y, t))).cut(Part.makeCylinder(2.0, 5.01, V(x, y, t+1)))
    return s

def flat_tile(w, h, t=3.0):
    s = Part.makeBox(w, h, t)
    s = s.fuse(Part.makeBox(w-30, 3, 6, V(15, h/2-1.5, t)))   # 裏リブ
    return _boss(s, [(15, 15), (w-15, 15), (15, h-15), (w-15, h-15)], t).removeSplitter()

def lattice_tile(w, h, d, p, t=4.0, corner=None, R=SHELL_R):
    """千鳥丸穴を面のワイヤーで作って押出し(高速)。corner='tl'/'tr'で上隅を外装Rに合わせて切る。"""
    outer = Part.makePolygon([V(0, 0, 0), V(w, 0, 0), V(w, h, 0), V(0, h, 0), V(0, 0, 0)])
    holes = []
    j = 0; y = 8.0
    while y < h-8:
        x = 8.0 + (p/2 if j % 2 else 0)
        while x < w-8:
            holes.append(Part.Face(Part.Wire(Part.makeCircle(d/2, V(x, y, 0)))))
            x += p
        y += p*math.sqrt(3)/2; j += 1
    f = Part.Face(Part.Wire(outer)).cut(Part.makeCompound(holes))
    s = f.extrude(V(0, 0, t))
    if corner:
        cx = R if corner == 'tl' else w-R
        cut = Part.makeBox(R, R, t+2, V(0 if corner == 'tl' else w-R, h-R, -1)).cut(Part.makeCylinder(R, t+4, V(cx, h-R, -2)))
        s = s.cut(cut)
    s = s.fuse(Part.makeBox(w, 6, t+4, V(0, 0, 0))).fuse(Part.makeBox(w, 6, t+4, V(0, h-6, 0))) if not corner else s.fuse(Part.makeBox(w, 6, t+4))
    return s.removeSplitter()

def shoulder_tile(length, R=SHELL_R, t=3.0):
    """肩R40の1/4円筒。円筒軸を造形Z(縦)にしてサポート無し。"""
    ring = Part.makeCylinder(R, length).cut(Part.makeCylinder(R-t, length))
    q = Part.makeBox(R, R, length)
    return ring.common(q).removeSplitter()

def tiles():
    W_ = OUT_X1-OUT_X0; Hs = H-10; Dd = OUT_Y1-OUT_Y0-LATTICE['t']-REAR_LATTICE['t']
    out = []
    sw, sh = Dd/2, (Hs-SHELL_R)/3
    out.append(('side_tile', lambda: flat_tile(sw, sh), 12, '平置き(外面下)'))
    tw, th = (W_-2*SHELL_R)/2, Dd/2
    out.append(('top_tile', lambda: flat_tile(tw, th), 4, '平置き(外面下)'))
    out.append(('shoulder_R40_tile', lambda: shoulder_tile(Dd/2), 4, '円筒軸を縦'))
    fw, fh = W_/3, Hs/3
    for nm, d, p, t in (('front_lattice', LATTICE['hole_d'], LATTICE['pitch'], 4.0), ('rear_lattice', REAR_LATTICE['hole_d'], REAR_LATTICE['pitch'], 3.0)):
        out.append((f'{nm}_tile', (lambda d=d, p=p, t=t: lattice_tile(fw, fh, d, p, t)), 7, '平置き(外面下)'))
        out.append((f'{nm}_tile_corner_L', (lambda d=d, p=p, t=t: lattice_tile(fw, fh, d, p, t, 'tl')), 1, '平置き(外面下)'))
        out.append((f'{nm}_tile_corner_R', (lambda d=d, p=p, t=t: lattice_tile(fw, fh, d, p, t, 'tr')), 1, '平置き(外面下)'))
    return out
