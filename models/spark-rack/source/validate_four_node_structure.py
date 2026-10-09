"""部品の閉じた形状、部品間干渉、機器の収容、ボルト経路を検査する。"""
import FreeCAD as App

from freecad_four_node_structure import bore, transformed, box
from controller_mount import RACK_U, RACK_PITCH


def positive_overlap(a, b):
    aa, bb = a.BoundBox, b.BoundBox
    return all(min(getattr(aa, axis + 'Max'), getattr(bb, axis + 'Max')) -
               max(getattr(aa, axis + 'Min'), getattr(bb, axis + 'Min')) > 1e-6 for axis in 'XYZ')


def dimensions(shape):
    b = shape.BoundBox
    return [b.XLength, b.YLength, b.ZLength]


def interfaces(item, p):
    """各固定具の締結軸。ねじ径の円柱が印刷部品を突き抜けないことを確認する。"""
    kind = item['part']
    rays = []
    radius = 1.9
    if kind == 'splice':
        rays += [(x, -19, 14, 38, 'Y') for x in (-20, -8, 8, 20)]
    elif kind in ('corner_single', 'corner_double'):
        holes = [(-14, 6), (-14, 22)] if kind == 'corner_double' else [(-14, 14)]
        rays += [(x, -19, z, 35, 'Y') for x, z in holes + [(8, 14), (20, 14)]]
    elif kind.startswith('end_shoe'):
        side = 1 if kind.endswith('left') else -1
        rays += [(-29 if side == 1 else -5, y, 14, 34, 'X') for y in (22, 34)]
        rays += [(x * side, -19, 14, 35, 'Y') for x in (8, 20)]
    elif kind == 'tray':
        rays += [(0, y, -29, 29 + p.tray_thickness, 'Z') for y in (-138, -12)]
    elif kind == 'fan_carrier':
        rays += [(x, -169, -47.25, 46, 'Y') for x in (-p.fan_arm_offset, p.fan_arm_offset)]
        rays += [(x, -207, z, 33, 'Y') for x in (-62.25, 62.25) for z in (-62.25, 62.25)]
    elif kind == 'controller_support':
        rays += [(-47.25, v, -29, 36, 'Z') for v in (-8, 8)]
    elif kind == 'controller_dock':
        rays += [(RACK_U, v, -12, 24, 'Z') for v in (-RACK_PITCH / 2, RACK_PITCH / 2)]
    return [(transformed(bore(x, y, z, radius, length, axis), item), kind)
            for x, y, z, length, axis in rays]


def validate_parts(parts, p):
    reports = {}
    for name, shape in parts.items():
        if not shape.isValid() or not shape.isClosed() or len(shape.Solids) != 1 or shape.Volume <= 0:
            raise ValueError('閉じた単一の部品になっていません: ' + name)
        reports[name] = {'volume_mm3': shape.Volume, 'dimensions_mm': dimensions(shape), 'solid_count': 1}
    return reports


def validate_assembly(report, assembly, p):
    collisions = []
    for i, (a, shape_a) in enumerate(assembly):
        for b, shape_b in assembly[i + 1:]:
            if positive_overlap(shape_a, shape_b):
                volume = shape_a.common(shape_b).Volume
                if volume > 1e-5:
                    collisions.append({'a': a['id'], 'b': b['id'], 'parts': [a['part'], b['part']], 'volume_mm3': volume})
    equipment = [*report['layout']['nodes'].values(), *report['layout']['fans'], *report['layout']['controllers']]
    if report['mode'] != 'ring':
        equipment.append(report['layout']['switch'])
    equipment_collisions = []
    for e in equipment:
        reference = box(*e['origin'], *e['size'])
        for item, shape in assembly:
            if positive_overlap(reference, shape):
                volume = reference.common(shape).Volume
                if volume > 1e-5:
                    equipment_collisions.append({'part': item['id'], 'equipment': e['label'], 'volume_mm3': volume})
    blocked = []
    count = 0
    for item, _ in assembly:
        for shaft, kind in interfaces(item, p):
            count += 1
            for other, shape in assembly:
                if positive_overlap(shaft, shape) and shaft.common(shape).Volume > 1e-5:
                    blocked.append({'interface': item['id'], 'blocked_by': other['id'], 'parts': [kind, other['part']]})
    bounds = App.BoundBox()
    for _, shape in assembly:
        bounds.add(shape.BoundBox)
    for e in equipment:
        bounds.add(box(*e['origin'], *e['size']).BoundBox)
    return {'status': 'passed' if not (collisions or equipment_collisions or blocked) else 'failed',
            'part_count': len(assembly), 'part_collisions': collisions,
            'equipment_collisions': equipment_collisions, 'blocked_fastener_paths': blocked,
            'checked_fastener_paths': count, 'occupied_dimensions_mm': [bounds.XLength, bounds.YLength, bounds.ZLength],
            'physical_validation': '未検証。形状検査は実物の耐荷重・振動・冷却・足の適合を保証しない。'}
