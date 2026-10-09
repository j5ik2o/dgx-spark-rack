"""次案の共通基準。未測定の取付位置を製造用の梁穴へ変換しない。"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class CandidateDatums:
    lower_base: float = 72
    ring_pitch: float = 160
    switch_pitch: float = 220
    frame_inner_width: float = 456
    frame_outer_width: float = 512
    frame_front_y: float = -428
    frame_rear_y: float = 92
    frame_height: float = 420
    section: float = 28
    controller_inner_x: float = 184
    controller_outer_x: float = 227
    controller_front_y: float = -239
    controller_depth: float = 44
    controller_length: float = 100


DATUMS = CandidateDatums()


def controller_box(name, center_z):
    left = name.endswith('left')
    labels = {'upper_left': '左上', 'upper_right': '右上', 'lower_left': '左下', 'lower_right': '右下'}
    return {'name': name + '_controller', 'label': labels[name] + 'のファンコントローラー範囲',
            'origin': [-DATUMS.controller_outer_x if left else DATUMS.controller_inner_x,
                       DATUMS.controller_front_y, center_z - DATUMS.controller_length / 2],
            'size': [DATUMS.controller_outer_x - DATUMS.controller_inner_x,
                     DATUMS.controller_depth, DATUMS.controller_length], 'kind': 'controller'}


def require_spark_mount_measurements(record):
    spark = record.get('spark', {})
    required = ('port_centers_from_left_and_bottom_mm', 'feet_contact_areas_mm', 'adopted_pair_offset_mm')
    missing = [name for name in required if spark.get(name) is None]
    if missing:
        raise ValueError('梁のファン・トレー取付穴は実測前に生成しません: ' + ', '.join(missing))
    if len(spark['port_centers_from_left_and_bottom_mm']) != 2 or not spark['feet_contact_areas_mm']:
        raise ValueError('端子2個と足の接触面の測定値が必要です')
    if not math.isfinite(spark['adopted_pair_offset_mm']):
        raise ValueError('採用する横ずれは有限の値にしてください')
    return spark


def require_switch_measurements(record, model):
    switch = record.get('switches', {}).get(model, {})
    required = ('overall_width_with_ears_mm', 'adopted_depth_mm')
    if any(switch.get(name) is None for name in required):
        raise ValueError('スイッチ支持板は耳込み幅と奥行が未確定です')
    if any(not math.isfinite(switch[name]) or switch[name] <= 0 for name in required):
        raise ValueError('スイッチの耳込み幅と奥行は正の測定値が必要です')
    if switch['overall_width_with_ears_mm'] > DATUMS.frame_inner_width:
        raise ValueError(f'耳込み幅が内のり{DATUMS.frame_inner_width:g}mmを超えています。枠幅か支持方式の見直しが必要です')
    return switch
