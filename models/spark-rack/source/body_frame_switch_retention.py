"""CRS812の軽い保持。低い滑り止めと、機器と支持レールを一緒に抱くベルト。"""


def plan(scene, p):
    switch = next(e for e in scene['equipment'] if e['name'] == 'crs812')
    x, y, z = switch['origin']
    width, depth, height = switch['size']
    clearance, wall = p.switch_fit_clearance, p.switch_stop_thickness
    front, rear = y - clearance - wall, y + depth + clearance + wall
    middle = (front + rear) / 2
    original = [r for r in scene['boxes'] if r['name'].startswith('network_rail_')]
    scene['boxes'] = [r for r in scene['boxes'] if r not in original]
    rails = []
    for rail in original:
        side = 1 if rail['origin'][0] > 0 else -1
        for end, lo, hi, keeper_y in (
                ('front', front, middle, y + 60),
                ('rear', middle, rear, y + depth - 48)):
            recipe = dict(rail, name=rail['name'] + '_' + end,
                          label='CRS812の低い抜け止め付き支持レール・' + ('前側' if end == 'front' else '後側'),
                          origin=[rail['origin'][0], lo, rail['origin'][2]],
                          size=[rail['size'][0], hi - lo, rail['size'][2]],
                          switch_keeper=dict(side=side, end=end, keeper_y=keeper_y))
            rails.append(recipe)
    scene['boxes'] += rails
    bands = []
    for number, band_y in enumerate((y + 80, y + depth - 68)):
        bands.append(dict(name=f'switch_band_{number}', label='CRS812と支持レールを一緒に抱く保持ベルト',
                          kind='switch_band', y=band_y, width=p.switch_band_width,
                          inner_x=[x - clearance, x + width + clearance],
                          inner_z=[p.network_rail_z, z + height], thickness=p.switch_band_thickness,
                          buckle_origin=[-15, band_y - 2, z + height + p.switch_band_thickness],
                          buckle_size=[30, p.switch_band_width + 4, 8]))
    return dict(target='crs812', scope='スイッチ単体の横滑り・落下を抑える簡易固定。机への固定は対象外。',
                rail_names=[r['name'] for r in rails], bands=bands,
                horizontal_clearance_mm=clearance, stop_height_mm=p.switch_stop_height,
                buckle_status='非伸縮の保持ベルトとバックルの参考形状。製品・締付け・耐荷重は未確定。',
                disassembly=['電源を切り、端子からケーブルを外す。',
                             '2本のベルトのバックルを開いて緩める。',
                             '低い抜け止めを越えるまで持ち上げ、CRS812を取り出す。'],
                physical_validation=False, seismic_rating_verified=False,
                requirement_reference='models/spark-rack/reference/body-frame-switch-retention-20261019.json')


def rail_shape(recipe, scene, p):
    from body_frame_geometry import block, fuse
    switch = next(e for e in scene['equipment'] if e['name'] == 'crs812')
    sx, sy, sz = switch['origin']
    sw, sd, _ = switch['size']
    x, y, z = recipe['origin']
    width, depth, height = recipe['size']
    keeper = recipe['switch_keeper']
    wall, clearance = p.switch_stop_thickness, p.switch_fit_clearance
    # 端の低い突起は前後の滑りを止める。側面の突起は筐体の下端だけに当てる。
    end_y = y if keeper['end'] == 'front' else y + depth - wall
    side_x = sx + sw + clearance if keeper['side'] > 0 else sx - clearance - wall
    arm_start = x + width if keeper['side'] > 0 else side_x
    arm_end = side_x + wall if keeper['side'] > 0 else x
    pieces = [block(recipe['origin'], recipe['size']),
              block([x, end_y, sz], [width, wall, p.switch_stop_height]),
              block([arm_start, keeper['keeper_y'], sz - 4], [arm_end - arm_start, 16, 4]),
              block([side_x, keeper['keeper_y'], sz - 4], [wall, 16, p.switch_stop_height + 4])]
    return fuse(pieces)


def band_shapes(scene):
    from body_frame_geometry import block, item
    references = []
    for band in scene['switch_retention']['bands']:
        x0, x1 = band['inner_x']
        z0, z1 = band['inner_z']
        t, y, w = band['thickness'], band['y'], band['width']
        outer = block([x0 - t, y, z0 - t], [x1 - x0 + 2 * t, w, z1 - z0 + 2 * t])
        inner = block([x0, y - 1, z0], [x1 - x0, w + 2, z1 - z0])
        references.append(item(band['name'], band['label'], outer.cut(inner), 'switch_band'))
        references.append(item(band['name'] + '_buckle', '開放できるバックル・参考外形',
                               block(band['buckle_origin'], band['buckle_size']), 'switch_buckle'))
    return references


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
