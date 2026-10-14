"""上下のSparkの間の機器棚と、ファンの間を閉じる前面板。

棚は上面板と下向きのリブで作り、左右の側枠の水平な受けへ差し込む。前面板は
ファン保持部と同じ前面に置き、下端の受け板を棚へねじで留める。中央の板は
Comet Proの画面の窓を持ち、外すと機器を前へ引き出せる。形状候補で造形用ではない。
"""
import FreeCAD as App
import Part

from integrated_rack_supports import _box, _fuse, _socket, _tiles, _window


def _hole(x, y, z, length):
    return Part.makeCylinder(2.25, length, App.Vector(x, y, z))


def _front_window(x, y, z, width, depth, height, radius):
    """前後方向に抜く角丸の窓。前後方向の辺を丸める。"""
    shape = _box((x, y, z), (width, depth, height))
    edges = [e for e in shape.Edges if abs(e.BoundBox.YLength - depth) < 1e-7]
    return shape.makeFillet(min(radius, width / 2 - 1e-3, height / 2 - 1e-3), edges)


def _flange_holes(acc, p):
    q = acc['parameters']
    half = q['panel_center_half_width']
    inner = p.inner_width / 2
    y = acc['front_y'] + q['flange_overlap'] / 2
    comet_half = acc['equipment'][0]['size'][0] / 2
    center = (comet_half + half) / 2
    side = [-(half + inner) / 2 - 40, -(half + inner) / 2 + 40]
    return [(x, y) for x in side + [-center, center] + [-v for v in side]]


def _sled_holes(acc):
    sled = next(o for o in acc['objects'] if o['name'] == 'remote_kvm_sled')
    y = sled['origin'][1] + sled['size'][1] - 15
    return [(-30, y), (30, y)]


def _sled(acc):
    """Comet Proの載せ台。後ろ寄りを棚へねじで留め、前の部分は片持ちで前面板の後ろまで延ばす。"""
    sled = next(o for o in acc['objects'] if o['name'] == 'remote_kvm_sled')
    shape = _box(sled['origin'], sled['size'])
    for x, y in _sled_holes(acc):
        shape = shape.cut(_hole(x, y, sled['origin'][2] - 1, sled['size'][2] + 2))
    return shape.removeSplitter()


def _shelf(p, acc):
    q = acc['parameters']
    end = p.inner_width / 2 + 8
    z0, top = acc['shelf_z'], acc['support_z']
    front, rear = acc['front_y'], p.rear_y
    run = rear - front
    joint_y = (front + rear) / 2
    rib_z, rib_h = z0, q['shelf_rib']
    plate = _box((-end, front, top - q['shelf_plate']), (2 * end, run, q['shelf_plate']))
    # 機器の外側に窓を開け、材料と上下の空気の遮りを減らす。
    for sign in (-1, 1):
        for ylo, yhi in ((front + 16, joint_y - 12), (joint_y + 12, rear - 16)):
            x0 = 140 if sign > 0 else -236
            plate = plate.cut(_window(x0, ylo, top - q['shelf_plate'] - 1, 96, yhi - ylo, q['shelf_plate'] + 2))
    shapes = [plate]
    for x, width in ((-end, 16), (end - 16, 16), (-4, 8)):
        shapes.append(_box((x, front, rib_z), (width, run, rib_h)))
    for joint in (-end / 3, end / 3):
        shapes.append(_box((joint - 4, front, rib_z), (8, run, rib_h)))
    for y, width in ((front, q['flange_overlap']), (joint_y - 4, 8), (rear - 6, 6)):
        shapes.append(_box((-end, y, rib_z), (2 * end, width, rib_h)))
    laps = [(x, y) for x in (-end / 3, end / 3) for y in (front + 10, rear - 12)]
    laps += [(x, joint_y) for x in (-2 * end / 3, 0, 2 * end / 3)]
    flange = _flange_holes(acc, p)
    shapes += [Part.makeCylinder(7, rib_h, App.Vector(x, y, rib_z)) for x, y in laps]
    shelf = _fuse(shapes)
    for x, y in laps + flange + _sled_holes(acc):
        shelf = shelf.cut(_hole(x, y, z0 - 1, top - z0 + 2))
    return shelf.removeSplitter(), [-end, front, z0], [2 * end, run, top - z0], laps, flange


def _panels(p, acc, pattern=None):
    q = acc['parameters']
    inner = p.inner_width / 2
    half = q['panel_center_half_width']
    y, (z0, z1) = acc['panel_y'], acc['panel_z']
    t = q['panel_thickness']
    top = acc['support_z']
    comet = acc['equipment'][0]
    comet_half = comet['size'][0] / 2
    flange_y1 = acc['front_y'] + q['flange_overlap']
    holes = _flange_holes(acc, p)
    parts = []
    for name, x0, x1 in (('mid_panel_left', -inner, -half), ('mid_panel_center', -half, half),
                         ('mid_panel_right', half, inner)):
        shape = _box((x0, y, z0), (x1 - x0, t, z1 - z0))
        flange = _box((x0, y + t, top), (x1 - x0, flange_y1 - (y + t), q['flange_thickness']))
        if name == 'mid_panel_center':
            # Comet Proの通り道を受け板から抜き、画面の前に窓を開ける。
            flange = flange.cut(_box((-comet_half - 1.5, y, top - 1), (2 * comet_half + 3, 200, q['flange_thickness'] + 2)))
            w, h = acc['window']['size']
            cz = acc['window']['center'][1]
            shape = shape.cut(_front_window(-w / 2, y - 1, cz - h / 2, w, t + 2, h, 6))
        elif pattern is not None and pattern.style == 'honeycomb':
            from grille_patterns import cut_all, honeycomb_in_rect
            shape = cut_all(shape, honeycomb_in_rect(x0 + 12, x1 - 12, z0 + 8, z1 - 8, y - 1, t + 2, 'xz',
                                                     pattern.hex_across_flats, pattern.hex_wall))
        else:
            # ファンの格子と同じ10mm間隔の縦溝で、前面の言葉をそろえる。
            pitch = q['slot_pitch']
            x = x0 + 12
            slots = []
            while x + p.vent_slot_width <= x1 - 12 + 1e-9:
                slots.append(_front_window(x, y - 1, z0 + 8, p.vent_slot_width, t + 2, z1 - z0 - 16, p.vent_slot_width / 2))
                x += pitch
            shape = shape.cut(Part.makeCompound(slots))
        shape = shape.fuse(flange)
        for hx, hy in holes:
            if x0 < hx < x1:
                shape = shape.cut(_hole(hx, hy, top - 1, q['flange_thickness'] + 2))
        label = {'mid_panel_left': '上下のファンの間を閉じる前面板・左',
                 'mid_panel_center': 'Comet Proの画面の窓を持つ前面板・外して機器を前へ出す',
                 'mid_panel_right': '上下のファンの間を閉じる前面板・右'}[name]
        parts.append({'name': name, 'label': label, 'shape': shape.removeSplitter(), 'role': 'mid_panel'})
    return parts


def accessory_parts(scene, p, acc, pattern=None):
    """部品一覧と、側枠の受け・支持面・ねじ候補を integrated_supports と同じ形式で返す。"""
    shelf, origin, size, laps, flange = _shelf(p, acc)
    parts = []
    tiles = []
    for col, row, shape in _tiles(shelf, origin, size, 3, 2, p.lap_length):
        name = f'accessory_shelf_{row}_{col}'
        tiles.append(name)
        parts.append({'name': name, 'label': f'遠隔操作機器の棚・{row + 1}列目・{col + 1}分割目',
                      'shape': shape, 'role': 'accessory_shelf'})
    panels = _panels(p, acc, pattern)
    parts += panels
    parts.append({'name': 'remote_kvm_sled', 'label': 'Comet Proの載せ台・棚から前へ延びる',
                  'shape': _sled(acc), 'role': 'accessory_shelf'})
    sockets = [_socket('accessory_shelf_' + side, side, origin[1], size[1], origin[2], size[2], p)
               for side in ('left', 'right')]
    fasteners = [{'assembly': 'accessory_shelf', 'axis': [0, 0, 1], 'origin': [x, y, origin[2]],
                  'through_length_mm': size[2], 'hole_diameter_mm': 4.5, 'thread_nominal_diameter_mm': 4,
                  'head_and_nut_retention': '頭とナットの保持方法は未確定',
                  'status': '棚の重ね継ぎを締める直径4mmねじの通し穴'} for x, y in laps]
    # 前面板の受け板と棚の前の帯を合わせて貫く長さ。下端は棚の下面。
    fasteners += [{'assembly': 'mid_panel', 'axis': [0, 0, 1], 'origin': [x, y, origin[2]],
                   'through_length_mm': size[2] + acc['parameters']['flange_thickness'], 'hole_diameter_mm': 4.5,
                   'thread_nominal_diameter_mm': 4, 'removable': True,
                   'head_and_nut_retention': '棚側は熱圧入ナットかナット保持の候補で未確定',
                   'status': '前面板の受け板を棚へ留める。中央の板はComet Proの交換時に外す。'} for x, y in flange]
    fasteners += [{'assembly': 'remote_kvm_sled', 'axis': [0, 0, 1], 'origin': [x, y, origin[2]],
                   'through_length_mm': size[2] + acc['parameters']['sled_thickness'], 'hole_diameter_mm': 4.5,
                   'thread_nominal_diameter_mm': 4, 'head_and_nut_retention': '頭とナットの保持方法は未確定',
                   'status': '載せ台を棚へ留める。前の部分は片持ち。'} for x, y in _sled_holes(acc)]
    carried = [{'target': 'remote_kvm', 'supports': ['remote_kvm_sled'], 'z': acc['comet_z'], 'each': False,
                'minimum_area_mm2': 500},
               {'target': 'remote_kvm_sled', 'supports': tiles, 'z': acc['support_z'], 'each': False,
                'minimum_area_mm2': 500},
               {'target': 'kvm_switch', 'supports': tiles, 'z': acc['support_z'], 'each': False,
                'minimum_area_mm2': 500}]
    carried += [{'target': panel['name'], 'supports': tiles, 'z': acc['support_z'], 'each': False,
                 'minimum_area_mm2': 200} for panel in panels]
    assembly = {'name': 'accessory_shelf', 'kind': 'accessory_shelf', 'origin': origin, 'size': size,
                'part_count': len(tiles), 'support_z': acc['support_z'], 'carried': carried,
                'open_under_equipment': False,
                'print_candidate': '上面板を造形台へ向け、リブを上へ立ち上げる',
                'lap_print_validation': '重ね継ぎの段差に必要な支持材と接合強度は未検証'}
    assembly['cad_solid_volume_mm3'] = sum(i['shape'].Volume for i in parts if i['name'] in tiles)
    metadata = {'socket_envelopes': sockets, 'support_surfaces': [], 'fastener_candidates': fasteners,
                'bearing_surfaces': [{'name': s['name'], 'side': s['side'], 'origin': s['bearing_origin'],
                                      'size': s['bearing_size'], 'normal': [0, 0, 1], 'kind': 'frame_bearing'}
                                     for s in sockets],
                'assemblies': [assembly], 'part_count': len(parts),
                'status': '形状候補。切替器の実寸、電源、配線の確認前。造形用へ出力しない。'}
    return parts, metadata
