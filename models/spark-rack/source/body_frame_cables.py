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
