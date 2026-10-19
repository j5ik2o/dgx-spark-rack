"""部品別の造形姿勢と指定断面の検査。スライス済みの製造データではない。"""
import FreeCAD as App
import Part

AXES = ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1))
DIRECTION_LABELS = ('右','左','後ろ','前','上','下')


def tight_bounds(shape):
    b = shape.optimalBoundingBox(False)
    return [b.XMin,b.YMin,b.ZMin],[b.XMax,b.YMax,b.ZMax]


def bed_faces(shape, axis):
    index = next(i for i,v in enumerate(axis) if v)
    low, high = tight_bounds(shape)
    coordinate = low[index] if axis[index] > 0 else high[index]
    faces = []
    for face in shape.Faces:
        lo, hi = tight_bounds(face)
        if hi[index]-lo[index] < 1e-6 and abs(lo[index]-coordinate) < 1e-6:
            faces.append(face)
    return faces


def orientation(shape, axis):
    """組立座標から単品の造形姿勢へ。反転・拡大縮小は行わない。"""
    w = App.Vector(*axis)
    u = next(App.Vector(*a) for a in AXES if abs(App.Vector(*a).dot(w)) < 1e-6)
    v = w.cross(u)
    rows = [list(u),list(v),list(w)]
    matrix = App.Matrix()
    for row in range(3):
        for col in range(3):
            setattr(matrix, f'A{row+1}{col+1}', rows[row][col])
    transformed = shape.copy()
    transformed.Placement = App.Placement(matrix).multiply(transformed.Placement)
    low, high = tight_bounds(transformed)
    transformed.translate(App.Vector(*[-n for n in low]))
    return dict(matrix=[rows[i]+[-low[i]] for i in range(3)],
                size_mm=[high[i]-low[i] for i in range(3)], shape=transformed)


def preferred_orientation(entry, model):
    name, kind = entry['name'], entry['kind']
    if kind == 'joint_key':
        return entry['grip']['print_build_axis'], '角栓の軸とつまみの曲がりを層の面内に置き、全長を平面で接地。', '不要の候補。はめ合い面に支持材を付けず、実際の経路はスライサーで確認。'
    if kind == 'fan_pin':
        return [0,0,1], '軸と二股がたわむ方向を層の面内に置き、切り欠いた平面を下にする。', '不要の候補。半円部と返しの経路をスライサーで確認。'
    if kind in ('controller','controller_lid'):
        controller = next(e for e in model['scene']['equipment'] if name.startswith(e['name']+'_') and e['kind']=='controller')
        sign = 1 if kind=='controller' else -1
        return [sign*v for v in controller['w']], 'ケースは底面を下、蓋は天面を下。基板押さえは蓋から上へ造形。', '開口の橋渡しと基板押さえの張出しを確認。端子と基板の着座面へ支持痕を残さない。'
    if name.endswith('_holder'):
        fan = next(e for e in model['scene']['equipment'] if name==e['name']+'_holder')
        if fan['axis'][0]:
            return fan['axis'], '側面ファンの取付板を平置きし、取付穴を造形台に垂直にする。', '不要の候補。穴と接合口をスライサーで確認。'
        options = [(1,0,0),(-1,0,0)]
        axis = max(options, key=lambda a:sum(f.Area for f in bed_faces(entry['shape'],a)))
        return axis, '前後ファンは側辺を下にし、長い腕を層の面内に置く。', '反対側の腕と枠の張出しに支持が必要。穴・ほぞ・角栓の通路には接触させない。'
    if kind == 'body_connector':
        from body_frame_support_regions import precision_area
        options = AXES[2:4]
        axis = min(options,key=lambda a:(precision_area(entry,model,a),
                                        -sum(f.Area for f in bed_faces(entry['shape'],a))))
        return axis, '上下の荷重が通る方向を層の面内に置き、機器に向く広い面へ支持材が掛かりにくい前後方向を選ぶ。', '一体化した受け・腕・ドックの張出しに支持が必要。受け面と差込口は支持範囲から外す。'
    return [0,0,1], '受け板を平置きし、床と主な張出しを層の面内に置く。', '側方の抜け止め・腕の下を確認。必要な支持が機器の受け面へ掛からないか確認。'


def check_joint_sections(model):
    """全形状の最小肉厚ではなく、栓の中央断面とほぞの両側の残り肉を測る。"""
    items = {e['name']:e for e in model['parts']}
    records = []
    for joint in model['scene']['screwless_assembly']['joints']:
        normal = joint['normal_axis']
        axis = next(i for i,v in enumerate(joint['key_axis']) if v)
        other = next(i for i in range(3) if i not in (normal,axis))
        center = list(joint['contact_point_mm'])
        center[normal] += joint['insertion_axis'][normal]*joint['engagement_mm']/2
        width, clearance = joint['key_shaft_width_mm'], joint['key_slot_clearance_mm']
        size = [width]*3
        size[axis] = .2
        low = [center[i]-size[i]/2 for i in range(3)]
        probe = Part.makeBox(*size,App.Vector(*low))
        volume = probe.common(items[joint['key']]['shape']).Volume
        if abs(volume-probe.Volume) > 1e-5 or width < model['parameters'].joint_key_min_width-1e-6:
            raise ValueError('角栓の指定断面が細いか欠けています: '+joint['key'])
        remaining = []
        for dimension, span in ((normal,joint['engagement_mm']),
                                (other,joint['tenon_widths_mm'][[i for i in range(3) if i!=normal].index(other)])):
            thickness = span/2-width/2-clearance
            if thickness < model['parameters'].joint_min_ligament-1e-6:
                raise ValueError('ほぞの角栓穴の周囲が薄すぎます: '+joint['name'])
            for side in (-1,1):
                size = [.2]*3
                size[dimension] = thickness-.02
                low = [center[i]-size[i]/2 for i in range(3)]
                ends = sorted((center[dimension]+side*(width/2+clearance+.01),
                               center[dimension]+side*(span/2-.01)))
                low[dimension] = ends[0]
                probe = Part.makeBox(*size,App.Vector(*low))
                if abs(probe.common(items[joint['donor']]['shape']).Volume-probe.Volume) > 1e-5:
                    raise ValueError('ほぞの残り肉の指定断面が欠けています: '+joint['name'])
            remaining.append(thickness)
        records.append(dict(joint=joint['name'],key=joint['key'],shaft_width_mm=width,
                            measured_shaft_area_mm2=volume/.2,remaining_ligaments_mm=remaining))
    return records


def build_print_plan(model):
    p = model['parameters']
    entries = model['parts']+[e for e in model['references'] if e['kind'] in ('controller','controller_lid')]
    parts = []
    for entry in entries:
        axis, reason, support = preferred_orientation(entry, model)
        candidate = orientation(entry['shape'], axis)
        size = candidate['size_mm']
        brim = 5
        if max(size[:2])+2*brim > p.usable_print_size+1e-6 or size[2] > p.usable_print_size+1e-6:
            raise ValueError('造形方向と外周5mmの接着補助を含めて造形範囲に入りません: '+entry['name'])
        bed = bed_faces(entry['shape'],axis)
        area = sum(f.Area for f in bed)
        if area < 1:
            raise ValueError('造形台へ平面で接地しません: '+entry['name'])
        if entry['kind'] in ('joint_key','fan_pin'):
            shaft_axis = next(i for i,v in enumerate(entry['grip']['axis']) if v) if entry['kind']=='joint_key' else next(
                i for i,v in enumerate(next(f for f in model['scene']['equipment'] if f['name']==entry['moves_with'])['axis']) if v)
            low, high = tight_bounds(entry['shape'])
            bed_low, bed_high = tight_bounds(Part.makeCompound(bed))
            if abs((bed_high[shaft_axis]-bed_low[shaft_axis])-(high[shaft_axis]-low[shaft_axis])) > 1e-5:
                raise ValueError('角栓または割りピンが全長にわたって接地しません: '+entry['name'])
        parts.append(dict(name=entry['name'],label=entry['label'],kind=entry['kind'],
                          build_axis=list(axis), build_direction='組立状態の'+DIRECTION_LABELS[AXES.index(tuple(axis))]+'方向',
                          transform=candidate['matrix'], size_mm=size, brim_mm=brim,
                          bed_contact_mm2=area, reason=reason, support_review=support))
    sections = check_joint_sections(model)
    case = model['scene']['controller_case_assembly']['nominal_thickness_mm']
    return dict(status='candidate', parts=parts, printed_part_count=len(parts),
                rack_parts=len(model['parts']),controller_case_parts=len(entries)-len(model['parts']),
                critical_sections=sections,minimum_key_width_mm=min(r['shaft_width_mm'] for r in sections),
                minimum_tenon_ligament_mm=min(min(r['remaining_ligaments_mm']) for r in sections),
                nominal_thickness_mm=dict(fan_plate=p.fan_plate,fan_arm=p.fan_arm_size,tray=p.tray_thickness,
                                          core_corner=p.corner_outside,controller_case=case),
                fan_pin=dict(shaft_diameter_mm=3.6,slot_width_mm=.9,split_length_mm=p.fan_pin_split_length,
                             root_radius_mm=.45,flat_offset_mm=p.fan_pin_flat_offset,
                             prong_center_section_mm=1.35,head_thickness_mm=1.6,
                             exception='二股の中央断面1.35mmと頭1.6mmは薄肉の例外。弾性・破損・繰り返し使用は本番素材で確認。'),
                material=dict(prototype='ポリ乳酸（仮組み用）',production='炭素繊維入り耐熱ナイロン PAHT-CF・黒',
                              source='print-projects/README.md',production_settings='未設定・本番生成は停止'),
                scope='指定断面、平面の接地、造形範囲と姿勢の候補。全形状の最小肉厚・支持材除去・強度の合格判定ではない。',
                physical_validation=False,slicer_validated=False,manufacturing_geometry=False,
                remaining=['本番のノズル・積層厚・外周数・充填率・乾燥と収縮の条件',
                           '支持材の配置・除去と、はめ合い面の品質をスライサーで確認',
                           '本番素材での割りピンの弾性、角栓の適合、曲げ・繰り返し・長期荷重'])
