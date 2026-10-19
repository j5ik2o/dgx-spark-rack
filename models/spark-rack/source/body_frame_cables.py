"""配線経路と保持部の候補。端子位置・線径・分岐長の実測に代わるものではない。"""
import math


def sub(a, b):
    return [a[i] - b[i] for i in range(3)]


def add(a, b, scale=1):
    return [a[i] + b[i] * scale for i in range(3)]


def distance(a, b):
    return math.dist(a, b)


def rounded_path(points, radius):
    """直交折線の角を接線付きの四分円へ変換し、短過ぎる区間を拒否する。"""
    vectors = [sub(b, a) for a, b in zip(points, points[1:])]
    lengths = [math.sqrt(sum(v * v for v in vector)) for vector in vectors]
    if not vectors or any(n <= 0 for n in lengths):
        raise ValueError('配線経路に長さのない区間があります')
    directions = [[v / n for v in vector] for vector, n in zip(vectors, lengths)]
    turns = [0]
    for a, b in zip(directions, directions[1:]):
        dot = sum(a[i] * b[i] for i in range(3))
        if abs(dot) > 1e-7:
            raise ValueError('配線の折線は直交する区間で指定してください')
        turns.append(radius)
    turns.append(0)
    if any(n + 1e-7 < turns[i] + turns[i + 1] for i, n in enumerate(lengths)):
        raise ValueError('曲げ半径に対して配線区間が短過ぎます')
    segments, current = [], list(points[0])
    for i in range(1, len(points) - 1):
        before, after = directions[i - 1], directions[i]
        start = add(points[i], before, -radius)
        end = add(points[i], after, radius)
        center = add(start, after, radius)
        if distance(current, start) > 1e-7:
            segments.append(dict(type='line', start=current, end=start))
        mid = add(center, [(-after[j] + before[j]) / math.sqrt(2) for j in range(3)], radius)
        segments.append(dict(type='arc', start=start, middle=mid, end=end, center=center, radius=radius))
        current = end
    if distance(current, points[-1]) > 1e-7:
        segments.append(dict(type='line', start=current, end=list(points[-1])))
    length = sum(distance(s['start'], s['end']) if s['type'] == 'line' else math.pi * radius / 2
                 for s in segments)
    return segments, length


def routing(scene, p):
    equipment = {e['name']: e for e in scene['equipment']}
    paths, mounts, storage = [], [], []

    def route(name, label, family, points, radius, diameter, endpoints, **extra):
        segments, length = rounded_path(points, radius)
        paths.append(dict(name=name, label=label, family=family, points=points,
                          segments=segments, centerline_length_mm=length,
                          radius_mm=radius, diameter_mm=diameter, endpoints=endpoints,
                          exact_port_positions_verified=False, length_fit_verified=False, **extra))

    def mount(name, label, origin, size, slots=False):
        mounts.append(dict(name=name, label=label, origin=origin, size=size,
                           kind='cable_mount', slots=slots))

    rear, outside = p.cable_rear_y, p.cable_side_x
    kvm_signal_z = equipment['kvm']['origin'][2]+19
    switch_network_z = equipment['crs812']['origin'][2]+22
    switch_power_z = equipment['crs812']['origin'][2]+26
    for col, side in enumerate((-1, 1)):
        side_label = '左' if side < 0 else '右'
        anchor_x = p.core_width / 2 + 4
        mount(f'cable_tie_arm_{col}', side_label + 'の中間接続部へ留める短い配線腕',
              [anchor_x if side > 0 else -anchor_x - 4, p.spark_depth,
               p.lower_base+p.spark_height+p.stack_gap/2-4], [4, 66, 8])
        mount(f'cable_tie_plate_{col}', side_label + 'の解除式結束バンドを通す束の留め板',
              [anchor_x if side > 0 else -anchor_x - 4, 216, 70], [4, 16, 104])
        mounts[-1]['tie_plate'] = True
        # 全段をつなぐ柱にはせず、上部の横梁だけから支持する。
        edge = p.core_width / 2 + p.beam_overhang
        arm_outer = outside + 42
        mount(f'cable_outreach_{col}', side_label + 'の上部横梁から出す短い腕',
              [edge if side > 0 else -(outside + 26), 134, p.beam_z],
              [outside + 26 - edge, 16, 10])
        mount(f'cable_side_arm_{col}', side_label + 'の余長受けだけを支える腕',
              [outside + 26 if side > 0 else -arm_outer, 134, p.beam_z],
              [16, 224, 10])
        mount(f'cable_storage_floor_{col}', side_label + 'の開放式余長受け・結束バンド用の穴',
              [outside - 32 if side > 0 else -arm_outer, 180, p.beam_z - 4],
              [74, 178, 4], slots=True)
        mounts[-1].update(feed_x=side * outside, feed_y=340)
        for turn in range(3):
            storage.append(dict(name=f'network_storage_{col}_{turn}',
                                label=side_label + f'の余長予約・{turn + 1}周目（実配線ではない）',
                                kind='cable_storage', family='network',
                                center=[side * (outside - 12 + turn * 12), 295, p.cable_storage_center_z],
                                normal=[1, 0, 0], radius=p.cable_storage_radius, diameter=8,
                                length_mm=2 * math.pi * p.cable_storage_radius))
        rear_tray = next(b for b in scene['boxes'] if b['name'] == f'power_tray_{col}_1')
        tray_back = rear_tray['origin'][1] + rear_tray['size'][1]
        mount(f'signal_storage_floor_{col}', side_label + 'の映像・USBの余長受け',
              [rear_tray['origin'][0], tray_back, 10],
              [rear_tray['size'][0], 366 - tray_back, 4], slots=True)
        mounts[-1].update(feed_x=side * 140, feed_y=338)
        for level in range(4):
            for radius in (30, 45):
                storage.append(dict(name=f'signal_storage_{col}_{level}_{radius}',
                                    label=side_label + 'の映像・USB余長の予約（実配線ではない）',
                                    kind='cable_storage', family='signal',
                                    center=[side * 85, 310, 20 + level * 13], normal=[0, 0, 1],
                                    radius=radius, diameter=12, length_mm=2 * math.pi * radius))
        split = [side * outside, rear, 200]
        for row in range(2):
            spark = equipment[f'spark_{col}_{row}']
            z = spark['origin'][2] + 22
            x = side * (140 - 10 * row)
            route(f'network_branch_{col}_{row}', f'{side_label}{"下" if row == 0 else "上"}段のネットワーク経路',
                  'network', [[x, p.spark_depth + 35, z], [x, rear, z],
                              [side * outside, rear, z], split], 42, 8,
                  [spark['name'], f'network_split_{col}'], cable_group=f'breakout_{col}')
            # 映像線とUSB線は同じ束の予約。束の内部で個別端子へ配る部分は未採寸。
            vx = side * (140 + 5 * row)
            route(f'video_usb_{col}_{row}', f'{side_label}{"下" if row == 0 else "上"}段の映像・USBの束',
                  'signal', [[vx, 150, z + 8], [vx, 300 + row * 20, z + 8],
                             [vx, 300 + row * 20, kvm_signal_z], [vx, 237, kvm_signal_z]],
                  20, 12, [spark['name'], 'kvm'], nominal_length_mm=1500)
            power = equipment[f'power_{col}_{row}']
            y, zpower = power['origin'][1], power['origin'][2] + 17
            px = side * (85 + row * 12)
            # 受けを8mm持ち上げ、下を通す。端子面は仮定で、現物に合わせる。
            route(f'spark_dc_{col}_{row}', side_label + f'の電源{row + 1}から本体への直流配線',
                  'dc', [[px, y, zpower], [px, y - 25, zpower], [px, y - 25, p.cable_underfloor_z],
                         [px, 320, p.cable_underfloor_z], [side * 140, 320, p.cable_underfloor_z],
                         [side * 140, 350, p.cable_underfloor_z],
                         [side * 140, 350, z + 15], [side * 140, 150, z + 15]],
                  10, 6, [power['name'], spark['name']])
            ac_y = y if row == 0 else y + power['size'][1]
            guide_y = -95 if row == 0 else 370
            outlet = [350 + col * 24 + row * 12, 0 if row == 0 else 90, 25]
            route(f'adapter_ac_{col}_{row}', side_label + f'の電源{row + 1}の交流配線',
                  'ac', [[side * 85, ac_y, zpower], [side * 85, guide_y, zpower],
                         [outlet[0], guide_y, zpower], [outlet[0], outlet[1], zpower]],
                  20, 8, [power['name'], 'external_power_strip'])
        route(f'network_trunk_{col}', side_label + 'の分岐点からCRS812への主線', 'network',
              [split, [side * outside, rear, switch_network_z],
               [side * 130, rear, switch_network_z], [side * 130, 293, switch_network_z]],
              42, 10, [f'network_split_{col}', 'crs812'], cable_group=f'breakout_{col}')
        route(f'switch_ac_{col}', f'CRS812の交流電源{col + 1}', 'ac',
              [[side * 170, -10, switch_power_z], [side * 170, -95, switch_power_z],
               [side * 240, -95, switch_power_z], [side * 240, -95, 30],
               [440 + col * 25, -95, 30], [440 + col * 25, 0, 30]],
              25, 8, ['crs812', 'external_power_strip'])
        for row in range(3):
            controller = equipment[f'controller_{side}_{row}']
            cy = controller['dock_origin'][1]
            cz = controller['dock_origin'][2]
            start = [side * (p.core_width / 2 + p.controller_offset + 41), cy, cz]
            disconnect = [side * 240, -65 if row == 0 else 355, 210 if row < 2 else 160]
            route(f'fan_feed_{col}_{row}', side_label + f'の制御器{row + 1}から着脱コネクターまで', 'control',
                  [start, [side * 240, cy, cz], [side * 240, cy, disconnect[2]], disconnect],
                  6, 4, [controller['name'], f'fan_disconnect_{col}_{row}'])
            fan_name = f'spark_fan_{col}_{"front" if row == 0 else "rear"}' if row < 2 else f'power_fan_{side}'
            fan = equipment[fan_name]
            if row < 2:
                fy = fan['origin'][1] + p.fan_depth / 2
                end = [side * 150, fy, fan['origin'][2]+fan['size'][2]-4.5]
                tail = [disconnect, [side * 150, disconnect[1], disconnect[2]],
                        [side * 150, fy, disconnect[2]], end]
            else:
                end = [side * 219, 290, 108]
                tail = [disconnect, [side * 240, 290, 160], [side * 240, 290, 108], end]
            route(f'fan_tail_{col}_{row}', side_label + f'のファン{row + 1}の取り外す短線', 'control',
                  tail, 6, 4, [f'fan_disconnect_{col}_{row}', fan_name], detachable_with=fan_name)
            route(f'controller_supply_{col}_{row}', side_label + f'の制御器{row + 1}の給電・センサー用経路予約', 'control',
                  [[start[0], cy + 10, cz], [side * 250, cy + 10, cz],
                   [side * 250, cy + 10, 170], [side * 250, 355, 170]],
                  6, 5, [controller['name'], 'auxiliary_supply_and_sensors'], unfinished_terminal=True)
    route('comet_video_usb', 'GL-RM10と切替器の映像・キーボード操作の束', 'signal',
          [[0, 44, 225], [0, 90, 225], [185, 90, 225], [185, 280, 225],
           [40, 280, 225], [40, 237, 225]], 18, 12, ['comet', 'kvm'])
    route('comet_ethernet', 'GL-RM10の管理用有線ネットワーク', 'signal',
          [[25, 44, 235], [25, 90, 235], [195, 90, 235], [195, 340, 235],
           [195, 340, 285], [195, 258, 285]], 15, 6, ['comet', 'crs812'])
    for name, x, y, z in [('comet', -25, 44, 240), ('kvm', -140, 237, 225)]:
        route(name + '_dc', name + 'の低電圧給電', 'dc',
              [[x, y, z], [x, y + 30, z], [-210, y + 30, z],
               [-210, 355, z], [-210, 355, 170]], 10, 5,
              [name, 'external_peripheral_adapters'], unfinished_terminal=True)
    airflow = [dict(name=f'airflow_{col}', label='Spark列の中央を開ける仮の排気通路',
                    origin=[side * 85 - 40, 210, 65], size=[80, p.spark_depth + p.rear_fan_gap - 4 - 210, 105])
               for col, side in enumerate((-1, 1))]
    return dict(paths=paths, storage=storage, mounts=mounts, airflow_spaces=airflow,
                endpoint_status='端子位置とプラグ形状は仮定。各端子への短い接続区間は未採寸。',
                path_scope='束の通過領域。束同士の重なりは許し、固定物と着脱経路との干渉を検査する。',
                external_regions=[dict(name='external_power_strip', label='机上別置きタップ・8口以上、補助電源と電源線余長の予約',
                                       origin=[320, 0, 0], size=[360, 90, 90],
                                       kind='external_reservation', purchased_product=False)],
                service_sequence=['電源を切り、対象ファンの着脱コネクターを外す。',
                                  '対象ファンの短線の留め具を開放し、短線をファン側へ寄せる。',
                                  '保持部の抜け止め用の角栓を外し、ファンと保持部を軸方向へ110mmまっすぐ引く。',
                                  '機器交換時は対象の結束バンドのロックを解除する。面ファスナーを併用した箇所も開放し、上部から順に分解する。'],
                unresolved=['端子中心、プラグ外形、実線径と束の内部配置',
                            '2m分岐ケーブルの主線・分岐線の長さ、分岐点の実寸と位置',
                            '電源タップの製品・定格・差込間隔、補助電源と周辺機器用アダプターの外形',
                            '制御器の給電仕様と温度センサーの取付・末端配線',
                            '保持帯と着脱コネクターの実物、実機での組立と冷却'])


def validate_routing(scene):
    data = scene['cable_management']
    names = [r['name'] for r in data['paths']]
    if len(names) != len(set(names)):
        raise ValueError('配線経路名が重複しています')
    required = {f'{family}_{col}_{row}' for family in ('network_branch', 'video_usb', 'spark_dc', 'adapter_ac')
                for col in range(2) for row in range(2)}
    required |= {f'network_trunk_{col}' for col in range(2)}
    required |= {f'{family}_{col}_{row}' for family in ('fan_feed', 'fan_tail', 'controller_supply')
                 for col in range(2) for row in range(3)}
    required |= {f'switch_ac_{col}' for col in range(2)}
    required |= {'comet_video_usb', 'comet_ethernet', 'comet_dc', 'kvm_dc'}
    if not required <= set(names):
        raise ValueError('維持する機器の配線経路が欠けています: ' + str(sorted(required - set(names))))
    storage_counts = {family: sum(s['family'] == family for s in data['storage'])
                      for family in ('network', 'signal')}
    if storage_counts != {'network': 6, 'signal': 16}:
        raise ValueError('ネットワークまたは映像・USBの余長予約が欠けています')
    for route in data['paths']:
        if route['diameter_mm'] <= 0 or route['radius_mm'] <= route['diameter_mm'] / 2:
            raise ValueError('配線の線径または曲げ半径が不正です')
        segments, length = rounded_path(route['points'], route['radius_mm'])
        if segments != route['segments'] or abs(length - route['centerline_length_mm']) > 1e-5:
            raise ValueError('配線の実経路と記録が一致しません: ' + route['name'])
        if route['family'] == 'network' and route['radius_mm'] < 42:
            raise ValueError('ネットワークの暫定最小曲げ半径42mmを下回っています')
        if route['length_fit_verified'] or route['exact_port_positions_verified']:
            raise ValueError('未採寸の配線を適合確認済みにできません')
    if any(s['radius'] < (42 if s['family'] == 'network' else 20) for s in data['storage']):
        raise ValueError('余長予約の曲げ半径が不足しています')
    return dict(status='passed', path_count=len(names), network_minimum_radius_mm=42,
                nominal_length_fit='未判定', actual_ports_fit='未判定',
                cable_to_cable_fit='束の内部配置と束同士の分離は未判定',
                storage_turns_per_side=3, storage_centerline_capacity_per_side_mm=
                sum(s['length_mm'] for s in data['storage'] if s['family'] == 'network') / 2,
                signal_storage_centerline_capacity_per_side_mm=
                sum(s['length_mm'] for s in data['storage'] if s['family'] == 'signal') / 2)
