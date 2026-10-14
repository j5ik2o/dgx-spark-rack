"""固定段ラックの配置と交換経路。実測値を確定した製造データではない。"""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sys

from spark_rack_parameters import FixedRackParameters
from four_node_layout import LayoutParameters, box, overlaps, route
from network_configuration import final_topology, selected_network

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'models/adapter-rack/source'))
from adapter_rack_parameters import INPUTS as ADAPTER_INPUTS


def cross_beams(p, bay=None):
    result = []
    def add(name, y, z, height, role, width=20):
        result.append(box(name, name, [-p.inner_width / 2 - 8, y - width / 2, z],
                          [p.inner_width + 16, width, height], role))
    # 下枠・電源梁は台座へ、本体の前後梁は開口を持つ支持棚へ統合する。
    for y, end in ((p.front_y + 14, 'front'), (p.rear_y - 14, 'rear')):
        add('frame_top_' + end, y, p.height - p.section, 28, 'frame_beam', 28)
    for row, base in enumerate((p.lower_base, p.upper_base)):
        fan_bottom = base + p.spark_height / 2 - p.fan_size / 2
        add(f'fan_rail_{row}', p.front_face_y + 10, fan_bottom - 14, 8, 'support_beam')
    # 上部専用段ではスイッチを中段へ置かないため、中央用の受け梁を外す。
    if bay is None:
        for y, end in ((-146, 'front'), (78, 'rear')):
            add('switch_rail_' + end, y, p.switch_center_z - 22 - 8 - 12, 12, 'support_beam')
    return result


def fixed_layout(mode='ring', parameters=None, bay=None, accessories=None, finish=None):
    """bayはupper_switch_bay.bay_layout、accessoriesはrack_accessories.accessory_layout、
    finishはrack_finish.finish_layoutの結果。

    省略時は中央の暫定配置。遠隔操作機器の棚は、中段が空く上部専用段の案でだけ使える。
    """
    if mode not in ('ring', 'crs812'):
        raise ValueError('採用構成はリング接続またはCRS812です')
    p = parameters or FixedRackParameters()
    p.validate()
    if bay is not None and p.height + 1e-9 < bay['required_height']:
        raise ValueError('上部専用段に必要な全高が不足しています')
    if accessories is not None and bay is None:
        raise ValueError('遠隔操作機器の棚は上部専用段の案でだけ使えます。中央配置ではスイッチと重なります。')
    if finish is not None and (bay is None or accessories is None):
        raise ValueError('前面と天面の板は、上部専用段と機器棚を持つ案でだけ使えます。')
    lp = replace(LayoutParameters(), lower_base=p.lower_base, row_pitch=p.row_pitch,
                 column_pitch=p.column_pitch, rack_width=p.width, rack_height=p.height,
                 rack_front_y=p.front_y, rear_space=p.rear_y, switch_face_y=100,
                 fan_front_gap=p.spark_front_clearance, shelf_thickness=8)
    nodes = []
    for name, label, col, row in (('upper_left', '左上', -1, 1), ('upper_right', '右上', 1, 1),
                                  ('lower_right', '右下', 1, 0), ('lower_left', '左下', -1, 0)):
        x, z = col * p.column_pitch / 2, p.lower_base + row * p.row_pitch
        node = box(name, label + 'のSpark', [x - p.spark_width / 2, p.spark_front_y, z],
                   [p.spark_width, p.spark_depth, p.spark_height], 'spark')
        node['ports'] = [[x + lp.spark_port_offset + sign * lp.spark_port_pitch / 2, 0, z + lp.spark_port_height]
                         for sign in (-1, 1)]
        nodes.append(node)
    by_name = {n['name']: n for n in nodes}
    ring_cables = []
    for label, a, ap, b, bp in (('上段の横配線', 'upper_left', 1, 'upper_right', 0),
            ('右側の縦配線', 'upper_right', 1, 'lower_right', 1),
            ('下段の横配線', 'lower_right', 0, 'lower_left', 1),
            ('左側の縦配線', 'lower_left', 0, 'upper_left', 0)):
        start, end = by_name[a]['ports'][ap], by_name[b]['ports'][bp]
        ring_cables.append({'label': label, 'from': a, 'to': b, **route(start, end, lp)})
    fans, carriers, trays, service, intake, exhaust = [], [], [], [], [], []
    for node in nodes:
        x = node['origin'][0] + p.spark_width / 2
        z = node['origin'][2]
        center_z = z + p.spark_height / 2
        fan = box(node['name'] + '_fan', node['label'] + 'の140mmファン',
                  [x - 70, p.fan_front_y, center_z - 70], [140, 27, 140], 'fan')
        fan.update(axis='y', size_mm=140, mounting_pitch_mm=p.fan_pitch, role='spark')
        fans.append(fan)
        # 各段の前面を左右の2モジュールでそろえる。持ち手は外へ張り出さない。
        carriers.append(box(node['name'] + '_carrier', node['label'] + 'の共通面にそろえたファン保持部',
                            [-p.inner_width / 2 if x < 0 else 0, p.front_face_y, center_z - 76],
                            [p.inner_width / 2, 24, 152], 'carrier'))
        trays.append(box(node['name'] + '_tray', node['label'] + 'の背面引き出しトレー',
                         [x - p.tray_width / 2, -153, z - p.tray_thickness],
                         [p.tray_width, p.tray_depth, p.tray_thickness], 'tray'))
        service.append(box(node['name'] + '_removal', node['label'] + 'の背面交換経路・手の仮余裕12mm',
                           [x - p.tray_width / 2 - p.hand_margin, -153, z - p.tray_thickness],
                           [p.tray_width + 2 * p.hand_margin, p.rear_y + p.tray_depth + 153,
                            p.tray_thickness + p.spark_height + p.hand_margin], 'service'))
        intake.append(box(node['name'] + '_intake', node['label'] + 'の前方100mmの空間',
                          [x - 75, p.spark_front_y - p.spark_front_clearance, z],
                          [150, p.spark_front_clearance, p.spark_height], 'air_space'))
        exhaust.append(box(node['name'] + '_exhaust', node['label'] + 'の後方400mmの空間',
                           [x - 75, 0, z], [150, p.spark_rear_clearance, p.spark_height], 'air_space'))
    dimensions = {name: float(value.split()[0]) for name, value, _ in ADAPTER_INPUTS}
    pw, pd, ph = (dimensions[n] for n in ('AdapterWidth', 'AdapterLength', 'AdapterHeight'))
    power, power_trays, connector_spaces = [], [], []
    for col, x in enumerate((-90, 90)):
        for row, y in enumerate((-250, -80)):
            name = f'power_{col}_{row}'
            power.append(box(name, '電源アダプター・既存寸法の参考外形',
                             [x - pw / 2, y, 40], [pw, pd, ph], 'adapter'))
            power_trays.append(box(name + '_tray', '電源の前方引き出しトレー',
                                   [x - 55, y - 5.5, 32], [110, 110, 8], 'power_tray'))
            for yy in (y - 30, y + pd):
                connector_spaces.append(box(name + '_connector_' + str(yy), '電源端子側30mmの参考予約',
                                            [x - pw / 2, yy, 40], [pw, 30, ph], 'connector_space'))
    for col, left in enumerate((True, False)):
        fan = box('power_fan_' + str(col), '電源区画の120mm側面排気ファン',
                  [-268 if left else 241, -180, 28], [27, 120, 120], 'fan')
        fan.update(axis='x', size_mm=120, mounting_pitch_mm=p.power_fan_pitch,
                   face_coordinate=-272.5 if left else 272.5, outward=-1 if left else 1, role='adapter')
        fans.append(fan)
    ceiling = box('power_ceiling', '本体と電源の空気を分ける水平な仕切り',
                  [-p.inner_width / 2, -280, p.power_ceiling_z],
                  [p.inner_width, p.rear_y - 28 + 280, p.power_ceiling_thickness], 'separator')
    controllers = []
    for row, z in enumerate(p.controller_centers_z):
        for col, x in enumerate((-90, 90)):
            labels = (('電源左', '電源右'), ('左下', '右下'), ('左上', '右上'))
            controllers.append(box(f'control_{row}_{col}', labels[row][col] + 'の制御器・既存ケースと共通ドック',
                                   [x - 50, p.controller_origin_y - 41, z - 22],
                                   [100, 44, 44], 'controller'))
    control_panel = box('control_panel', '制御器6組を載せた左開きの前面サービス扉',
                        [-180, p.controller_origin_y + 3, 8], [360, 12, 140], 'control_panel')
    storage = [box('breakout_storage_' + str(i), '2m分岐ケーブルの余長収納予約・収納量は未検証',
                   [x, -220, 272], [220, 290, p.cable_storage_height], 'cable_storage')
               for i, x in enumerate((-230, 10))]
    # 接続を外した本体とトレーの移動を確認する。接続中の引き出しは想定しない。
    equipment = nodes + fans + power + controllers
    switch = None
    if mode == 'crs812' and bay is not None:
        switch = deepcopy(bay['switch'])
        equipment.append(switch)
        service.append(deepcopy(bay['removal']))
    elif mode == 'crs812':
        spec = selected_network()['final_phase']['switch']
        width, depth, height = spec['body_envelope_mm']
        switch = box('switch', 'CRS812の参考外形・実支持板は未設計',
                     [-width / 2, 100 - depth, p.switch_center_z - height / 2], [width, depth, height], 'switch')
        equipment.append(switch)
        service.append(box('switch_removal', 'スイッチの背面交換経路・手の仮余裕12mm',
                           [switch['origin'][0] - 12, switch['origin'][1], switch['origin'][2] - 8],
                           [switch['size'][0] + 24, p.rear_y + switch['size'][1] - switch['origin'][1], 64], 'service'))
    scene = {'mode': mode, 'parameters': p.values(), 'frame_outer_mm': [p.width, p.depth, p.height],
            'nodes': nodes, 'equipment': equipment, 'fans': fans, 'carriers': carriers, 'trays': trays,
            'power_trays': power_trays, 'separator': ceiling, 'control_panel': control_panel,
            'cross_beams': cross_beams(p, bay), 'service_spaces': service,
            'intake_spaces': intake, 'exhaust_spaces': exhaust, 'connector_spaces': connector_spaces,
            'cable_storage_spaces': storage, 'switch': switch,
            'ring_cables': ring_cables, 'final_network': final_topology(),
            'manufacturing_geometry': False, 'mount_holes_committed': False,
            'physical_validation': '実物の適合、耐荷重、材料、冷却、配線、交換操作は未検証。',
            'installation_depth_to_rear_clearance_mm': p.spark_rear_clearance - p.front_y,
            'control_door_sweep': box('control_door_sweep', '制御器扉を前方へ90度開く経路の保守的な箱',
                                     [-224, p.controller_origin_y + 3 - 360, 8], [404, 372, 140], 'service'),
            'selected_switch': selected_network()['final_phase']['switch']}
    if accessories is not None:
        scene['equipment'] = scene['equipment'] + deepcopy(accessories['equipment'])
        scene['accessories'] = deepcopy(accessories)
    if finish is not None:
        scene['finish'] = deepcopy(finish)
        scene['frame_outer_mm'] = [p.width, p.depth, finish['overall_height_mm']]
    if bay is not None:
        scene['switch_bay'] = deepcopy(bay)
        scene['conditional_service_spaces'] = [deepcopy(bay['front_service'])] if mode == 'crs812' else []
    return scene


def check_fixed_layout(scene):
    bay = scene.get('switch_bay')
    bay_objects = bay['objects'] if bay else []
    if scene.get('accessories'):
        bay_objects = bay_objects + scene['accessories']['objects']
    finish = scene.get('finish')
    if finish:
        bay_objects = bay_objects + finish['objects']
    solids = scene['equipment'] + scene['carriers'] + scene['trays'] + scene['power_trays']
    solids += [scene['separator'], scene['control_panel']] + bay_objects
    def own_fan_and_holder(a, b):
        return (a['name'].removesuffix('_fan') == b['name'].removesuffix('_carrier')
                and {a['kind'], b['kind']} == {'fan', 'carrier'})
    collisions = [[a['name'], b['name']] for i, a in enumerate(solids) for b in solids[i + 1:]
                  if not own_fan_and_holder(a, b) and overlaps(a, b)]
    obstacles = scene['equipment'] + scene['carriers'] + [scene['separator'], scene['control_panel']]
    # 専用段の床・ガイド・止めは固定障害物。トレーはスイッチと一緒に動く。
    obstacles += [b for b in bay_objects if b['kind'] != 'switch_tray']
    air_conflicts = [[a['name'], b['name']] for a in scene['intake_spaces'] + scene['exhaust_spaces']
                     for b in obstacles if overlaps(a, b)]
    service_conflicts = []
    for sweep in scene['service_spaces']:
        target = sweep['name'].removesuffix('_removal')
        for obstacle in obstacles + scene['cable_storage_spaces']:
            if obstacle['name'] in (target, target + '_fan', target + '_carrier'):
                continue
            if overlaps(sweep, obstacle):
                service_conflicts.append([sweep['name'], obstacle['name']])
    storage_conflicts = [[a['name'], b['name']] for a in scene['cable_storage_spaces'] for b in solids if overlaps(a, b)]
    p = FixedRackParameters(**scene['parameters'])
    # 天板を載せる案では、天板の厚さだけ上限を上げる。
    top = finish['overall_height_mm'] if finish else p.height
    outside = [s['name'] for s in solids if any(s['origin'][axis] < low or s['origin'][axis] + s['size'][axis] > high
               for axis, low, high in ((0, -p.width / 2, p.width / 2), (1, p.front_y, p.rear_y), (2, 0, top)))]
    result = {'equipment_collisions': collisions, 'fixed_air_obstructions': air_conflicts,
              'rear_service_obstructions': service_conflicts, 'storage_obstructions': storage_conflicts,
              'outside_frame': outside, 'scope': '参考外形・固定障害物・手の仮余裕12mmを含む背面交換経路。接続端子と配線の実操作は未検証。'}
    if bay:
        result['conditional_front_service'] = [
            {'name': space['name'], 'required': bay['front_service_required'],
             'dependency': bay['front_service_dependency'],
             'obstructions': sorted({b['name'] for b in obstacles + scene['cross_beams'] + scene['cable_storage_spaces']
                                     if b['name'] != 'switch' and b['kind'] != 'removable_cover' and overlaps(space, b)})}
            for space in scene.get('conditional_service_spaces', [])]
        if any(row['required'] and row['obstructions'] for row in result['conditional_front_service']):
            raise ValueError(str(result))
    if scene.get('accessories'):
        from rack_accessories import check_accessories
        result.update(check_accessories(scene))
        if result['accessory_service_obstructions'] or result['accessory_connector_obstructions']:
            raise ValueError(str(result))
    if finish:
        from rack_finish import check_finish
        result.update(check_finish(scene))
        if result['finish_service_obstructions'] or result['control_door_sweep_obstructions']:
            raise ValueError(str(result))
    if collisions or air_conflicts or service_conflicts or storage_conflicts or outside:
        raise ValueError(str(result))
    return result
