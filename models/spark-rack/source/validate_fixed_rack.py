"""参考形状の干渉と交換経路を検査し、未完成の機構は別に記録する。"""
import FreeCAD as App
from fixed_rack_geometry import box, cylinder
from fixed_rack_layout import fixed_layout, check_fixed_layout


def horizontal_contact(lower, upper, height):
    def faces(shape, normal_z):
        result = []
        for f in shape.Faces:
            if abs(f.BoundBox.ZMin - height) > 1e-6 or abs(f.BoundBox.ZMax - height) > 1e-6:
                continue
            u0, u1, v0, v1 = f.ParameterRange
            if f.normalAt((u0 + u1) / 2, (v0 + v1) / 2).z * normal_z > .99:
                result.append(f)
        return result
    return sum(a.common(b).Area for a in faces(lower, 1) for b in faces(upper, -1))


def support_contacts(model):
    items = model['parts']
    metadata = model['supports']
    rows = []
    for assembly in metadata['assemblies']:
        name = assembly['name']
        parts = [i['shape'] for i in items if i['name'].startswith(name + '_')]
        for tray in model['scene']['trays'] + model['scene']['power_trays']:
            if abs(tray['origin'][2] - assembly['support_z']) > 1e-6:
                continue
            shape = next(i['shape'] for i in items if i['name'] == tray['name'])
            area = sum(horizontal_contact(s, shape, assembly['support_z']) for s in parts)
            if area < 500:
                raise ValueError('トレーと固定支持面の接触が不足しています: ' + tray['name'])
            rows.append({'target': tray['name'], 'support': name, 'area_mm2': area})
        for socket in metadata['socket_envelopes']:
            if not socket['name'].startswith(name + '_'):
                continue
            panels = [i['shape'] for i in items if i['name'].startswith('side_' + socket['side'] + '_')]
            area = sum(horizontal_contact(panel, s, socket['bearing_z']) for panel in panels for s in parts)
            if area < 100:
                raise ValueError('固定棚から側壁への受け面が不足しています: ' + socket['name'])
            rows.append({'target': name, 'support': socket['name'], 'area_mm2': area})
        # 上部専用段：可動トレーを床で受け、スイッチの参考外形をトレーで受ける。
        for target in assembly.get('moving_parts', []):
            shape = next(i['shape'] for i in items if i['name'] == target)
            area = sum(horizontal_contact(s, shape, assembly['support_z']) for s in parts)
            if area < 500:
                raise ValueError('トレーと固定支持面の接触が不足しています: ' + target)
            rows.append({'target': target, 'support': name, 'area_mm2': area})
        carried = assembly.get('carried')
        if carried:
            shape = next(i['shape'] for i in model['references'] if i['name'] == carried['target'])
            for support in carried['supports']:
                tray = next(i['shape'] for i in items if i['name'] == support)
                area = horizontal_contact(tray, shape, carried['z'])
                if area < 500:
                    raise ValueError('機器とトレーの接触が不足しています: ' + support)
                rows.append({'target': carried['target'], 'support': support, 'area_mm2': area})
    return {'status': 'passed', 'contacts': rows,
            'scope': 'トレーから固定支持棚・支持床、側壁の水平な受け面へ荷重を渡す面の存在。強度と長期荷重は未検証。'}


def overlap(a, b):
    # ここは交差検査前の保守的な除外だけなので、精密な最小外形は不要。
    aa, bb = a.BoundBox, b.BoundBox
    if any(min(getattr(aa, axis + 'Max'), getattr(bb, axis + 'Max')) -
           max(getattr(aa, axis + 'Min'), getattr(bb, axis + 'Min')) <= 1e-6 for axis in 'XYZ'):
        return 0.0
    local_a, local_b = a.copy(), b.copy()
    local_a.Placement = App.Placement()
    local_b.Placement = a.Placement.inverse().multiply(b.Placement)
    return local_a.common(local_b).Volume


def grille_openings(model):
    p = model['parameters']
    by_name = {i['name']: i['shape'] for i in model['parts']}
    openings = []

    def measure(name, origin, radius, axis):
        probe = cylinder(origin, radius, 4, axis)
        covered = probe.common(by_name[name]).Volume
        openings.append({'part': name, 'bare_circle_area_mm2': probe.Volume / 4,
                         'open_area_mm2': (probe.Volume - covered) / 4,
                         'open_fraction': 1 - covered / probe.Volume})

    for node in model['scene']['nodes']:
        x = node['origin'][0] + p.spark_width / 2
        z = node['origin'][2] + p.spark_height / 2
        measure(node['name'] + '_carrier', [x, p.front_face_y, z], p.fan_opening / 2, [0, 1, 0])
    for right in (False, True):
        x = p.width / 2 - 4 if right else -p.width / 2
        measure('power_carrier_' + ('right' if right else 'left'), [x, -120, 88], 57, [1, 0, 0])
    return {'openings': openings,
            'scope': '一体格子による円開口面積の減少。ファン本体や風量・圧力損失・騒音の評価を含まない。'}


def exchange_envelopes(model):
    """候補の交換方向を、移動部品ごとの保守的な箱で確認する。"""
    p = model['parameters']
    items = model['parts'] + model['references']
    by_name = {i['name']: i for i in items}
    door_names = {i['name'] for i in items if i['name'].startswith(('control_panel_', 'case_', 'dock_'))}
    failures = []
    checks = []

    def inspect(label, envelope, moving_names, obstacles):
        for name, shape in obstacles:
            if name not in moving_names and overlap(envelope, shape) > .001:
                failures.append([label, name])
        checks.append(label)

    fixed = [(i['name'], i['shape']) for i in items]
    reserve = model['scene']['control_door_sweep']
    inspect('制御器取付面の90度開放予約', box(reserve['origin'], reserve['size']), door_names, fixed)
    opened = []
    for name, shape in fixed:
        s = shape.copy()
        if name in door_names:
            s.rotate(App.Vector(-180, p.controller_origin_y + 3, 0), App.Vector(0, 0, 1), -90)
        opened.append((name, s))
    for col in range(2):
        for row in range(2):
            name = f'power_{col}_{row}'
            moving = {name, name + '_tray'}
            bounds = [by_name[n]['shape'].optimalBoundingBox(False) for n in moving]
            xlo, xhi = min(b.XMin for b in bounds) - 12, max(b.XMax for b in bounds) + 12
            ylo, yhi = min(b.YMin for b in bounds), max(b.YMax for b in bounds)
            zlo, zhi = min(b.ZMin for b in bounds), max(b.ZMax for b in bounds) + 12
            if row == 0:
                ylo = p.front_y - 110
            else:
                yhi = p.rear_y + 110
            inspect(name + ('を前方へ' if row == 0 else 'を背面へ'),
                    box([xlo, ylo, zlo], [xhi - xlo, yhi - ylo, zhi - zlo]), moving, opened)
    for node in model['scene']['nodes']:
        name = node['name']
        moving = {name + '_fan', name + '_carrier'}
        for part in moving:
            b = by_name[part]['shape'].optimalBoundingBox(False)
            inspect(part + 'を前方へ', box([b.XMin, p.front_y - 110, b.ZMin],
                    [b.XLength, b.YMax - (p.front_y - 110), b.ZLength]), moving, fixed)
    for col, right in enumerate((False, True)):
        moving = {'power_fan_' + str(col), 'power_carrier_' + ('right' if right else 'left')}
        for part in moving:
            b = by_name[part]['shape'].optimalBoundingBox(False)
            x = b.XMin if right else b.XMin - 80
            inspect(part + 'を側面へ', box([x, b.YMin, b.ZMin], [b.XLength + 80, b.YLength, b.ZLength]), moving, fixed)
    front_service = None
    bay = model.get('switch_bay')
    if bay is not None:
        space = model['scene']['conditional_service_spaces'][0]
        envelope = box(space['origin'], space['size'])
        blocked = sorted({name for name, shape in fixed if name != 'switch' and overlap(envelope, shape) > .001})
        front_service = {'name': space['name'], 'required': bay['front_service_required'],
                         'dependency': bay['front_service_dependency'], 'obstructions': blocked,
                         'status': 'passed' if not blocked else 'blocked'}
        if bay['front_service_required']:
            failures += [[space['name'], name] for name in blocked]
            checks.append('スイッチのラック前側の面から部品を前へ出す仮の経路')
    if failures:
        raise ValueError('交換予約の形状干渉: ' + str(failures))
    result = {'status': 'passed', 'checked': checks,
              'scope': '接続を外した機器、開いた取付面、移動方向の外形箱。ヒンジ、留め具、配線、実際の手の操作は未検証。'}
    if front_service is not None:
        result['switch_front_service'] = front_service
    return result


def validate(model):
    p = model['parameters']
    p.validate()
    records = {}
    for item in model['parts']:
        s = item['shape']
        if not s.isValid() or not s.isClosed() or len(s.Solids) != 1:
            raise ValueError('閉じた単一部品ではありません: ' + item['name'])
        b = s.optimalBoundingBox(False)
        dimensions = [b.XLength, b.YLength, b.ZLength]
        if max(dimensions) > p.usable_print_size + 1e-6:
            raise ValueError('造形範囲を超えています: ' + item['name'])
        records[item['name']] = {'volume_mm3': s.Volume, 'dimensions_mm': dimensions, 'role': item['role']}
    items = model['parts'] + model['references']
    for i in model['references']:
        if not i['shape'].isValid() or not i['shape'].isClosed():
            raise ValueError('参考形状が無効です: ' + i['name'])
    collisions = []
    for n, a in enumerate(items):
        for b in items[n + 1:]:
            volume = overlap(a['shape'], b['shape'])
            if volume > .001:
                collisions.append([a['name'], b['name'], volume])
    if collisions:
        raise ValueError('形状干渉: ' + str(collisions))
    results = {}
    for mode in ('ring', 'crs812'):
        scene = fixed_layout(mode, p, model.get('switch_bay'))
        results[mode] = check_fixed_layout(scene)
    reference = model['scene']
    service_failures, air_failures = [], []
    for envelope in reference['service_spaces']:
        target = envelope['name'].removesuffix('_removal')
        sweep = box(envelope['origin'], envelope['size'])
        for item in items:
            # 機器と一緒に動くトレー（左右2枚に分けたものを含む）は除く。
            if item['name'] == target or item['name'].startswith(target + '_tray'):
                continue
            if overlap(sweep, item['shape']) > .001:
                service_failures.append([envelope['name'], item['name']])
    for envelope in reference['intake_spaces'] + reference['exhaust_spaces']:
        sweep = box(envelope['origin'], envelope['size'])
        for item in items:
            if overlap(sweep, item['shape']) > .001:
                air_failures.append([envelope['name'], item['name']])
    if service_failures or air_failures:
        raise ValueError(str({'service_failures': service_failures, 'air_failures': air_failures}))
    motion = exchange_envelopes(model)
    contacts = support_contacts(model)
    remaining = ['側枠と横梁を全体へ組み込む順序と連続した経路',
                 '制御器扉のヒンジと留め具', '機器トレーのガイドと抜け止め',
                 '前面・側面ファン保持部の留め具と格子の実物確認', '電源仕切りの固定',
                 'スイッチ支持板と固定', '余長収納の保持部', '脚と滑り止め', '接合面を保護した外周の面取りと丸み']
    bay = model.get('switch_bay')
    bay_summary = None
    if bay is not None:
        remaining[remaining.index('スイッチ支持板と固定')] = 'スイッチ本体をトレーへ留める金具（後方支持耳の穴位置を実測後）'
        remaining += ['トレー抜け止めねじの床側の雌ねじ（熱圧入ナットかナット保持）',
                      '専用段前面の開口の覆いと配線の引き出し口']
        bay_summary = {'variant': bay['variant'], 'frame_height_mm': p.height,
                       'floor_bottom_mm': bay['floor_z'], 'tray_support_mm': bay['support_z'],
                       'switch_bottom_mm': bay['switch_z'], 'binding_constraint': bay['binding_constraint'],
                       'part_count': model['supports']['switch_bay']['part_count'],
                       'removed_cross_beams': bay['replaced_cross_beams'],
                       'load_path': 'スイッチ→左右のトレー→床の支持帯→床の左右の舌→側枠の水平な受け→側枠の重ね継ぎ→脚',
                       'switch_fixing': 'トレーの側面の止めと前側の止めで位置を決め、後ろのねじ2本でトレーを床へ留める。'
                                        'スイッチ本体の固定金具は穴位置の実測後に設計する。'}
    volumes = {}
    for record in records.values():
        role = record['role']
        volumes[role] = volumes.get(role, 0) + record['volume_mm3']
    return {'status': 'passed', 'parts': records, 'candidate_part_instances': len(records),
            'reference_objects': len(model['references']), 'shape_collisions': [],
            'fixed_air_obstructions': [], 'rear_exchange_obstructions': [],
            'layout_checks': results, 'exchange_envelopes': motion, 'support_contacts': contacts,
            'controller_face_validation': model['controller_face']['validation'],
            'fan_grille_openings': grille_openings(model),
            'design_changes': {'outer_diagonal_braces': 0,
                               'replaced_support_parts': model['supports']['old_split_part_count'],
                               'integrated_support_parts': model['supports']['integrated_part_count'],
                               'outer_structural_wall_thickness_mm': p.skin,
                               'common_front_plane_y_mm': model['parameters'].front_face_y},
            'material_volume': {'total_cad_solid_mm3': sum(volumes.values()),
                                'by_role_mm3': volumes,
                                'scope': '参考部品を除いた形状体積。充填率・支持材・印刷損失を含む材料使用量ではない。'},
            **({'switch_bay': bay_summary} if bay_summary else {}),
            'scope': '形状候補の妥当性、246mm外形、静止干渉、機器の交換予約、前後の固定障害物。',
            'manufacturing_geometry': False, 'physical_validation': False,
            'whole_assembly_path_validated': False,
            'remaining_mechanisms': remaining,
            'physical_checks_pending': ['足・吸気口・端子・電源・スイッチ・分岐ケーブルの実測',
                '接合隙間と長期荷重・横揺れ', '4台同時負荷の温度・性能・騒音', '実物の交換操作']}
