"""本体連結案の設計条件を読み込み、正本から得た配置を検査する。"""
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
    pending, inventory, network, cable_basis, retention_basis, screwless_basis = [json.loads((ROOT / name).read_text(encoding='utf-8')) for name in REFERENCES]
    requirements = json.loads((ROOT / REQUIREMENTS).read_text(encoding='utf-8'))
    from spark_rack_parameters import body_frame_scene
    scene = body_frame_scene(p, pending, inventory, network)
    from spark_rack_parameters import body_frame_switch_plan
    scene['switch_retention'] = body_frame_switch_plan(scene, p)
    scene['switch_retention']['specification_basis'] = retention_basis
    from spark_rack_parameters import body_frame_routing
    scene['cable_management'] = body_frame_routing(scene, p)
    scene['cable_management']['assumption_reference'] = REFERENCES[3]
    scene['cable_management']['specification_basis'] = cable_basis
    scene['screwless_requirement'] = screwless_basis
    scene['requirements'] = requirements
    validate_requirements(scene)
    return scene


def validate_requirements(scene):
    """入力の設計条件と、実際の配置・機器・取付条件を照合する。"""
    from collections import Counter
    requirements=scene['requirements']
    sparks=[e for e in scene['equipment'] if e['kind']=='spark']
    if (len({e['origin'][0] for e in sparks})!=requirements['spark_columns']
            or len({e['origin'][2] for e in sparks})!=requirements['spark_rows']):
        raise ValueError('設計条件の本体の段数・列数と配置が一致しません')
    expected={}
    for record in requirements['maintained_equipment']:
        kind,quantity=record['kind'],record['quantity']
        if kind in expected or type(quantity) is not int or quantity<=0:
            raise ValueError('設計条件の機器の種類・個数が不正です')
        expected[kind]=quantity
        if 'model' in record and any(e.get('model')!=record['model'] for e in scene['equipment'] if e['kind']==kind):
            raise ValueError('設計条件の機器の型番と配置が一致しません: '+kind)
    actual=Counter(e['kind'] if e['kind']!='fan' else f'fan_{e["fan_size"]:.17g}' for e in scene['equipment'])
    if dict(actual)!=expected:
        raise ValueError('設計条件で維持する機器の種類・個数と配置が一致しません')
    for key,field in (('screws','assembly_screws'),('nuts','assembly_nuts')):
        if requirements['assembly_fasteners'][key]!=scene['screwless_requirement'][field]:
            raise ValueError('設計条件の組立用ビス・ナットの個数と一致しません')
    policy=requirements['fan_mounting']
    for fan in (e for e in scene['equipment'] if e['kind']=='fan'):
        if fan['mounting']!=policy['mode'] or policy['vertical'] and fan['axis'][2]!=0:
            raise ValueError('設計条件のファン取付姿勢と一致しません')


def validate_layout(scene):
    from collections import Counter
    equipment = scene['equipment']
    if any(scene['screwless_requirement'][key] != 0 for key in ('assembly_screws', 'assembly_nuts')):
        raise ValueError('組立用のビス・ナットは0にしてください')
    names = [e['name'] for e in equipment]
    if len(names) != len(set(names)):
        raise ValueError('機器名が重複しています')
    count = Counter(e['kind'] for e in equipment if e['kind'] != 'fan')
    count.update(f'fan_{e["fan_size"]:.17g}' for e in equipment if e['kind'] == 'fan')
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
    validate_requirements(scene)
    return {'status': 'passed', 'inventory': dict(count), 'equipment_collisions': collisions,
            'cable_routing': cable_report,
            'fan_mounting': '6個すべて前後・左右の軸方向へ正立固定',
            'scope': '参考外形の配置・機器個数・ファンの取付軸。実機の適合・冷却は含まない。'}
