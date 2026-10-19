"""配線予約と固定物、ファンの連続した直線着脱との干渉を検査する。"""
from body_frame_cables import validate_routing


def validate_cables(model):
    from freecad_spark_rack import block
    from validate_body_frame import near, bounds
    import FreeCAD as App
    data = model['scene']['cable_management']
    report = validate_routing(model['scene'])
    fixed = model['parts'] + model['references']
    routing = model['cables'] + model['cable_storage']
    collisions = []
    for cable in routing:
        shape = cable['shape']
        if not shape.isValid() or not shape.isClosed() or len(shape.Solids) != 1:
            raise ValueError('配線予約が有効な単一立体ではありません: ' + cable['name'])
        if shape.BoundBox.ZMin < -1e-6:
            raise ValueError('配線が設置面の下へ出ています: ' + cable['name'])
        for obstacle in fixed:
            if near(shape, obstacle['shape'], volume=True):
                intersection = shape.common(obstacle['shape'])
                # 接続先を丸ごと除外せず、仮の端末周辺15mmだけを検査外とする。
                owner = obstacle.get('group', obstacle['name'])
                if owner in cable.get('endpoints', []):
                    import Part
                    recipe = next(r for r in data['paths'] if r['name'] == cable['name'])
                    for index, endpoint in enumerate(recipe['endpoints']):
                        if endpoint == owner:
                            point = recipe['points'][0 if index == 0 else -1]
                            intersection = intersection.cut(Part.makeSphere(15, App.Vector(*point)))
                volume = intersection.Volume
                if volume > 1e-5:
                    collisions.append([cable['name'], obstacle['name'], round(volume, 4)])
    if collisions:
        raise ValueError('配線予約と固定物の干渉: ' + str(collisions))
    for space in data['airflow_spaces']:
        probe = block(space['origin'], space['size'])
        for entry in routing + model['parts']:
            if near(probe, entry['shape'], volume=True) and probe.common(entry['shape']).Volume > 1e-5:
                raise ValueError('仮の排気通路を塞いでいます: ' + str([space['name'], entry['name']]))
    sweeps = []
    by_name = {e['name']: e for e in fixed}
    for fan in (e for e in model['scene']['equipment'] if e['kind'] == 'fan'):
        axis = App.Vector(*fan['axis'])
        vector = axis * model['parameters'].fan_removal_distance
        moving_names = {fan['name'], fan['name']+'_holder'} | {e['name'] for e in model['parts'] if e.get('moves_with') == fan['name']}
        for name in moving_names:
            shape = by_name[name]['shape']
            # 軸に垂直な端面を押し出し、途中位置も含む掃引領域を作る。
            probes = [shape] + [face.extrude(vector) for face in shape.Faces
                                if abs(face.normalAt(0, 0).dot(axis)) > .999]
            for cable in routing:
                if cable.get('detachable_with') == fan['name']:
                    continue
                for probe in probes:
                    if near(probe, cable['shape'], volume=True) and probe.common(cable['shape']).Volume > 1e-5:
                        raise ValueError('固定配線がファンの連続した着脱経路を塞いでいます: ' +
                                         str([fan['name'], cable['name']]))
        sweeps.append(dict(fan=fan['name'], distance_mm=model['parameters'].fan_removal_distance,
                           condition='対象の着脱コネクターを外し、短線をファン側へ寄せた後'))
    internal = fixed + routing
    low = [min(bounds(e['shape'])[0][i] for e in internal) for i in range(3)]
    high = [max(bounds(e['shape'])[1][i] for e in internal) for i in range(3)]
    region_low = [min([low[i]] + [r['origin'][i] for r in data['external_regions']]) for i in range(3)]
    region_high = [max([high[i]] + [r['origin'][i] + r['size'][i] for r in data['external_regions']]) for i in range(3)]
    report.update(fixed_obstacle_collisions=collisions, continuous_fan_removal=sweeps,
                  routed_origin_mm=low, routed_size_mm=[high[i] - low[i] for i in range(3)],
                  installation_origin_mm=region_low, installation_size_mm=[region_high[i] - region_low[i] for i in range(3)],
                  storage_is_reservation=True, external_regions=data['external_regions'],
                  airflow_reservation=data['airflow_spaces'], terminal_exemption_radius_mm=15,
                  scope='経路束と固定物、仮の中央排気通路、余長予約、ファンの連続着脱。端末周辺15mmと束同士の干渉は検査外。',
                  unresolved=data['unresolved'])
    return report
