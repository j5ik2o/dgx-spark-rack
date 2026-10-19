"""造形姿勢ごとの支持材領域、支持禁止箇所、除去手順を参考データにする。"""
from body_frame_support_regions import transformed,protection,planar_regions,fan_arch_region,tight_bounds
from body_frame_support_removal import removal_plan,validate_removal


def build_support_plan(model):
    entries = {e['name']:e for e in model['parts']+model['references']}
    parts,meshes = [],[]
    for info in model['print_plan']['parts']:
        entry = entries[info['name']]
        shape = transformed(entry['shape'],info['transform'])
        guards = [dict(g,shape=transformed(g['shape'],info['transform'])) for g in protection(entry,model)]
        if entry['kind'] in ('joint_key','fan_pin'):
            regions,reviews = [],[]
        else:
            regions,reviews = planar_regions(shape,guards)
            regions += fan_arch_region(entry,model,info['transform'])
        for region in regions:
            if any(g.get('mode')=='volume' and region['shape'].common(g['shape']).Volume > 1e-5 for g in guards):
                raise ValueError('支持材領域が精密面または差込口に入り込んでいます: '+entry['name'])
        steps,blocked = removal_plan(shape,regions)
        if blocked:
            raise ValueError('支持材領域を引き出せません: '+entry['name']+' '+str(blocked))
        validate_removal(shape,regions,steps)
        record = dict(name=entry['name'],label=entry['label'],regions=[],steps=steps,face_review=reviews,
                      precision_regions=[dict(name=g['name'],label=g['label'],mode=g['mode'],bounds_mm=tight_bounds(g['shape'])) for g in guards],
                      region_count=len(regions),protected_face_count=sum(r['protected']>0 for r in reviews),
                      removal_geometry='passed',slicer_validated=False)
        for region in regions:
            points,faces = region['shape'].tessellate(.5)
            full_name = entry['name']+'__support__'+region['name']
            record['regions'].append({k:v for k,v in region.items() if k!='shape'}|dict(bounds_mm=tight_bounds(region['shape']),mesh_name=full_name))
            meshes.append(dict(name=full_name,owner=entry['name'],region=region['name'],label=region['label'],kind='print_support',
                               bounds=tight_bounds(region['shape']),vertices=[list(p) for p in points],faces=faces,color=[.88,.54,.20],members=[]))
        parts.append(record)
    return dict(status='candidate',parts=parts,printed_parts=len(parts),
                parts_with_regions=sum(p['region_count']>0 for p in parts),
                region_count=sum(p['region_count'] for p in parts),
                removal_steps=sum(len(p['steps']) for p in parts),
                protected_face_count=sum(p['protected_face_count'] for p in parts),
                scope='支持材を置く領域と、ほぐした後の領域単位の除去経路。小分けの境界は切り離す箇所の候補。支持構造・印刷経路・破断力を表していない。',
                assumptions=dict(interface_gap_mm=.3,edge_margin_mm=.6,max_segment_mm=36,
                                 removal_tool_tip_mm=[2,3,12],hand_and_handle_checked=False),
                precision_policy='機器へ向く面、ほぞ・角栓の通路、ファン取付穴を支持禁止。残る開口は橋渡しの経路をスライサーで確認。',
                remaining=['精密面の橋渡しと、丸み・小さい穴・曲面の実際の支持判定',
                           '支持材の密度・界面・接着・安定性、ペンチで切り離す力と柄・手の空間',
                           '支持材除去後の実寸・表面品質・強度'],
                physical_validation=False,slicer_validated=False,manufacturing_geometry=False),meshes
