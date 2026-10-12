"""固定段の支持棚と電源支持床を、造形できる一体部品へまとめる。

本体・電源を載せた引き出しトレーとは別の固定構造である。形状候補であり、
材料、締結、耐荷重は実物で検証するまで確定しない。
"""
import FreeCAD as App
import Part


def _box(origin, size):
    return Part.makeBox(*size, App.Vector(*origin))


def _window(x, y, z, width, depth, height, radius=6):
    """床の開口。床に垂直な辺を丸めて四隅の応力集中を抑える。"""
    shape = _box((x, y, z), (width, depth, height))
    vertical = [edge for edge in shape.Edges
                if abs(edge.BoundBox.ZLength - height) < 1e-7]
    return shape.makeFillet(min(radius, width / 4, depth / 4), vertical)


def _fuse(shapes):
    nonempty = [shape for shape in shapes if shape.Volume > 1e-7]
    if not nonempty:
        raise ValueError('支持形状の分割領域に体積がありません')
    return nonempty[0].multiFuse(nonempty[1:]).removeSplitter()


def _axis_regions(start, end, count, lap):
    """重ね部分を独立した区間にし、重複する部品番号も記録する。"""
    pitch = (end - start) / count
    half = lap / 2
    regions = []
    cursor = start
    for index in range(count - 1):
        joint = start + (index + 1) * pitch
        regions.append((cursor, joint - half, (index,)))
        regions.append((joint - half, joint + half, (index, index + 1)))
        cursor = joint + half
    regions.append((cursor, end, (count - 1,)))
    return regions


def _tiles(shape, origin, size, columns, rows, lap):
    """交差する重ね継ぎも厚さを分配し、部品間の体積重複を避ける。"""
    x, y, z = origin
    width, depth, height = size
    xs = _axis_regions(x, x + width, columns, lap)
    ys = _axis_regions(y, y + depth, rows, lap)
    result = []
    for row in range(rows):
        for col in range(columns):
            fragments = []
            for xlo, xhi, owners_x in xs:
                if col not in owners_x:
                    continue
                for ylo, yhi, owners_y in ys:
                    if row not in owners_y:
                        continue
                    count = len(owners_x) * len(owners_y)
                    layer = owners_y.index(row) * len(owners_x) + owners_x.index(col)
                    thickness = height / count
                    mask = _box((xlo, ylo, z + layer * thickness),
                                (xhi - xlo, yhi - ylo, thickness))
                    fragment = shape.common(mask)
                    if fragment.Volume > 1e-7:
                        fragments.append(fragment)
            result.append((col, row, _fuse(fragments)))
    return result


def _socket(name, side, y, depth, z, height, p):
    """差込み実体、切欠き、ゼロ隙間の水平座を別々に返す。"""
    inner = p.inner_width / 2
    x = -inner - 8 if side == 'left' else inner
    gap = p.fit_clearance
    origin = [x, y, z]
    size = [8, depth, height]
    return {
        'name': name, 'side': side, 'origin': origin, 'size': size,
        'cut_origin': [x - gap, y - gap, z],
        'cut_size': [8 + 2 * gap, depth + 2 * gap, height + gap],
        'bearing_z': z, 'bearing_origin': origin,
        'bearing_size': [8, depth, 0], 'side_and_top_clearance_mm': gap,
        'bottom_clearance_mm': 0,
        'purpose': '水平な下面座で荷重を受け、側面と上面だけ組立隙間を設ける',
    }


def _node_shelf(base, p):
    end = p.inner_width / 2 + 8
    z = base - p.tray_thickness - 12
    bands = [_box((-end, y, z), (2 * end, 20, 12)) for y in (-148, -22)]
    # 外側の帯と中央帯だけで前後をつなぎ、本体下面に大きな板を置かない。
    bands += [_box((x, -148, z), (width, 146, 12))
              for x, width in ((-end, end - 220), (-8, 16), (220, end - 220))]
    shelf = _fuse(bands)
    for joint in (-end / 3, end / 3):
        for y in (-138, -12):
            shelf = shelf.cut(Part.makeCylinder(2.25, 14, App.Vector(joint, y, z - 1)))
    return shelf.removeSplitter(), [-end, -148, z], [2 * end, 146, 12]


def _power_floor(p):
    end = p.inner_width / 2 + 8
    top = _box((-end, -280, 24), (2 * end, 390, 8))
    # トレーの左右縁の直下に8mm帯を通す。横帯を細くしても縁全体の支持を失わない。
    openings_x = [(-244, -228), (-220, -145), (-137, -43), (-35, -4),
                  (4, 35), (43, 137), (145, 220), (228, 244)]
    openings_y = [(-264, -247), (-237, -199), (-189, -91),
                  (-79, -51), (-41, 5), (15, 94)]
    for xlo, xhi in openings_x:
        for ylo, yhi in openings_y:
            top = top.cut(_window(xlo, ylo, 23, xhi - xlo, yhi - ylo, 10))
    # 下面へ開いたT字断面。座の8mm幅は残し、縁の荷重を4mmの縦リブへ渡す。
    # 上面を造形台へ向けるとリブが上へ立ち上がり、リブに密閉中空を作らない。
    # 重ね継ぎの段差に必要な支持材と接合強度は、造形試験で別途確認する。
    ribs = [_box((x, -280, 8), (width, 390, 16))
            for x, width in ((-end, 8), (-226, 4), (-143, 4), (-41, 4),
                             (-2, 4), (37, 4), (139, 4), (222, 4), (end - 8, 8))]
    # 24mmの重ね部分には8mm幅の連続リブを残す。帯との交点とねじ座も一体である。
    for joint in (-end / 3, end / 3):
        ribs.append(_box((joint - 4, -280, 8), (8, 390, 16)))
    for y, width in ((-275, 6), (-89, 8), (99, 6),
                     (-244, 4), (-196, 4), (-48, 4), (8, 4)):
        ribs.append(_box((-end, y, 8), (2 * end, width, 16)))
    holes = [(x, y) for x in (-end / 3, end / 3) for y in (-272, 102)]
    holes += [(x, -85) for x in (-2 * end / 3, 0, 2 * end / 3)]
    # 穴の周りは細いウェブだけにせず、直径14mmの円形座で上下の継ぎを締める。
    bosses = [Part.makeCylinder(7, 24, App.Vector(x, y, 8)) for x, y in holes]
    floor = _fuse([top] + ribs + bosses)
    # 側面ファンの保持部を外す経路は床の上端と重なる。4mm余裕を含めて逃がす。
    for x in (-end - 1, 230):
        width = end - 229
        floor = floor.cut(_box((x, -184, 7), (width, 128, 26)))
    for x, y in holes:
        floor = floor.cut(Part.makeCylinder(2.25, 26, App.Vector(x, y, 7)))
    return floor.removeSplitter(), [-end, -280, 8], [2 * end, 390, 24]


def integrated_supports(scene, p):
    """部品一覧と側枠側の受け・支持面の仕様を返す。

    部品一覧は name、label、shape、role を持つ辞書の配列である。
    socket_envelopes の切欠きを側枠へ適用してから干渉を検査する。
    """
    parts, sockets, surfaces, assemblies, fasteners = [], [], [], [], []
    end = p.inner_width / 2 + 8

    def add_fastener(assembly, x, y, z, length):
        fasteners.append({'assembly': assembly, 'axis': [0, 0, 1],
                          'origin': [x, y, z], 'through_length_mm': length,
                          'hole_diameter_mm': 4.5, 'thread_nominal_diameter_mm': 4,
                          'head_and_nut_retention': '頭とナットの保持方法は未確定',
                          'status': '既存横梁と同じ直径4mmねじの通し穴を採用した締結候補'})
    for level, base in enumerate((p.lower_base, p.upper_base)):
        shelf, origin, size = _node_shelf(base, p)
        name = f'node_shelf_{level}'
        for col, _, shape in _tiles(shelf, origin, size, 3, 1, p.lap_length):
            parts.append({'name': f'{name}_{col}',
                          'label': f'本体{level + 1}段目の固定支持棚・{col + 1}分割目',
                          'shape': shape, 'role': 'node_shelf'})
        for side in ('left', 'right'):
            sockets.append(_socket(f'{name}_{side}', side, -148, 146, origin[2], 12, p))
        for joint in (-end / 3, end / 3):
            for y in (-138, -12):
                add_fastener(name, joint, y, origin[2], 12)
        for tray in scene['trays']:
            if abs(tray['origin'][2] - (base - p.tray_thickness)) > 1e-6:
                continue
            for end_name, y in (('front', -148), ('rear', -22)):
                surfaces.append({'name': f'{tray["name"]}_{end_name}_support',
                                 'target': tray['name'], 'assembly': name,
                                 'origin': [tray['origin'][0], y, base - p.tray_thickness],
                                 'size': [tray['size'][0], 20, 0],
                                 'normal': [0, 0, 1], 'kind': 'moving_tray_support',
                                 'description': '取り外せる本体トレーの下面を固定棚の前後帯で支える'})
        assemblies.append({'name': name, 'kind': 'node_shelf', 'origin': origin, 'size': size,
                           'part_count': 3, 'support_z': base - p.tray_thickness,
                           'open_under_equipment': True})
    floor, origin, size = _power_floor(p)
    for col, row, shape in _tiles(floor, origin, size, 3, 2, p.lap_length):
        parts.append({'name': f'power_floor_{row}_{col}',
                      'label': f'電源の固定支持床・{row + 1}列目・{col + 1}分割目',
                      'shape': shape, 'role': 'power_floor'})
    for side in ('left', 'right'):
        for segment, y, depth in (('front', -280, 96), ('rear', -56, 166)):
            sockets.append(_socket(f'power_floor_{side}_{segment}', side, y, depth, 8, 24, p))
    for x, y in ([(x, y) for x in (-end / 3, end / 3) for y in (-272, 102)] +
                 [(x, -85) for x in (-2 * end / 3, 0, 2 * end / 3)]):
        add_fastener('power_floor', x, y, 8, 24)
    for tray in scene['power_trays']:
        for y in (-247, -199, -51, 5):
            lo = max(y, tray['origin'][1])
            hi = min(y + 10, tray['origin'][1] + tray['size'][1])
            if hi > lo:
                surfaces.append({'name': f'{tray["name"]}_{y}_support',
                                 'target': tray['name'], 'assembly': 'power_floor',
                                 'origin': [tray['origin'][0], lo, 32],
                                 'size': [tray['size'][0], hi - lo, 0],
                                 'normal': [0, 0, 1], 'kind': 'moving_tray_support',
                                 'description': '取り外せる電源トレーの下面を固定床の横帯で支える'})
        for side, x in (('left', tray['origin'][0]),
                        ('right', tray['origin'][0] + tray['size'][0] - 8)):
            surfaces.append({'name': f'{tray["name"]}_{side}_edge_support',
                             'target': tray['name'], 'assembly': 'power_floor',
                             'origin': [x, tray['origin'][1], 32],
                             'size': [8, tray['size'][1], 0], 'normal': [0, 0, 1],
                             'kind': 'moving_tray_support',
                             'description': '電源トレーの左右縁をT字断面の縦帯で連続支持する'})
    assemblies.append({'name': 'power_floor', 'kind': 'power_floor', 'origin': origin,
                       'size': size, 'part_count': 6, 'support_z': 32,
                       'rib_z_range': [8, 24], 'fan_clearance_x': [-230, 230],
                       'fan_clearance_y': [-184, -56],
                       'rib_structure': '上面8mm、荷重帯の縦ウェブ4mm、重ね継ぎウェブ8mmの開放T字断面',
                       'screw_boss_diameter_mm': 14,
                       'print_candidate': '上面を造形台へ向け、床下リブを上へ立ち上げる',
                       'lap_print_validation': '重ね継ぎの段差に必要な支持材と接合強度は未検証',
                       'closed_internal_cavities': False})
    for assembly in assemblies:
        assembly['cad_solid_volume_mm3'] = sum(item['shape'].Volume for item in parts
                                               if item['name'].startswith(assembly['name'] + '_'))
    replaced = [f'node_rail_{level}_{end}' for level in range(2) for end in ('front', 'rear')]
    replaced += ['frame_bottom_front', 'frame_bottom_rear'] + [f'power_rail_{i}' for i in range(4)]
    metadata = {'socket_envelopes': sockets, 'support_surfaces': surfaces,
                'fastener_candidates': fasteners,
                'bearing_surfaces': [{'name': socket['name'], 'side': socket['side'],
                                      'origin': socket['bearing_origin'], 'size': socket['bearing_size'],
                                      'normal': [0, 0, 1], 'kind': 'frame_bearing'}
                                     for socket in sockets],
                'assemblies': assemblies, 'replaced_cross_beams': replaced,
                'old_split_part_count': 30, 'integrated_part_count': len(parts),
                'status': '形状候補。実物の材料・耐荷重・締結を検証するまで造形用へ出力しない。'}
    return parts, metadata
