"""固定段ラックの接合を含む形状候補。正本の入口はfreecad_spark_rack.py。"""
import math
from pathlib import Path
import sys

import FreeCAD as App
import Part

from fixed_rack_layout import cross_beams, fixed_layout
from spark_rack_parameters import FixedRackParameters

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/cad'))
from controller_mount import dock, place, THICKNESS, RACK_U, RACK_PITCH
from integrated_rack_supports import integrated_supports
from controller_front_face import controller_front_face, load_case_model

ROLE_COLORS = {'spark': (.77, .61, .30), 'fan': (.79, .70, .56), 'adapter': (.30, .34, .38),
               'switch': (.52, .54, .60), 'separator': (.40, .56, .63),
               'side_panel': (.69, .71, .73), 'frame_beam': (.69, .71, .73),
               'carrier': (.62, .65, .67), 'power_carrier': (.62, .65, .67),
               'controller_face': (.62, .65, .67), 'case_reference': (.19, .21, .23),
               'controller_display_reference': (.12, .19, .22),
               'controller_knob_reference': (.18, .19, .20),
               'accessory': (.20, .22, .25), 'mid_panel': (.62, .65, .67),
               'removable_cover': (.62, .65, .67), 'top_lid': (.69, .71, .73), 'lower_filler': (.62, .65, .67)}


def box(origin, size):
    return Part.makeBox(*size, App.Vector(*origin))


def cylinder(origin, radius, length, axis):
    return Part.makeCylinder(radius, length, App.Vector(*origin), App.Vector(*axis))


def rounded_window(x, y, z, depth, width, height, radius=8):
    shape = box([x, y, z], [depth, width, height])
    edges = [e for e in shape.Edges if abs(e.BoundBox.XLength - depth) < 1e-6]
    return shape.makeFillet(min(radius, width / 4, height / 4), edges)


def vent_grid(x, y0, y1, z0, z1, depth, p, pattern=None):
    """側枠の通気穴。patternを省くと角丸の縦長穴、honeycombなら同じ余白の内側を六角形の穴で抜く。"""
    if pattern is not None and pattern.style == 'honeycomb':
        from grille_patterns import honeycomb_in_rect
        return honeycomb_in_rect(y0 + 6, y1 - 6, z0 + 5, z1 - 5, x, depth, 'yz',
                                 pattern.hex_across_flats, pattern.hex_wall)
    tools = []
    y = y0 + 6
    while y + p.vent_slot_width <= y1 - 6:
        z = z0 + 5
        while z + p.vent_slot_height <= z1 - 5:
            tools.append(rounded_window(x, y, z, depth, p.vent_slot_width, p.vent_slot_height, 3))
            z += p.vent_row_pitch
        y += p.vent_pitch
    return tools


def side_pattern(p, right, support_metadata=None, bay=None, accessories=None, pattern=None):
    if support_metadata is None:
        scene = fixed_layout(parameters=p, bay=bay, accessories=accessories)
        _, support_metadata = integrated_supports(scene, p)
        if bay is not None:
            from switch_bay_geometry import switch_bay_parts
            support_metadata = merge_bay(support_metadata, switch_bay_parts(scene, p, bay)[1])
        if accessories is not None:
            from accessory_geometry import accessory_parts
            support_metadata = merge_bay(support_metadata, accessory_parts(scene, p, accessories)[1], 'accessories')
    x = p.width / 2 - p.section if right else -p.width / 2
    skin_x = p.width / 2 - p.skin if right else x
    s = box([skin_x, p.front_y, 0], [p.skin, p.depth, p.height])
    for y in (p.front_y, p.panel_split_y - 14, p.rear_y - 28):
        s = s.fuse(box([x, y, 0], [p.section, 28, p.height]))
    bands = [(0, 40), (p.power_ceiling_z - 4, p.lower_base), (p.switch_center_z - 50, p.switch_center_z - 22),
             (p.upper_base - 60, p.upper_base), (p.height - 28, p.height)]
    upper_zones = [(p.upper_base, p.height - 28)]
    if bay is not None:
        # 専用段の床を受ける帯。通気穴の範囲をこの帯の上下へ分ける。
        bands.append((bay['floor_z'] - 12, bay['switch_z']))
        upper_zones = [(p.upper_base, bay['floor_z'] - 12), (bay['switch_z'], p.height - 28)]
    lower_zone_top, middle_zone_bottom = p.switch_center_z - 50, p.switch_center_z - 22
    if accessories is not None:
        # 中段の機器棚を受ける帯。通気穴の範囲をこの帯の上下へ縮める。
        band = (accessories['shelf_z'] - 12, accessories['support_z'] + 8)
        bands.append(band)
        lower_zone_top = min(lower_zone_top, band[0])
        middle_zone_bottom = max(middle_zone_bottom, band[1])
    for z0, z1 in bands:
        s = s.fuse(box([x, p.front_y, z0], [p.section, p.depth, z1 - z0]))
    ys = ((p.front_y + 28, p.panel_split_y - 14), (p.panel_split_y + 14, p.rear_y - 28))
    zs = [(p.lower_base, lower_zone_top), (middle_zone_bottom, p.upper_base - 60)] + upper_zones
    vents = []
    for y0, y1 in ys:
        for z0, z1 in zs:
            vents.extend(vent_grid(x - 1, y0, y1, z0, z1, p.section + 2, p, pattern))
    # 内側を開放したポケット。受けの下面と分割境界は全厚で外壁へつなぐ。
    inner_x = x - 1 if right else x + p.skin
    pocket = rounded_window(inner_x, p.front_y + 28, 4,
                            p.section - p.skin + 1, p.depth - 56, p.height - 8)
    protected = [(p.panel_split_y - 14, p.panel_split_y + 14, 0, p.height),
                 (-198, -42, 10, 166)]
    protected += [(p.front_y, p.rear_y, z - p.lap_length / 2, z + p.lap_length / 2)
                  for z in p.panel_splits_z]
    for socket in support_metadata['socket_envelopes']:
        if (socket['side'] == 'right') == right:
            oy, oz = socket['cut_origin'][1:]
            dy, dz = socket['cut_size'][1:]
            protected.append((oy, oy + dy, socket['bearing_z'] - 6, oz + dz + 2))
    beams = cross_beams(p, bay)
    for beam in beams:
        oy, oz = beam['origin'][1:]
        dy, dz = beam['size'][1:]
        protected.append((oy - p.fit_clearance, oy + dy + p.fit_clearance,
                          oz - 6, oz + dz + p.fit_clearance + 2))
    keepouts = [box([inner_x - 1, y0, z0], [p.section + 2, y1 - y0, z1 - z0])
                for y0, y1, z0, z1 in protected]
    pocket = pocket.cut(Part.makeCompound(keepouts))
    s = s.cut(pocket).cut(Part.makeCompound(vents))
    lower_vents = vent_grid(x - 1, -310, -210, 45, 140, p.section + 2, p, pattern)
    lower_vents += vent_grid(x - 1, -25, 72, 45, 140, p.section + 2, p, pattern)
    s = s.cut(Part.makeCompound(lower_vents))
    # 保持板を外面の4mmの座へ収め、120mm角のファンが外へ通る開口を残す。
    s = s.cut(rounded_window(x - 1, -183, 25, p.section + 2, 126, 126, 6))
    recess_x = x + p.section - 4 if right else x - 1
    s = s.cut(box([recess_x, -192, 16], [5, 144, 144]))
    for b in beams:
        y, z = b['origin'][1:]
        pocket_x = x - 1 if right else x + p.section - 8 - p.fit_clearance
        s = s.cut(box([pocket_x, y - p.fit_clearance, z],
                      [9 + p.fit_clearance, b['size'][1] + 2 * p.fit_clearance,
                       b['size'][2] + p.fit_clearance]))
    for socket in support_metadata['socket_envelopes']:
        if (socket['side'] == 'right') == right:
            s = s.cut(box(socket['cut_origin'], socket['cut_size']))
    # 重ね継ぎを締める穴は内側から。外側の面には2mmの皮を残す。
    joins = [(p.panel_split_y, 16), (p.panel_split_y, p.height - 12)]
    joins += [(y, z) for z in p.panel_splits_z for y in (p.front_y + 14, p.panel_split_y, p.rear_y - 14)]
    for y, z in joins:
        hole_x = x - 1 if right else x + 2
        s = s.cut(cylinder([hole_x, y, z], 2.25, p.section - 1, [1, 0, 0]))
    return s.removeSplitter()


def side_tiles(p, right, support_metadata=None, bay=None, accessories=None, pattern=None):
    frame = side_pattern(p, right, support_metadata, bay, accessories, pattern)
    h = p.lap_length / 2
    ys = [(p.front_y, p.panel_split_y - h, (0,)),
          (p.panel_split_y - h, p.panel_split_y + h, (0, 1)),
          (p.panel_split_y + h, p.rear_y, (1,))]
    z0, z1 = p.panel_splits_z
    zs = [(0, z0 - h, (0,)), (z0 - h, z0 + h, (0, 1)),
          (z0 + h, z1 - h, (1,)), (z1 - h, z1 + h, (1, 2)),
          (z1 + h, p.height, (2,))]
    result = []
    for row in range(3):
        for col in range(2):
            masks = []
            for ylo, yhi, cols in ys:
                if col not in cols:
                    continue
                for zlo, zhi, rows in zs:
                    if row not in rows:
                        continue
                    layers = len(cols) * len(rows)
                    layer = rows.index(row) * len(cols) + cols.index(col)
                    thick = p.section / layers
                    x = p.width / 2 - (layer + 1) * thick if right else -p.width / 2 + layer * thick
                    masks.append(box([x, ylo, zlo], [thick, yhi - ylo, zhi - zlo]))
            # 重ね継ぎの各層を領域ごとに切り出して一体化する。
            fragments = [frame.common(mask) for mask in masks]
            fragments = [fragment for fragment in fragments if fragment.Volume > 1e-7]
            shape = fragments[0].multiFuse(fragments[1:]).removeSplitter()
            result.append({'name': f'side_{"right" if right else "left"}_{row}_{col}',
                           'label': f'{"右" if right else "左"}側枠・{row + 1}段目・{col + 1}枚目',
                           'shape': shape, 'role': 'side_panel'})
    return result


def beam_segments(b, p):
    start, y, z = b['origin']
    length, width, height = b['size']
    pitch, h = length / 3, p.lap_length / 2
    parts = []
    for i in range(3):
        a, end = start + i * pitch, start + (i + 1) * pitch
        lo, hi = a - (h if i else 0), end + (h if i < 2 else 0)
        shape = box([lo, y, z], [hi - lo, width, height])
        if i:
            shape = shape.cut(box([a - h - 1, y - 1, z - 1], [2 * h + 1, width + 2, height / 2 + 1]))
        if i < 2:
            shape = shape.cut(box([end - h, y - 1, z + height / 2], [2 * h + 1, width + 2, height / 2 + 1]))
        for joint in (start + pitch, start + 2 * pitch):
            if lo < joint < hi:
                shape = shape.cut(cylinder([joint, y + width / 2, z - 1], 2.25, height + 2, [0, 0, 1]))
        parts.append({'name': b['name'] + '_' + str(i), 'label': '重ね継ぎでつなぐ' + b['name'],
                      'shape': shape.removeSplitter(), 'role': b['kind']})
    return parts


def ring_tray(b, rim=9):
    x, y, z = b['origin']
    dx, dy, dz = b['size']
    s = box(b['origin'], b['size'])
    s = s.cut(box([x + rim, y + rim, z - 1], [dx - 2 * rim, dy - 2 * rim, dz + 2]))
    return s.removeSplitter()


def fan_carrier(node, p, pattern=None):
    """patternを省くと従来の縦の格子。honeycombなら円の内側を六角形の穴で抜く。"""
    x = node['origin'][0] + p.spark_width / 2
    z = node['origin'][2] + p.spark_height / 2
    y = p.front_face_y
    xlo = -p.inner_width / 2 if x < 0 else 0
    s = box([xlo, y, z - 76], [p.inner_width / 2, 4, 152])
    honeycomb = pattern is not None and pattern.style == 'honeycomb'
    if not honeycomb:
        s = s.cut(cylinder([x, y - 1, z], p.fan_opening / 2, 6, [0, 1, 0]))
    for sx in (-1, 1):
        for sz in (-1, 1):
            s = s.cut(cylinder([x + sx * p.fan_pitch / 2, y - 1, z + sz * p.fan_pitch / 2],
                               2.25, 6, [0, 1, 0]))
        s = s.fuse(box([x + sx * 78 - 6, y, z - 76], [12, 24, 10]))
    # 外へ張り出す持ち手を廃止し、下縁の指掛かりを前面内へ収める。
    s = s.cut(box([x - 16, y - 1, z - 76 + 2], [32, 3, 3]))
    if honeycomb:
        from grille_patterns import cut_all, honeycomb_clipped_to_circle
        holes = honeycomb_clipped_to_circle(x, z, p.fan_opening / 2, y - 1, 6, 'xz', pattern.hex_across_flats,
                                            pattern.hex_wall, pattern.minimum_fragment_area)
        return cut_all(s, holes).removeSplitter()
    return grille(s, x, z, y, 4, p.fan_opening / 2, 'y', p)


def grille(shape, u_center, z_center, plane, depth, radius, axis, p):
    strips = []
    u = -radius
    pitch = p.vent_slot_width + p.vent_rib_width
    while u <= radius:
        if axis == 'y':
            strips.append(box([u_center + u - p.vent_rib_width / 2, plane, z_center - radius - 2],
                              [p.vent_rib_width, depth, 2 * radius + 4]))
        else:
            strips.append(box([plane, u_center + u - p.vent_rib_width / 2, z_center - radius - 2],
                              [depth, p.vent_rib_width, 2 * radius + 4]))
        u += pitch
    # 円の外へはみ出した部分を外周に接続し、長い細片を独立部品にしない。
    return shape.multiFuse(strips).removeSplitter()


def power_carrier(p, right, pattern=None):
    """patternを省くと従来の縦の格子。honeycombなら円の内側を六角形の穴で抜く。"""
    x = p.width / 2 - 4 if right else -p.width / 2
    s = box([x, -192, 16], [4, 144, 144])
    honeycomb = pattern is not None and pattern.style == 'honeycomb'
    if not honeycomb:
        s = s.cut(cylinder([x - 1, -120, 88], 57, 6, [1, 0, 0]))
    for sy in (-1, 1):
        for sz in (-1, 1):
            s = s.cut(cylinder([x - 1, -120 + sy * p.power_fan_pitch / 2,
                                88 + sz * p.power_fan_pitch / 2], 2.25, 6, [1, 0, 0]))
    if honeycomb:
        from grille_patterns import cut_all, honeycomb_clipped_to_circle
        holes = honeycomb_clipped_to_circle(-120, 88, 57, x - 1, 6, 'yz', pattern.hex_across_flats,
                                            pattern.hex_wall, pattern.minimum_fragment_area)
        return cut_all(s, holes).removeSplitter()
    return grille(s, -120, 88, x, 4, 57, 'x', p)


def control_panel_halves(scene, p, face=None):
    panel = scene['control_panel']
    x, y, z = panel['origin']
    dx, dy, dz = panel['size']
    whole = box(panel['origin'], panel['size'])
    for center_z in p.controller_centers_z:
        for center_x in (-90, 90):
            for offset in (-RACK_PITCH / 2, RACK_PITCH / 2):
                whole = whole.cut(cylinder([center_x + RACK_U, y - 1, center_z + offset], 2.25, dy + 2, [0, 1, 0]))
    if face is not None:
        for hole in face['mount_holes']:
            whole = whole.cut(cylinder(hole['origin'], hole['radius'], hole['length'], hole['axis']))
    parts = []
    for i in range(2):
        lo, hi = (x, 12) if i == 0 else (-12, x + dx)
        shape = whole.common(box([lo, y, z], [hi - lo, dy, dz]))
        cut_y = y + dy / 2 if i == 0 else y - 1
        shape = shape.cut(box([-12, cut_y, z - 1], [24, dy / 2 + 1, dz + 2]))
        shape = shape.cut(cylinder([0, y - 1, 78], 2.25, dy + 2, [0, 1, 0]))
        parts.append({'name': 'control_panel_' + str(i), 'label': '制御器扉の取付面・重ね継ぎ',
                      'shape': shape.removeSplitter(), 'role': 'control_panel'})
    return parts


def ceiling_tiles(scene):
    b = scene['separator']
    x, y, z = b['origin']
    dx, dy, dz = b['size']
    return [{'name': f'ceiling_{col}_{row}', 'label': '電源区画の水平な仕切り・固定方法は未設計',
             'shape': box([x + col * dx / 3, y + row * dy / 2, z], [dx / 3, dy / 2, dz]), 'role': 'separator'}
            for row in range(2) for col in range(3)]


def case_references(scene, p, case_model=None):
    model = case_model if case_model is not None else load_case_model()
    cx = (model['envelope_x'] + model['outer_right']) / 2
    cy = (model['envelope_y'] + model['envelope_back']) / 2
    shift = App.Vector(-cx, -cy, THICKNESS - model['bottom_z'])
    normalized = []
    for name, shape in [('body', model['body_final']), ('lid', model['lid_final'])] + [(f'clamp{i}', s) for i, s in enumerate(model['clamps'])]:
        shape = shape.copy()
        shape.translate(shift)
        normalized.append((name, shape))
    result = []
    for row, z in enumerate(p.controller_centers_z):
        for col, x in enumerate((-90, 90)):
            origin = (x, p.controller_origin_y, z)
            axes = ((1, 0, 0), (0, 0, 1), (0, -1, 0))
            result.append({'name': f'dock_{row}_{col}', 'label': '既存の共通ドック',
                           'shape': place(dock(), origin, *axes), 'role': 'controller_dock'})
            for name, shape in normalized:
                result.append({'name': f'case_{row}_{col}_{name}', 'label': f'制御器{row + 1}列{col + 1}・{name}',
                               'shape': place(shape, origin, *axes), 'role': 'case_reference'})
    return result


def merge_bay(support_metadata, bay_metadata, key_name='switch_bay'):
    """専用段や機器棚の受け・支持面・ねじ候補を、固定棚の記録へ加える。"""
    for key in ('socket_envelopes', 'support_surfaces', 'fastener_candidates', 'bearing_surfaces', 'assemblies'):
        support_metadata[key] = support_metadata[key] + bay_metadata[key]
    support_metadata[key_name] = {k: v for k, v in bay_metadata.items()
                                  if k not in ('socket_envelopes', 'support_surfaces', 'fastener_candidates',
                                               'bearing_surfaces', 'assemblies')}
    return support_metadata


def shapes(parameters=None, mode='crs812', bay=None, accessories=None, finish=None, pattern=None):
    """bayを渡すと上部専用段、accessoriesを渡すと中段の機器棚を持つ案を作る。省略時は中央の暫定配置。"""
    p = parameters or FixedRackParameters()
    scene = fixed_layout(mode, p, bay, accessories, finish)
    supports, support_metadata = integrated_supports(scene, p)
    bay_parts = []
    if bay is not None:
        from switch_bay_geometry import switch_bay_parts
        bay_parts, bay_metadata = switch_bay_parts(scene, p, bay)
        support_metadata = merge_bay(support_metadata, bay_metadata)
    if accessories is not None:
        from accessory_geometry import accessory_parts
        accessory_items, accessory_metadata = accessory_parts(scene, p, accessories, pattern)
        bay_parts = bay_parts + accessory_items
        support_metadata = merge_bay(support_metadata, accessory_metadata, 'accessories')
    if finish is not None:
        from finish_geometry import finish_parts
        finish_items, finish_metadata = finish_parts(scene, p, finish, pattern)
        bay_parts = bay_parts + finish_items
        support_metadata = merge_bay(support_metadata, finish_metadata, 'finish')
    case_model = load_case_model()
    face = controller_front_face(p, case_model)
    if abs(face['metadata']['face_front_y_mm'] - p.front_face_y) > 1e-6:
        raise ValueError('共通前面の基準と既存の制御器蓋が一致しません。寸法定義を更新してください。')
    parts = (side_tiles(p, False, support_metadata, bay, accessories, pattern)
             + side_tiles(p, True, support_metadata, bay, accessories, pattern))
    parts.extend(supports)
    parts.extend(bay_parts)
    for b in scene['cross_beams']:
        parts.extend(beam_segments(b, p))
    for b in scene['trays'] + scene['power_trays']:
        parts.append({'name': b['name'], 'label': b['label'], 'shape': ring_tray(b), 'role': b['kind']})
    for node in scene['nodes']:
        parts.append({'name': node['name'] + '_carrier', 'label': '共通前面にそろえた保護格子一体のファン保持部',
                      'shape': fan_carrier(node, p, pattern), 'role': 'carrier'})
    for right in (False, True):
        parts.append({'name': 'power_carrier_' + ('right' if right else 'left'),
                      'label': '外へ取り出す電源用ファン保持板・留め具は未設計',
                      'shape': power_carrier(p, right, pattern), 'role': 'power_carrier'})
    parts.extend(control_panel_halves(scene, p, face))
    parts.extend(face['parts'])
    parts.extend(ceiling_tiles(scene))
    cases = case_references(scene, p, case_model)
    parts.extend(i for i in cases if i['role'] == 'controller_dock')
    refs = [i for i in cases if i['role'] == 'case_reference'] + face['references']
    for b in scene['equipment']:
        if b['kind'] == 'controller':
            continue
        s = box(b['origin'], b['size'])
        if b['kind'] == 'fan':
            axis = [1, 0, 0] if b['axis'] == 'x' else [0, 1, 0]
            center = [b['origin'][i] + b['size'][i] / 2 for i in range(3)]
            w = 0 if b['axis'] == 'x' else 1
            center[w] = b['origin'][w] - 1
            s = s.cut(cylinder(center, b['size_mm'] / 2 - 6, b['size'][w] + 2, axis))
        refs.append({'name': b['name'], 'label': b['label'], 'shape': s, 'role': b['kind']})
    return {'parameters': p, 'scene': scene, 'parts': parts, 'references': refs,
            'supports': support_metadata, 'controller_face': face, 'switch_bay': bay,
            'accessories': accessories, 'finish': finish, 'pattern': pattern}


def create(parameters=None, mode='crs812', bay=None, accessories=None, finish=None, pattern=None):
    model = shapes(parameters, mode, bay, accessories, finish, pattern)
    doc = App.newDocument('FixedFourNodeRack')
    doc.Label = ('上部専用段を持つ4台ラック・形状候補' if bay is not None
                 else '固定段・独立電源区画の4台ラック・形状候補')
    for item in model['parts'] + model['references']:
        obj = doc.addObject('Part::Feature', item['name'])
        obj.Label = item['label']
        obj.Shape = item['shape']
        obj.ViewObject.ShapeColor = ROLE_COLORS.get(item['role'], (.22, .26, .29))
        obj.addProperty('App::PropertyString', 'DesignStatus')
        obj.DesignStatus = '形状候補。実測と全体の組立・固定機構の確認前。造形用へ出力しない。'
    doc.recompute()
    return doc, model
