"""4台用ラックの部品検討案。寸法はmm、実物の強度・適合は未検証。"""
from dataclasses import asdict, dataclass, replace
from collections import Counter
import math

from four_node_layout import LayoutParameters, evaluate


@dataclass(frozen=True)
class StructureParameters:
    section: float = 28
    tray_thickness: float = 8
    splice_length: float = 56
    splice_wall: float = 4
    splice_base: float = 6
    fit_clearance: float = 0.3
    bolt_hole: float = 4.5
    bolt_head: float = 8.5
    tray_width: float = 158
    tray_depth: float = 156
    tray_border: float = 18
    tray_rib: float = 12
    tray_lip: float = 3
    fan_plate_width: float = 176
    fan_plate_height: float = 152
    fan_plate_thickness: float = 4
    fan_opening: float = 132
    fan_arm_offset: float = 78
    usable_print_size: float = 246
    column_lengths: tuple = (105, 222, 93)
    cross_lengths: tuple = (250, 214)
    side_lengths: tuple = (190, 142, 142)

    def validate(self):
        if sum(self.column_lengths) != 420 or sum(self.cross_lengths) != 464 or sum(self.side_lengths) != 474:
            raise ValueError('分割部材の長さが共通枠の寸法に一致しません')
        if max(*self.column_lengths, *self.side_lengths, self.fan_plate_width,
               (max(self.cross_lengths) + self.section) / math.sqrt(2)) > self.usable_print_size:
            raise ValueError('造形範囲を超える部材があります')
        if not 0 < self.fit_clearance < 1:
            raise ValueError('接続金具の片側隙間は0〜1mmの範囲にしてください')
        if self.fan_arm_offset - 5 <= 70 or self.fan_arm_offset + 5 > self.fan_plate_width / 2:
            raise ValueError('ファン保持部の腕がファン外形や保持板と整合しません')


def layout(mode, p):
    lp = replace(LayoutParameters(), shelf_thickness=p.tray_thickness, lower_base=72, spark_pair_offset=-30,
                 rack_width=520, rack_height=420, rack_front_y=-420, rear_space=110,
                 row_pitch=160 if mode == 'ring' else 220)
    report = evaluate(lp, 'crs812' if mode == 'ring' else mode, include_switch=mode != 'ring')
    # 部品設計では制御ケースを側面の外へ置き、支持梁との重なりを解消する。
    for controller in report['controllers']:
        controller['origin'][0] = -309 if controller['name'].startswith(('upper_left', 'lower_left')) else 277
        controller['size'][0] = 32
        controller['origin'][1] = -294
    return report


def instances(mode, p=None):
    p = p or StructureParameters()
    p.validate()
    report = layout(mode, p)
    lp = report['parameters']
    parts = []

    def add(part, label, origin, rotation=(), group='frame'):
        parts.append({'id': 'Part' + str(len(parts) + 1), 'part': part, 'label': label,
                      'origin': list(origin), 'rotation': list(rotation), 'group': group})

    # 四隅の柱は全体で4本。部材分割は造形のためで、ラックの増設単位ではない。
    for x in (-246, 246):
        for y in (-406, 96):
            angle = 0 if x < 0 and y < 0 else 90 if x > 0 and y < 0 else 180 if x > 0 else 270
            add('foot', '四隅の着座パッド', (x, y, 0), [('z', angle)])
            z = 0
            for index, length in enumerate(p.column_lengths):
                add('column_' + str(index + 1), '共通柱', (x + 14, y, z), [('y', -90)])
                z += length
                if index < 2:
                    add('splice', '柱の接続金具', (x + 14, y, z), [('y', -90)], 'joint')

    def cross(y, bottom, label):
        x = -232
        for index, length in enumerate(p.cross_lengths):
            add('cross_' + str(index + 1), label, (x, y, bottom))
            x += length
            if index == 0:
                add('splice', '横梁の接続金具', (x, y, bottom), group='joint')

    def side(x, bottom, label):
        y = -392
        for index, length in enumerate(p.side_lengths):
            add('side_' + str(index + 1), label, (x, y, bottom), [('z', 90)])
            y += length
            if index < 2:
                add('splice', '奥行梁の接続金具', (x, y, bottom), [('z', 90)], 'joint')

    def side_straps(bottom):
        add('corner_single', '側梁と柱の固定板', (246, -392, bottom), [('z', 90)], 'joint')
        add('corner_single', '側梁と柱の固定板', (-246, -392, bottom + 28), [('z', 90), ('x', 180)], 'joint')
        add('corner_single', '側梁と柱の固定板', (246, 82, bottom + 28), [('z', 90), ('y', 180)], 'joint')
        add('corner_single', '側梁と柱の固定板', (-246, 82, bottom), [('z', 270)], 'joint')

    for bottom in (0, 392):
        cross(-406, bottom, '外周の横梁')
        cross(96, bottom, '外周の横梁')
        for x in (-246, 246):
            side(x, bottom, '外周の奥行梁')
        side_straps(bottom)
        add('corner_double', '横梁と柱の固定板', (-232, -406, bottom), group='joint')
        add('corner_double', '横梁と柱の固定板', (232, -406, bottom + 28), [('y', 180)], 'joint')
        add('corner_double', '横梁と柱の固定板', (-232, 96, bottom + 28), [('x', 180)], 'joint')
        add('corner_double', '横梁と柱の固定板', (232, 96, bottom), [('z', 180)], 'joint')

    for row in (0, 1):
        top = lp['lower_base'] + row * lp['row_pitch'] - p.tray_thickness
        bottom = top - p.section
        for x in (-246, 246):
            side(x, bottom, '本体支持段の奥行梁')
        side_straps(bottom)
        for y in (-138, -12):
            cross(y, bottom, '本体を支える横梁')
            add('end_shoe_left', '横梁を側梁へ固定する受け', (-232, y, bottom), group='joint')
            add('end_shoe_right', '横梁を側梁へ固定する受け', (232, y, bottom), group='joint')

    for name, node in report['nodes'].items():
        cx = node['origin'][0] + 75
        base = node['origin'][2]
        center_z = base + 25.25
        add('tray', node['label'] + 'の通気トレー', (cx, 0, base - p.tray_thickness), group='support')
        add('fan_carrier', node['label'] + 'の140mm保持部', (cx, 0, center_z), group='fan')
        left = name.endswith('left')
        # 独自の反射を避け、右手系の共通ドック座標を指定して配置する。
        pose = {'u': [0, 0, 1], 'v': [0, 1 if left else -1, 0], 'w': [-1 if left else 1, 0, 0]}
        for part, face in [('controller_support', 260), ('controller_dock', 269)]:
            add(part, node['label'] + 'の制御ケース取付部', (-face if left else face, -272, center_z), group='controller')
            parts[-1]['basis'] = pose

    counts = dict(Counter(item['part'] for item in parts))
    return {'mode': mode, 'layout': report, 'instances': parts, 'part_counts': counts,
            'parameters': asdict(p), 'frame_dimensions_mm': [520, 530, 420],
            'hardware': {'M4x45_socket_screws': 32 * 4 + 16 * 3 - 8 + 8 * 4 + 8,
                         'M4x40_socket_screws': 8 * 2, 'M4x35_socket_screws': 24,
                         'M4x55_socket_screws': 8, 'M4x45_90deg_countersunk_screws': 8,
                         'M4x45_fan_bolts': 16, 'M4x25_socket_screws': 8,
                         'M3x12_90deg_countersunk_screws': 8},
            'physical_validation': '未検証。試作での適合・強度・振動・冷却確認が必要。',
            'switch_support': '中央のスイッチ支持段は取付穴位置のみ予約。支持板と耐荷重は別設計。'}
