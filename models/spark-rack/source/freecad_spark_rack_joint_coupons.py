"""別部品の継ぎ手を使わない、28mm角の短い接合試験片。"""
from dataclasses import dataclass
import math
import FreeCAD as App
import Part


@dataclass(frozen=True)
class CouponParameters:
    section: float = 28
    clearance: float = 0.3
    root_depth: float = 8
    tenon_depth: float = 12
    tenon_width: float = 12
    stub_length: float = 40
    fork_engagement: float = 24
    fork_floor: float = 4.3


def box(x, y, z, dx, dy, dz):
    return Part.makeBox(dx, dy, dz, App.Vector(x, y, z))


def prism(points, bottom, height):
    vertices = [App.Vector(x, y, bottom) for x, y in points]
    return Part.Face(Part.makePolygon(vertices + vertices[:1])).extrude(App.Vector(0, 0, height))


def clip_polygon(points, threshold, keep_above):
    result = []
    previous = points[-1]
    old = previous[1] - previous[0] - threshold
    for current in points:
        new = current[1] - current[0] - threshold
        inside = new >= 0 if keep_above else new <= 0
        old_inside = old >= 0 if keep_above else old <= 0
        if inside != old_inside:
            t = old / (old - new)
            result.append((previous[0] + t * (current[0] - previous[0]), previous[1] + t * (current[1] - previous[1])))
        if inside:
            result.append(current)
        previous, old = current, new
    return result


def parts(p=None):
    p = p or CouponParameters()
    if p.section != 28 or not 0 < p.clearance < 1:
        raise ValueError('この試験片は28mm角、片側隙間0〜1mm用です')
    c = p.clearance
    receiver = box(-28, -14, -28, 28, 28, 56)
    receiver = receiver.cut(box(-8 - c, -14 - c, 0, 9 + c, 28 + 2 * c, 29))
    receiver = receiver.cut(box(-28 - c, 6 - c, 0, 28 + 2 * c, 9 + c, 29))
    receiver = receiver.cut(box(-20 - c, -6 - c, 8, 12 + 2 * c, 12 + 2 * c, 21))
    lower = box(-8, -14, 0, p.stub_length + 8, 28, 28).fuse(box(-20, -6, 10, 12, 12, 8))
    upper = box(-8, -14, 0, p.stub_length + 8, 28, 28).fuse(box(-20, -6, 20, 12, 12, 6))
    # 隣接する2本の梁の根元を、角の内側だけ相補的に逃がす。
    square = [(-8, 6), (0, 6), (0, 14), (-8, 14)]
    shift = c * math.sqrt(2) / 2
    lower_cut = clip_polygon(square, 14 - shift, True)
    lower = lower.cut(prism(lower_cut, -1, 30))
    upper_cut = clip_polygon(square, 14 + shift, False)
    upper_local = [(y - 14, -(x + 14)) for x, y in upper_cut]
    upper = upper.cut(prism(upper_local, -1, 30))
    # 直線部の二股は上へ開き、差し込み側も上から入る。
    fork = box(-40, -14, 0, 40, 28, 28)
    fork = fork.cut(box(-p.fork_engagement - c, -6 - c, p.fork_floor,
                        p.fork_engagement + c + 1, 12 + 2 * c, 28))
    blade = box(0, -14, 0, 40, 28, 28).fuse(box(-p.fork_engagement, -6, p.fork_floor,
                                               p.fork_engagement, 12, 28 - p.fork_floor - c))
    return {'column_socket': receiver.removeSplitter(), 'beam_lower_tenon': lower.removeSplitter(),
            'beam_upper_tenon': upper.removeSplitter(), 'beam_fork': fork.removeSplitter(),
            'beam_drop_blade': blade.removeSplitter()}


def corner_assembly(shapes):
    upper = shapes['beam_upper_tenon'].copy()
    upper.rotate(App.Vector(), App.Vector(0, 0, 1), 90)
    upper.translate(App.Vector(-14, 14, 0))
    return [('column_socket', shapes['column_socket']), ('beam_lower_tenon', shapes['beam_lower_tenon']),
            ('beam_upper_tenon', upper)]


def airflow_preview():
    # 円から本体前面の参考外形へ絞る案。通気口は未実測、製造用には出力しない。
    def circle(radius):
        angles = [0, math.pi / 4, 3 * math.pi / 4, 5 * math.pi / 4, 7 * math.pi / 4, 2 * math.pi]
        def point(angle):
            return App.Vector(radius * math.cos(angle), -175, radius * math.sin(angle))
        edges = [Part.Arc(point(a), point((a + b) / 2), point(b)).toShape() for a, b in zip(angles, angles[1:])]
        return Part.Wire(edges)
    def rectangle(width, height):
        points = [App.Vector(x, -152, z) for x, z in [(width / 2, 0), (width / 2, height / 2),
                  (-width / 2, height / 2), (-width / 2, -height / 2), (width / 2, -height / 2)]]
        return Part.makePolygon(points + points[:1])
    outer = Part.makeLoft([circle(68.4), rectangle(158.8, 59.3)], True, True)
    inner = Part.makeLoft([circle(66), rectangle(154, 54.5)], True, True)
    return outer.cut(inner).removeSplitter()
