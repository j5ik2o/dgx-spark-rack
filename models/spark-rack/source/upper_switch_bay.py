"""上枠を共有する上部専用段の高さ・予約・比較。形状候補で製造用ではない。

本体の段位置208／428mmと電源区画は動かさない。床の高さは、上段Sparkを背面へ
引き出す空間と、上段ファン保持部の上を通るスイッチ前側の作業空間で決める。
"""
from dataclasses import asdict, replace
import math

from fixed_rack_layout import check_fixed_layout, fixed_layout
from four_node_layout import box, overlaps
from network_configuration import selected_network
from spark_rack_parameters import FixedRackParameters, SwitchPlacementComparisonParameters, UpperSwitchBayParameters
from switch_placement_comparison import comparison


def switch_size():
    return list(selected_network()['final_phase']['switch']['body_envelope_mm'])


def levels(p, q, size):
    """床の下端とスイッチ底面を、下の機器の予約から求める。"""
    q.validate()
    under = q.under_switch
    upper_exchange_top = p.upper_base + p.spark_height + p.hand_margin
    carrier_top = max(c['origin'][2] + c['size'][2] for c in fixed_layout('ring', p)['carriers'])
    floors = {'upper_spark_rear_exchange': upper_exchange_top + p.fit_clearance}
    if q.preserve_front_service:
        floors['switch_front_service_over_fan_carriers'] = carrier_top + q.front_service_clearance - under
    binding = max(floors, key=floors.get)
    floor_z = math.ceil(floors[binding] - 1e-9)
    switch_z = floor_z + under
    return {'floor_z': floor_z, 'support_z': floor_z + q.floor_plate + q.support_band,
            'switch_z': switch_z, 'required_height': switch_z + size[2] + q.upper_hand_margin + p.section,
            'binding_constraint': binding, 'floor_candidates_mm': floors,
            'upper_spark_exchange_top_mm': upper_exchange_top, 'fan_carrier_top_mm': carrier_top}


def rack_parameters(q=None, base=None):
    """段位置を保ったまま、上部専用段に必要な全高だけを変えた寸法を返す。"""
    base, q = base or FixedRackParameters(), q or UpperSwitchBayParameters()
    base.validate()
    p = replace(base, height=levels(base, q, switch_size())['required_height'])
    p.validate()
    return p


def bay_layout(p, q=None):
    """fixed_layoutへ渡す専用段の予約。床・ガイド・止めは固定、トレー2枚は可動。"""
    q = q or UpperSwitchBayParameters()
    size = switch_size()
    width, depth, height = size
    level = levels(p, q, size)
    if p.height + 1e-9 < level['required_height']:
        raise ValueError('上部専用段に必要な全高が不足しています')
    inner = p.inner_width / 2
    z0, zs, sw = level['floor_z'], level['support_z'], level['switch_z']
    # 床が上段ファンと同じ高さに入るため、ファン後端より後ろから始める。
    front = p.fan_front_y + p.fan_depth + q.floor_front_gap
    half = width / 2 + q.side_hand_margin
    guide_x = half + p.fit_clearance
    y0 = q.switch_face_y - depth
    run = p.rear_y - front
    fence_x = width / 2 + q.switch_side_clearance
    tray_width = half - q.tray_split_gap / 2
    objects = [
        box('switch_floor', '上部専用段の固定床・本体区画との仕切りを兼ねる',
            [-inner, front, z0], [p.inner_width, run, q.floor_plate + q.support_band], 'bay_floor'),
        box('switch_front_stop', 'トレーの前側の止め',
            [-guide_x, y0 - p.fit_clearance - q.front_stop_depth, zs],
            [2 * guide_x, q.front_stop_depth, q.tray_thickness], 'bay_floor')]
    for right in (False, True):
        side = 'right' if right else 'left'
        objects.append(box('switch_guide_' + side, 'トレーの側面ガイド',
                           [guide_x if right else -inner, front, zs],
                           [inner - guide_x, run, q.tray_thickness], 'bay_floor'))
        objects.append(box('switch_tray_' + side, 'スイッチを載せて背面へ引き出すトレー',
                           [q.tray_split_gap / 2 if right else -half, y0, zs],
                           [tray_width, q.tray_depth, q.tray_thickness], 'switch_tray'))
        objects.append(box('switch_tray_' + side + '_fence', 'トレーの側面の止め',
                           [fence_x if right else -fence_x - q.fence_thickness, y0, sw],
                           [q.fence_thickness, q.tray_depth, q.fence_height], 'switch_tray'))
    switch = box('switch', 'CRS812の参考外形・吸排気方向と電源・ファンの面は未確認',
                 [-width / 2, y0, sw], size, 'switch')
    removal = box('switch_removal', 'スイッチとトレーの背面交換・上方の手の仮余裕12mm',
                  [-half, y0, zs], [2 * half, p.rear_y + depth - y0, q.tray_thickness + height + q.upper_hand_margin],
                  'service')
    front_service = box('switch_front_service', 'スイッチのラック前側の面から電源とファンを前へ出す仮の経路',
                        [-half, p.front_y - 110, sw], [2 * half, y0 - (p.front_y - 110), height + q.upper_hand_margin],
                        'conditional_service')
    return {'variant': 'integrated' if q.preserve_front_service else 'integrated_lowest',
            'parameters': asdict(q), **level, 'floor_front_y': front, 'tray_half_width': half,
            'guide_inner_x': guide_x, 'switch_back_y': y0, 'tray_rear_y': y0 + q.tray_depth,
            'fence_inner_x': fence_x, 'switch': switch, 'objects': objects, 'removal': removal,
            'front_service': front_service, 'front_service_required': q.preserve_front_service,
            'front_service_dependency': 'CRS812のラック前側（端子と反対側）の面に交換できる電源とファンがある場合に必要。'
                                        '公式取扱説明に面の記載はなく未確認。',
            'replaced_cross_beams': ['switch_rail_front', 'switch_rail_rear'],
            'manufacturing_geometry': False, 'physical_validation': False}


def upper_scene(mode='crs812', q=None, with_accessories=True, with_finish=True):
    """上部専用段の案の寸法・専用段・中段の機器棚・前面と天面の板をそろえて返す。

    互換のため4要素を返す。前面と天面の板はscene['finish']から読む。
    """
    from rack_accessories import accessory_layout
    from rack_finish import finish_layout
    q = q or UpperSwitchBayParameters()
    p = rack_parameters(q)
    bay = bay_layout(p, q)
    accessories = accessory_layout(p, fixed_layout(mode, p, bay)) if with_accessories else None
    finish = None
    if with_accessories and with_finish:
        finish = finish_layout(p, fixed_layout(mode, p, bay, accessories), accessories)
    return p, bay, accessories, fixed_layout(mode, p, bay, accessories, finish)


def front_service_obstructions(service, obstacles):
    return sorted({b['name'] for b in obstacles if b['name'] != 'switch' and overlaps(service, b)})


def scene_obstacles(scene):
    objects = [b for b in scene['equipment'] if b['kind'] != 'switch']
    objects += scene['carriers'] + scene['trays'] + scene['power_trays'] + scene['cross_beams']
    objects += [scene['separator'], scene['control_panel']] + scene['cable_storage_spaces']
    if scene.get('switch_bay'):
        objects += scene['switch_bay']['objects']
    return objects


def integrated_case(q):
    p = rack_parameters(q)
    bay = bay_layout(p, q)
    scene = fixed_layout('crs812', p, bay)
    checks = check_fixed_layout(scene)
    blocked = front_service_obstructions(bay['front_service'], scene_obstacles(scene))
    return p, bay, scene, checks, blocked


def variants(q=None):
    """積み増し・上枠共有・最低高さの3案を、同じ予約の考え方で比べる。"""
    q = q or UpperSwitchBayParameters()
    base = FixedRackParameters()
    # 積み増し案も同じ床下の積み上げと手の余裕で計算し、3案の条件をそろえる。
    stacked_q = SwitchPlacementComparisonParameters(
        boundary_thickness=q.floor_plate, support_beam_height=q.support_band,
        support_plate_thickness=q.tray_thickness, upper_hand_margin=q.upper_hand_margin,
        upper_frame_height=base.section, switch_face_y=q.switch_face_y)
    reference = next(c for c in comparison(base, stacked_q)['cases'] if c['key'] == 'upper')
    size = switch_size()
    half = size[0] / 2 + q.side_hand_margin
    stacked_z = reference['switch']['origin'][2]
    stacked_service = box('switch_front_service', '積み増し案の前側作業空間',
                          [-half, base.front_y - 110, stacked_z],
                          [2 * half, reference['switch']['origin'][1] - (base.front_y - 110), size[2] + q.upper_hand_margin],
                          'conditional_service')
    stacked_blocked = front_service_obstructions(stacked_service, reference['objects'])
    rows = [{'key': 'stacked', 'label': '現行枠の上へ専用段を積み増す',
             'height_mm': reference['metrics']['frame_size_mm'][2],
             'switch_bottom_mm': stacked_z, 'floor_bottom_mm': base.height,
             'spark_bottoms_mm': reference['metrics']['spark_bottoms_from_new_base_mm'],
             'layout_checks': reference['checks']['status'],
             'front_service': 'passed' if not stacked_blocked else 'blocked',
             'front_service_obstructions': stacked_blocked,
             'load_path': '専用段の側柱を現行の側枠の上端へ載せる。重ね継ぎとねじは未設計。',
             'part_changes': '現行枠は変えずに側柱4本・上枠2本・仕切り・支持梁・支持板を追加。'
                             '既存の上枠28mmと専用段の床が重なり、高さを使う。',
             'binding_constraint': '現行枠の上端560mm'}]
    for key, label, variant_q in (('integrated', '上枠を専用段の上へ移し、床を側枠へ差し込む', q),
                                  ('integrated_lowest', '床を上段Sparkの交換空間の直上まで下げる',
                                   replace(q, preserve_front_service=False))):
        p, bay, scene, checks, blocked = integrated_case(variant_q)
        rows.append({'key': key, 'label': label, 'height_mm': p.height,
                     'switch_bottom_mm': bay['switch_z'], 'floor_bottom_mm': bay['floor_z'],
                     'spark_bottoms_mm': [p.lower_base, p.upper_base],
                     'layout_checks': 'passed',
                     'front_service': 'passed' if not blocked else 'blocked',
                     'front_service_obstructions': blocked,
                     'load_path': '側枠を上まで連続させ、専用段の床を側枠の水平な受けへ差し込む。上枠2本は側枠の上端へ移す。',
                     'part_changes': '中央用の受け梁2本を外し、側枠の上段の板を高くする。',
                     'binding_constraint': bay['binding_constraint']})
    by_key = {r['key']: r for r in rows}
    recommended = by_key['integrated']
    for row in rows:
        row['height_added_to_560_mm'] = row['height_mm'] - base.height
        row['height_saved_vs_stacked_mm'] = by_key['stacked']['height_mm'] - row['height_mm']
    return {'purpose': '上部専用段の全高と支持方法の比較。製造用ではない。', 'rows': rows,
            'recommendation': 'integrated',
            'reason': '本体の段位置と電源区画を保ち、スイッチ前側の作業空間を残す案のうち最も低い。'
                      '側枠が連続するため、専用段の荷重を新しい継ぎ目なしで側枠へ渡せる。',
            'conditional_alternative': {
                'key': 'integrated_lowest',
                'condition': 'スイッチの電源とファンが端子側にある、または前側の部品交換でもスイッチ全体を背面へ出すと決めた場合。',
                'tradeoff': '上段ファン保持部の上端に前側の作業空間が当たる。'},
            'retrofit_note': '積み増しは現行枠へ後から追加できる。ただし部品は未印刷のため、後付けの利点は小さい。',
            'parameters': asdict(q), 'switch_body_mm': size, 'manufacturing_geometry': False,
            'physical_validation': False,
            'decision_dependencies': ['スイッチの電源とファンがどちらの面にあるか',
                                      'スイッチの吸排気方向と、背面で上がる本体排気の再吸込み',
                                      'スイッチの実奥行（156mmと268mmの不一致）・質量・後方支持耳の穴位置',
                                      '分岐ケーブルの主線長・分岐線長・端子と分岐部の外形',
                                      f'全高{recommended["height_mm"]:g}mmを設置場所で許容できるか']}
