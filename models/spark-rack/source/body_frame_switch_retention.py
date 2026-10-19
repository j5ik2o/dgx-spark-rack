"""CRS812の軽い保持。低い滑り止めと、機器と支持レールを一緒に抱くベルト。"""


def validate_retention(model):
    import FreeCAD as App
    from validate_body_frame import shared_area
    scene, p = model['scene'], model['parameters']
    data = scene['switch_retention']
    all_items = {e['name']: e for e in model['parts'] + model['references']}
    for entry in model['parts']:
        all_items.update({name: entry for name in entry.get('integrated_members', [])})
    required = set(data['rail_names']) | {b['name'] for b in data['bands']}
    if len(data['bands']) != 2 or not required <= all_items.keys():
        raise ValueError('CRS812の抜け止めレールまたは保持ベルトが欠けています')
    switch = all_items['crs812']['shape']
    rails = [all_items[n]['shape'] for n in data['rail_names']]
    bands = [all_items[b['name']]['shape'] for b in data['bands']]
    # ベルトがケースだけを巻いて支持レールから離れていないことを確認する。
    for band in bands:
        if sum(shared_area(band, rail) for rail in rails) < 100:
            raise ValueError('CRS812のベルトが支持レールを抱いていません')
        if shared_area(band, switch) < 100:
            raise ValueError('CRS812のベルトが本体の上面を押さえていません')
    directions = [('左右の右', [1, 0, 0]), ('左右の左', [-1, 0, 0]),
                  ('前後の後ろ', [0, 1, 0]), ('前後の前', [0, -1, 0]), ('上方向', [0, 0, 1])]
    blocked = []
    displacement = max(2, p.switch_fit_clearance + 1)
    for label, axis in directions:
        moved = switch.copy()
        moved.translate(App.Vector(*[n * displacement for n in axis]))
        obstacles = rails if axis[2] == 0 else bands
        if not any(moved.common(s).Volume > 1e-5 for s in obstacles):
            raise ValueError('CRS812の簡易固定が移動を止めません: ' + label)
        blocked.append(dict(direction=axis, displacement_mm=displacement))
    return dict(status='passed', checked_displacements=blocked, bands=2, stops='前後左右に高さ8mmの低い抜け止め',
                scope='参考外形を2mm動かすと保持部に当たる形状検査。強度・摩擦・振動の試験ではない。',
                physical_validation=False, seismic_rating_verified=False,
                remaining=['本体・足・通気口と抜け止めの実物適合',
                           'ベルト・バックルの選定、緩み、筐体と樹脂部品の変形・強度'])
