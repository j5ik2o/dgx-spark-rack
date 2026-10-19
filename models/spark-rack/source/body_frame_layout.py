"""本体連結案の配置と部品の作り方。機器の外形は参考値で、製造可否を判定しない。"""
from dataclasses import asdict
import json
from pathlib import Path

from spark_rack_parameters import BodyFrameParameters

ROOT = Path(__file__).resolve().parents[3]
REFERENCES = (
    'models/spark-rack/reference/pending-mount-measurements.json',
    'models/spark-rack/reference/prepared-fans-and-cable.json',
    'models/spark-rack/reference/selected-network-20261012/configuration.json',
    'models/spark-rack/reference/body-frame-cable-assumptions-20261019.json',
    'models/spark-rack/reference/body-frame-switch-retention-20261019.json',
    'models/spark-rack/reference/body-frame-screwless-20261019.json',
)
REQUIREMENTS = 'models/spark-rack/reference/body-frame-requirements-20261019.json'
FAN_AXES = {'front': [0, -1, 0], 'rear': [0, 1, 0], 'left': [-1, 0, 0], 'right': [1, 0, 0]}


def box(name, label, origin, size, kind, **extra):
    return dict(name=name, label=label, origin=list(origin), size=list(size), kind=kind, **extra)


def overlaps(a, b, tolerance=1e-6):
    return all(min(a['origin'][i] + a['size'][i], b['origin'][i] + b['size'][i])
               - max(a['origin'][i], b['origin'][i]) > tolerance for i in range(3))


def layout(parameters=None):
    p = parameters or BodyFrameParameters()
    p.validate()
    pending, inventory, network, cable_basis, retention_basis, screwless_basis = [json.loads((ROOT / name).read_text()) for name in REFERENCES]
    equipment, corners, boxes = [], [], []
    half = p.core_width / 2
    center_x = (p.spark_width + p.column_gap) / 2
    for col, x in enumerate((-half, p.column_gap / 2)):
        for row, z in enumerate((p.lower_base, p.upper_base)):
            equipment.append(box(f'spark_{col}_{row}', f'Spark・{"左" if col == 0 else "右"}{"下" if row == 0 else "上"}',
                                 (x, 0, z), (p.spark_width, p.spark_depth, p.spark_height), 'spark'))
    stages = (('foot', 0, p.lower_base + p.foot_grip),
              ('joint', p.lower_base + p.spark_height - p.corner_grip,
               p.stack_gap + 2 * p.corner_grip),
              ('top', p.core_top - p.corner_grip, p.corner_grip + p.top_riser))
    for stage, z, h in stages:
        for end, y in (('front', -p.corner_outside), ('back', p.spark_depth - p.corner_inside)):
            # 端子が未実測でも背面全体を開ける。背面側は側面と上下の面だけで保持する。
            depth = p.corner_inside + (p.corner_outside if end == 'front' else 0)
            for group, spans in (
                ('left', [(-half - p.corner_outside, p.corner_inside + p.corner_outside)]),
                ('pair', [(-p.column_gap / 2 - p.corner_inside, p.corner_inside + p.corner_outside),
                          (p.column_gap / 2 - p.corner_outside, p.corner_inside + p.corner_outside)]),
                ('right', [(half - p.corner_inside, p.corner_inside + p.corner_outside)])):
                pieces = [dict(origin=[x, y, z], size=[w, depth, h]) for x, w in spans]
                if group == 'pair':
                    x0, x1 = spans[0][0] + spans[0][1] - 1, spans[1][0] + 1
                    pieces.append(dict(origin=[x0, y, z], size=[x1 - x0, depth, h]))
                stage_label = {'foot': '脚', 'joint': '上下段', 'top': '上部機器'}[stage]
                group_label = {'left': '左列の外側', 'pair': '左右の列の間', 'right': '右列の外側'}[group]
                end_label = '前側' if end == 'front' else '背面側'
                corners.append(dict(name=f'core_{stage}_{group}_{end}', label=f'{stage_label}の局所接続部・{group_label}・{end_label}',
                                    kind='body_connector', pieces=pieces))
    beam_half = half + p.beam_overhang
    beam_ys = (10, p.spark_depth - p.corner_inside)
    for row, y in enumerate(beam_ys):
        for side, x in enumerate((-beam_half, 0)):
            boxes.append(box(f'accessory_beam_{row}_{side}', '周辺機器の短い横梁',
                             (x, y, p.beam_z), (beam_half, p.beam_width, p.beam_height), 'accessory_support'))
    rail_x = half + p.corner_outside - 2
    for side in (-1, 1):
        x = side * rail_x - p.beam_width / 2
        for row, y in enumerate(beam_ys):
            boxes.append(box(f'network_riser_{side}_{row}', '本体上の機器だけを支える支柱',
                             (x, y, p.accessory_surface), (p.beam_width, p.beam_width, p.network_standoff),
                             'network_support'))
        boxes.append(box(f'network_rail_{side}', 'CRS812を底面で受ける短いレール',
                         (x, beam_ys[0], p.network_rail_z),
                         (p.beam_width, p.network_rail_depth, p.beam_height), 'network_support'))
    remote = pending['remote_console']
    cw, cd, ch = remote['comet_pro']['body_mm']
    kw, kd, kh = remote['kvm_switch']['body_mm']
    device_z = p.accessory_surface + p.tray_thickness
    equipment += [
        box('comet', 'GL-RM10・前面に画面', (-cw / 2, p.comet_front_y, device_z), (cw, cd, ch), 'comet'),
        box('kvm', 'TESmart HKS401-P23・未実測の参考外形', (-kw / 2, p.kvm_front_y, device_z), (kw, kd, kh), 'kvm'),
    ]
    sw = network['final_phase']['switch']['body_envelope_mm']
    equipment.append(box('crs812', 'CRS812・耳と奥行は未実測',
                         (-sw[0] / 2, p.switch_front_y, p.network_rail_z + p.beam_height), sw, 'switch'))
    boxes.append(box('comet_tray', 'GL-RM10の小さな載せ台',
                     (-cw / 2 - 4, p.comet_front_y, p.accessory_surface),
                     (cw + 8, cd + 4, p.tray_thickness), 'accessory_tray', tray_device='comet'))
    for side, x in enumerate((-kw / 2 - 5, 0)):
        boxes.append(box(f'kvm_tray_{side}', '切替器の分割した載せ台',
                         (x, p.kvm_front_y - 4, p.accessory_surface),
                         (kw / 2 + 5, kd + 8, p.tray_thickness), 'accessory_tray',
                         tray_device='kvm', tray_side=side))
    adapter = [99.05, 98.99, 35.17]
    for col, x in enumerate((-center_x, center_x)):
        for row in range(2):
            y = p.power_first_y + row * p.power_row_pitch
            equipment.append(box(f'power_{col}_{row}', '電源アダプター・参考外形',
                                 (x - adapter[0] / 2, y, p.power_bottom), adapter, 'power'))
            size = p.power_tray_size
            boxes.append(box(f'power_tray_{col}_{row}', '電源を囲い込まない小さな受け',
                             (x - size / 2, y - (size - adapter[1]) / 2, p.power_bottom - p.tray_thickness),
                             (size, size, p.tray_thickness), 'power_tray'))
    fan_z = p.lower_base + (2 * p.spark_height + p.stack_gap) / 2
    fans = []
    for col, x in enumerate((-center_x, center_x)):
        for end, y, axis in (
                ('front', -p.front_fan_gap - p.fan_depth, [0, -1, 0]),
                ('rear', p.spark_depth + p.rear_fan_gap, [0, 1, 0])):
            fans.append(box(f'spark_fan_{col}_{end}', f'Spark列の{"前面" if end == "front" else "背面"}・140mm固定ファン',
                            (x - p.fan_size / 2, y, fan_z - p.fan_size / 2),
                            (p.fan_size, p.fan_depth, p.fan_size), 'fan',
                            axis=axis, fan_size=p.fan_size, pitch=p.fan_pitch, opening=p.fan_opening,
                            mounting='fixed_axis_aligned', mount_face=end, attachment_stage='joint'))
    side_plane = half + p.corner_outside + p.power_fan_gap
    for side in (-1, 1):
        x = side_plane + p.fan_plate if side > 0 else -side_plane - p.fan_plate - p.fan_depth
        fans.append(box(f'power_fan_{side}', '電源用・側面120mm固定ファン',
                        (x, p.power_fan_center_y - p.power_fan_size / 2,
                         p.power_fan_center_z - p.power_fan_size / 2),
                        (p.fan_depth, p.power_fan_size, p.power_fan_size), 'fan',
                        axis=[side, 0, 0], fan_size=p.power_fan_size,
                        pitch=p.power_fan_pitch, opening=p.power_fan_opening,
                        mounting='fixed_axis_aligned', mount_face='right' if side > 0 else 'left',
                        attachment_stage='foot'))
    equipment += fans
    controllers = []
    for side in (-1, 1):
        y = p.controller_right_y if side > 0 else p.controller_left_y
        u, v, w = [0, side, 0], [0, 0, 1], [side, 0, 0]
        dock_x = side * (half + p.controller_offset)
        for row in range(3):
            z = p.controller_first_z + row * p.controller_pitch_z
            x = dock_x - 3 if side > 0 else dock_x + 3 - p.controller_depth
            controller = box(f'controller_{side}_{row}', f'{"右" if side > 0 else "左"}側の{"下中上"[row]}段制御器・正立',
                             (x, y - p.controller_width / 2, z - p.controller_height / 2),
                             (p.controller_depth, p.controller_width, p.controller_height), 'controller',
                             dock_origin=[dock_x, y, z], u=u, v=v, w=w)
            controllers.append(controller)
            # 実際の取付位置は共通ドックの正本から形状生成時に求める。
            boxes.append(dict(name=f'controller_mount_{side}_{row}', label='制御器ごとの局所取付部',
                              kind='controller_mount', controller=controller['name']))
    equipment += controllers
    connectors = [
        box(f'{e["name"]}_ports', 'Spark背面の端子用の仮空間・実端子未確認',
            (e['origin'][0], p.spark_depth, e['origin'][2]),
            (p.spark_width, p.rear_connector_depth, p.spark_height), 'connector_space')
        for e in equipment if e['kind'] == 'spark'
    ]
    connectors += [
        box('comet_ports', 'GL-RM10の背面配線用の仮空間',
            (-cw / 2, p.comet_front_y + cd, device_z), (cw, 60, ch), 'connector_space'),
        box('kvm_ports', '切替器の背面配線用の仮空間',
            (-kw / 2, p.kvm_front_y + kd, device_z), (kw, 60, kh), 'connector_space'),
    ]
    scene = dict(parameters=asdict(p), equipment=equipment, corners=corners, boxes=boxes,
                connectors=connectors, references=list(REFERENCES) + [REQUIREMENTS],
                expected_inventory={'spark': 4, 'switch': 1, 'comet': 1, 'kvm': 1,
                                    'power': 4, 'controller': inventory['controllers']['quantity'],
                                    'fan_140': inventory['fans'][0]['quantity'],
                                    'fan_120': inventory['fans'][1]['quantity']},
                assumptions=[
                    'Sparkの箱の参考外形へ局所接続部を当てる。外装へ荷重を掛けることはメーカー確認・実測前。',
                    'CRS812の奥行は資料間の不一致が残るため268mmを参考値とする。足と取付耳は未確認。',
                    'TESmartの300×117×30mmは検索要約に基づく未実測の参考値。',
                    '背面ファンは直線方向へ外して端子へアクセスする。斜め取付やヒンジは使わない。',
                    'Spark下段の交換は、上の機器と上段を先に外す手順が必要。独立した引き出し式ではない。',
                ], manufacturing_geometry=False, physical_validation=False)
    from body_frame_switch_retention import plan
    scene['switch_retention'] = plan(scene, p)
    scene['switch_retention']['specification_basis'] = retention_basis
    from body_frame_cables import routing
    scene['cable_management'] = routing(scene, p)
    scene['cable_management']['assumption_reference'] = REFERENCES[3]
    scene['cable_management']['specification_basis'] = cable_basis
    scene['screwless_requirement'] = screwless_basis
    return scene


def validate_layout(scene):
    from collections import Counter
    equipment = scene['equipment']
    if any(scene['screwless_requirement'][key] != 0 for key in ('assembly_screws', 'assembly_nuts')):
        raise ValueError('組立用のビス・ナットは0にしてください')
    names = [e['name'] for e in equipment]
    if len(names) != len(set(names)):
        raise ValueError('機器名が重複しています')
    count = Counter(e['kind'] for e in equipment if e['kind'] != 'fan')
    count.update(f'fan_{e["fan_size"]}' for e in equipment if e['kind'] == 'fan')
    if dict(count) != scene['expected_inventory']:
        raise ValueError('維持する機器の種類・個数が一致しません: ' + str(dict(count)))
    for fan in (e for e in equipment if e['kind'] == 'fan'):
        axis = fan['axis']
        if len(axis) != 3 or sum(abs(v) for v in axis) != 1 or any(v not in (-1, 0, 1) for v in axis):
            raise ValueError('ファンの斜め取付は禁止です: ' + fan['name'])
        if axis[2] != 0 or fan['mounting'] != 'fixed_axis_aligned':
            raise ValueError('ファンは前後面か側面への正立固定です: ' + fan['name'])
        if FAN_AXES.get(fan['mount_face']) != axis:
            raise ValueError('ファンの取付面と軸が一致していません: ' + fan['name'])
    collisions = [(a['name'], b['name']) for i, a in enumerate(equipment)
                  for b in equipment[i + 1:] if overlaps(a, b)]
    if collisions:
        raise ValueError('機器の参考外形が干渉しています: ' + str(collisions))
    from body_frame_cables import validate_routing
    cable_report = validate_routing(scene)
    return {'status': 'passed', 'inventory': dict(count), 'equipment_collisions': collisions,
            'cable_routing': cable_report,
            'fan_mounting': '6個すべて前後・左右の軸方向へ正立固定',
            'scope': '参考外形の配置・機器個数・ファンの取付軸。実機の適合・冷却は含まない。'}
