"""段差を残してほぞを差し、ねじ山のない角栓で抜けを止める。実物適合は別途確認。"""
from itertools import combinations, product

import FreeCAD as App
import Part


def box_between(low, high):
    return Part.makeBox(*[high[i]-low[i] for i in range(3)], App.Vector(*low))


def contact_faces(a, b):
    from validate_body_frame import planes, near
    first, second = planes(a), planes(b)
    faces = []
    for key in sorted(first.keys() & second.keys()):
        for fa in first[key]:
            for fb in second[key]:
                if near(fa, fb):
                    for face in fa.common(fb).Faces:
                        if face.Area > 2:
                            faces.append((face.Area, key[0], key[1], face))
    return sorted(faces, key=lambda x: -x[0])


def exit_distance(shape, center, axis, sign):
    b = shape.BoundBox
    bound = [b.XMax, b.YMax, b.ZMax][axis] if sign > 0 else [b.XMin, b.YMin, b.ZMin][axis]
    end = list(center)
    end[axis] = bound + sign
    ray = Part.makeLine(App.Vector(*center), App.Vector(*end)).common(shape)
    for edge in ray.Edges:
        ends = [v.Point for v in edge.Vertexes]
        if any((p-App.Vector(*center)).Length < 1e-5 for p in ends):
            return max(sign*(p[axis]-center[axis]) for p in ends)
    return None


def design_joint(first, second, obstacles, number, clearance=.15, maximum_depth=5,
                 minimum_key_width=1.8, minimum_ligament=1):
    """実際の平面接触から、ほぞと角栓が入る局所領域を探す。"""
    from freecad_spark_rack import item
    from validate_body_frame import near, shared_area
    from body_frame_assembly import MotionCheck, escape
    from body_frame_access import grip_path, fan_key_path
    from freecad_spark_rack import key_grip
    original_motion = MotionCheck({e['name']:e for e in (first, second)})
    for _, normal, plane, face in contact_faces(first['shape'], second['shape'])[:6]:
        tangent = [i for i in range(3) if i != normal]
        b = face.BoundBox
        lo, hi = [b.XMin, b.YMin, b.ZMin], [b.XMax, b.YMax, b.ZMax]
        for ratio in (.5, .3, .7):
            point = [(lo[i]+hi[i])/2 for i in range(3)]
            point[tangent[0]] = lo[tangent[0]]+(hi[tangent[0]]-lo[tangent[0]])*ratio
            point[normal] = plane
            widths = [min(10, (hi[i]-lo[i])*.55) for i in tangent]
            if min(widths) < 1.8:
                continue
            for donor, receiver in ((first, second), (second, first)):
                for sign in (-1, 1):
                    withdraw = [-sign if i == normal else 0 for i in range(3)]
                    if original_motion.path({donor['name']}, {receiver['name']}, [[0,0,0],withdraw]):
                        continue
                    for depth in (d for d in (5, 4, 3, 2) if d <= maximum_depth):
                        low, high = list(point), list(point)
                        for i, width in zip(tangent, widths):
                            low[i], high[i] = point[i]-width/2, point[i]+width/2
                        low[normal], high[normal] = sorted((plane, plane+sign*depth))
                        inside = box_between(low, high)
                        if receiver['shape'].common(inside).Volume < inside.Volume-1e-5:
                            continue
                        low_root, high_root = list(low), list(high)
                        low_root[normal], high_root[normal] = sorted((plane-sign*.5, plane))
                        root = box_between(low_root, high_root)
                        if donor['shape'].common(root).Volume < root.Volume-1e-5:
                            continue
                        male = inside.fuse(root).removeSplitter()
                        pocket_low, pocket_high = list(low), list(high)
                        for i in tangent:
                            pocket_low[i] -= clearance
                            pocket_high[i] += clearance
                        if sign > 0:
                            pocket_low[normal] -= .01
                            pocket_high[normal] += clearance
                        else:
                            pocket_low[normal] -= clearance
                            pocket_high[normal] += .01
                        pocket = box_between(pocket_low, pocket_high)
                        new_donor = donor['shape'].fuse(male).removeSplitter()
                        new_receiver = receiver['shape'].cut(pocket).removeSplitter()
                        if any(len(s.Solids) != 1 or not s.isValid() for s in (new_donor, new_receiver)):
                            continue
                        # 受け面はほぞ以外にも残す。自重を細い栓だけで支えない。
                        shoulder = shared_area(new_donor, new_receiver)
                        if shoulder < 2:
                            continue
                        pair = MotionCheck({donor['name']:dict(shape=new_donor),
                                            receiver['name']:dict(shape=new_receiver)})
                        if pair.path({donor['name']}, {receiver['name']},
                                     [[0,0,0],[v*(depth+.5) for v in withdraw]]):
                            continue
                        for entry_axis in tangent:
                            other = next(i for i in tangent if i != entry_axis)
                            width = min(1.8, depth*.45, widths[tangent.index(other)]*.45)
                            ligament = min(depth, widths[tangent.index(other)])/2-width/2-.08
                            if width < minimum_key_width-1e-6 or ligament < minimum_ligament-1e-6:
                                continue
                            center = list(point)
                            center[normal] = plane+sign*depth/2
                            signs = (1,-1) if entry_axis == 0 and point[0] > 20 else (-1,1)
                            for entry_sign, grip_offset, flat_side in product(signs, (0, -8, 8), (-1, 1)):
                                distance = exit_distance(receiver['shape'], center, entry_axis, entry_sign)
                                if distance is None or distance > 80:
                                    continue
                                end = center[entry_axis]+entry_sign*distance
                                far = center[entry_axis]-entry_sign*(widths[tangent.index(entry_axis)]/2+.4)
                                kl, kh = list(center), list(center)
                                for i in (normal, other):
                                    kl[i], kh[i] = center[i]-width/2, center[i]+width/2
                                kl[entry_axis], kh[entry_axis] = sorted((far, end))
                                shaft = box_between(kl, kh)
                                head, grip = key_grip(center, end, entry_axis, entry_sign, normal, width, grip_offset, flat_side)
                                if shared_area(head, receiver['shape']) < 1.05:
                                    continue
                                key_shape = shaft.fuse(head).removeSplitter()
                                if key_shape.BoundBox.ZMin < -1e-6:
                                    continue
                                if any(near(key_shape, e['shape'], volume=True) and key_shape.common(e['shape']).Volume > 1e-5
                                       for e in obstacles if e['name'] not in (donor['name'], receiver['name'])):
                                    continue
                                sl, sh = list(kl), list(kh)
                                for i in (normal, other):
                                    sl[i] -= .08
                                    sh[i] += .08
                                sl[entry_axis], sh[entry_axis] = sorted((far-entry_sign*.1, end+entry_sign*2))
                                slot = box_between(sl, sh)
                                final_donor = new_donor.cut(slot).removeSplitter()
                                final_receiver = new_receiver.cut(slot).removeSplitter()
                                if any(len(s.Solids) != 1 or not s.isValid() for s in (final_donor, final_receiver, key_shape)):
                                    continue
                                if shared_area(key_shape, final_receiver) < 1.05:
                                    continue
                                if any(key_shape.common(s).Volume > 1e-5 for s in (final_donor, final_receiver)):
                                    continue
                                if shared_area(final_donor, final_receiver) < 2:
                                    continue
                                if final_donor.common(final_receiver).Volume > 1e-5:
                                    continue
                                key = item(f'joint_key_{number}', '幅10mmのつまみを持つ、ねじ山のない角栓',
                                           key_shape, 'joint_key', grip=grip)
                                key_axis = [entry_sign if i == entry_axis else 0 for i in range(3)]
                                local = MotionCheck({donor['name']:dict(shape=final_donor),
                                                     receiver['name']:dict(shape=final_receiver), key['name']:key})
                                key_length = key_shape.BoundBox.XLength if entry_axis == 0 else (
                                    key_shape.BoundBox.YLength if entry_axis == 1 else key_shape.BoundBox.ZLength)
                                key_path = escape(local, {key['name']}, {donor['name'],receiver['name']}, key_axis, key_length+2)
                                if key_path is None:
                                    continue
                                if not grip_path(local.items, key['name'], grip,
                                                 {donor['name'],receiver['name']}, key_path):
                                    continue
                                fan_holder = next((e['name'] for e in (donor, receiver) if e['name'].endswith('_holder')), None)
                                if fan_holder:
                                    key['unlock_before'] = fan_holder.removesuffix('_holder')
                                    service = {e['name']:e for e in obstacles}
                                    service[donor['name']] = dict(donor, shape=final_donor)
                                    service[receiver['name']] = dict(receiver, shape=final_receiver)
                                    service[key['name']] = key
                                    if not all(fan_key_path(service, e['name']) for e in service.values()
                                               if e.get('unlock_before')):
                                        continue
                                record = dict(name=f'joint_{number}', donor=donor['name'], receiver=receiver['name'],
                                              contact_point_mm=point,
                                              normal_axis=normal, insertion_axis=[sign if i == normal else 0 for i in range(3)],
                                              engagement_mm=depth, tenon_widths_mm=widths,
                                              key=key['name'], key_axis=key_axis,
                                              key_shaft_width_mm=width, key_slot_clearance_mm=.08,
                                              tenon_ligament_mm=ligament,
                                              grip=grip,
                                              shoulder_area_mm2=shoulder, method='段差で受けるほぞ差し＋横から差す角栓')
                                record['isolated_insertion_motion_verified'] = True
                                record['isolated_key_insertion_motion_verified'] = True
                                return donor, receiver, final_donor, final_receiver, key, record
    return None


def connect_parts(parts, references, parameters=None):
    from validate_body_frame import near, shared_area, components
    frame = [e for e in parts if e['kind'] != 'fan_pin']
    edges = []
    for a, b in combinations(frame, 2):
        if near(a['shape'], b['shape']):
            area = shared_area(a['shape'], b['shape'])
            if area > 2:
                edges.append((a, b, area))
    names = [e['name'] for e in frame]
    target = components(names, [(a['name'], b['name'], area) for a, b, area in edges])
    links, keys, records, failed = [], [], [], []
    for a, b, area in sorted(edges, key=lambda e: -e[2]):
        groups = components(names, links)
        together = any(a['name'] in group and b['name'] in group for group in groups)
        if together:
            continue
        options = {} if parameters is None else dict(clearance=parameters.joinery_clearance,
                                                     maximum_depth=parameters.joinery_max_depth,
                                                     minimum_key_width=parameters.joint_key_min_width,
                                                     minimum_ligament=parameters.joint_min_ligament)
        joint = design_joint(a, b, parts+references+keys, len(keys), **options)
        if joint is None:
            failed.append([a['name'], b['name'], area])
            continue
        donor, receiver, first_shape, second_shape, key, record = joint
        donor['shape'], receiver['shape'] = first_shape, second_shape
        keys.append(key)
        records.append(record)
        links.append([a['name'], b['name'], area])
    if components(names, links) != target:
        raise ValueError('ねじ不要の接合を具体化できない接触部があります: '+str(failed))
    return parts+keys, dict(joints=records, integrated_parts=[dict(name=e['name'], members=e.get('integrated_members', [e['name']]))
                                                           for e in frame],
                           assembly_screws=0, assembly_nuts=0,
                           key_retention='角栓のはめ合いと脱落防止は試作で確認。必要箇所は解除式結束バンドも併用し、ねじ・ナットは使わない。',
                           physical_validation=False)


def joint_detail(parts, scene):
    """実際の接合部から切り出した説明図。組立モデルそのものの位置は変えない。"""
    from freecad_spark_rack import block, item
    lookup = {e['name']: e for e in parts}
    candidates = [j for j in scene['screwless_assembly']['joints']
                  if not any(j[k].endswith('_holder') for k in ('donor', 'receiver'))]
    chosen = min(candidates, key=lambda j: lookup[j['key']]['shape'].BoundBox.DiagonalLength)
    point = chosen['contact_point_mm']
    region = block([v-16 for v in point], [32, 32, 32])
    details = []
    for role, kind, movement in (
            ('donor', 'joint_detail_donor', [-12*v for v in chosen['insertion_axis']]),
            ('receiver', 'joint_detail_receiver', [0, 0, 0]),
            ('key', 'joint_detail_key', [30*v for v in chosen['key_axis']])):
        source = lookup[chosen[role]]['shape']
        shape = source.copy() if role == 'key' else source.common(region)
        shape.translate(App.Vector(*movement))
        details.append(item('detail_'+role, {'donor':'ほぞ側・説明用切り出し',
                                           'receiver':'受け穴側・説明用切り出し',
                                           'key':'横から差す角栓・説明用移動'}[role], shape, kind))
    scene['screwless_assembly']['detail_joint'] = chosen['name']
    return details


def validate_screwless(model):
    from validate_body_frame import shared_area
    scene = model['scene']
    assembly = scene['screwless_assembly']
    if assembly['assembly_screws'] or assembly['assembly_nuts']:
        raise ValueError('ねじ・ナットを必要とする組立条件が残っています')
    case = scene['controller_case_assembly']
    if case['assembly_screws'] or case['assembly_nuts']:
        raise ValueError('制御器ケースにねじ・ナットが残っています')
    by_name = {e['name']: e for e in model['parts']+model['references']}
    for joint in assembly['joints']:
        if not all(joint[k] in by_name for k in ('donor', 'receiver', 'key')):
            raise ValueError('ほぞの抜け止め用の角栓が欠けています')
        donor, receiver, key = [by_name[joint[k]]['shape'] for k in ('donor', 'receiver', 'key')]
        if shared_area(donor, receiver) < 2:
            raise ValueError('ほぞ以外の受け面が残っていません')
        moved = donor.copy()
        moved.translate(App.Vector(*[-.5*v for v in joint['insertion_axis']]))
        if moved.common(key).Volume < 1e-5:
            raise ValueError('角栓がほぞの引き抜きを止めません: '+joint['name'])
    for fan in (e for e in scene['equipment'] if e['kind'] == 'fan'):
        pins = [e for e in model['parts'] if e.get('moves_with') == fan['name'] and e['kind'] == 'fan_pin']
        if len(pins) != 4:
            raise ValueError('ファン固定用の樹脂割りピンが欠けています: '+fan['name'])
        for pin in pins:
            if shared_area(pin['shape'], by_name[fan['name']]['shape']) < 1:
                raise ValueError('樹脂割りピンの頭がファンの外枠に掛かっていません')
            if shared_area(pin['shape'], by_name[fan['name']+'_holder']['shape']) < 1:
                raise ValueError('樹脂割りピンの返しが保持部に掛かっていません')
    for controller in (e for e in scene['equipment'] if e['kind'] == 'controller'):
        bands = [e for e in model['references'] if e['kind'] == 'controller_band' and e.get('group') == controller['name']]
        if len(bands) != 2:
            raise ValueError('制御器ケースを保持する解除式バンドが欠けています')
    return dict(status='passed', assembly_screws=0, assembly_nuts=0,
                tenon_joints=len(assembly['joints']), square_keys=len(assembly['joints']), fan_pins=24,
                controller_cases='蓋一体の基板押さえと解除式バンド。ねじ式ドックは使用しない。',
                scope='接合部の実形状と固定部品の有無。材料強度・角栓の脱落・割りピンの弾性は未検証。組立経路は別検査。',
                physical_validation=False,
                remaining=['角栓のはめ合いと脱落防止、割りピンの押込みと解除の操作',
                           '作業台で手で支える操作、材料・積層方向・繰り返し着脱'])
