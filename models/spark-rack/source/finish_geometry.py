"""上部専用段の案の前面と天面を閉じる板。溝の間隔は前面のファン格子にそろえる。

最上段の前面の板は上枠の下へ受け板を差し込み、上向きのねじで吊る。天板は枠の上に載せ、
裏の縁を枠の内側へ入れて位置を決める。最下段の左右の板は扉の後ろに置き、下端の受け板を
電源の床へ留める。形状候補で造形用ではない。
"""
import FreeCAD as App
import Part

from integrated_rack_supports import _box, _fuse, _tiles, _window


def _hole(x, y, z, length, axis=(0, 0, 1)):
    return Part.makeCylinder(2.25, length, App.Vector(x, y, z), App.Vector(*axis))


def _slot(x, y, z, width, depth, height):
    """前後方向に抜く角丸の縦溝。"""
    shape = _box((x, y, z), (width, depth, height))
    edges = [e for e in shape.Edges if abs(e.BoundBox.YLength - depth) < 1e-7]
    return shape.makeFillet(width / 2 - 1e-3, edges)


def _slotted_plate(x0, x1, y, z0, z1, thickness, p, q, pattern=None):
    plate = _box((x0, y, z0), (x1 - x0, thickness, z1 - z0))
    if pattern is not None and pattern.style == 'honeycomb':
        from grille_patterns import cut_all, honeycomb_in_rect
        return cut_all(plate, honeycomb_in_rect(x0 + q['edge_margin'], x1 - q['edge_margin'],
                                                z0 + q['slot_margin'], z1 - q['slot_margin'], y - 1, thickness + 2,
                                                'xz', pattern.hex_across_flats, pattern.hex_wall))
    slots, x = [], x0 + q['edge_margin']
    while x + p.vent_slot_width <= x1 - q['edge_margin'] + 1e-9:
        slots.append(_slot(x, y - 1, z0 + q['slot_margin'], p.vent_slot_width, thickness + 2,
                           z1 - z0 - 2 * q['slot_margin']))
        x += 10
    return plate.cut(Part.makeCompound(slots)) if slots else plate


def _covers(p, finish, beam, pattern=None):
    q = finish['parameters']
    t = q['panel_thickness']
    y = finish['panel_y']
    z0, z1 = finish['cover_z']
    beam_back = beam['origin'][1] + beam['size'][1]
    parts, holes = [], []
    for name in finish['removable_covers']:
        b = next(o for o in finish['objects'] if o['name'] == name)
        x0, x1 = b['origin'][0], b['origin'][0] + b['size'][0]
        shape = _slotted_plate(x0, x1, y, z0, z1, t, p, q, pattern)
        # 上枠の下面へ当てる受け板。前へ引けば上枠から外れる。
        flange = _box((x0, y + t, z1 - q['flange_thickness']), (x1 - x0, beam_back - (y + t), q['flange_thickness']))
        shape = shape.fuse(flange)
        width = x1 - x0
        piece_holes = [(x0 + width / 4, (y + t + beam_back) / 2), (x1 - width / 4, (y + t + beam_back) / 2)]
        for hx, hy in piece_holes:
            shape = shape.cut(_hole(hx, hy, z1 - q['flange_thickness'] - 1, q['flange_thickness'] + 2))
        holes += [(name, hx, hy) for hx, hy in piece_holes]
        parts.append({'name': name, 'label': b['label'], 'shape': shape.removeSplitter(), 'role': 'removable_cover'})
    return parts, holes


def _lid(p, finish, pattern=None):
    q = finish['parameters']
    z = p.height
    half_w = p.width / 2
    inner = p.inner_width / 2 - p.fit_clearance
    y0, y1 = finish['lid_inner_y']
    rib_z = z - q['lid_rib']
    joint_x = p.width / 6
    joint_y = (p.front_y + p.rear_y) / 2
    plate = _box((-half_w, p.front_y, z), (p.width, p.depth, q['lid_plate']))
    # 前後方向の溝かハニカム。継ぎ目のリブと縁の上は避ける。
    slots = []
    honeycomb = pattern is not None and pattern.style == 'honeycomb'
    for ylo, yhi in ((y0 + 16, joint_y - 16), (joint_y + 16, y1 - 16)):
        if honeycomb:
            from grille_patterns import honeycomb_in_rect
            for xlo, xhi in ((-inner + q['edge_margin'], -joint_x - 12), (-joint_x + 12, joint_x - 12),
                             (joint_x + 12, inner - q['edge_margin'])):
                slots += honeycomb_in_rect(xlo, xhi, ylo, yhi, z - 1, q['lid_plate'] + 2, 'xy',
                                           pattern.hex_across_flats, pattern.hex_wall)
            continue
        x = -inner + q['edge_margin']
        while x + p.vent_slot_width <= inner - q['edge_margin'] + 1e-9:
            if not any(abs(x + p.vent_slot_width / 2 - j) < 12 for j in (-joint_x, joint_x)):
                slots.append(_window(x, ylo, z - 1, p.vent_slot_width, yhi - ylo, q['lid_plate'] + 2, p.vent_slot_width / 2))
            x += 10
    plate = plate.cut(Part.makeCompound(slots))
    lip = q['lid_lip']
    ribs = [_box((-inner, y0, rib_z), (lip, y1 - y0, q['lid_rib'])),
            _box((inner - lip, y0, rib_z), (lip, y1 - y0, q['lid_rib'])),
            _box((-inner, y0, rib_z), (2 * inner, lip, q['lid_rib'])),
            _box((-inner, y1 - lip, rib_z), (2 * inner, lip, q['lid_rib'])),
            _box((-inner, joint_y - 4, rib_z), (2 * inner, 8, q['lid_rib']))]
    ribs += [_box((j - 4, y0, rib_z), (8, y1 - y0, q['lid_rib'])) for j in (-joint_x, joint_x)]
    lid = _fuse([plate] + ribs)
    # 上枠と側枠の上面へ留めるねじ穴。継ぎ目の重ね部分は避ける。
    beam_y = [p.front_y + p.section / 2, p.rear_y - p.section / 2]
    side_x = [-half_w + p.section / 2, half_w - p.section / 2]
    holes = [(x, y) for x in (-180, 0, 180) for y in beam_y]
    holes += [(x, y) for x in side_x for y in (p.front_y + 60, joint_y - 60, joint_y + 60, p.rear_y - 60)]
    for x, y in holes:
        lid = lid.cut(_hole(x, y, z - 1, q['lid_plate'] + 2))
    return lid.removeSplitter(), [-half_w, p.front_y, rib_z], [p.width, p.depth, q['lid_rib'] + q['lid_plate']], holes


def _fillers(p, finish, pattern=None):
    q = finish['parameters']
    t = q['panel_thickness']
    y = finish['filler_y']
    z0, z1 = finish['filler_z']
    floor_top = 32
    parts, holes = [], []
    for name in ('lower_filler_left', 'lower_filler_right'):
        b = next(o for o in finish['objects'] if o['name'] == name)
        x0, x1 = b['origin'][0], b['origin'][0] + b['size'][0]
        shape = _slotted_plate(x0, x1, y, z0, z1, t, p, q, pattern)
        # 下端の受け板を電源の床の上面へ載せる。
        flange = _box((x0, y + t, floor_top), (x1 - x0, q['filler_flange_depth'], q['flange_thickness']))
        shape = shape.fuse(flange)
        hy = y + t + q['filler_flange_depth'] / 2
        piece_holes = [((x0 + x1) / 2, hy)]
        for hx, _ in piece_holes:
            shape = shape.cut(_hole(hx, hy, floor_top - 1, q['flange_thickness'] + 2))
        holes += [(name, hx, hy) for hx, hy in piece_holes]
        parts.append({'name': name, 'label': b['label'], 'shape': shape.removeSplitter(), 'role': 'lower_filler'})
    return parts, holes


def finish_parts(scene, p, finish, pattern=None):
    """部品一覧と、支持面・ねじ候補を integrated_supports と同じ形式で返す。"""
    beam = next(b for b in scene['cross_beams'] if b['name'] == 'frame_top_front')
    covers, cover_holes = _covers(p, finish, beam, pattern)
    lid, origin, size, lid_holes = _lid(p, finish, pattern)
    lid_parts = []
    for col, row, shape in _tiles(lid, origin, size, 3, 2, p.lap_length):
        lid_parts.append({'name': f'top_lid_{row}_{col}', 'label': f'溝付きの天板・{row + 1}列目・{col + 1}分割目',
                          'shape': shape, 'role': 'top_lid'})
    fillers, filler_holes = _fillers(p, finish, pattern)
    parts = covers + lid_parts + fillers
    fasteners = [{'assembly': 'bay_cover', 'part': name, 'axis': [0, 0, 1],
                  'origin': [x, y, finish['cover_z'][1] - finish['parameters']['flange_thickness']],
                  'through_length_mm': finish['parameters']['flange_thickness'], 'hole_diameter_mm': 4.5,
                  'thread_nominal_diameter_mm': 4, 'removable': True,
                  'head_and_nut_retention': '上枠側は熱圧入ナットの候補で未確定',
                  'status': '最上段の前面の板を上枠の下へ吊る。スイッチ前側の交換時に外す。'} for name, x, y in cover_holes]
    fasteners += [{'assembly': 'top_lid', 'axis': [0, 0, 1], 'origin': [x, y, p.height],
                   'through_length_mm': finish['parameters']['lid_plate'], 'hole_diameter_mm': 4.5,
                   'thread_nominal_diameter_mm': 4, 'head_and_nut_retention': '枠側は熱圧入ナットの候補で未確定',
                   'status': '天板を上枠と側枠の上面へ留める'} for x, y in lid_holes]
    fasteners += [{'assembly': 'lower_filler', 'part': name, 'axis': [0, 0, 1], 'origin': [x, y, 32],
                   'through_length_mm': finish['parameters']['flange_thickness'], 'hole_diameter_mm': 4.5,
                   'thread_nominal_diameter_mm': 4, 'head_and_nut_retention': '電源の床側は熱圧入ナットの候補で未確定',
                   'status': '最下段の左右の板を電源の床へ留める'} for name, x, y in filler_holes]
    beams = [f'frame_top_front_{i}' for i in range(3)]
    frame_tops = beams + [f'frame_top_rear_{i}' for i in range(3)]
    frame_tops += [f'side_{side}_2_{col}' for side in ('left', 'right') for col in range(2)]
    carried = [{'target': c['name'], 'supports': beams, 'z': finish['cover_z'][1], 'each': False,
                'minimum_area_mm2': 200, 'support_above': True} for c in covers]
    carried += [{'target': t['name'], 'supports': frame_tops, 'z': p.height, 'each': False,
                 'minimum_area_mm2': 200} for t in lid_parts]
    floor_tiles = [f'power_floor_0_{col}' for col in range(3)]
    carried += [{'target': f['name'], 'supports': floor_tiles, 'z': 32, 'each': False,
                 'minimum_area_mm2': 200} for f in fillers]
    assembly = {'name': 'front_finish', 'kind': 'front_finish', 'origin': [0, 0, 0], 'size': [0, 0, 0],
                'part_count': len(parts), 'support_z': None, 'carried': carried}
    metadata = {'socket_envelopes': [], 'support_surfaces': [], 'fastener_candidates': fasteners,
                'bearing_surfaces': [], 'assemblies': [assembly], 'part_count': len(parts),
                'status': '形状候補。溝の開口と風量、板の固定の実物確認前。造形用へ出力しない。'}
    return parts, metadata
