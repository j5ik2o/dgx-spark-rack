"""上部専用段の案の前面と天面を閉じる板の配置。形状候補で製造用ではない。

最上段の前面は、スイッチ前側の部品を交換するために外せる板で閉じる。天面は枠の上へ
溝付きの天板を載せる。最下段の左右は、左端を軸に開く制御器扉の範囲を避けて扉の後ろへ置く。
"""
from dataclasses import asdict

from four_node_layout import box, overlaps
from spark_rack_parameters import FrontFinishParameters


def finish_layout(p, scene, accessories, q=None):
    """sceneは上部専用段と機器棚を含むfixed_layoutの結果。前面の板の割り付けは中段の板にそろえる。"""
    q = q or FrontFinishParameters()
    q.validate()
    if not scene.get('switch_bay'):
        raise ValueError('前面と天面の板は上部専用段の案でだけ使えます')
    inner = p.inner_width / 2
    half = accessories['parameters']['panel_center_half_width']
    beams = {b['name']: b for b in scene['cross_beams']}
    top_front = beams['frame_top_front']
    upper_top = max(c['origin'][2] + c['size'][2] for c in scene['carriers'] if c['name'].startswith('upper_'))
    z0, z1 = upper_top + p.fit_clearance, top_front['origin'][2]
    panel_y = p.front_face_y
    objects, covers = [], []
    for name, label, x0, x1 in (('bay_cover_left', '最上段の前面を閉じる板・左', -inner, -half),
                                ('bay_cover_center', '最上段の前面を閉じる板・中央', -half, half),
                                ('bay_cover_right', '最上段の前面を閉じる板・右', half, inner)):
        objects.append(box(name, label + '・外してスイッチ前側を交換', [x0, panel_y, z0],
                           [x1 - x0, q.panel_thickness, z1 - z0], 'removable_cover'))
        covers.append(name)
    # 天板の裏の縁は枠の内側へ入れて位置を決める。上枠と側枠の上面には板だけが載る。
    rear_top = beams['frame_top_rear']
    lid_inner_y = (top_front['origin'][1] + top_front['size'][1] + p.fit_clearance,
                   rear_top['origin'][1] - p.fit_clearance)
    objects.append(box('top_lid', '溝付きの天板・枠の上に載せる', [-p.width / 2, p.front_y, p.height],
                       [p.width, p.depth, q.lid_plate], 'top_lid'))
    objects.append(box('top_lid_ribs', '天板の裏の縁と継ぎ目のリブ・枠の内側へ入る',
                       [-inner + p.fit_clearance, lid_inner_y[0], p.height - q.lid_rib],
                       [p.inner_width - 2 * p.fit_clearance, lid_inner_y[1] - lid_inner_y[0], q.lid_rib], 'top_lid'))
    door = scene['control_panel']
    door_x0, door_x1 = door['origin'][0], door['origin'][0] + door['size'][0]
    filler_y = door['origin'][1] + door['size'][1] + p.fit_clearance
    filler_z0, filler_z1 = door['origin'][2], scene['separator']['origin'][2]
    for name, label, x0, x1 in (('lower_filler_left', '最下段の左の開口を閉じる板・扉の後ろ', -inner, door_x0 - p.fit_clearance),
                                ('lower_filler_right', '最下段の右の開口を閉じる板・扉の後ろ', door_x1 + p.fit_clearance, inner)):
        objects.append(box(name, label, [x0, filler_y, filler_z0], [x1 - x0, q.panel_thickness, filler_z1 - filler_z0],
                           'lower_filler'))
    services = [dict(box(name + '_removal', '板を前へ外す', o['origin'][:1] + [p.front_y - 110] + o['origin'][2:],
                         [o['size'][0], o['origin'][1] + o['size'][1] - (p.front_y - 110), o['size'][2]], 'service'),
                     moving=[name]) for name, o in ((n, next(b for b in objects if b['name'] == n)) for n in covers)]
    return {'parameters': asdict(q), 'objects': objects, 'removable_covers': covers, 'service_spaces': services,
            'cover_z': [z0, z1], 'panel_y': panel_y, 'filler_y': filler_y, 'filler_z': [filler_z0, filler_z1],
            'lid_z': [p.height, p.height + q.lid_plate], 'overall_height_mm': p.height + q.lid_plate,
            'lid_inner_y': list(lid_inner_y),
            'filler_recess_mm': filler_y - panel_y,
            'notes': {'bay_cover': 'スイッチの電源とファンがどの面にあるか未確認のため、最上段の前面の板は外せる形にした。',
                      'lid': '最大134Wのスイッチの上で自然に上がる空気を逃がすため、天板に溝を開けた。',
                      'filler': '制御器扉は左端を軸に前へ開くため、左右の板を扉の後ろへ下げて開く範囲を避けた。',
                      'declined': ['制御器扉を下端の軸で前へ倒す形にして左右の板を前面へそろえる案',
                                   '上段ファンの横梁を動かす案', '上枠の断面を薄くして天板を枠の上面へ埋める案']},
            'manufacturing_geometry': False, 'physical_validation': False}


def check_finish(scene):
    """前面の板を外す経路を確かめる。スイッチ前側の作業空間は、外せる板を除いて検査済み。"""
    finish = scene['finish']
    solids = scene['equipment'] + scene['carriers'] + scene['trays'] + scene['power_trays']
    solids += [scene['separator'], scene['control_panel']] + scene['cross_beams'] + finish['objects']
    for key in ('switch_bay', 'accessories'):
        if scene.get(key):
            solids += scene[key]['objects']
    blocked = [[s['name'], b['name']] for s in finish['service_spaces'] for b in solids
               if b['name'] not in s['moving'] and overlaps(s, b)]
    door = [b['name'] for b in finish['objects'] if overlaps(scene['control_door_sweep'], b)]
    return {'finish_service_obstructions': blocked, 'control_door_sweep_obstructions': door}
