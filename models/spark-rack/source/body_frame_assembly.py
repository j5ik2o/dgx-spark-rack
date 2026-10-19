"""剛体部品を通せる組立順を、作業台の小組みと本体への搭載に分けて確認する。"""
import FreeCAD as App
import Part

EPS = 1e-5
AXES = ((0, 0, 1), (0, -1, 0), (0, 1, 0), (-1, 0, 0), (1, 0, 0), (0, 0, -1))
SOFT_KINDS = {'switch_band', 'switch_buckle', 'controller_band'}


def shifted(shape, vector):
    result = shape.copy()
    result.translate(App.Vector(*vector))
    return result


def swept_box(shape, vector):
    b = shape.BoundBox
    low, high = [b.XMin, b.YMin, b.ZMin], [b.XMax, b.YMax, b.ZMax]
    lo = [min(low[i], low[i]+vector[i]) for i in range(3)]
    hi = [max(high[i], high[i]+vector[i]) for i in range(3)]
    return lo, hi


def boxes_overlap(first, second):
    return all(min(first[1][i], second[1][i])-max(first[0][i], second[0][i]) > 1e-6 for i in range(3))


def shape_bounds(shape):
    b = shape.BoundBox
    return [b.XMin, b.YMin, b.ZMin], [b.XMax, b.YMax, b.ZMax]


def sweep_probes(shape, vector):
    """端面を押し出し、軸平行の回転面と他の曲面は環状領域や外形箱で保守的に覆う。"""
    direction = App.Vector(*vector)
    unit = direction/direction.Length
    probes = [shape, shifted(shape, vector)]
    for face in shape.Faces:
        surface = face.Surface
        kind = surface.__class__.__name__
        if kind == 'Plane':
            if abs(face.normalAt(0, 0).dot(unit)) > 1e-7:
                prism = face.extrude(direction)
                if prism.Volume > EPS:
                    if not prism.isValid():
                        raise ValueError('組立経路の押出し形状が無効です')
                    probes.append(prism)
        elif kind in ('Cylinder', 'Cone') and abs(surface.Axis.dot(unit)) > 1-1e-7:
            # 軸方向の円柱・単調な円すいは端面と両端の立体で覆う。
            continue
        elif kind == 'Toroid' and abs(surface.Axis.dot(unit)) > 1-1e-7:
            # 穴の縁の丸めを箱に置き換えると、穴の中央まで塞いでしまう。
            # 回転軸と平行に動く場合は、中心を空けた環状の押出しで保守的に覆う。
            lo,hi = swept_box(face,vector)
            axis = max(range(3),key=lambda i:abs(vector[i]))
            center = [surface.Center.x,surface.Center.y,surface.Center.z]
            center[axis] = lo[axis]
            direction = App.Vector(*[int(i==axis) for i in range(3)])
            outer = Part.makeCylinder(surface.MajorRadius+surface.MinorRadius,
                                      hi[axis]-lo[axis],App.Vector(*center),direction)
            inner_radius = max(0,surface.MajorRadius-surface.MinorRadius)
            if inner_radius > 1e-7:
                inner = Part.makeCylinder(inner_radius,hi[axis]-lo[axis],App.Vector(*center),direction)
                outer = outer.cut(inner)
            probes.append(outer)
        else:
            lo, hi = swept_box(face, vector)
            if all(hi[i]-lo[i] > 1e-7 for i in range(3)):
                probes.append(Part.makeBox(*[hi[i]-lo[i] for i in range(3)], App.Vector(*lo)))
    return probes


class MotionCheck:
    def __init__(self, items):
        self.items = items
        self.bounds = {name:shape_bounds(e['shape']) for name,e in items.items()}
        self.cache = {}
        self.pair_cache = {}
        self.checked = 0

    def segment(self, moving, fixed, start, end):
        delta = [end[i]-start[i] for i in range(3)]
        if sum(abs(v)>1e-7 for v in delta) != 1:
            raise ValueError('組立経路は1軸ずつの平行移動で指定してください')
        for name in moving:
            shape = shifted(self.items[name]['shape'], start)
            region = swept_box(shape, delta)
            targets = [other for other in fixed if boxes_overlap(region, self.bounds[other])]
            if not targets:
                continue
            key = (name, tuple(round(v, 6) for v in start), tuple(round(v, 6) for v in end))
            pending = []
            for other in targets:
                pair = key+(other,)
                if pair not in self.pair_cache:
                    pending.append(other)
                elif self.pair_cache[pair]:
                    return [name, other]
            if not pending:
                continue
            probes = self.cache.get(key)
            if probes is None:
                probes = [(p, shape_bounds(p)) for p in sweep_probes(shape, delta)]
                self.cache[key] = probes
            for other in pending:
                for probe, bounds in probes:
                    if boxes_overlap(bounds, self.bounds[other]):
                        self.checked += 1
                        if probe.common(self.items[other]['shape']).Volume > EPS:
                            self.pair_cache[key+(other,)] = True
                            return [name, other]
                self.pair_cache[key+(other,)] = False
        return None

    def path(self, moving, fixed, offsets):
        for start,end in zip(offsets, offsets[1:]):
            hit = self.segment(moving, fixed, start, end)
            if hit:
                return hit
        return None


def unit_bounds(names, items, offset=(0, 0, 0)):
    bounds = [shape_bounds(items[n]['shape']) for n in names]
    return ([min(b[0][i] for b in bounds)+offset[i] for i in range(3)],
            [max(b[1][i] for b in bounds)+offset[i] for i in range(3)])


def outside_offset(moving, fixed, items, axis, start=(0, 0, 0)):
    lo,hi = unit_bounds(moving, items, start)
    flo,fhi = unit_bounds(fixed or moving, items)
    index = next(i for i,v in enumerate(axis) if v)
    distance = fhi[index]-lo[index]+25 if axis[index] > 0 else hi[index]-flo[index]+25
    return [start[i]+axis[i]*max(25, distance) for i in range(3)]


def escape(check, moving, fixed, axis, first_distance):
    first = [axis[i]*first_distance for i in range(3)]
    if check.path(moving, fixed, [[0, 0, 0], first]):
        return None
    for direction in (tuple(axis),)+tuple(a for a in AXES if tuple(a) != tuple(axis)):
        end = outside_offset(moving, fixed, check.items, direction, first)
        if check.path(moving, fixed, [first, end]) is None:
            return [[0, 0, 0], first, end]
    return None


def part_label(name, scene):
    equipment = {e['name']:e['label'] for e in scene['equipment']}
    if name in ('comet','kvm','crs812'):
        return {'comet':'GL-RM10','kvm':'TESmart切替器','crs812':'CRS812'}[name]
    if name.startswith('power_'):
        _,col,row = name.split('_')
        return ('左' if col=='0' else '右')+'列の'+('手前' if row=='0' else '後ろ')+'の電源アダプター'
    if name in equipment:
        return equipment[name].replace('・正立','')
    labels = {
        'core_foot_pair_front':'下部受けの前側・左と中央', 'core_foot_right_front':'下部受けの前側・右',
        'core_foot_pair_back':'下部受けの後ろ側・左と中央', 'core_foot_right_back':'下部受けの後ろ側・右',
        'core_top_pair_front':'上部支持部の前側・左と中央', 'core_top_right_front':'上部支持部の前側・右',
        'core_top_pair_back':'上部支持部の後ろ側・左と中央', 'core_top_right_back':'上部支持部の後ろ側・右',
        'cable_outreach_0':'左側のケーブル余長受け', 'cable_outreach_1':'右側のケーブル余長受け',
        'signal_storage_floor_0':'左下の映像ケーブル受け',
        'network_rail_-1_front':'スイッチ左レールの前半', 'network_rail_-1_rear':'スイッチ左レールの後半',
    }
    return labels.get(name, '連結部またはファン保持部')


def build_plan(model, progress=None):
    from validate_body_frame import components
    from body_frame_access import grip_path
    scene = model['scene']
    all_entries = model['parts']+model['references']
    items = {e['name']:e for e in all_entries if e['kind'] not in SOFT_KINDS}
    check = MotionCheck(items)
    joints = scene['screwless_assembly']['joints']
    frame_names = {e['name'] for e in scene['screwless_assembly']['integrated_parts']}
    graph_edges = [(j['donor'], j['receiver'], 1) for j in joints]
    groups = components(frame_names, graph_edges)

    def rigid_members(parts, js):
        result = set(parts) | {j['key'] for j in js}
        for e in all_entries:
            fan = e.get('moves_with')
            if fan and fan+'_holder' in parts:
                result.add(e['name'])
        for fan in (e for e in scene['equipment'] if e['kind']=='fan'):
            if fan['name']+'_holder' in parts:
                result.add(fan['name'])
        return result

    bench_cache = {}

    def bench(parts, js, label):
        key = tuple(sorted(parts))
        if key not in bench_cache:
            bench_cache[key] = bench_impl(parts, js, label)
        return bench_cache[key]

    def bench_impl(parts, js, label):
        if len(parts) == 1:
            return []
        options = []
        for joint in js:
            edges = [(j['donor'],j['receiver'],1) for j in js if j is not joint]
            split = components(parts, edges)
            if len(split) != 2:
                continue
            options.append((abs(len(split[0])-len(split[1])),joint,split))
        for _,joint,split in sorted(options, key=lambda o:(o[0],o[1]['name'])):
            whole = rigid_members(parts, js)
            key = joint['key']
            a = next(i for i,v in enumerate(joint['key_axis']) if v)
            b = items[key]['shape'].BoundBox
            length = [b.XLength,b.YLength,b.ZLength][a]+2
            key_path = escape(check, {key}, whole-{key}, joint['key_axis'], length)
            if key_path is None:
                continue
            if not grip_path(items, key, items[key]['grip'], whole-{key}, key_path):
                continue
            choices = sorted(split, key=lambda x:(len(x),x))
            for moving_parts in choices:
                stationary_parts = next(p for p in split if p is not moving_parts)
                mj = [j for j in js if j is not joint and j['donor'] in moving_parts and j['receiver'] in moving_parts]
                sj = [j for j in js if j is not joint and j['donor'] in stationary_parts and j['receiver'] in stationary_parts]
                moving = rigid_members(moving_parts, mj)
                fixed = rigid_members(stationary_parts, sj)
                sign = -1 if joint['donor'] in moving_parts else 1
                direction = [sign*v for v in joint['insertion_axis']]
                path = escape(check, moving, fixed, direction, joint['engagement_mm']+2)
                if path is None:
                    continue
                first = bench(set(stationary_parts), sj, label)
                if first is None:
                    continue
                second = bench(set(moving_parts), mj, label)
                if second is None:
                    continue
                operation = dict(stage='bench', title=label+'：'+part_label(joint['donor'],scene)+'を合わせ、角栓を差す',
                                 moving=sorted(moving), fixed=sorted(fixed), offsets=list(reversed(path)),
                                 key=key, key_offsets=list(reversed(key_path)), joint=joint['name'],
                                 support='作業台で小組みする。合体前の両方のユニットを手で支える。')
                return first+second+[operation]
        return None

    units = []
    bench_steps = []
    def group_order(group):
        if any(n.startswith('core_foot_') for n in group):
            return 0 if any(n.startswith('core_foot_') and n.endswith('_front') for n in group) else 1
        if any(n.startswith('core_joint_') for n in group):
            return 2 if any(n.startswith('core_joint_') and n.endswith('_front') for n in group) else 3
        return 4
    for group in sorted(groups,key=group_order):
        if any(n.startswith('core_top_') for n in group):
            label, role = '上部の支持ユニット', 'top'
        elif any(n.startswith('core_foot_') for n in group):
            front = any(n.startswith('core_foot_') and n.endswith('_front') for n in group)
            label,role = ('前側の下部受けユニット','base_front') if front else ('後ろ側の下部受けユニット','base_rear')
        else:
            front = any(n.startswith('core_joint_') and n.endswith('_front') for n in group)
            label,role = ('前側の中間連結ユニット','middle_front') if front else ('後ろ側の中間連結ユニット','middle_rear')
        js = [j for j in joints if j['donor'] in group and j['receiver'] in group]
        if progress:
            progress(label+'の小組みを検査')
        steps = bench(set(group), js, label)
        if steps is None:
            raise ValueError('小組みの最後の部材または角栓が入りません: '+label)
        bench_steps += steps
        units.append(dict(role=role, title=label, members=sorted(rigid_members(group, js))))

    installed = set()
    mount_steps = []
    unit_map = {u['role']:u for u in units}

    def mount(names, label, direction, phase):
        moving = set(names)
        if progress:
            progress(label)
        if installed & moving:
            raise ValueError('同じ部品を二度取り付けようとしています')
        far = outside_offset(moving, installed or (set(items)-moving), items, direction)
        path = [far, [0, 0, 0]]
        hit = check.path(moving, installed, path)
        if hit:
            raise ValueError('搭載順または差込方向が干渉しています: '+label+' '+str(hit))
        mount_steps.append(dict(stage='mount', phase=phase, title=label, moving=sorted(moving),
                                fixed=sorted(installed), offsets=path))
        installed.update(moving)

    for role in ('base_front','base_rear'):
        mount(unit_map[role]['members'],unit_map[role]['title']+'を置く',[0,0,1],1)
    for e in (e for e in scene['equipment'] if e['kind']=='power'):
        mount([e['name']],part_label(e['name'],scene)+'を受けへ入れる',[0,0,1],1)
    for row, phase in ((0,2),(1,4)):
        if row:
            for role in ('middle_front','middle_rear'):
                mount(unit_map[role]['members'],unit_map[role]['title']+'を載せる',[0,0,1],3)
        for col in range(2):
            name=f'spark_{col}_{row}'
            mount([name],part_label(name,scene)+'を上から入れる',[0,0,1],phase)
    mount(unit_map['top']['members'],'上部の支持ユニットを載せる',[0,0,1],5)
    for name in ('comet','kvm','crs812'):
        mount([name],part_label(name,scene)+'を載せる',[0,0,1],6)
    for controller in (e for e in scene['equipment'] if e['kind']=='controller'):
        names = {e['name'] for e in model['references'] if e.get('group')==controller['name'] and e['kind'] not in SOFT_KINDS}
        mount(names,part_label(controller['name'],scene)+'を受け台へ入れる',controller['w'],6)
    if installed != set(items):
        raise ValueError('組立手順に含まれない剛体部品があります: '+str(sorted(set(items)-installed)))
    return dict(bench_steps=bench_steps, mount_steps=mount_steps, units=units,
                phases=['受けと連結部を作業台で先に組む', '前後の下部受けと電源を置く',
                        '下段のSparkを入れる', '前後の中間連結ユニットを載せる',
                        '上段のSparkを入れる', '上部の支持ユニットを載せる',
                        '周辺機器と制御器を入れる', 'ベルトを締め、配線を解除式バンドで固定する'],
                all_rigid_names=sorted(items), rigid_object_count=len(items),
                excluded_flexible_names=[e['name'] for e in all_entries if e['kind'] in SOFT_KINDS],
                assumptions=['配線とベルトは取り付ける前の剛体形状を確認する。柔軟部材の通し方は実物確認が必要。',
                             'ファンと保持部と4本の樹脂割りピンは、小組み前に1組にする。割りピンのたわみは未検証。',
                             '制御器は基板を入れ、蓋を上から合わせてから搭載し、解除式バンドで留める。',
                             '小組みは両方の部材を支えた状態。支持面の強度・机上の安定は別途確認する。'],
                checked_volume_intersections=check.checked,
                motion_scope='軸方向の平行移動を端面の押出しで検査。曲面の一部は外形箱で保守的に覆う。',
                physical_validation=False)
