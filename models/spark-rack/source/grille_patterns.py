"""前面と天板の通気の模様。縦溝とハニカムを同じ入口で作る。

ハニカムは頂点を上下へ向けた正六角形の穴を、横の行ごとに半ピッチずらして並べる。
穴は範囲の内側に収まるものだけを開け、縁で細く欠けた壁を作らない。
"""
import math

import FreeCAD as App
import Part


def _hexagon(cu, cv, across_flats, plane, offset, depth):
    """planeは'xz'（前後方向へ抜く）か'xy'（上下方向へ抜く）。"""
    r = across_flats / math.sqrt(3)
    points = []
    for i in range(7):
        angle = math.radians(90 + 60 * i)
        u, v = cu + r * math.cos(angle), cv + r * math.sin(angle)
        points.append(App.Vector(u, offset, v) if plane == 'xz' else App.Vector(u, v, offset))
    face = Part.Face(Part.makePolygon(points))
    return face.extrude(App.Vector(0, depth, 0) if plane == 'xz' else App.Vector(0, 0, depth))


def _centers(u0, u1, v0, v1, across_flats, wall, inside):
    """範囲の中央へ寄せた六角形の中心。insideで穴全体が収まるかを判定する。"""
    pitch = across_flats + wall
    row = pitch * math.sqrt(3) / 2
    r = across_flats / math.sqrt(3)
    rows = int((v1 - v0 - 2 * r) // row) + 1 if v1 - v0 >= 2 * r else 0
    cols = int((u1 - u0 - across_flats) // pitch) + 1 if u1 - u0 >= across_flats else 0
    if rows <= 0 or cols <= 0:
        return []
    height = (rows - 1) * row
    width = (cols - 1) * pitch + (pitch / 2 if rows > 1 else 0)
    su, sv = (u0 + u1 - width) / 2, (v0 + v1 - height) / 2
    centers = []
    for j in range(rows):
        for i in range(cols + 1):
            cu, cv = su + i * pitch + (pitch / 2 if j % 2 else 0), sv + j * row
            if inside(cu, cv, r):
                centers.append((cu, cv))
    return centers


def honeycomb_in_rect(u0, u1, v0, v1, offset, depth, plane, across_flats=10, wall=2):
    def inside(cu, cv, r):
        return (cu - across_flats / 2 >= u0 - 1e-9 and cu + across_flats / 2 <= u1 + 1e-9
                and cv - r >= v0 - 1e-9 and cv + r <= v1 + 1e-9)
    return [_hexagon(cu, cv, across_flats, plane, offset, depth)
            for cu, cv in _centers(u0, u1, v0, v1, across_flats, wall, inside)]


def honeycomb_in_circle(cu0, cv0, radius, offset, depth, plane, across_flats=10, wall=2):
    def inside(cu, cv, r):
        return math.hypot(cu - cu0, cv - cv0) + r <= radius + 1e-9
    centers = _centers(cu0 - radius, cu0 + radius, cv0 - radius, cv0 + radius, across_flats, wall, inside)
    return [_hexagon(cu, cv, across_flats, plane, offset, depth) for cu, cv in centers]


def honeycomb_clipped_to_circle(cu0, cv0, radius, offset, depth, plane, across_flats=10, wall=2,
                                minimum_fragment_area=12):
    """円の内側の六角形と、縁で円に沿って切った六角形。小さすぎる欠片は穴にしない。"""
    r = across_flats / math.sqrt(3)
    def touches(cu, cv, _r):
        return math.hypot(cu - cu0, cv - cv0) - r < radius
    centers = _centers(cu0 - radius - r, cu0 + radius + r, cv0 - radius - r, cv0 + radius + r,
                       across_flats, wall, touches)
    axis = App.Vector(0, 1, 0) if plane == 'xz' else App.Vector(0, 0, 1)
    origin = App.Vector(cu0, offset, cv0) if plane == 'xz' else App.Vector(cu0, cv0, offset)
    disk = Part.makeCylinder(radius, depth, origin, axis)
    holes = []
    for cu, cv in centers:
        hexagon = _hexagon(cu, cv, across_flats, plane, offset, depth)
        if math.hypot(cu - cu0, cv - cv0) + r <= radius + 1e-9:
            holes.append(hexagon)
            continue
        piece = hexagon.common(disk)
        for solid in piece.Solids:
            if solid.Volume / depth >= minimum_fragment_area:
                holes.append(solid)
    return holes


def cut_all(shape, tools):
    return shape.cut(Part.makeCompound(tools)) if tools else shape
