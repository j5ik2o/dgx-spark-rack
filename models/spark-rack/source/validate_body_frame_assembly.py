"""組立手順を剛体形状へ再適用し、順番・全数・差し込み方向と移動途中を検査する。"""
import math

from body_frame_assembly import MotionCheck, SOFT_KINDS, unit_bounds


def path_valid(offsets):
    if len(offsets) < 2 or any(len(p)!=3 or any(not math.isfinite(v) for v in p) for p in offsets):
        raise ValueError('組立経路の座標が不正です')
    if any(abs(v)>1e-7 for v in offsets[-1]):
        raise ValueError('組立経路が完成位置で終わっていません')


def starts_outside(moving, fixed, items, offsets):
    lo,hi = unit_bounds(moving, items, offsets[0])
    flo,fhi = unit_bounds(fixed, items)
    if not any(lo[i]>fhi[i]+10 or hi[i]<flo[i]-10 for i in range(3)):
        raise ValueError('組立の開始位置が相手ユニットの外へ出ていません')


def validate_plan(model, plan):
    scene = model['scene']
    entries = model['parts']+model['references']
    items = {e['name']:e for e in entries if e['kind'] not in SOFT_KINDS}
    check = MotionCheck(items)
    frame = {e['name'] for e in model['parts'] if e['kind'] not in ('joint_key','fan_pin')}
    recorded_frame = {e['name'] for e in scene['screwless_assembly']['integrated_parts']}
    if frame != recorded_frame:
        raise ValueError('小組みの部品一覧が実形状と一致しません')
    ready = []
    for name in frame:
        members = {name}
        if name.endswith('_holder'):
            fan = name.removesuffix('_holder')
            if fan in items and items[fan]['kind']=='fan':
                members.add(fan)
                members |= {e['name'] for e in model['parts'] if e.get('moves_with')==fan}
        ready.append(frozenset(members))
    joints = {j['name']:j for j in scene['screwless_assembly']['joints']}
    used = set()
    segments = 0
    for step in plan['bench_steps']:
        if step['joint'] not in joints or step['joint'] in used:
            raise ValueError('接合の工程が欠落または重複しています')
        joint = joints[step['joint']]
        moving, fixed = frozenset(step['moving']),frozenset(step['fixed'])
        if moving not in ready or fixed not in ready or moving & fixed:
            raise ValueError('まだ組み立てていない小組み部品を使用しています')
        if step['key'] != joint['key']:
            raise ValueError('接合と角栓が一致しません')
        if (joint['donor'] in moving)==(joint['receiver'] in moving):
            raise ValueError('ほぞ側と受け側が別のユニットになっていません')
        path_valid(step['offsets']);path_valid(step['key_offsets'])
        starts_outside(moving,fixed,items,step['offsets'])
        sign = -1 if joint['donor'] in moving else 1
        approach = step['offsets'][-2]
        distance = sum(approach[i]*sign*joint['insertion_axis'][i] for i in range(3))
        if distance < joint['engagement_mm']+.1 or any(abs(approach[i]-distance*sign*joint['insertion_axis'][i])>1e-6 for i in range(3)):
            raise ValueError('ほぞの最後の差し込み方向が一致しません')
        hit = check.path(moving,fixed,step['offsets'])
        if hit:
            raise ValueError('小組みの差し込み途中が干渉します: '+str(hit))
        whole = moving | fixed
        starts_outside({step['key']},whole,items,step['key_offsets'])
        key_last = step['key_offsets'][-2]
        key_distance = sum(key_last[i]*joint['key_axis'][i] for i in range(3))
        if key_distance <= 0 or any(abs(key_last[i]-key_distance*joint['key_axis'][i])>1e-6 for i in range(3)):
            raise ValueError('角栓を入れる方向が一致しません')
        hit = check.path({step['key']},whole,step['key_offsets'])
        if hit:
            raise ValueError('小組み後に角栓を差せません: '+str(hit))
        ready.remove(moving);ready.remove(fixed)
        ready.append(whole | {step['key']})
        used.add(step['joint'])
        segments += len(step['offsets'])+len(step['key_offsets'])-2
    if used != set(joints):
        raise ValueError('組み立てていないほぞの接合が残っています')
    unit_sets = {frozenset(u['members']) for u in plan['units']}
    if set(ready) != unit_sets:
        raise ValueError('作業台で完成するユニットが搭載一覧と一致しません')
    allowed = set(unit_sets)
    for e in scene['equipment']:
        if e['kind'] in ('spark','power','switch','comet','kvm'):
            allowed.add(frozenset([e['name']]))
        elif e['kind']=='controller':
            allowed.add(frozenset(x['name'] for x in model['references']
                                  if x.get('group')==e['name'] and x['kind'] not in SOFT_KINDS))
    installed,previous_phase = set(),0
    for step in plan['mount_steps']:
        moving,fixed = set(step['moving']),set(step['fixed'])
        if frozenset(moving) not in allowed or moving & installed:
            raise ValueError('搭載単位の欠落または重複があります')
        if fixed != installed or step['phase']<previous_phase:
            raise ValueError('搭載順または先行部品が一致しません')
        path_valid(step['offsets'])
        if fixed:
            starts_outside(moving,fixed,items,step['offsets'])
        hit = check.path(moving,fixed,step['offsets'])
        if hit:
            raise ValueError('先に取り付けた部品が差し込みを塞ぎます: '+str(hit))
        for offset in step['offsets']:
            if unit_bounds(moving,items,offset)[0][2]<-1e-6:
                raise ValueError('設置面の下を通る搭載経路になっています')
        installed |= moving
        previous_phase = step['phase']
        segments += len(step['offsets'])-1
    if installed != set(items) or set(plan['all_rigid_names']) != installed:
        raise ValueError('全ての剛体部品を組み立てる手順になっていません')
    return dict(status='passed', bench_join_operations=len(plan['bench_steps']),
                mounting_operations=len(plan['mount_steps']), rigid_objects=len(installed),
                verified_axis_segments=segments, checked_swept_intersections=check.checked,
                scope=plan['motion_scope'], physical_validation=False,
                not_verified=['割りピンの弾性・押込み・解除、保持ベルトと結束バンドを通す実際の操作',
                              '基板裏面の部品位置、実機の足・丸み・通気口、実際の手での操作',
                              '作業台での仮支持、強度・変形・繰り返し使用'])
