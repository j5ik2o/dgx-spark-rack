"""上下のSparkの間へ置く遠隔操作機器の棚・前面板・予約。形状候補で製造用ではない。

上部専用段の案では中央用の受け梁を外したため、上下段の間が空く。そこへ棚を差し込み、
前にComet Pro、後ろに4入力の切替器を置く。前面の隙間は窓付きの板でふさぐ。
Comet Proは棚から前へ延ばした薄い載せ台に置き、画面を前面板の窓のすぐ後ろへ出す。
中央配置ではスイッチがこの高さを使うため、この棚は置けない。
"""
from dataclasses import asdict
import json
import math
from pathlib import Path

from four_node_layout import box
from spark_rack_parameters import RemoteConsoleParameters

RECORD = Path(__file__).resolve().parents[1] / 'reference/pending-mount-measurements.json'


def devices():
    record = json.loads(RECORD.read_text(encoding='utf-8'))['remote_console']
    kvm = record['kvm_switch']
    return {'comet': list(record['comet_pro']['body_mm']),
            'kvm': list(kvm['body_mm'] or kvm['provisional_envelope_mm']),
            'kvm_measured': kvm['body_mm'] is not None, 'record': record}


def accessory_layout(p, scene, q=None):
    """sceneは同じ寸法で作ったfixed_layoutの結果。棚の高さと機器の位置をここで決める。"""
    q = q or RemoteConsoleParameters()
    q.validate()
    info = devices()
    cw, cd, ch = info['comet']
    kw, kd, kh = info['kvm']
    carriers, beams = scene['carriers'], scene['cross_beams']
    lower_top = max(c['origin'][2] + c['size'][2] for c in carriers if c['name'].startswith('lower_'))
    # 前面を通る上限は、上段ファン保持部と、その下の横梁の下面。
    upper = [c for c in carriers if c['name'].startswith('upper_')]
    upper += [b for b in beams if b['name'] == 'fan_rail_1']
    front_top = min(b['origin'][2] for b in upper)
    storage_top = max(s['origin'][2] + s['size'][2] for s in scene['cable_storage_spaces'])
    # 棚はファンの後ろから始める。上面は下段ファン保持部より上に置き、機器を前へ通せる高さにする。
    top = math.ceil(max(lower_top + p.fit_clearance, storage_top + p.fit_clearance + q.shelf_thickness) - 1e-9)
    shelf_z = top - q.shelf_thickness
    comet_z = top + q.sled_thickness
    if comet_z + ch + q.comet_top_margin > front_top - p.fit_clearance:
        raise ValueError('Comet Proと手の余裕が上段ファンの横梁へ届きます')
    upper_shelf_bottom = p.upper_base - p.tray_thickness - 12
    if top + kh + q.kvm_hand_margin > upper_shelf_bottom:
        raise ValueError('切替器と手の余裕が上段の固定棚へ届きます')
    inner = p.inner_width / 2
    panel_y = p.front_face_y
    front = p.fan_front_y + p.fan_depth + q.front_gap
    z0, z1 = lower_top + p.fit_clearance, front_top - p.fit_clearance
    half = q.panel_center_half_width
    objects = [box('accessory_shelf', '遠隔操作機器の棚・左右の側枠へ差し込む',
                   [-inner, front, shelf_z], [p.inner_width, p.rear_y - front, q.shelf_thickness], 'accessory_shelf')]
    for name, label, x0, x1 in (('mid_panel_left', '上下のファンの間を閉じる前面板・左', -inner, -half),
                                ('mid_panel_center', 'Comet Proの画面を見せる窓付きの前面板・外して交換', -half, half),
                                ('mid_panel_right', '上下のファンの間を閉じる前面板・右', half, inner)):
        objects.append(box(name, label, [x0, panel_y, z0], [x1 - x0, q.panel_thickness, z1 - z0], 'mid_panel'))
    # 画面を窓のすぐ後ろへ出す。載せ台の前の部分は下段ファン保持部の上を片持ちで延びる。
    comet_y = panel_y + q.panel_thickness + p.fit_clearance
    comet = box('remote_kvm', 'GL.iNet Comet Pro・前面にタッチ画面', [-cw / 2, comet_y, comet_z], [cw, cd, ch], 'accessory')
    sled_half = cw / 2 + 1
    objects.append(box('remote_kvm_sled', 'Comet Proの載せ台・棚から前へ延びる',
                       [-sled_half, comet_y, top], [2 * sled_half, cd, q.sled_thickness], 'accessory_shelf'))
    ky0 = q.kvm_rear_face_y - kd
    kvm = box('kvm_switch', '4入力1出力のHDMI・USB切替器' + ('' if info['kvm_measured'] else '・外形は仮の箱'),
              [-kw / 2, ky0, top], [kw, kd, kh], 'accessory')
    connectors = [
        box('remote_kvm_rear_cables', 'Comet Proの背面の配線と曲げ', [-cw / 2, comet_y + cd, comet_z],
            [cw, q.comet_rear_cable_space, ch], 'connector_space'),
        box('kvm_switch_front_connectors', '切替器の前面の端子と配線', [-kw / 2, ky0 - q.kvm_front_connector_space, top],
            [kw, q.kvm_front_connector_space, kh], 'connector_space'),
        box('kvm_switch_rear_connectors', '切替器の背面の端子と配線・枠の外へ出る', [-kw / 2, q.kvm_rear_face_y, top],
            [kw, q.kvm_rear_connector_space, kh], 'connector_space')]
    services = [
        dict(box('remote_kvm_removal', '中央の前面板を外し、Comet Proを前へ引き出す',
                 [-cw / 2 - q.comet_side_margin, p.front_y - 110, comet_z],
                 [cw + 2 * q.comet_side_margin, comet_y + cd - (p.front_y - 110), ch + q.comet_top_margin], 'service'),
             moving=['remote_kvm', 'mid_panel_center']),
        dict(box('kvm_switch_removal', '切替器を背面へ引き出す',
                 [-kw / 2 - q.kvm_hand_margin, ky0, top],
                 [kw + 2 * q.kvm_hand_margin, p.rear_y + kd - ky0, kh + q.kvm_hand_margin], 'service'),
             moving=['kvm_switch'])]
    return {'parameters': asdict(q), 'shelf_z': shelf_z, 'support_z': top, 'comet_z': comet_z,
            'lower_carrier_top_mm': lower_top, 'front_top_limit_mm': front_top,
            'storage_top_mm': storage_top, 'front_y': front, 'panel_y': panel_y, 'panel_z': [z0, z1],
            'screen_recess_mm': comet_y - (panel_y + q.panel_thickness),
            'objects': objects, 'equipment': [comet, kvm], 'connector_spaces': connectors,
            'service_spaces': services, 'kvm_measured': info['kvm_measured'],
            'window': {'center': [0, comet_z + ch / 2], 'size': [cw - 2 * q.window_margin, ch - 2 * q.window_margin]},
            'thermal_reason': 'Comet Proの動作温度は0〜40℃。Sparkと電源の排気が流れない前側へ置き、前面の窓と溝から室内の空気に触れさせる。温度は未測定。',
            'wifi_note': '炭素繊維入りの素材の前面板は電波を弱める可能性がある。有線接続を基本にする。',
            'open_items': ['切替器の実寸・電源・端子の面', 'SparkのHDMIとUSBの端子位置とケーブル長',
                           'Comet Proと切替器、CRS812の交流電源（電源タップの置き場）',
                           'Comet Proのキーボード入力で切替器を切り替えられるか'],
            'manufacturing_geometry': False, 'physical_validation': False}


def check_accessories(scene):
    """棚の機器の交換経路と配線の予約が、固定物に当たらないかを調べる。"""
    acc = scene['accessories']
    solids = scene['equipment'] + scene['carriers'] + scene['trays'] + scene['power_trays']
    solids += [scene['separator'], scene['control_panel']] + scene['cross_beams'] + acc['objects']
    for key in ('switch_bay', 'finish'):
        if scene.get(key):
            solids += scene[key]['objects']
    from four_node_layout import overlaps
    service = [[s['name'], b['name']] for s in acc['service_spaces'] for b in solids + scene['cable_storage_spaces']
               if b['name'] not in s['moving'] and overlaps(s, b)]
    owners = {'remote_kvm_rear_cables': 'remote_kvm', 'kvm_switch_front_connectors': 'kvm_switch',
              'kvm_switch_rear_connectors': 'kvm_switch'}
    connectors = [[c['name'], b['name']] for c in acc['connector_spaces'] for b in solids
                  if b['name'] != owners[c['name']] and overlaps(c, b)]
    return {'accessory_service_obstructions': service, 'accessory_connector_obstructions': connectors}
