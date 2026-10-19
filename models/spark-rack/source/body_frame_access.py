"""角栓をつまむ空間の仮条件。人体寸法や操作力の適合を保証する値ではない。"""
import FreeCAD as App
import Part


FINGER_SIZE = [12, 10, 12]  # 接合面の法線、つまみを挟む方向、栓の引出し方向。
TAB_WIDTH = 10
TAB_START = 4
TAB_END = 10


def rectangular(low, high):
    return Part.makeBox(*[high[i]-low[i] for i in range(3)], App.Vector(*low))


def key_grip(center, end, axis, sign, normal, shaft_width, offset=0, flat_side=-1):
    """細い栓の外側へ、幅10mmの平たいつまみと二指分の予約を作る。"""
    other = next(i for i in range(3) if i not in (axis, normal))
    low, high = list(center), list(center)
    for i in (normal, other):
        low[i], high[i] = center[i]-shaft_width/2-1, center[i]+shaft_width/2+1
    bed = center[other]+flat_side*shaft_width/2
    if flat_side < 0:
        low[other] = bed
    else:
        high[other] = bed
    low[axis], high[axis] = sorted((end, end+sign*TAB_START))
    low[normal] += min(0, offset)
    high[normal] += max(0, offset)
    neck = rectangular(low, high)
    low[normal], high[normal] = center[normal]+offset-shaft_width/2-1, center[normal]+offset+shaft_width/2+1
    low[other], high[other] = sorted((bed, bed-flat_side*TAB_WIDTH))
    low[axis], high[axis] = sorted((end+sign*TAB_START, end+sign*TAB_END))
    tab = rectangular(low, high)
    fingers = []
    for side in (-1, 1):
        fl, fh = list(low), list(high)
        fl[normal], fh[normal] = center[normal]+offset-FINGER_SIZE[0]/2, center[normal]+offset+FINGER_SIZE[0]/2
        fl[axis], fh[axis] = sorted((end+sign*3, end+sign*15))
        edge = low[other] if side < 0 else high[other]
        fl[other], fh[other] = sorted((edge, edge+side*FINGER_SIZE[1]))
        fingers.append(dict(origin=fl, size=[fh[i]-fl[i] for i in range(3)]))
    return neck.fuse(tab).removeSplitter(), dict(
        tab_width_mm=TAB_WIDTH, tab_length_mm=TAB_END-TAB_START,
        tab_thickness_mm=shaft_width+2, stand_off_mm=TAB_START, grip_offset_mm=offset,
        print_build_axis=[-flat_side if i==other else 0 for i in range(3)],
        print_bed_coordinate_mm=bed,
        axis=[sign if i == axis else 0 for i in range(3)],
        finger_boxes=fingers, assumption='各指12×10×12mmの直方体。素手の仮の操作空間で、人体寸法の規格値ではない。')


def finger_shape(grip):
    return Part.makeCompound([Part.makeBox(*b['size'], App.Vector(*b['origin'])) for b in grip['finger_boxes']])


def grip_path(items, key, grip, fixed, path):
    """栓と一緒に指を動かす経路と、着座後に指だけ離す経路を検査する。"""
    from body_frame_assembly import MotionCheck
    name = key+'_fingers'
    entries = dict(items, **{name:dict(shape=finger_shape(grip))})
    check = MotionCheck(entries)
    if check.path({name}, fixed, path):
        return False
    # 栓を置いた後も、引出し方向へ指を離せること。
    release = [[0, 0, 0], [v*30 for v in grip['axis']]]
    return check.path({name}, set(fixed)|{key}, release) is None


def fan_key_path(items, key):
    """ファンの抜け止めは、他を載せた状態でも栓と指を直線で引ける候補を選ぶ。"""
    from body_frame_assembly import MotionCheck
    entry = items[key]
    grip = entry['grip']
    axis = grip['axis']
    index = next(i for i,v in enumerate(axis) if v)
    b = entry['shape'].BoundBox
    length = [b.XLength,b.YLength,b.ZLength][index]+2
    path = [[0,0,0],[v*length for v in axis]]
    fixed = set(items)-{key}
    # 羽根を省略した参考形状の空洞へ、指を通して合格させない。
    finger_items = dict(items)
    for name, e in items.items():
        if e['kind'] == 'fan':
            from body_frame_assembly import shape_bounds
            low, high = shape_bounds(e['shape'])
            finger_items[name] = dict(e, shape=rectangular(low, high))
    return (MotionCheck(items).path({key}, fixed, path) is None
            and grip_path(finger_items, key, grip, fixed, path))


def validate_access(model, plan):
    """実際の小組み順で、20箇所すべての指の空間を再検査する。"""
    items = {e['name']:e for e in model['parts']+model['references']}
    records = []
    for step in plan['bench_steps']:
        key = items[step['key']]
        grip = key['grip']
        fixed = set(step['fixed'])|set(step['moving'])
        if not grip_path(items, key['name'], grip, fixed, step['key_offsets']):
            raise ValueError('角栓をつまむ仮の指の経路が塞がっています: '+key['name'])
        records.append(dict(key=key['name'], joint=step['joint'], title=step['title'], **grip))
    releases = check_release_reservations(model)
    service_keys = [e['name'] for e in items.values() if e.get('unlock_before')]
    for key in service_keys:
        if not fan_key_path(items, key):
            raise ValueError('完成形状でファン用の角栓と指を直線で引けません: '+key)
    return dict(status='passed', key_grips=len(records), operations=records,
                fan_service_keys=service_keys,
                release_reservations=releases,
                scope='作業台の各接合工程で、二指の仮外形を栓と一緒に動かし、着座後に指だけ離す。分解は逆順。',
                finger_size_mm=FINGER_SIZE, physical_validation=False,
                not_verified=['手のひら・関節・手袋と操作力', '実物のはめ合いとつまみの強度',
                              '装着したままの全角栓の操作', '購入品の解除レバーとバックル・配線後の操作'])


def check_release_reservations(model):
    """解除部は外向き。未選定の購入品に対して、操作側の空間だけを先に予約する。"""
    from controller_mount import place
    from body_frame_assembly import MotionCheck, unit_bounds, shape_bounds
    from body_frame_geometry import block
    scene = model['scene']
    items = {e['name']:e for e in model['parts']+model['references']+model['cables']+model['cable_storage']}
    source = scene['controller_case_assembly']
    cx = -source['reference_shift'][0]
    # ケースの蓋上のバンド面から、解除頭の仮厚さ8mmを見込む。
    reservations = []
    for controller in (e for e in scene['equipment'] if e['kind']=='controller'):
        origin = controller['dock_origin']
        w = controller['w']
        lo, hi = unit_bounds({controller['name']+'_lid'}, items)
        axis = next(i for i,v in enumerate(w) if v)
        lid_depth = (hi[axis]-origin[axis]) if w[axis]>0 else (origin[axis]-lo[axis])
        for number, pcb_x in enumerate((5, 70)):
            local = block([pcb_x-cx-6, -6, lid_depth+1.2+8], [12, 12, 20])
            shape = place(local, origin, controller['u'], controller['v'], w)
            reservations.append(dict(name=controller['name']+f'_release_{number}',
                                     label=controller['label']+'・バンド解除部の前の予約', shape=shape,
                                     axis=w, source=controller['name']+f'_band_{number}',
                                     assumption='解除頭の仮厚さ8mm、操作側12×12×20mm。解除頭をケースの外側へ向ける。'))
    for band in scene['switch_retention']['bands']:
        x,y,z = band['buckle_origin']
        dx,dy,dz = band['buckle_size']
        for side in (-1,1):
            px = x-12 if side<0 else x+dx
            shape = block([px,y+(dy-12)/2,z], [12,12,20])
            reservations.append(dict(name=band['name']+f'_release_{side}',
                                     label='CRS812のバックルを両側から挟む仮空間', shape=shape,
                                     axis=[0,0,1], source=band['name']+'_buckle',
                                     assumption='参考バックルの両側に各12×12×20mm。上から手を入れる。'))
    for reservation in reservations:
        name = reservation['name']
        check = MotionCheck(dict(items, **{name:reservation}))
        path = [[v*30 for v in reservation['axis']], [0,0,0]]
        hit = check.path({name}, set(items), path)
        if hit:
            raise ValueError('バンドの解除部の前の予約が塞がっています: '+str(hit))
    return [dict(name=r['name'], label=r['label'], source=r['source'], axis=r['axis'],
                 bounds_mm=shape_bounds(r['shape']), assumption=r['assumption']) for r in reservations]
