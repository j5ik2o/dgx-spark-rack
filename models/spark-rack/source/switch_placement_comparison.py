"""現行の段位置を基準に中央・上部・下部のスイッチ外形と交換予約を比較する。"""
from copy import deepcopy
from dataclasses import asdict
import math

from fixed_rack_layout import fixed_layout
from four_node_layout import box, overlaps
from network_configuration import selected_network, final_topology
from spark_rack_parameters import FixedRackParameters, SwitchPlacementComparisonParameters


def lower_shelf_bottom(p, q):
    return p.lower_base - p.tray_thickness - q.node_support_height


def common_objects(scene, p, q):
    objects = [b for b in scene['equipment'] if b['kind'] != 'switch']
    objects += scene['carriers'] + scene['trays'] + scene['power_trays']
    objects += [scene['separator'], scene['control_panel']]
    objects += [b for b in scene['cross_beams'] if not b['name'].startswith('switch_rail_')]
    for level, base in enumerate((scene['parameters']['lower_base'],
                                  scene['parameters']['lower_base'] + scene['parameters']['row_pitch'])):
        objects.append(box('node_support_' + str(level), '本体支持棚の保守的な外形予約',
                           [-p.inner_width / 2, p.spark_front_y + 2, base - p.tray_thickness - q.node_support_height],
                           [p.inner_width, p.spark_depth - 4, q.node_support_height], 'support_reservation'))
    return objects


def dedicated_bay(p, q, bottom, switch_size):
    width, depth, height = switch_size
    support_z = bottom + q.boundary_thickness + q.support_beam_height
    switch_bottom = support_z + q.support_plate_thickness
    top_beam_z = switch_bottom + height + q.upper_hand_margin
    objects = [box('bay_floor', '専用段の下側仕切り・取付は未設計',
                   [-p.inner_width / 2, p.front_y, bottom],
                   [p.inner_width, p.depth, q.boundary_thickness], 'bay_boundary'),
               box('switch_tray', 'スイッチの支持板予約・足と吸気口は要実測',
                   [-p.inner_width / 2, q.switch_face_y - depth, support_z],
                   [p.inner_width, depth, q.support_plate_thickness], 'switch_tray')]
    for y, end in ((-146, 'front'), (78, 'rear')):
        objects.append(box('bay_support_' + end, '専用段の支持梁予約',
                           [-p.inner_width / 2, y - 10, bottom + q.boundary_thickness],
                           [p.inner_width, 20, q.support_beam_height], 'bay_support'))
    # 側柱は分割接合と通風開口を設計する前の外形予約。閉じた側壁ではない。
    for right in (False, True):
        x = p.width / 2 - p.section if right else -p.width / 2
        for y, end in ((p.front_y, 'front'), (p.rear_y - p.section, 'rear')):
            objects.append(box(f'bay_post_{right}_{end}', '専用段の側柱予約',
                               [x, y, bottom], [p.section, p.section, q.module_height(height)], 'bay_frame'))
    for y, end in ((p.front_y, 'front'), (p.rear_y - p.section, 'rear')):
        objects.append(box('bay_top_' + end, '専用段の上枠予約',
                           [-p.inner_width / 2, y, top_beam_z],
                           [p.inner_width, p.section, q.upper_frame_height], 'bay_frame'))
    return switch_bottom, objects


def check_candidate(candidate):
    scene, switch, objects = candidate['scene'], candidate['switch'], candidate['objects']
    new = candidate['new_objects']
    collision_pairs = [[a['name'], b['name']] for a in [switch] + new for b in candidate['common_objects']
                       if overlaps(a, b)]
    collision_pairs += [[a['name'], b['name']] for i, a in enumerate([switch] + new)
                       for b in ([switch] + new)[i + 1:] if overlaps(a, b)]
    air_pairs = [[air['name'], b['name']] for air in scene['intake_spaces'] + scene['exhaust_spaces']
                 for b in [switch] + new if overlaps(air, b)]
    service_pairs = []
    service = [s for s in scene['service_spaces'] if s['name'] != 'switch_removal'] + [candidate['switch_service']]
    for sweep in service:
        target = sweep['name'].removesuffix('_removal')
        for obstacle in objects:
            if obstacle['name'] in (target, target + '_tray'):
                continue
            if overlaps(sweep, obstacle):
                service_pairs.append([sweep['name'], obstacle['name']])
    storage_pairs = [[s['name'], b['name']] for s in scene['cable_storage_spaces']
                     for b in [switch] + new if overlaps(s, b)]
    bounds = candidate['frame']
    outside = [b['name'] for b in [switch] + new if any(
        b['origin'][i] < bounds['origin'][i] - 1e-6 or
        b['origin'][i] + b['size'][i] > bounds['origin'][i] + bounds['size'][i] + 1e-6 for i in range(3))]
    conflicts = collision_pairs + air_pairs + service_pairs + storage_pairs
    return {'status': 'passed' if not conflicts and not outside else 'rejected',
            'new_object_collisions': collision_pairs, 'spark_air_reservation_obstructions': air_pairs,
            'exchange_obstructions': service_pairs, 'storage_obstructions': storage_pairs,
            'outside_frame': outside, 'cooling_verified': False,
            'scope': '購入品と支持・柱の外形予約、前後の通風予約、接続を外した背面交換の箱。詳細形状・配線・実冷却・全体組立は未検証。'}


def endpoint_distance_bounds(nodes, switch):
    rows = []
    for node in nodes:
        gaps, maxima = [], []
        for axis in (0, 2):
            nlo, slo = node['origin'][axis], switch['origin'][axis]
            nhi, shi = nlo + node['size'][axis], slo + switch['size'][axis]
            gaps.append(max(slo - nhi, nlo - shi, 0))
            maxima.append(max(abs(nlo - shi), abs(nhi - slo)))
        dy = abs(switch['origin'][1] + switch['size'][1] - (node['origin'][1] + node['size'][1]))
        rows.append({'node': node['name'], 'minimum_possible_straight_mm': math.hypot(dy, *gaps),
                     'maximum_possible_straight_mm': math.hypot(dy, *maxima)})
    return {'body_face_bounds': rows, 'routing_validated': False,
            'scope': '端子が筐体の背面内にある場合の直線距離の範囲。実端子位置・分岐点・曲線・余長は含まない。'}


def comparison(p=None, q=None):
    p, q = p or FixedRackParameters(), q or SwitchPlacementComparisonParameters()
    p.validate()
    values = asdict(q)
    if any(not math.isfinite(v) or v <= 0 for key, v in values.items() if key != 'switch_face_y'):
        raise ValueError('専用段の寸法は有限の正の値にしてください')
    if not math.isfinite(q.switch_face_y):
        raise ValueError('端子面の位置は有限の値にしてください')
    baseline = fixed_layout('crs812', p)
    size = selected_network()['final_phase']['switch']['body_envelope_mm']
    width, depth, height = size
    extension = q.module_height(height)
    common = common_objects(baseline, p, q)
    cases = []
    placements = [('central', '中央・現行比較基準', baseline['switch']['origin'][2], 0, p.height),
                  ('upper', '上部専用段・推奨候補', None, 0, p.height + extension),
                  ('lower_extension', '下部追加段・本体の床からの高さが変わる', None, -extension, p.height),
                  ('lower_gap', '既存下部の隙間・収容不可', p.power_ceiling_z + p.power_ceiling_thickness, 0, p.height)]
    for key, label, switch_z, frame_bottom, frame_top in placements:
        new = []
        if key in ('upper', 'lower_extension'):
            bay_bottom = p.height if key == 'upper' else -extension
            switch_z, new = dedicated_bay(p, q, bay_bottom, size)
            if key == 'lower_extension':
                new.append(box('bay_upper_boundary', '電源区画と専用段を分ける上側仕切り予約',
                               [-p.inner_width / 2, p.front_y + p.section, -q.boundary_thickness],
                               [p.inner_width, p.depth - 2 * p.section, q.boundary_thickness], 'bay_boundary'))
        elif key == 'central':
            new = [b for b in baseline['cross_beams'] if b['name'].startswith('switch_rail_')]
        switch = box('switch', 'CRS812・吸排気方向と耳込み幅は未確認',
                     [-width / 2, q.switch_face_y - depth, switch_z], size, 'switch')
        service = box('switch_removal', 'スイッチと支持板の背面交換・上方の手の仮余裕12mm',
                      [-width / 2 - p.hand_margin, q.switch_face_y - depth, switch_z - q.support_plate_thickness],
                      [width + 2 * p.hand_margin, p.rear_y + 2 * depth - q.switch_face_y,
                       q.support_plate_thickness + height + q.upper_hand_margin], 'service')
        frame = box('frame', '比較案の外形・脚は含まない',
                    [-p.width / 2, p.front_y, frame_bottom], [p.width, p.depth, frame_top - frame_bottom], 'frame')
        case = {'key': key, 'label': label, 'scene': deepcopy(baseline), 'switch': switch,
                'frame': frame, 'common_objects': deepcopy(common), 'new_objects': new,
                'objects': deepcopy(common) + new + [switch], 'switch_service': service,
                'metrics': {'frame_size_mm': frame['size'], 'height_added_mm': frame['size'][2] - p.height,
                            'spark_bottoms_from_new_base_mm': [p.lower_base - frame_bottom, p.upper_base - frame_bottom],
                            'spark_bottoms_preserved': frame_bottom == 0,
                            'switch_bottom_from_new_base_mm': switch_z - frame_bottom,
                            'switch_center_from_new_base_mm': switch_z + height / 2 - frame_bottom,
                            'switch_center_above_original_base_mm': switch_z + height / 2,
                            'mass_kg': None, 'center_of_gravity_verified': False,
                            'cable_routing_verified': False,
                            'dedicated_bay': key in ('upper', 'lower_extension')}}
        case['checks'] = check_candidate(case)
        case['endpoint_distance_bounds'] = endpoint_distance_bounds(baseline['nodes'], switch)
        cases.append(case)
    gap = lower_shelf_bottom(p, q) - (p.power_ceiling_z + p.power_ceiling_thickness)
    return {'purpose': '現行の固定段を基準に専用段を比較する配置候補。製造用ではない。',
            'parameters': p.values(), 'comparison_parameters': values, 'cases': cases,
            'recommendation': 'upper', 'extension_height_mm': extension,
            'lower_available_height_mm': gap, 'switch_body_height_mm': height,
            'lower_height_shortfall_before_support_mm': height - gap,
            'reason': '上部だけがSparkの底面208/428mmと電源区画を維持しながら独立した段を追加できる。冷却最適の証明ではない。',
            'print_split_screening': {'side_panel_envelope_mm': [p.section, p.depth / 2 + p.lap_length / 2, extension],
                                     'boundary_tile_envelope_mm': [p.inner_width / 3 + p.lap_length, p.depth / 2 + p.lap_length / 2, q.boundary_thickness],
                                     'support_tile_envelope_mm': [p.inner_width / 3 + p.lap_length, depth / 2 + p.lap_length, q.support_plate_thickness],
                                     'joint_geometry_validated': False,
                                     'note': '分割の寸法枠だけ。接合と支持・材料・印刷方向は未設計。'},
            'network': final_topology(), 'manufacturing_geometry': False, 'physical_validation': False,
            'balance_screening': {'lower_extension_lifts_base_module_mm': extension,
                                  'switch_center_difference_upper_minus_lower_mm': p.height,
                                  'lower_cg_favors_switch_mass_ratio_above': extension / p.height,
                                  'scope': '追加区画の質量差を除くと、下部案の重心が低くなる条件はスイッチ質量／既存本体区画質量がこの比率を上回ること。両質量が未確定なので重心の優劣は未判定。'},
            'decision_dependencies': ['スイッチの吸排気方向と電源・ファン交換範囲',
                                      'スイッチ質量・耳込み幅・支持面・奥行の不一致',
                                      '分岐ケーブルの主線長・分岐線長・端子と分岐部',
                                      '上部追加による転倒と接合強度、熱い排気の再吸込み',
                                      '全高668mmを許容できるか（現在の仮余裕で計算）']}
