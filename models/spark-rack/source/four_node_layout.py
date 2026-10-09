"""4台専用ラックの配置検討。単位mm。印刷部品の形状を定義しない。"""
from dataclasses import asdict, dataclass
from rack_candidate_datums import DATUMS, controller_box
from itertools import permutations, product
import math


SWITCHES = {
    'crs812': {'label': 'CRS812', 'width': 443.0, 'depth': 268.0, 'height': 44.0,
               'port_fractions': [-0.32, -0.23, -0.14, -0.05],
               'dimension_note': '奥行は資料間で不一致。大きい268mmを仮採用。'},
    'crs804': {'label': 'CRS804', 'width': 218.0, 'depth': 387.0, 'height': 44.0,
               'port_fractions': [-0.34, -0.13, 0.08, 0.29],
               'dimension_note': '寸法図の最大奥行387mmを収容範囲として仮採用。'},
}


@dataclass(frozen=True)
class LayoutParameters:
    column_pitch: float = 180
    row_pitch: float = 220
    lower_base: float = DATUMS.lower_base
    spark_pair_offset: float = 0
    spark_port_offset: float = 30
    spark_port_pitch: float = 24
    spark_port_height: float = 25.25
    switch_x: float = 0
    switch_face_y: float = 0
    switch_z_offset: float = 0
    straight_lead: float = 30
    bend_radius: float = 20
    service_slack: float = 30
    length_basis_reserve: float = 40
    cable_length: float = 400
    rear_space: float = DATUMS.frame_rear_y
    shelf_thickness: float = 6
    rack_width: float = DATUMS.frame_outer_width
    rack_height: float = DATUMS.frame_height
    rack_front_y: float = DATUMS.frame_front_y
    fan_front_gap: float = 25
    include_fans: bool = True

    def validate(self):
        if any(not math.isfinite(v) for v in asdict(self).values()):
            raise ValueError('寸法は有限の値にしてください')
        if self.column_pitch < 150 or self.row_pitch < 110:
            raise ValueError('機器を配置するための列間隔・段間隔が不足しています')
        if min(self.lower_base, self.straight_lead, self.bend_radius,
               self.cable_length, self.shelf_thickness) <= 0:
            raise ValueError('高さ・引き出し・曲げ半径・ケーブル長・板厚は正にしてください')
        if min(self.service_slack, self.length_basis_reserve, self.rear_space) < 0:
            raise ValueError('余裕と配線空間は負にしないでください')
        if min(self.rack_width, self.rack_height, self.fan_front_gap) <= 0:
            raise ValueError('収容幅・高さ・ファン前後間隔は正にしてください')


def box(name, label, origin, size, kind):
    return {'name': name, 'label': label, 'origin': list(origin), 'size': list(size), 'kind': kind}


def overlaps(a, b):
    return all(min(a['origin'][i] + a['size'][i], b['origin'][i] + b['size'][i])
               - max(a['origin'][i], b['origin'][i]) > 1e-6 for i in range(3))


def route(start, end, p):
    """同じ側を向く端子間を、2つの四分円と直線でつなぐ。"""
    distance = math.hypot(end[0] - start[0], end[2] - start[2])
    r = p.bend_radius
    if distance < 2 * r:
        return {'screening': 'needs_reroute', 'points': [], 'route_length_mm': None,
                'required_length_mm': None, 'margin_mm': None,
                'reason': '指定の曲げ半径では2つの曲線を置けない。別経路が必要。'}
    ux, uz = (end[0] - start[0]) / distance, (end[2] - start[2]) / distance
    high_y = max(start[1], end[1]) + p.straight_lead + r
    points = [list(start), [start[0], high_y - r, start[2]]]
    for i in range(1, 17):
        angle = math.pi - i * math.pi / 32
        points.append([start[0] + r * ux + r * ux * math.cos(angle),
                       high_y - r + r * math.sin(angle),
                       start[2] + r * uz + r * uz * math.cos(angle)])
    points.append([end[0] - r * ux, high_y, end[2] - r * uz])
    for i in range(1, 17):
        angle = math.pi / 2 - i * math.pi / 32
        points.append([end[0] - r * ux + r * ux * math.cos(angle),
                       high_y - r + r * math.sin(angle),
                       end[2] - r * uz + r * uz * math.cos(angle)])
    points.append(list(end))
    length = distance - 2 * r + math.pi * r + 2 * p.straight_lead + abs(end[1] - start[1])
    required = length + p.service_slack + p.length_basis_reserve
    return {'screening': 'within_assumed_budget' if required <= p.cable_length else 'over_budget',
            'points': points, 'route_length_mm': length, 'required_length_mm': required,
            'margin_mm': p.cable_length - required, 'rear_extent_mm': high_y,
            'straight_distance_mm': math.dist(start, end)}


def evaluate(p=None, switch_key='crs812', *, include_switch=True):
    p = p or LayoutParameters()
    p.validate()
    sw = SWITCHES[switch_key]
    nodes = {}
    for name, label, col, row in [('upper_left', '左上', -1, 1), ('upper_right', '右上', 1, 1),
                                  ('lower_right', '右下', 1, 0), ('lower_left', '左下', -1, 0)]:
        x = col * p.column_pitch / 2 + p.spark_pair_offset
        z = p.lower_base + row * p.row_pitch
        nodes[name] = box(name, label + 'のSpark', (x - 75, -150, z), (150, 150, 50.5), 'spark')
        nodes[name]['ports'] = [[x + p.spark_port_offset + side * p.spark_port_pitch / 2,
                                 0, z + p.spark_port_height] for side in (-1, 1)]
    switch_center_z = p.lower_base + p.spark_port_height + p.row_pitch / 2 + p.switch_z_offset
    switch = box('switch', sw['label'], (p.switch_x - sw['width'] / 2,
                 p.switch_face_y - sw['depth'], switch_center_z - sw['height'] / 2),
                 (sw['width'], sw['depth'], sw['height']), 'switch')
    switch['ports'] = [[p.switch_x + f * sw['width'], p.switch_face_y, switch_center_z]
                       for f in sw['port_fractions']]
    rings = []
    # 各台の2端子を重複なく使用し、端子はすべて背面側へ引き出す。
    edges = [('上段の横配線', 'upper_left', 1, 'upper_right', 0),
             ('右側の縦配線', 'upper_right', 1, 'lower_right', 1),
             ('下段の横配線', 'lower_right', 0, 'lower_left', 1),
             ('左側の縦配線', 'lower_left', 0, 'upper_left', 0)]
    for label, a, ap, b, bp in edges:
        start, end = nodes[a]['ports'][ap], nodes[b]['ports'][bp]
        rings.append({'label': label, 'from': a, 'to': b, 'start': start, 'end': end,
                      **route(start, end, p)})
    # 仮端子に対して最長経路が短くなる割当を全24通りで比較。
    node_names = list(nodes)
    choices = []
    for assignment in permutations(range(4)):
        cables = []
        for name, port in zip(node_names, assignment):
            candidates = []
            for start in nodes[name]['ports']:
                end = switch['ports'][port]
                result = route(start, end, p)
                if result['required_length_mm'] is not None:
                    candidates.append({'label': nodes[name]['label'] + ' → ' + sw['label'],
                                       'from': name, 'to': 'switch', 'switch_port': port,
                                       'start': start, 'end': end, **result})
            if not candidates:
                break
            cables.append(min(candidates, key=lambda c: c['required_length_mm']))
        if len(cables) == 4:
            choices.append(cables)
    connections = min(choices, key=lambda cs: (round(max(c['required_length_mm'] for c in cs), 8),
                       round(sum(c['required_length_mm'] for c in cs), 8),
                       tuple(c['switch_port'] for c in cs))) if choices else []
    # 端子位置が未確認なので、筐体の左右端・上下端の全組合せでも長さを評価。
    worst = []
    for node in nodes.values():
        candidates = [route(start, (p.switch_x + side * sw['width'] / 2, p.switch_face_y,
                      switch_center_z + vertical * sw['height'] / 2), p)
                      for start, side, vertical in product(node['ports'], (-1, 1), (-1, 1))]
        valid = [c for c in candidates if c['required_length_mm'] is not None]
        worst.append({'label': node['label'], **max(valid, key=lambda c: c['required_length_mm'])}
                     if valid else {'label': node['label'], 'screening': 'needs_reroute'})
    shelves = [box('lower_shelf', '下段の支持範囲', (-230, -150, p.lower_base - p.shelf_thickness),
                    (460, 150, p.shelf_thickness), 'shelf'),
               box('switch_shelf', '交換するスイッチ支持範囲', (-230, -387, switch['origin'][2] - p.shelf_thickness),
                    (460, 387, p.shelf_thickness), 'shelf'),
               box('upper_shelf', '上段の支持範囲', (-230, -150, p.lower_base + p.row_pitch - p.shelf_thickness),
                    (460, 150, p.shelf_thickness), 'shelf')]
    fans, fan_holders, fan_guards, controllers = [], [], [], []
    if p.include_fans:
        for name, node in nodes.items():
            size = 140
            x, z = node['origin'][0] + 75, node['origin'][2] + 25.25
            front = -150 - p.fan_front_gap - 27
            fan = box(name + '_fan', str(size) + 'mm・' + node['label'],
                      (x - size / 2, front, z - size / 2), (size, 27, size), 'fan')
            fan.update(size_mm=size, mounting_pitch_mm=124.5,
                       assigned_node=name)
            fans.append(fan)
            holder = box(name + '_fan_holder', node['label'] + 'の保持板範囲',
                         (x - size / 2 - 6, front - 4, z - size / 2 - 6),
                         (size + 12, 4, size + 12), 'fan_holder')
            holder.update(size_mm=size, mounting_pitch_mm=fan['mounting_pitch_mm'])
            fan_holders.append(holder)
            fan_guards.append(box(name + '_guard', node['label'] + 'のガード範囲',
                                  (x - size / 2, front - 8, z - size / 2), (size, 4, size), 'guard'))
            # 現行ケースの耳込み長さ100mm、幅39.4mm、つまみ込み厚さ29.5mm、
            # 共通ドック11mmを、100×44×43mmの収容範囲へ切り上げる。
            controllers.append(controller_box(name, z))

    if not include_switch:
        shelves = [s for s in shelves if s['name'] != 'switch_shelf']
    equipment = [*nodes.values(), *([switch] if include_switch else []), *fans,
                 *fan_holders, *fan_guards, *controllers]
    collisions = [[a['label'], b['label']] for i, a in enumerate(equipment + shelves)
                  for b in (equipment + shelves)[i + 1:] if overlaps(a, b)]
    envelope = box('rack_envelope', '共通枠の仮収容範囲', (-p.rack_width / 2, p.rack_front_y, 0),
                   (p.rack_width, p.rear_space - p.rack_front_y, p.rack_height), 'envelope')
    outside = [b['label'] for b in equipment + shelves if b['kind'] != 'controller' and any(
        b['origin'][i] < envelope['origin'][i] or b['origin'][i] + b['size'][i]
        > envelope['origin'][i] + envelope['size'][i] for i in range(3))]
    cables = rings + (connections if include_switch else [])
    rear_overflow = [c['label'] for c in cables if c.get('rear_extent_mm', 0) > p.rear_space]
    return {'purpose': '配置・配線の仮検討。印刷用設計ではない。', 'switch_key': switch_key,
            'include_switch': include_switch,
            'parameters': asdict(p), 'switch_spec': sw, 'nodes': nodes, 'switch': switch,
            'fans': fans, 'fan_holders': fan_holders, 'fan_guards': fan_guards, 'controllers': controllers,
            'adapter_cooling': {'adapter_count': 4, 'fan_size_mm': 120, 'fan_count': 2,
                                'placement': '最新の枠内統合案はoverview:spark-rackで確認。既存の別置きラックも保持。',
                                'source': 'models/adapter-rack/docs/設計と組立.md'},
            'shelves': shelves, 'envelope': envelope, 'controller_placement_basis': 'rack_candidate_datums.pyの内側位置を共用', 'mount_holes_committed': False, 'ring_cables': rings,
            'switch_cables': connections, 'switch_worst_cases': worst,
            'checks': {'equipment_and_shelf_collisions': collisions, 'outside_envelope': outside,
                       'rear_space_overflow': rear_overflow, 'switch_assignment_found': len(connections) == 4},
            'physical_validation': '未検証。端子位置・曲げ条件・公称長の基準は仮定。',
            'routing_limit': '曲線の中心線のみ。線径、ケーブル間干渉、余長の収納、実端子・吸排気・金具は未検証。'}
