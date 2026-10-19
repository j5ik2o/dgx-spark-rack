"""参考外形の干渉、接触関係、正立ファンの直線着脱だけを検査する。耐荷重試験ではない。"""
from collections import defaultdict
from itertools import combinations

from body_frame_layout import validate_layout

EPS = 1e-6


def bounds(shape):
    b = shape.BoundBox
    return [b.XMin, b.YMin, b.ZMin], [b.XMax, b.YMax, b.ZMax]


def near(a, b, *, volume=False):
    lo, hi = bounds(a)
    other_lo, other_hi = bounds(b)
    tolerance = EPS if volume else -EPS
    return all(min(hi[i], other_hi[i]) - max(lo[i], other_lo[i]) > tolerance for i in range(3))


def planes(shape):
    result = defaultdict(list)
    for face in shape.Faces:
        lo, hi = bounds(face)
        for axis in range(3):
            if hi[axis] - lo[axis] < EPS:
                result[(axis, round((lo[axis] + hi[axis]) / 2, 5))].append(face)
                break
    return result


def shared_area(first, second, *, axis=None, height=None):
    a, b = planes(first), planes(second)
    area = 0
    for key in a.keys() & b.keys():
        if axis is not None and (key[0] != axis or abs(key[1] - height) > EPS):
            continue
        for fa in a[key]:
            for fb in b[key]:
                if near(fa, fb):
                    area += fa.common(fb).Area
    return area


def components(names, edges):
    graph = {name: set() for name in names}
    for a, b, _ in edges:
        if a in graph and b in graph:
            graph[a].add(b)
            graph[b].add(a)
    remaining, groups = set(names), []
    while remaining:
        visited, todo = set(), [next(iter(remaining))]
        while todo:
            name = todo.pop()
            if name not in visited:
                visited.add(name)
                todo += list(graph[name] - visited)
        remaining -= visited
        groups.append(sorted(visited))
    return sorted(groups)


def validate(model):
    p, scene = model['parameters'], model['scene']
    report = validate_layout(scene)
    parts, references = model['parts'], model['references']
    all_items = parts + references
    info = {}
    for entry in all_items:
        shape = entry['shape']
        if not shape.isValid() or not shape.isClosed() or not shape.Solids:
            raise ValueError('形状が閉じた有効な立体ではありません: ' + entry['name'])
        lo, hi = bounds(shape)
        sizes = [hi[i] - lo[i] for i in range(3)]
        if entry in parts and (len(shape.Solids) != 1 or max(sizes) > p.usable_print_size + EPS):
            raise ValueError('候補部品が単一立体または造形範囲の条件を満たしません: ' + entry['name'])
        info[entry['name']] = {'dimensions_mm': sizes, 'volume_mm3': shape.Volume, 'kind': entry['kind']}
        if lo[2] < -EPS:
            raise ValueError('設置面の下にはみ出しています: ' + entry['name'])
    by_name = {e['name']: e for e in all_items}
    for fan in (e for e in scene['equipment'] if e['kind'] == 'fan'):
        actual = info[fan['name']]['dimensions_mm']
        if any(abs(actual[i] - fan['size'][i]) > EPS for i in range(3)):
            raise ValueError('ファンの実形状が定義した取付軸に沿っていません: ' + fan['name'])
    collisions = []
    for first, second in combinations(all_items, 2):
        if first.get('group') and first.get('group') == second.get('group'):
            continue
        if near(first['shape'], second['shape'], volume=True):
            volume = first['shape'].common(second['shape']).Volume
            if volume > 1e-5:
                collisions.append([first['name'], second['name'], round(volume, 6)])
    if collisions:
        raise ValueError('部品・機器の干渉: ' + str(collisions))
    sparks = [r for r in references if r['kind'] == 'spark']
    structural = parts + sparks
    edges = []
    for first, second in combinations(structural, 2):
        if near(first['shape'], second['shape']):
            area = shared_area(first['shape'], second['shape'])
            if area > 1:
                edges.append([first['name'], second['name'], round(area, 3)])
    connected = components([e['name'] for e in structural], edges)
    if len(connected) != 1:
        raise ValueError('本体を含む接触関係が分かれています: ' + str(connected))
    without = components([e['name'] for e in parts], edges)
    if len(without) < 2:
        raise ValueError('本体なしで全段がつながる独立した外枠になっています')
    bearings = []
    for spark in sparks:
        for z in (spark['shape'].BoundBox.ZMin, spark['shape'].BoundBox.ZMax):
            area = sum(shared_area(spark['shape'], part['shape'], axis=2, height=z)
                       for part in parts if part['kind'] == 'body_connector' and near(spark['shape'], part['shape']))
            if area < 1000:
                raise ValueError('筐体の参考外形と接続部の受け面が不足しています: ' + spark['name'])
            bearings.append(dict(spark=spark['name'], height_mm=z, reference_contact_mm2=round(area, 3)))
    movements = []
    for fan in (e for e in scene['equipment'] if e['kind'] == 'fan'):
        names = {fan['name'], fan['name'] + '_holder'} | {e['name'] for e in parts if e.get('moves_with') == fan['name']}
        for distance in (20, 50, p.fan_removal_distance):
            for name in names:
                moved = by_name[name]['shape'].copy()
                import FreeCAD as App
                moved.translate(App.Vector(*[v * distance for v in fan['axis']]))
                for fixed in all_items:
                    if fixed['name'] in names or fixed.get('unlock_before') == fan['name']:
                        continue
                    if near(moved, fixed['shape'], volume=True) and moved.common(fixed['shape']).Volume > 1e-5:
                        raise ValueError('ファンの直線着脱が干渉します: ' + str([name, distance, fixed['name']]))
        movements.append(dict(fan=fan['name'], axis=fan['axis'], straight_removal_mm=p.fan_removal_distance))
    obstructions = []
    for space in scene['connectors']:
        from freecad_spark_rack import block
        probe = block(space['origin'], space['size'])
        owner = space['name'].removesuffix('_ports')
        for entry in all_items:
            if entry['name'] == owner or entry.get('group') == owner:
                continue
            if near(probe, entry['shape'], volume=True) and probe.common(entry['shape']).Volume > 1e-5:
                obstructions.append([space['name'], entry['name']])
    if obstructions:
        raise ValueError('端子の仮空間を塞いでいます: ' + str(obstructions))
    # ケースの正本が変わったとき、配置に用いた収容外形からはみ出せば検査を止める。
    for controller in (e for e in scene['equipment'] if e['kind'] == 'controller'):
        group = [e['shape'] for e in all_items if e.get('group') == controller['name']
                 or e['name'] == controller['name'] + '_dock']
        for shape in group:
            b = shape.optimalBoundingBox(False)
            lo, hi = [b.XMin, b.YMin, b.ZMin], [b.XMax, b.YMax, b.ZMax]
            if any(lo[i] < controller['origin'][i] - EPS
                   or hi[i] > controller['origin'][i] + controller['size'][i] + EPS for i in range(3)):
                raise ValueError('制御器の正本が配置用の収容外形を超えています: ' + controller['name'])
    low = [min(bounds(e['shape'])[0][i] for e in all_items) for i in range(3)]
    high = [max(bounds(e['shape'])[1][i] for e in all_items) for i in range(3)]
    from validate_body_frame_cables import validate_cables
    cable_report = validate_cables(model)
    from body_frame_switch_retention import validate_retention
    switch_retention = validate_retention(model)
    from body_frame_joinery import validate_screwless
    screwless = validate_screwless(model)
    from check_controller_mounts import check_screwless_mounts
    controller_mounts = check_screwless_mounts(model)
    from body_frame_assembly import build_plan
    from validate_body_frame_assembly import validate_plan
    from body_frame_controller_assembly import check_controller_assembly
    assembly_plan = build_plan(model)
    assembly_order = validate_plan(model, assembly_plan)
    assembly_order['controller_preassembly'] = check_controller_assembly(model)
    from body_frame_access import validate_access
    assembly_order['finger_access'] = validate_access(model, assembly_plan)
    model['assembly_plan'] = assembly_plan
    from body_frame_print_plan import build_print_plan
    model['print_plan'] = build_print_plan(model)
    report.update(
        candidate_parts=len(parts), reference_objects=len(references), shapes=info,
        overall_origin_mm=low, overall_size_mm=[high[i] - low[i] for i in range(3)],
        static_collisions=collisions, contact_edges=edges,
        contact_components_with_sparks=len(connected),
        contact_components_without_sparks=len(without),
        reference_bearing_contacts=bearings, fan_straight_removal=movements,
        connector_obstructions=obstructions,
        cable_routing=cable_report,
        switch_retention=switch_retention,
        screwless_assembly=screwless,
        controller_mounts=controller_mounts,
        assembly_order=assembly_order,
        print_plan=dict(status='candidate',printed_part_count=model['print_plan']['printed_part_count'],
                        minimum_key_width_mm=model['print_plan']['minimum_key_width_mm'],
                        physical_validation=False,slicer_validated=False),
        manufacturing_geometry=False, physical_validation=False,
        remaining=[
            'Spark外装の荷重許容、足・通気口・丸みとコーナー接触部の実測',
            'CRS812と切替器の実寸・足・質量・吸排気と支持レールの位置',
            'ほぞ・角栓のはめ合いと脱落防止、樹脂割りピンの弾性、接触面の保護',
            '下段交換時に実際に手を入れる操作空間、仮支持と実物のはめ合い',
            '実端子への接続、分岐線ごとの到達と余長量、束同士の配置、タップと補助電源の現物適合',
            '近接ファンの送風方向、排気の再吸込み、温度・性能・騒音',
        ])
    return report
