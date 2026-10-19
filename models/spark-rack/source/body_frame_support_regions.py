"""支持材を置く領域の候補。充填パターンや印刷経路ではない。"""
import math

import FreeCAD as App
import Part

from body_frame_print_plan import tight_bounds

GAP = .3
EDGE = .6
MAX_SPAN = 36
PRECISION_MARGIN = .6


def box(low, high):
    return Part.makeBox(*[high[i]-low[i] for i in range(3)], App.Vector(*low))


def transformed(shape, rows):
    matrix = App.Matrix()
    for i,row in enumerate(rows):
        for j,value in enumerate(row):
            setattr(matrix, f'A{i+1}{j+1}', value)
    result = shape.copy()
    result.Placement = App.Placement(matrix).multiply(result.Placement)
    return result


def overlap(a,b):
    return all(min(a[1][i],b[1][i])-max(a[0][i],b[0][i]) > 1e-6 for i in range(3))


def protection(entry, model):
    """機器に向く面、ほぞと角栓の通路、ファン取付穴を保護する。組立座標。"""
    name = entry['name']
    own = tight_bounds(entry['shape'])
    regions = []
    kinds = {'spark','switch','comet','kvm','power','fan','controller','controller_lid'}
    for ref in model['references']:
        if ref['name']==name or ref['kind'] not in kinds:
            continue
        lo,hi = tight_bounds(ref['shape'])
        bounds = ([v-PRECISION_MARGIN for v in lo],[v+PRECISION_MARGIN for v in hi])
        if overlap(own,bounds):
            regions.append(dict(name='contact_'+ref['name'],label='機器または相手部品に向く面',mode='contact',shape=box(*bounds)))
    items = {e['name']:e for e in model['parts']}
    for joint in model['scene']['screwless_assembly']['joints']:
        if name not in (joint['donor'],joint['receiver']):
            continue
        lo,hi = tight_bounds(items[joint['key']]['shape'])
        regions.append(dict(name=joint['name']+'_key',label='角栓の通路',mode='volume',
                            shape=box([v-EDGE for v in lo],[v+EDGE for v in hi])))
        center = joint['contact_point_mm']
        size = [max(joint['tenon_widths_mm'])+2*EDGE]*3
        size[joint['normal_axis']] = 2*(joint['engagement_mm']+EDGE)
        regions.append(dict(name=joint['name']+'_tenon',label='ほぞと受け穴の周囲',mode='volume',
                            shape=box([center[i]-size[i]/2 for i in range(3)],
                                      [center[i]+size[i]/2 for i in range(3)])))
    if name.endswith('_holder'):
        fan = next(e for e in model['scene']['equipment'] if name==e['name']+'_holder')
        axis = next(i for i,v in enumerate(fan['axis']) if v)
        tangents = [i for i in range(3) if i!=axis]
        for first in (-1,1):
            for second in (-1,1):
                center = [fan['origin'][i]+fan['size'][i]/2 for i in range(3)]
                for i,sign in zip(tangents,(first,second)):
                    center[i] += sign*fan['pitch']/2
                center[axis] = fan['origin'][axis]-model['parameters'].fan_plate-1
                shape = Part.makeCylinder(2.25+EDGE,fan['size'][axis]+2*model['parameters'].fan_plate+2,
                                          App.Vector(*center),App.Vector(*[int(i==axis) for i in range(3)]))
                regions.append(dict(name=f'fan_hole_{first}_{second}',label='ファン取付穴',mode='volume',shape=shape))
    return regions


def precision_area(entry, model, axis):
    """造形方向の選択用。機器に向く広い下面へ支持材を付ける候補を避ける。"""
    guards = protection(entry,model)
    result = 0
    for face in entry['shape'].Faces:
        if face.Surface.__class__.__name__!='Plane' or face.normalAt(0,0).dot(App.Vector(*axis)) > -.99:
            continue
        lo,hi = tight_bounds(face)
        spans = sorted(hi[i]-lo[i] for i in range(3))
        if spans[1] <= 10:
            continue
        for guard in guards:
            if overlap(([v-.01 for v in lo],[v+.01 for v in hi]),tight_bounds(guard['shape'])):
                result += face.common(guard['shape']).Area
    return result


def partitions(values):
    values = sorted(set(round(v,5) for v in values))
    result = []
    for lo,hi in zip(values,values[1:]):
        count = max(1,math.ceil((hi-lo)/MAX_SPAN))
        result += [(lo+(hi-lo)*i/count,lo+(hi-lo)*(i+1)/count) for i in range(count)]
    return result


def floor_height(shape,x,y,top):
    ray = Part.makeLine(App.Vector(x,y,0),App.Vector(x,y,top-.02))
    intersections = ray.common(shape)
    return max([v.Point.z for v in intersections.Vertexes]+[0])


def planar_regions(shape, guards):
    """水平な下面の内側に小分けの領域を置く。密度と界面は後で設定する。"""
    bounds = [(g,tight_bounds(g['shape'])) for g in guards]
    regions, reviews = [], []
    for index,face in enumerate(shape.Faces):
        if face.Surface.__class__.__name__!='Plane' or face.normalAt(0,0).z > -.99:
            continue
        lo,hi = tight_bounds(face)
        if lo[2] < 1.5 or face.Area < 8:
            continue
        xs = partitions([v.Point.x for v in face.Vertexes])
        ys = partitions([v.Point.y for v in face.Vertexes])
        counts = dict(placed=0,protected=0,small=0,uneven=0)
        for x0,x1 in xs:
            for y0,y1 in ys:
                x0,x1,y0,y1 = x0+EDGE,x1-EDGE,y0+EDGE,y1-EDGE
                if min(x1-x0,y1-y0) < 1.4 or (x1-x0)*(y1-y0) < 6:
                    counts['small'] += 1
                    continue
                patch = Part.Face(Part.makePolygon([App.Vector(x,y,lo[2]) for x,y in
                             ((x0,y0),(x1,y0),(x1,y1),(x0,y1),(x0,y0))]))
                if abs(patch.common(face).Area-patch.Area) > 1e-5:
                    continue
                contact = ([x0,y0,lo[2]-.4],[x1,y1,lo[2]+.1])
                if any(overlap(contact,b) and box(*contact).common(g['shape']).Volume > 1e-5 for g,b in bounds):
                    counts['protected'] += 1
                    continue
                samples = [(x,y) for x in (x0+.01,x1-.01) for y in (y0+.01,y1-.01)]+[((x0+x1)/2,(y0+y1)/2)]
                heights = [floor_height(shape,x,y,lo[2]) for x,y in samples]
                bottom = max(heights)
                if bottom-min(heights) > .02:
                    counts['uneven'] += 1
                    continue
                base = bottom+GAP if bottom > .02 else 0
                top = lo[2]-GAP
                if top-base < 1.2:
                    counts['small'] += 1
                    continue
                region = box([x0,y0,base],[x1,y1,top])
                if region.common(shape).Volume > 1e-5:
                    counts['uneven'] += 1
                    continue
                if any(g.get('mode')=='volume' and overlap(tight_bounds(region),b)
                       and region.common(g['shape']).Volume > 1e-5 for g,b in bounds):
                    counts['protected'] += 1
                    continue
                if bottom > .02:
                    landing = box([x0,y0,bottom-.05],[x1,y1,bottom])
                    if abs(landing.common(shape).Volume-landing.Volume) > 1e-5:
                        counts['uneven'] += 1
                        continue
                    if any(overlap(tight_bounds(landing),b) and landing.common(g['shape']).Volume > 1e-5 for g,b in bounds):
                        counts['protected'] += 1
                        continue
                regions.append(dict(name=f'face_{index}_{counts["placed"]}',label='張出しの下の支持材領域',
                                    shape=region,face=index,contact_height_mm=lo[2],base_height_mm=bottom,
                                    contact_area_mm2=patch.Area,landing='造形台' if bottom<.02 else '部品の非精密面'))
                counts['placed'] += 1
        reviews.append(dict(face=index,area_mm2=face.Area,bounds_mm=[lo,hi],**counts))
    return regions,reviews


def fan_arch_region(entry,model,rows):
    if not entry['name'].startswith('spark_fan_') or not entry['name'].endswith('_holder'):
        return []
    fan = next(e for e in model['scene']['equipment'] if entry['name']==e['name']+'_holder')
    axis = App.Vector(0,1,0)
    center = [fan['origin'][i]+fan['size'][i]/2 for i in range(3)]
    plane = fan['origin'][1]+fan['size'][1] if fan['axis'][1]<0 else fan['origin'][1]-model['parameters'].fan_plate
    center[1] = plane+EDGE
    shape = Part.makeCylinder(fan['opening']/2-EDGE,model['parameters'].fan_plate-2*EDGE,App.Vector(*center),axis)
    shape = transformed(shape,rows)
    lo,hi = tight_bounds(shape)
    split_axis = max((0,1),key=lambda i:hi[i]-lo[i])
    count = math.ceil((hi[split_axis]-lo[split_axis])/MAX_SPAN)
    result = []
    for number in range(count):
        low,high = list(lo),list(hi)
        low[split_axis] = lo[split_axis]+(hi[split_axis]-lo[split_axis])*number/count
        high[split_axis] = lo[split_axis]+(hi[split_axis]-lo[split_axis])*(number+1)/count
        result.append(dict(name='fan_arch_'+str(number),label='ファン開口上部の曲面を支える領域',
                           shape=shape.common(box(low,high)),face=None,contact_area_mm2=None,
                           landing='ファン開口の下側。界面はスライサーで設定'))
    return result
