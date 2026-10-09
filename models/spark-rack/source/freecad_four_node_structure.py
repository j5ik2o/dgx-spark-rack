"""4台ラックの共通枠・本体支持・ファン保持の部品検討案を作る。"""
from pathlib import Path
import sys
import FreeCAD as App
import Part

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/cad'))
from controller_mount import dock, place, RACK_U, RACK_PITCH
from four_node_structure_parameters import StructureParameters, instances


def box(x, y, z, dx, dy, dz):
    return Part.makeBox(dx, dy, dz, App.Vector(x, y, z))


def bore(x, y, z, radius, length, axis='Y'):
    return Part.makeCylinder(radius, length, App.Vector(x, y, z),
                             App.Vector(*{'X': (1, 0, 0), 'Y': (0, 1, 0), 'Z': (0, 0, 1)}[axis]))


def beam(length, p, horizontal=(), vertical=(), end_holes=True):
    shape = box(0, -14, 0, length, 28, 28)
    holes = [(x, 14) for x in horizontal]
    if end_holes:
        holes.extend((x, 14) for x in (8, 20, length - 20, length - 8))
    for x, z in set(holes):
        shape = shape.cut(bore(x, -15, z, p.bolt_hole / 2, 30))
    for x in vertical:
        shape = shape.cut(bore(x, 0, -1, p.bolt_hole / 2, 30, 'Z'))
    return shape.removeSplitter()


def column(index, p):
    length = p.column_lengths[index]
    start = sum(p.column_lengths[:index])
    shape = beam(length, p, end_holes=False)
    positions = []
    if index > 0:
        positions += [8, 20]
    if index < 2:
        positions += [length - 20, length - 8]
    if index == 0:
        positions += [6, 22]
    if index == 2:
        positions += [length - 22, length - 6]
    for x in positions:
        shape = shape.cut(bore(x, -15, 14, p.bolt_hole / 2, 30))
        if (index == 0 and x in (6, 22)) or (index == 2 and x in (length - 22, length - 6)):
            for y in (-14, 10.6):
                shape = shape.cut(hex_y(x, 14, y, 3.4))
    # 外周、リング支持、スイッチ支持、将来の中央支持段の取付位置。
    for height in (14, 50, 163.25, 210, 270, 406):
        if start < height < start + length:
            shape = shape.cut(bore(height - start, 0, -1, p.bolt_hole / 2, 30, 'Z'))
            if height in (14, 406):
                for z in (0, 24.6):
                    pocket = hex_pocket(height - start, 0, 3.4)
                    pocket.translate(App.Vector(0, 0, z))
                    shape = shape.cut(pocket)
    return shape.removeSplitter()


def splice(p):
    c, w, base, half = p.fit_clearance, p.splice_wall, p.splice_base, p.splice_length / 2
    shape = box(-half, -14 - c - w, -base - c, p.splice_length, 28 + 2 * c + 2 * w, base)
    for y in (-14 - c - w, 14 + c):
        shape = shape.fuse(box(-half, y, -c - 0.1, p.splice_length, w, 28 + c + 0.1))
    for x in (-20, -8, 8, 20):
        shape = shape.cut(bore(x, -20, 14, p.bolt_hole / 2, 40))
    return shape.removeSplitter()


def corner(double, p):
    shape = box(-28, -18, 0, 60, 4, 28)
    holes = [(-14, 6), (-14, 22)] if double else [(-14, 14)]
    holes += [(8, 14), (20, 14)]
    for x, z in holes:
        shape = shape.cut(bore(x, -19, z, p.bolt_hole / 2, 6))
    return shape.removeSplitter()


def end_shoe(side, p):
    shape = box(-28 if side == 1 else -44, -18, -6, 72, 66, 6)
    shape = shape.fuse(box(0 if side == 1 else -4, 14, 0, 4, 34, 28))
    shape = shape.fuse(box(0 if side == 1 else -26, -18, 0, 26, 4, 28))
    for y in (22, 34):
        shape = shape.cut(bore(-5, y, 14, p.bolt_hole / 2, 10, 'X'))
    for x in (8 * side, 20 * side):
        shape = shape.cut(bore(x, -19, 14, p.bolt_hole / 2, 6))
    return shape.removeSplitter()


def tray(p):
    half = p.tray_width / 2
    front = 2 - p.tray_depth
    shape = box(-half, front, 0, p.tray_width, p.tray_depth, p.tray_thickness)
    # 外周の支持面と中央の十字を残す。足の接触位置は実測後に調整する。
    x_ranges = [(-half + p.tray_border, -p.tray_rib / 2), (p.tray_rib / 2, half - p.tray_border)]
    y_ranges = [(front + p.tray_border, -75 - p.tray_rib / 2), (-75 + p.tray_rib / 2, 2 - p.tray_border)]
    for x0, x1 in x_ranges:
        for y0, y1 in y_ranges:
            shape = shape.cut(box(x0, y0, -1, x1 - x0, y1 - y0, p.tray_thickness + 2))
    for x in (-half, half - 2):
        shape = shape.fuse(box(x, front, p.tray_thickness - 0.1, 2, p.tray_depth, p.tray_lip + 0.1))
    shape = shape.fuse(box(-half, front, p.tray_thickness - 0.1, p.tray_width, 2, p.tray_lip + 0.1))
    for y in (-138, -12):
        shape = shape.cut(bore(0, y, -1, p.bolt_hole / 2, p.tray_thickness + 2, 'Z'))
        shape = shape.cut(Part.makeCone(p.bolt_hole / 2, p.bolt_head / 2, 2,
                                      App.Vector(0, y, p.tray_thickness - 2)))
    return shape.removeSplitter()


def fan_carrier(p):
    shape = box(-p.fan_plate_width / 2, -206, -p.fan_plate_height / 2,
                p.fan_plate_width, p.fan_plate_thickness, p.fan_plate_height)
    shape = shape.cut(bore(0, -207, 0, p.fan_opening / 2, 6))
    for x in (-62.25, 62.25):
        for z in (-62.25, 62.25):
            shape = shape.cut(bore(x, -207, z, p.bolt_hole / 2, 6))
    # 支持梁の前面へ留める腕。ファン外形より外へ出し、羽根の領域を避ける。
    for x in (-p.fan_arm_offset - 5, p.fan_arm_offset - 5):
        arm = box(x, -202, -61.25, 10, 50, 28)
        arm = arm.cut(box(x - 1, -192, -55.25, 12, 24, 16))
        arm = arm.cut(bore(x + 5, -169, -47.25, p.bolt_hole / 2, 18))
        shape = shape.fuse(arm)
    return shape.removeSplitter()


def hex_pocket(u, v, depth):
    import math
    r = 7.3 / math.sqrt(3)
    points = [App.Vector(u + r * math.cos(i * math.pi / 3), v + r * math.sin(i * math.pi / 3), 0)
              for i in range(6)]
    return Part.Face(Part.makePolygon(points + points[:1])).extrude(App.Vector(0, 0, depth))


def hex_y(x, z, y, depth):
    import math
    r = 7.3 / math.sqrt(3)
    points = [App.Vector(x + r * math.cos(i * math.pi / 3), y, z + r * math.sin(i * math.pi / 3)) for i in range(6)]
    return Part.Face(Part.makePolygon(points + points[:1])).extrude(App.Vector(0, depth, 0))


def foot(p):
    half = 18 + p.fit_clearance + 2
    shape = box(-half, -half, -8, half * 2, half * 2, 8)
    shape = shape.fuse(box(-half, -half, -0.1, 2, half * 2, 2.1))
    shape = shape.fuse(box(-half, -half, -0.1, half * 2, 2, 2.1))
    return shape.removeSplitter()


def controller_support(p):
    shape = box(-56, -22, 0, 112, 44, 6)
    for v in (-RACK_PITCH / 2, RACK_PITCH / 2):
        shape = shape.cut(bore(RACK_U, v, -1, p.bolt_hole / 2, 8, 'Z'))
        shape = shape.cut(hex_pocket(RACK_U, v, 3.4))
    for v in (-8, 8):
        shape = shape.cut(bore(-47.25, v, -1, p.bolt_hole / 2, 8, 'Z'))
    return shape.removeSplitter()


def shapes(p=None):
    p = p or StructureParameters()
    p.validate()
    left = beam(250, p, horizontal=(34, 190, 214), vertical=(112,))
    right = beam(214, p, horizontal=(120,), vertical=(42,))
    # 柱側に捕捉したナットからのねじ先端を、隣接梁の端へ逃がす。
    left = left.cut(bore(-1, 0, 14, p.bolt_hole / 2, 6, 'X')).removeSplitter()
    right = right.cut(bore(209, 0, 14, p.bolt_hole / 2, 6, 'X')).removeSplitter()
    front = beam(190, p, horizontal=(112, 128))
    for pos in (106, 134):
        front = front.cut(bore(pos, -15, 19, p.bolt_hole / 2, 30))
    for z in (6, 22):
        front = front.cut(bore(-1, 0, z, p.bolt_hole / 2, 6, 'X'))
    rear = beam(142, p, horizontal=(70, 82))
    for z in (6, 22):
        rear = rear.cut(bore(137, 0, z, p.bolt_hole / 2, 6, 'X'))
    return {'cross_1': left, 'cross_2': right, 'side_1': front,
            'side_2': beam(142, p, horizontal=(86, 98)),
            'side_3': rear.removeSplitter(),
            **{'column_' + str(i + 1): column(i, p) for i in range(3)},
            'splice': splice(p), 'corner_single': corner(False, p), 'corner_double': corner(True, p),
            'end_shoe_left': end_shoe(1, p), 'end_shoe_right': end_shoe(-1, p),
            'tray': tray(p), 'fan_carrier': fan_carrier(p),
            'controller_support': controller_support(p), 'controller_dock': dock(),
            'joint_fit_stub': beam(40, p), 'foot': foot(p)}


def transformed(shape, item):
    if 'basis' in item:
        basis = item['basis']
        return place(shape, item['origin'], basis['u'], basis['v'], basis['w'])
    rotation = App.Rotation()
    for axis, degrees in item['rotation']:
        rotation = rotation.multiply(App.Rotation(App.Vector(*{'x': (1, 0, 0), 'y': (0, 1, 0), 'z': (0, 0, 1)}[axis]), degrees))
    result = shape.copy()
    result.Placement = App.Placement(App.Vector(*item['origin']), rotation).multiply(result.Placement)
    return result


def assembly(p, parts, mode):
    report = instances(mode, p)
    return report, [(item, transformed(parts[item['part']], item)) for item in report['instances']]
