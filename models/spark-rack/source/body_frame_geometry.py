"""本体連結案の参考形状。筐体に穴を開けず、各段の角を局所的につなぐ。"""
import runpy
import sys

import FreeCAD as App
import Part

from body_frame_layout import ROOT, layout, validate_layout
from spark_rack_parameters import BodyFrameParameters

sys.path.insert(0, str(ROOT / 'tools/cad'))
from controller_mount import RACK_U, STANDOFF, THICKNESS, screwless_cradle, place

COLORS = {
    'spark': (.66, .56, .37), 'body_connector': (.10, .30, .42),
    'accessory_support': (.20, .28, .34), 'network_support': (.20, .28, .34),
    'accessory_tray': (.26, .34, .40), 'power_tray': (.26, .34, .40),
    'fan_holder': (.13, .24, .30), 'controller_mount': (.16, .29, .36),
    'dock': (.20, .28, .34), 'fan': (.12, .13, .15),
    'controller': (.34, .38, .42), 'controller_lid': (.47, .50, .53),
    'knob': (.12, .14, .16), 'display': (.15, .38, .45),
    'switch': (.63, .66, .69), 'comet': (.18, .23, .28),
    'kvm': (.23, .25, .28), 'power': (.24, .27, .29),
    'cable_mount': (.15, .35, .43), 'cable_network': (.12, .55, .68),
    'cable_signal': (.48, .31, .72), 'cable_dc': (.90, .55, .12),
    'cable_ac': (.70, .25, .20), 'cable_control': (.25, .62, .37),
    'cable_storage': (.31, .68, .73), 'external_reservation': (.75, .75, .67),
    'switch_band': (.18, .40, .60), 'switch_buckle': (.35, .40, .45),
    'fan_pin': (.85, .48, .16), 'joint_key': (.85, .48, .16),
    'controller_band': (.18, .40, .60),
    'joint_detail_donor': (.18, .42, .56), 'joint_detail_receiver': (.43, .55, .62),
    'joint_detail_key': (.85, .48, .16),
}


def block(origin, size):
    return Part.makeBox(*size, App.Vector(*origin))


def fuse(shapes):
    result = shapes[0]
    for shape in shapes[1:]:
        result = result.fuse(shape)
    return result.removeSplitter()


def item(name, label, shape, kind, **extra):
    return dict(name=name, label=label, shape=shape, kind=kind, **extra)


def corner_shape(recipe, scene, p):
    shape = fuse([block(piece['origin'], piece['size']) for piece in recipe['pieces']])
    for spark in (e for e in scene['equipment'] if e['kind'] == 'spark'):
        x, y, z = spark['origin']
        dx, dy, dz = spark['size']
        c = p.fit_clearance
        shape = shape.cut(block((x - c, y - c, z), (dx + 2 * c, dy + 2 * c, dz)))
    return shape.removeSplitter()


def tray_shape(recipe, p):
    shape = block(recipe['origin'], recipe['size'])
    x, y, z = recipe['origin']
    dx, dy, dz = recipe['size']
    if recipe['kind'] == 'power_tray':
        walls = [block((x, y, z + dz), (4, dy, 8)),
                 block((x + dx - 4, y, z + dz), (4, dy, 8))]
    elif recipe['name'] == 'comet_tray':
        walls = [block((x, y, z + dz), (3.7, dy, 8)),
                 block((x + dx - 3.7, y, z + dz), (3.7, dy, 8))]
    else:
        wall_x = x if recipe['tray_side'] == 0 else x + dx - 4.7
        walls = [block((wall_x, y, z + dz), (4.7, dy, 8))]
        walls.append(block((x, y, z + dz), (dx, 3.7, 6)))
    return fuse([shape] + walls)


def fan_holder(fan, p):
    x, y, z = fan['origin']
    dx, dy, dz = fan['size']
    r = p.fan_rim
    if fan['axis'][1]:
        plane = y + dy if fan['axis'][1] < 0 else y - p.fan_plate
        shape = block((x - r, plane, z - r), (dx + 2 * r, p.fan_plate, dz + 2 * r))
        center = (x + dx / 2, plane - 1, z + dz / 2)
        shape = shape.cut(Part.makeCylinder(fan['opening'] / 2, p.fan_plate + 2,
                                           App.Vector(*center), App.Vector(0, 1, 0)))
        for hx in (-fan['pitch'] / 2, fan['pitch'] / 2):
            for hz in (-fan['pitch'] / 2, fan['pitch'] / 2):
                shape = shape.cut(Part.makeCylinder(2.25, p.fan_plate + 2,
                    App.Vector(center[0] + hx, plane - 1, center[2] + hz), App.Vector(0, 1, 0)))
        # ファン保持部は中間の接続部だけへ付ける。脚と上部を支える独立フレームにはしない。
        a = p.fan_arm_size
        back = -p.corner_outside if fan['axis'][1] < 0 else p.spark_depth
        start, end = (plane + p.fan_plate, back) if fan['axis'][1] < 0 else (back, plane)
        arms = [block((center[0] + offset - a / 2, start, center[2] - a / 2),
                      (a, end - start, a)) for offset in (-fan['fan_size'] / 2, fan['fan_size'] / 2)]
        shape = fuse([shape] + arms)
    else:
        plane = x - p.fan_plate if fan['axis'][0] > 0 else x + dx
        shape = block((plane, y - r, z - r), (p.fan_plate, dy + 2 * r, dz + 2 * r))
        center = (plane - 1, y + dy / 2, z + dz / 2)
        shape = shape.cut(Part.makeCylinder(fan['opening'] / 2, p.fan_plate + 2,
                                           App.Vector(*center), App.Vector(1, 0, 0)))
        for hy in (-fan['pitch'] / 2, fan['pitch'] / 2):
            for hz in (-fan['pitch'] / 2, fan['pitch'] / 2):
                shape = shape.cut(Part.makeCylinder(2.25, p.fan_plate + 2,
                    App.Vector(plane - 1, center[1] + hy, center[2] + hz), App.Vector(1, 0, 0)))
    return shape.removeSplitter()


def power_fan_arms(p):
    half = p.core_width / 2
    plane = half + p.corner_outside + p.power_fan_gap
    result = []
    rear = p.spark_depth
    fan_edge = p.power_fan_center_y - p.power_fan_size / 2 - p.fan_rim
    for side in (-1, 1):
        for row, z in enumerate((8, p.lower_base - 4)):
            def mirror(x, width):
                return x if side > 0 else -x - width
            outer = p.corner_outside - p.fit_clearance
            a = block((mirror(half + p.fit_clearance, outer), rear, z),
                      (outer, fan_edge + p.power_fan_arm_overlap - rear, 8))
            b = block((mirror(half + 8, p.power_fan_gap), fan_edge - 4, z),
                      (p.power_fan_gap, 4+p.power_fan_arm_overlap, 8))
            result.append(item(f'power_fan_arm_{side}_{row}', '電源ファンを脚の接続部へ留める短い腕',
                               fuse([a, b]), 'fan_holder'))
    return result


def fan_shape(fan):
    """外枠・ハブ・支持桟による参考形状。取付軸は常に座標軸と一致する。"""
    origin, size, axis = fan['origin'], fan['size'], fan['axis']
    a = next(i for i, v in enumerate(axis) if v)
    uv = [i for i in range(3) if i != a]
    center = [origin[i] + size[i] / 2 for i in range(3)]
    cut_base = list(center)
    cut_base[a] = origin[a] - 1
    positive_axis = [int(i == a) for i in range(3)]
    radius = fan['opening'] / 2
    shape = block(origin, size).cut(Part.makeCylinder(radius, size[a] + 2,
                                   App.Vector(*cut_base), App.Vector(*positive_axis)))
    cut_base[a] = origin[a]
    hub = Part.makeCylinder(18, size[a], App.Vector(*cut_base), App.Vector(*positive_axis))
    bars = []
    for direction in uv:
        o, d = list(center), list(size)
        for i in range(3):
            if i == a:
                o[i], d[i] = origin[i], size[i]
            elif i == direction:
                o[i], d[i] = origin[i], size[i]
            else:
                o[i], d[i] = center[i] - 3, 6
        bars.append(block(o, d))
    return fuse([shape, hub] + bars)


def controller_shapes(scene):
    """ケースと共通ドックは現在の正本を使い、左右の面へ正立配置する。"""
    source = runpy.run_path(str(ROOT / 'models/fan-controller/source/freecad_fan_controller.py'))
    App.closeDocument(source['doc'].Name)
    cx = (source['envelope_x'] + source['outer_right']) / 2
    cy = (source['envelope_y'] + source['envelope_back']) / 2
    shift = App.Vector(-cx, -cy, THICKNESS - source['bottom_z'])
    screwless = source['screwless_case_parts']()
    scene['controller_case_assembly'] = {key:value for key,value in screwless.items() if key not in ('body', 'lid')}
    scene['controller_case_assembly']['reference_shift'] = list(shift)
    body, lid = screwless['body'].copy(), screwless['lid'].copy()
    body.translate(shift)
    lid.translate(shift)
    knob = Part.makeCylinder(source['KNOB_PASS_DIAMETER'] / 2,
                            source['KNOB_TOP_Z'] - source['lid_top_z'],
                            App.Vector(source['ENCODER_X'], source['ENCODER_Y'], source['lid_top_z']))
    knob.translate(shift)
    display = block((source['DISPLAY_X'], source['DISPLAY_Y'], source['DISPLAY_TOP_Z']),
                    (source['DISPLAY_LENGTH'], source['DISPLAY_WIDTH'], .4))
    display.translate(shift)
    parts, references = [], []
    dock_shape = screwless_cradle(source['envelope_length'], source['envelope_width'])
    for controller in (e for e in scene['equipment'] if e['kind'] == 'controller'):
        args = (controller['dock_origin'], controller['u'], controller['v'], controller['w'])
        name = controller['name']
        parts.append(item(name + '_dock', controller['label'] + '・共通ドック', place(dock_shape, *args), 'dock'))
        for suffix, shape, kind in (('body', body, 'controller'), ('lid', lid, 'controller_lid'),
                                     ('knob', knob, 'knob'), ('display', display, 'display')):
            suffix_label = {'body': 'ケース本体', 'lid': '蓋', 'knob': 'つまみ', 'display': '表示器'}[suffix]
            references.append(item(name + '_' + suffix, controller['label'] + '・' + suffix_label,
                                   place(shape, *args), kind, group=name))
        from body_frame_screwless import controller_bands
        references += controller_bands(controller, source)
    return parts, references


def create(parameters=None):
    p = parameters or BodyFrameParameters()
    scene = layout(p)
    scene['layout_validation'] = validate_layout(scene)
    parts = [item(r['name'], r['label'], corner_shape(r, scene, p), r['kind'])
             for r in scene['corners']]
    for recipe in scene['boxes']:
        if recipe['kind'] == 'controller_mount':
            controller = next(e for e in scene['equipment'] if e['name'] == recipe['controller'])
            side = controller['w'][0]
            center = [controller['dock_origin'][i] + controller['u'][i] * RACK_U
                      for i in range(3)]
            dock_back = controller['dock_origin'][0] - side * STANDOFF
            core_edge = side * (p.core_width / 2 + p.corner_outside)
            recipe.update(origin=[min(dock_back, core_edge), center[1] - 9, center[2] - 21],
                          size=[abs(dock_back - core_edge), 18, 42])
        if recipe.get('switch_keeper'):
            from body_frame_switch_retention import rail_shape
            shape = rail_shape(recipe, scene, p)
        else:
            shape = tray_shape(recipe, p) if recipe['kind'] in ('accessory_tray', 'power_tray') else block(recipe['origin'], recipe['size'])
        parts.append(item(recipe['name'], recipe['label'], shape, recipe['kind']))
    fans = [e for e in scene['equipment'] if e['kind'] == 'fan']
    parts += [item(f['name'] + '_holder', '正立固定するファン保持部', fan_holder(f, p), 'fan_holder')
              for f in fans]
    parts += power_fan_arms(p)
    docks, references = controller_shapes(scene)
    parts += docks
    for equipment in scene['equipment']:
        if equipment['kind'] == 'controller':
            continue
        shape = fan_shape(equipment) if equipment['kind'] == 'fan' else block(equipment['origin'], equipment['size'])
        if equipment['kind'] == 'fan':
            from body_frame_screwless import fan_holes, fan_pin
            shape, centers = fan_holes(shape, equipment)
            parts += [item(equipment['name']+f'_pin_{n}', 'ファン固定用のねじ山のない樹脂割りピン',
                           fan_pin(equipment, center, p), 'fan_pin', moves_with=equipment['name'])
                      for n, center in enumerate(centers)]
        references.append(item(equipment['name'], equipment['label'], shape, equipment['kind']))
    from body_frame_cable_geometry import create_cable_geometry
    mounts, cables, storage = create_cable_geometry(scene)
    parts += mounts
    from body_frame_switch_retention import band_shapes
    references += band_shapes(scene)
    from body_frame_screwless import integrate_small_parts, lap_storage_floors
    lap_storage_floors(parts)
    protected = {f['name']+'_holder' for f in fans} | {e['name'] for e in parts if e['kind'] == 'fan_pin'}
    parts = integrate_small_parts(parts, p, protected)
    from body_frame_joinery import connect_parts
    parts, scene['screwless_assembly'] = connect_parts(parts, references, p)
    from body_frame_joinery import joint_detail
    details = joint_detail(parts, scene)
    external = [item(r['name'], r['label'], block(r['origin'], r['size']), r['kind'])
                for r in scene['cable_management']['external_regions']]
    doc = App.newDocument('SparkBodyFrameCandidate')
    for group, items in (('Candidate', parts), ('Reference', references), ('Cable', cables),
                         ('Storage', storage), ('Reservation', external)):
        for entry in items:
            obj = doc.addObject('Part::Feature', group + '_' + entry['name'].replace('-', 'N'))
            obj.Label = entry['label']
            obj.Shape = entry['shape']
            if App.GuiUp:
                obj.ViewObject.ShapeColor = entry.get('color', COLORS.get(entry['kind'], (.4, .4, .4)))
    doc.recompute()
    return doc, dict(parameters=p, scene=scene, parts=parts, references=references,
                     cables=cables, cable_storage=storage, external_reservations=external,
                     assembly_details=details)
