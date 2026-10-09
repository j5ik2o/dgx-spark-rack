"""凹凸でつなぐ4台ラックの全体構想図。製造形状を定義しない。"""
from collections import Counter
from dataclasses import replace
from datetime import datetime
import hashlib
import json
from math import cos, sin, pi
from pathlib import Path
import shutil
import uuid
from zoneinfo import ZoneInfo
import sys

from four_node_layout import LayoutParameters, box, evaluate, overlaps
from rack_candidate_datums import DATUMS

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(__file__).parent
sys.path.insert(0, str(ROOT / 'models/adapter-rack/source'))
from adapter_rack_parameters import INPUTS as ADAPTER_INPUTS

PREVIOUS = ROOT / 'archive/spark-rack-overview-20261009-200723'


def adapter_layout():
    dimensions = {name: float(value.split()[0]) for name, value, _ in ADAPTER_INPUTS}
    adapters, fans, holders, controllers, mounts, cable_spaces = [], [], [], [], [], []
    width, depth, height = (dimensions[n] for n in ('AdapterLength', 'AdapterWidth', 'AdapterHeight'))
    # ACとUSB-Cの出口はY方向へ向け、左右のファンから外へ排気する構想。
    for column, x in enumerate((-90, 90)):
        for row, z in enumerate((39, 115)):
            name = f'adapter_{column}_{row}'
            adapters.append(box(name, 'ACアダプター・既存図面の参考寸法',
                                [x - width / 2, -363, z], [width, depth, height], 'adapter'))
            for y in (-393, -363 + depth):
                cable_spaces.append(box(name + '_cable_' + str(y), '電源端子側30mmの予約・実物未確認',
                                         [x - width / 2, y, z], [width, 30, height], 'cable_space'))
        left = x < 0
        fan = box('adapter_fan_' + str(column), '120mmファン・電源2個から側面へ排気する構想',
                  [-223 if left else 196, -379, 34], [27, 120, 120], 'fan')
        fan.update(size_mm=120, axis='x', face_coordinate=-223.7 if left else 223.7,
                   outward=-1 if left else 1, role='adapter')
        fans.append(fan)
        holder = box('adapter_fan_holder_' + str(column), '120mmファン保持範囲・固定は未設計',
                     [-227 if left else 223, -391, 22], [4, 144, 144], 'holder')
        holder.update(axis='x', opening_mm=114)
        holders.append(holder)
        controllers.append(box('adapter_controller_' + str(column), '電源用のファンコントローラー範囲',
                               [-193 if left else 150, -426, 45], [43, 44, 100], 'controller'))
    for y in (-376, -256):
        mounts.append(box('adapter_base_' + str(y), '底枠へ渡す電源支持梁・端の接合は未設計',
                          [-228, y, 12], [456, 8, 8], 'adapter_mount'))
        for x in (-180, 172):
            mounts.append(box('adapter_post_' + str((x, y)), '電源支持用の短い柱の参考外形',
                              [x, y, 20], [8, 8, 95], 'adapter_mount'))
    for z in (31, 107):
        for x in (-180, 172):
            mounts.append(box('adapter_side_' + str((x, z)), '電源支持段の奥行梁の参考外形',
                              [x, -368, z], [8, 112, 8], 'adapter_mount'))
        for y in (-353.475, -285.475):
            mounts.append(box('adapter_cross_' + str((y, z)), '電源底面を受ける支持桟の参考外形',
                              [-172, y, z], [344, 12, 8], 'adapter_mount'))
    separator = box('adapter_air_separator', '電源排気を本体の吸気から分ける参考仕切り',
                    [-180, -230, 28], [360, 2, 138], 'separator')
    return {'adapters': adapters, 'fans': fans, 'holders': holders, 'controllers': controllers,
            'mounts': mounts, 'cable_spaces': cable_spaces, 'separator': separator,
            'body_mm': [width, depth, height], 'connector_orientation': '前後Y方向',
            'cooling': '前側から取り込んだ空気を左右へ排気する候補。冷却は未検証。'}


def scene(mode):
    p = replace(LayoutParameters(), row_pitch=DATUMS.ring_pitch if mode == 'ring' else DATUMS.switch_pitch,
                shelf_thickness=8)
    report = evaluate(p, 'crs804' if mode == 'crs804' else 'crs812', include_switch=mode != 'ring')
    members = []

    def member(label, origin, size, family):
        item = box('member_' + str(len(members)), label, origin, size, 'frame')
        item['family'] = family
        members.append(item)

    # 造形分割の候補を外形で示す。全長部材の端の凹凸は未統合。
    for x in (-256, 228):
        for y in (-428, 64):
            z = 0
            for length in (105, 222, 93):
                member('柱・分割位置は候補', [x, y, z], [28, 28, length], 'column')
                z += length

    def cross(y, z):
        x = -228
        for length in (228, 228):
            member('横梁・端の凹凸で接続する構想', [x, y, z], [length, 28, 28], 'cross')
            x += length

    def side(x, z):
        y = -400
        for length in (180, 142, 142):
            member('奥行梁・二股と差し込みで接続する構想', [x, y, z], [28, length, 28], 'side')
            y += length

    for z in (0, 392):
        for y in (-428, 64):
            cross(y, z)
        for x in (-256, 228):
            side(x, z)
    for row in (0, 1):
        z = p.lower_base + row * p.row_pitch - 8 - 28
        for x in (-256, 228):
            side(x, z)
        for y in (-138, -12):
            cross(y, z)

    equipment, ducts, trays = [], [], []
    for node in report['nodes'].values():
        equipment.append(node)
        x = node['origin'][0] + 75
        z = node['origin'][2]
        trays.append(box(node['name'] + '_tray', node['label'] + 'のトレー外形・取付穴未確定',
                         [x - 79, -153, z - 8], [158, 156, 8], 'tray'))
        center_z = z + 25.25
        # 円から長方形へ移る導風の外形。通気口の実測前の参考。
        inlet, outlet = [], []
        for i in range(32):
            angle = 2 * pi * i / 32
            inlet.append([x + 68.4 * cos(angle), -175, center_z + 68.4 * sin(angle)])
            # 同じ角度の放射方向と長方形の交点を対応させる。
            factor = min(79.4 / max(abs(cos(angle)), 1e-12),
                         29.65 / max(abs(sin(angle)), 1e-12))
            outlet.append([x + factor * cos(angle), -152, center_z + factor * sin(angle)])
        ducts.append({'label': node['label'] + 'へ風を寄せる参考形状', 'inlet': inlet, 'outlet': outlet})
    for fan in report['fans']:
        fan.update(axis='y', role='spark')
    equipment.extend(report['fans'])
    holders = []
    for fan in report['fans']:
        x, y, z = fan['origin']
        holder = box(fan['name'] + '_holder', '140mmファン保持部の外形・穴位置未確定',
                     [x - 18, y - 4, z - 6], [176, 4, 152], 'holder')
        holder.update(axis='y', opening_mm=132)
        holders.append(holder)
    equipment.extend(report['controllers'])
    feet = [box('foot_' + str(i), '脚の外形', [x, y, -8], [28, 28, 8], 'foot')
            for i, (x, y) in enumerate(((-256, -428), (228, -428), (-256, 64), (228, 64)))]
    power = adapter_layout()
    equipment.extend(power['adapters'] + power['fans'] + power['controllers'])
    holders.extend(power['holders'])
    cables = report['ring_cables'] if mode == 'ring' else report['switch_cables']
    if mode != 'ring':
        equipment.append(report['switch'])
    counts = dict(Counter(item['family'] for item in members))
    assert counts == {'column': 12, 'cross': 16, 'side': 24}
    return {'mode': mode, 'members': members, 'equipment': equipment, 'holders': holders,
            'trays': trays, 'ducts': ducts, 'feet': feet, 'cables': cables,
            'frame_outer_mm': [512, 520, 420], 'controller_width_mm': 512,
            'frame_inner_width_mm': 456, 'adapter_layout': power,
            'member_counts': counts, 'lower_base_mm': p.lower_base, 'row_pitch_mm': p.row_pitch,
            'manufacturing_geometry': False, 'whole_assembly_validated': False,
            'switch_support_generated': False, 'mount_holes_committed': False,
            'switch_note': report['switch_spec']['dimension_note']}


def check_scene(value):
    # 枠と機器は外形箱で検査。円形開口、導風内部、実端子・操作空間は対象外。
    boxes = value['members'] + value['feet'] + value['equipment'] + value['trays'] + value['holders']
    boxes += value['adapter_layout']['mounts'] + [value['adapter_layout']['separator']]
    collisions = [[a['name'], b['name']] for i, a in enumerate(boxes) for b in boxes[i+1:] if overlaps(a, b)]
    outside = [b['name'] for b in boxes if any(b['origin'][i] < [-256, -428, -8][i] - 1e-8
               or b['origin'][i] + b['size'][i] > [256, 92, 420][i] + 1e-8 for i in range(3))]
    cable_conflicts = []
    radius = 5  # 仮のケーブル外径10mm。実物のコネクターを表す値ではない。
    for cable in value['cables']:
        for point in cable['points']:
            probe = box('cable_probe', 'ケーブルの仮外径', [v-radius for v in point], [radius*2]*3, 'probe')
            for other in boxes:
                if other['name'] in (cable['from'], cable['to']):
                    continue
                if overlaps(probe, other):
                    cable_conflicts.append([cable['label'], other['name']])
    reserved = [[a['name'], b['name']] for a in value['adapter_layout']['cable_spaces']
                for b in boxes if b['kind'] not in ('adapter', 'adapter_mount') and overlaps(a, b)]
    result = {'outer_box_collisions': collisions, 'outside_frame_volume': outside,
              'cable_reference_tube_collisions': sorted({tuple(c) for c in cable_conflicts}),
              'adapter_connector_reservation_conflicts': reserved,
              'scope': '外形箱・仮外径10mmの配線・電源端子側30mmの予約。接合と実コネクターは未検証'}
    if collisions or outside or cable_conflicts or reserved:
        raise ValueError(json.dumps(result, ensure_ascii=False))
    return result


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def build():
    stamp = datetime.now(ZoneInfo('Asia/Tokyo')).strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8]
    out = ROOT / 'build/spark-rack/candidate-overview' / stamp
    out.mkdir(parents=True, exist_ok=False)
    # 実際に検査済みの短い接合図を使う。以前の全体案の形状は読み込まない。
    coupon = ROOT / 'models/spark-rack/reference/joint-illustrations-20261009'
    pictures = ('corner-assembled.png', 'corner-insertion-order.png', 'straight-assembled.png')
    paths = [SOURCE / name for name in ('build_rack_candidate_overview.py', 'rack_candidate_overview.html',
                                       'four_node_layout.py', 'rack_candidate_datums.py')]
    paths += [ROOT / 'models/spark-rack/reference/pending-mount-measurements.json',
              ROOT / 'models/spark-rack/reference/four-node-layout-assumptions.json',
              ROOT / 'models/spark-rack/reference/prepared-fans-and-cable.json',
              ROOT / 'models/adapter-rack/source/adapter_rack_parameters.py',
              ROOT / 'tests/check_rack_candidate_overview.cjs',
              PREVIOUS / 'overview-report.json', PREVIOUS / 'manifest.json']
    paths += [coupon / name for name in (*pictures, 'manifest.json', 'validation.json')]
    hashes = {str(p.relative_to(ROOT)): digest(p) for p in paths}
    data = {mode: scene(mode) for mode in ('ring', 'crs812', 'crs804')}
    checks = {mode: check_scene(value) for mode, value in data.items()}
    previous = json.loads((PREVIOUS / 'overview-report.json').read_text())
    comparison = {'previous_frame_mm': [520, 530, 420], 'current_frame_mm': [512, 520, 420],
                  'previous_installation_width_mm': 618, 'current_installation_width_mm': 512,
                  'frame_floor_area_reduction_percent': (1 - (512*520)/(520*530))*100,
                  'installation_rectangle_reduction_percent': (1 - (512*520)/(618*530))*100,
                  'note': '設置長方形の比較。線材・突出した実コネクター・取付耳は未確定。'}
    write_json(out / 'overview-report.json', data)
    write_json(out / 'comparison.json', comparison)
    shutil.copyfile(PREVIOUS / 'overview-report.json', out / 'previous-overview-report.json')
    template = (SOURCE / 'rack_candidate_overview.html').read_text(encoding='utf-8')
    assert template.count('__OVERVIEW_DATA__') == 1
    (out / 'rack-candidate-overview.html').write_text(
        template.replace('__OVERVIEW_DATA__', json.dumps({'current': data, 'previous': previous,
                                                         'comparison': comparison}, ensure_ascii=False).replace('<', '\\u003c')),
        encoding='utf-8')
    for name in pictures:
        shutil.copyfile(coupon / name, out / name)
    write_json(out / 'validation.json', {'status': 'passed', 'scope': '構想図の外形箱、共通座標、仮の配線経路',
        'checks': {mode: {'frame_members': len(value['members']),
                          'sparks': sum(i['kind'] == 'spark' for i in value['equipment']),
                          'fans_140mm': sum(i['kind'] == 'fan' and i['size_mm'] == 140 for i in value['equipment']),
                          'fans_120mm': sum(i['kind'] == 'fan' and i['size_mm'] == 120 for i in value['equipment']),
                          'controllers': sum(i['kind'] == 'controller' for i in value['equipment'])}
                   for mode, value in data.items()},
        'outer_geometry_checks': checks,
        'whole_assembly_and_joined_geometry': '未検証。外形図を接合済みの製造形状として扱わない',
        'physical_fit_strength_cooling': '未検証。試験片の印刷は後回し'})
    assert hashes == {str(p.relative_to(ROOT)): digest(p) for p in paths}
    write_json(out / 'manifest.json', {'status': 'generated', 'purpose': '設計変更後の全体構想図',
        'sources_sha256': hashes, 'outputs_sha256': {p.name: digest(p) for p in sorted(out.iterdir())},
        'manufacturing_geometry': False})
    return out


if __name__ == '__main__':
    print(build())
