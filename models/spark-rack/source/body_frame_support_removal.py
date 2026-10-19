"""支持材領域を小分けに外し、仮のペンチ先端と共に引き出す経路を検査する。"""
import FreeCAD as App
import Part

from body_frame_assembly import MotionCheck
from body_frame_print_plan import tight_bounds


DIRECTIONS = ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1))


def tip_shape(region,axis):
    lo,hi = tight_bounds(region)
    index = next(i for i,v in enumerate(axis) if v)
    tangents = [i for i in range(3) if i!=index]
    center = [(lo[i]+hi[i])/2 for i in range(3)]
    low,high = list(center),list(center)
    for i,width in zip(tangents,(3,2)):
        low[i],high[i] = center[i]-width/2,center[i]+width/2
    edge = hi[index] if axis[index]>0 else lo[index]
    low[index],high[index] = sorted((edge-axis[index]*.4,edge+axis[index]*11.6))
    return Part.makeBox(*[high[i]-low[i] for i in range(3)],App.Vector(*low))


def removal_plan(shape,regions):
    items = {'part':dict(shape=shape)}|{r['name']:r for r in regions}
    remaining = {r['name'] for r in regions}
    low,high = tight_bounds(shape)
    tips = {(name,index):'tip_'+name+'_'+str(index) for name in remaining for index in range(len(DIRECTIONS))}
    for (name,index),tip in tips.items():
        items[tip] = dict(shape=tip_shape(items[name]['shape'],DIRECTIONS[index]))
    check = MotionCheck(items)
    steps = []
    while remaining:
        selected = None
        for name in sorted(remaining):
            region = items[name]['shape']
            lo,hi = tight_bounds(region)
            for direction_index,axis in enumerate(DIRECTIONS):
                index = next(i for i,v in enumerate(axis) if v)
                distance = high[index]-lo[index]+15 if axis[index]>0 else hi[index]-low[index]+15
                path = [[0,0,0],[v*distance for v in axis]]
                tip = tips[name,direction_index]
                if check.path({name,tip},{'part'}|(remaining-{name}),path) is None:
                    selected = dict(region=name,offsets_mm=path,tool_bounds_mm=tight_bounds(items[tip]['shape']),axis=list(axis),
                                    tool='先細ペンチの先端を2×3×12mmの仮外形で検査。手と柄は含まない。')
                    break
            if selected:
                break
        if selected is None:
            return steps,sorted(remaining)
        steps.append(selected)
        remaining.remove(selected['region'])
    return steps,[]


def validate_removal(shape,regions,steps):
    items = {'part':dict(shape=shape)}|{r['name']:r for r in regions}
    remaining = {r['name'] for r in regions}
    part_low,part_high = tight_bounds(shape)
    for step in steps:
        name = step['region']
        if name not in remaining:
            raise ValueError('支持材の除去手順が重複しています')
        tip = tip_shape(items[name]['shape'],step['axis'])
        axis = tuple(step['axis'])
        path = step['offsets_mm']
        if axis not in DIRECTIONS or len(path)!=2 or path[0]!=[0,0,0]:
            raise ValueError('支持材の除去方向または開始位置が不正です')
        index = next(i for i,v in enumerate(axis) if v)
        if path[-1][index]*axis[index] <= 0 or any(path[-1][i] for i in range(3) if i!=index):
            raise ValueError('支持材の除去方向と経路が一致しません')
        for moving in (items[name]['shape'],tip):
            lo,hi = tight_bounds(moving)
            if (axis[index]>0 and lo[index]+path[-1][index]<=part_high[index]
                    or axis[index]<0 and hi[index]+path[-1][index]>=part_low[index]):
                raise ValueError('支持材またはペンチ先端を部品の外まで引き出していません')
        check = MotionCheck(dict(items,tip=dict(shape=tip)))
        if check.path({name,'tip'},{'part'}|(remaining-{name}),step['offsets_mm']):
            raise ValueError('支持材またはペンチ先端の除去経路が干渉します: '+name)
        remaining.remove(name)
    if remaining:
        raise ValueError('取り出す手順のない支持材領域があります: '+str(sorted(remaining)))
