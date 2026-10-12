"""上部専用段の固定床と、スイッチを載せて背面へ引き出すトレー。

床は本体区画との仕切りを兼ね、左右の側枠の水平な受けへ差し込む。トレーは左右2枚で、
スイッチ底面を受けて床の支持帯の上を滑る。形状候補であり、材料・締結・耐荷重は
実物で検証するまで確定しない。
"""
import FreeCAD as App
import Part

from integrated_rack_supports import _box, _fuse, _socket, _tiles, _window


def _hole(x, y, z, length):
    return Part.makeCylinder(2.25, length, App.Vector(x, y, z))


def _floor(p, bay):
    q = bay['parameters']
    end = p.inner_width / 2 + 8
    z0, zs, sw = bay['floor_z'], bay['support_z'], bay['switch_z']
    front, rear = bay['floor_front_y'], p.rear_y
    run = rear - front
    half, guide = bay['tray_half_width'], bay['guide_inner_x']
    tray_front, tray_rear = bay['switch_back_y'], bay['tray_rear_y']
    joint_y = (front + rear) / 2
    shapes = [_box((-end, front, z0), (2 * end, run, q['floor_plate']))]
    rib_z, rib_h = z0 + q['floor_plate'], q['support_band']
    # トレーの縁と中央の継ぎ目の直下に、背面の端まで続く支持帯を置く。
    # 外側の帯はガイドまで埋め、ガイドとの間に細い溝を残さない。
    edge = 8 + guide - half
    for x, width in ((-guide, edge), (half - 8, edge), (-4, 8)):
        shapes.append(_box((x, tray_front, rib_z), (width, rear - tray_front, rib_h)))
    for y in (tray_front, tray_rear - q['band_width']):
        shapes.append(_box((-guide, y, rib_z), (2 * guide, q['band_width'], rib_h)))
    # 重ね継ぎの帯と前後の縁。重ね部分の各層に材料を残す。
    for joint in (-end / 3, end / 3):
        shapes.append(_box((joint - 4, front, rib_z), (8, run, rib_h)))
    for y, width in ((front, 6), (joint_y - 4, 8), (rear - 6, 6)):
        shapes.append(_box((-end, y, rib_z), (2 * end, width, rib_h)))
    # 側面ガイドは側枠の受けへ入る舌と一体にし、トレー上面の高さまで立ち上げる。
    for x in (-end, guide):
        shapes.append(_box((x, front, rib_z), (end - guide, run, sw - rib_z)))
    stop_y = tray_front - p.fit_clearance - q['front_stop_depth']
    shapes.append(_box((-guide, stop_y, rib_z), (2 * guide, q['front_stop_depth'], sw - rib_z)))
    laps = [(x, y) for x in (-end / 3, end / 3) for y in (front + 12, rear - 12)]
    laps += [(x, joint_y) for x in (-2 * end / 3, 0, 2 * end / 3)]
    retention = [(x, tray_rear - q['band_width'] / 2) for x in (-half + 3.75, half - 3.75)]
    shapes += [Part.makeCylinder(7, rib_h, App.Vector(x, y, rib_z)) for x, y in laps]
    shapes += [Part.makeCylinder(6, rib_h, App.Vector(x, y, rib_z)) for x, y in retention]
    floor = _fuse(shapes)
    for x, y in laps + retention:
        floor = floor.cut(_hole(x, y, z0 - 1, zs - z0 + 2))
    return floor.removeSplitter(), [-end, front, z0], [2 * end, run, sw - z0], laps, retention


def _tray(p, bay, right):
    q = bay['parameters']
    zs, sw = bay['support_z'], bay['switch_z']
    y0, y1 = bay['switch_back_y'], bay['tray_rear_y']
    gap, rim = q['tray_split_gap'], q['tray_rim']
    x0 = gap / 2 if right else -bay['tray_half_width']
    x1 = bay['tray_half_width'] if right else -gap / 2
    tray = _box((x0, y0, zs), (x1 - x0, y1 - y0, q['tray_thickness']))
    middle = (y0 + y1) / 2
    for ylo, yhi in ((y0 + rim, middle - 8), (middle + 8, y1 - rim)):
        tray = tray.cut(_window(x0 + rim, ylo, zs - 1, x1 - x0 - 2 * rim, yhi - ylo, q['tray_thickness'] + 2))
    fence = bay['fence_inner_x'] if right else -bay['fence_inner_x'] - q['fence_thickness']
    tray = tray.fuse(_box((fence, y0, sw), (q['fence_thickness'], y1 - y0, q['fence_height'])))
    x = bay['tray_half_width'] - 3.75
    tray = tray.cut(_hole(x if right else -x, y1 - q['band_width'] / 2, zs - 1, q['tray_thickness'] + 2))
    return tray.removeSplitter()


def switch_bay_parts(scene, p, bay):
    """部品一覧と、側枠の受け・支持面・ねじ候補を integrated_supports と同じ形式で返す。"""
    q = bay['parameters']
    floor, origin, size, laps, retention = _floor(p, bay)
    parts = []
    for col, row, shape in _tiles(floor, origin, size, 3, 2, p.lap_length):
        parts.append({'name': f'switch_floor_{row}_{col}',
                      'label': f'上部専用段の固定床・{row + 1}列目・{col + 1}分割目',
                      'shape': shape, 'role': 'bay_floor'})
    trays = []
    for right in (False, True):
        name = 'switch_tray_' + ('right' if right else 'left')
        trays.append(name)
        parts.append({'name': name, 'label': f'スイッチの{"右" if right else "左"}側トレー・背面へ引き出す',
                      'shape': _tray(p, bay, right), 'role': 'switch_tray'})
    depth = size[1]
    sockets = [_socket('switch_floor_' + side, side, origin[1], depth, origin[2], size[2], p)
               for side in ('left', 'right')]
    fasteners = [{'assembly': 'switch_floor', 'axis': [0, 0, 1], 'origin': [x, y, origin[2]],
                  'through_length_mm': bay['support_z'] - origin[2], 'hole_diameter_mm': 4.5,
                  'thread_nominal_diameter_mm': 4, 'head_and_nut_retention': '頭とナットの保持方法は未確定',
                  'status': '床の重ね継ぎを締める直径4mmねじの通し穴'} for x, y in laps]
    fasteners += [{'assembly': 'switch_tray_retention', 'axis': [0, 0, 1], 'origin': [x, y, origin[2]],
                   'through_length_mm': bay['switch_z'] - origin[2], 'hole_diameter_mm': 4.5,
                   'thread_nominal_diameter_mm': 4, 'removable': True,
                   'head_and_nut_retention': '床側は熱圧入ナットかナット保持の候補で未確定',
                   'status': 'トレーを床の後側の帯へ留める抜け止め。交換時に外す。'} for x, y in retention]
    surfaces = [{'name': f'{name}_on_switch_floor', 'target': name, 'assembly': 'switch_floor',
                 'origin': [-bay['tray_half_width'], bay['switch_back_y'], bay['support_z']],
                 'size': [2 * bay['tray_half_width'], bay['tray_rear_y'] - bay['switch_back_y'], 0],
                 'normal': [0, 0, 1], 'kind': 'moving_tray_support',
                 'description': 'トレーの縁と継ぎ目側の縁を、背面の端まで続く床の支持帯で受ける'}
                for name in trays]
    surfaces.append({'name': 'switch_on_trays', 'target': 'switch', 'assembly': 'switch_tray',
                     'origin': bay['switch']['origin'], 'size': [bay['switch']['size'][0], bay['switch']['size'][1], 0],
                     'normal': [0, 0, 1], 'kind': 'equipment_support',
                     'description': 'スイッチ底面を左右のトレーで受ける。ゴム足の位置は未実測。'})
    assembly = {'name': 'switch_floor', 'kind': 'switch_floor', 'origin': origin, 'size': size,
                'part_count': 6, 'support_z': bay['support_z'], 'moving_parts': trays,
                'carried': {'target': 'switch', 'supports': trays, 'z': bay['switch_z']},
                'open_under_equipment': False,
                'separator': '床板4mmで本体区画と専用段の空気を分ける。床下は上段Sparkの交換空間の上。',
                'print_candidate': '床板を造形台へ向け、支持帯とガイドを上へ立ち上げる',
                'lap_print_validation': '重ね継ぎの段差に必要な支持材と接合強度は未検証'}
    assembly['cad_solid_volume_mm3'] = sum(i['shape'].Volume for i in parts if i['name'].startswith('switch_floor_'))
    metadata = {'socket_envelopes': sockets, 'support_surfaces': surfaces, 'fastener_candidates': fasteners,
                'bearing_surfaces': [{'name': s['name'], 'side': s['side'], 'origin': s['bearing_origin'],
                                      'size': s['bearing_size'], 'normal': [0, 0, 1], 'kind': 'frame_bearing'}
                                     for s in sockets],
                'assemblies': [assembly], 'part_count': len(parts),
                'removed_cross_beams': bay['replaced_cross_beams'],
                'status': '形状候補。スイッチ本体の固定、実物の材料・耐荷重・締結を検証するまで造形用へ出力しない。'}
    return parts, metadata
