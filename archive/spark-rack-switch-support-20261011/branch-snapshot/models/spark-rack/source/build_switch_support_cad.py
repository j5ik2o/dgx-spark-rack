"""支持部と柱の接合を参照CADへ保存し、全体配置との干渉・交換経路を検査する。"""
import json
import os
from pathlib import Path
import sys

import FreeCAD as App
import FreeCADGui as Gui
import Part
from freecad_switch_support import build_shapes, box
from switch_support_parameters import SUPPORT


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def overlap_bounds(a, b):
    aa, bb = a.BoundBox, b.BoundBox
    return min(aa.XMax,bb.XMax)-max(aa.XMin,bb.XMin)>1e-7 and min(aa.YMax,bb.YMax)-max(aa.YMin,bb.YMin)>1e-7 and min(aa.ZMax,bb.ZMax)-max(aa.ZMin,bb.ZMin)>1e-7


def contact(a, b, z):
    left=[f for f in a.Faces if abs(f.BoundBox.ZMin-z)<1e-6 and abs(f.BoundBox.ZMax-z)<1e-6]
    right=[f for f in b.Faces if abs(f.BoundBox.ZMin-z)<1e-6 and abs(f.BoundBox.ZMax-z)<1e-6]
    return sum(x.common(y).Area for x in left for y in right)


def band_shape(band):
    points=band['section_xz'];outer=[];thickness=band['thickness']
    for i,point in enumerate(points):
        previous=points[i-1];following=points[(i+1)%len(points)]
        a=[point[j]-previous[j] for j in range(2)];b=[following[j]-point[j] for j in range(2)]
        la=(a[0]**2+a[1]**2)**.5;lb=(b[0]**2+b[1]**2)**.5
        pa=[point[0]+a[1]/la*thickness,point[1]-a[0]/la*thickness]
        pb=[point[0]+b[1]/lb*thickness,point[1]-b[0]/lb*thickness]
        difference=[pb[j]-pa[j] for j in range(2)]
        t=(difference[0]*b[1]-difference[1]*b[0])/(a[0]*b[1]-a[1]*b[0])
        outer.append([pa[j]+a[j]*t for j in range(2)])
    def solid(polygon):
        vectors=[App.Vector(x,band['center_y']-band['width']/2,z) for x,z in polygon]
        return Part.Face(Part.makePolygon(vectors+vectors[:1])).extrude(App.Vector(0,band['width'],0))
    return solid(outer).cut(solid(points)).removeSplitter()


def validate(shapes, fixtures):
    for name,s in shapes.items():
        if not s.isValid() or not s.isClosed() or len(s.Solids)!=1:
            raise ValueError('支持部が閉じた一部品になっていません: '+name)
    pairs=list(shapes.items()); collisions=[]
    for i,(name,a) in enumerate(pairs):
        for other,b in pairs[i+1:]:
            if overlap_bounds(a,b) and a.common(b).Volume>1e-5:
                collisions.append([name,other])
    if collisions: raise ValueError('支持部の干渉: '+json.dumps(collisions))
    bearings={}
    for side in ('left','right'):
        for end,index in (('front',0),('rear',2)):
            bearings[f'{side}_{end}_rail_to_column']=contact(shapes[f'rail_{side}_{index}'],shapes[f'column_{side}_{end}_lower'],SUPPORT.rail_top-28)
            bearings[f'{side}_{end}_column_cap']=contact(shapes[f'column_{side}_{end}_lower'],shapes[f'column_{side}_{end}_upper'],SUPPORT.rail_top)
        for i,y in enumerate(SUPPORT.cross_centers_y):
            index=0 if y<-220 else 2
            bearings[f'cross_{i}_{side}_to_rail']=contact(shapes[f'cross_{i}_{side}'],shapes[f'rail_{side}_{index}'],SUPPORT.rail_top-10)
    for i in range(2):
        bearings[f'cross_{i}_to_tray']=sum(contact(shapes[f'cross_{i}_{side}'],shapes['tray'],SUPPORT.rail_top) for side in ('left','right'))
    if min(bearings.values())<150: raise ValueError('支持部の受け面を確認できません: '+str(bearings))
    # ナットのねじ穴を横切る長さと、その先の突出量まで確認する。
    fasteners=[]
    for f in fixtures:
        axis=f['axis'];sign=f['sign'];nut=shapes[f['name']+'_nut'];screw=shapes[f['name']+'_screw']
        minimum=['XMin','YMin','ZMin'];maximum=['XMax','YMax','ZMax']
        nut_start=getattr(nut.BoundBox,minimum[axis] if sign>0 else maximum[axis])
        nut_end=getattr(nut.BoundBox,maximum[axis] if sign>0 else minimum[axis])
        tip=getattr(screw.BoundBox,maximum[axis] if sign>0 else minimum[axis])
        thickness=sign*(nut_end-nut_start)
        engagement=max(0,min(thickness,sign*(tip-nut_start)))
        projection=sign*(tip-nut_end)
        direction=[sign if j==axis else 0 for j in range(3)]
        centerline=Part.makeCylinder(.5,f['length'],App.Vector(*f['start']),App.Vector(*direction))
        nut_line_start=list(f['start']);nut_line_start[axis]=nut_start
        nut_line=Part.makeCylinder(.5,thickness,App.Vector(*nut_line_start),App.Vector(*direction))
        centered=all(abs((getattr(nut.BoundBox,minimum[j])+getattr(nut.BoundBox,maximum[j]))/2-f['start'][j])<1e-6 for j in range(3) if j!=axis)
        if engagement<thickness-1e-7 or projection<0 or not centered or centerline.cut(screw).Volume>1e-5 or nut_line.common(nut).Volume>1e-5:
            raise ValueError('ねじが相手のナットを貫通しません: '+f['name'])
        fasteners.append({'name':f['name'],'engagement_mm':engagement,'tip_projection_mm':round(projection,3)})
    # 下柱→奥行梁の前・中・後→横梁の左・右→上柱。ねじは最後に入れる。
    fixed=[shapes[n] for n in shapes if n.startswith('column_') and n.endswith('_lower')]
    sequence=[f'rail_{side}_{i}' for side in ('left','right') for i in range(3)]
    sequence += [f'cross_{i}_{side}' for i in range(2) for side in ('left','right')]
    sequence += [n for n in shapes if n.startswith('column_') and n.endswith('_upper')]
    samples=0
    for name in sequence:
        for dz in range(70,-1,-2):
            moved=shapes[name].copy();moved.translate(App.Vector(0,0,dz));samples+=1
            if any(overlap_bounds(moved,s) and moved.common(s).Volume>1e-5 for s in fixed):
                raise ValueError('上からの挿入が途中で塞がります: '+name+' / '+str(dz))
        fixed.append(shapes[name])
    return {'status':'passed','bearing_contact_mm2':bearings,'fasteners':fasteners,
            'insertion_samples':samples,'insertion_order':sequence,
            'scope':'支持部の接合・受け面・仮ねじとナットの到達・離散的な組立経路。強度と実物の適合は未検証。'}


def build(folder):
    Gui.showMainWindow()
    data=json.loads((folder/'overview-report.json').read_text());shapes,fixtures=build_shapes()
    validation=validate(shapes,fixtures); scenes={};checks={}
    for mode,layout in data.items():
        installed=mode!='ring'
        active={n:s for n,s in shapes.items() if installed or (n!='tray' and not n.startswith('tray_lock_'))}
        for band in layout['switch_support']['bands']:
            strap=band_shape(band)
            if any(overlap_bounds(strap,s) and strap.common(s).Volume>1e-5 for s in active.values()):raise ValueError('保持バンドが支持部へ重なります')
            active[band['name']]=strap
        refs={}
        for b in layout['members']+layout['feet']+layout['equipment']+layout['trays']+layout['holders']+layout['adapter_layout']['mounts']+[layout['adapter_layout']['separator']]:
            if b.get('family')=='column':continue
            refs[b['name']]=box(*b['origin'],*b['size'])
        if installed:
            for b in layout['switch_support']['reference_feet']:refs[b['name']]=box(*b['origin'],*b['size'])
        collisions=[]
        for name,s in active.items():
            for label,r in refs.items():
                if overlap_bounds(s,r) and s.common(r).Volume>1e-5:collisions.append([name,label])
        if collisions:raise ValueError(mode+'の全体配置と支持部が干渉: '+json.dumps(collisions))
        exchange=[]
        if installed:
            # 保持ねじとバンドを外し、受け板と本体を手で下から支えて引き出す。
            moving=Part.makeCompound([active['tray'],refs['switch'],*[refs[b['name']] for b in layout['switch_support']['reference_feet']]])
            obstacles=[s for n,s in active.items() if n!='tray' and not n.startswith(('tray_lock_','switch_band_'))]
            obstacles += [s for n,s in refs.items() if n!='switch' and not n.startswith('switch_reference_foot')]
            for dy in range(0,501,5):
                moved=moving.copy();moved.translate(App.Vector(0,dy,0))
                if any(overlap_bounds(moved,s) and moved.common(s).Volume>1e-5 for s in obstacles):
                    raise ValueError(mode+'の後方取り出しが塞がります: '+str(dy))
                exchange.append(dy)
        tool_failures=[]
        for f in fixtures:
            if f['name'].startswith('tray_lock_') and not installed:continue
            start=list(f['start']);start[f['axis']]-=f['sign']*4
            tool=Part.makeCylinder(3,30,App.Vector(*start),App.Vector(*[(-f['sign'] if j==f['axis'] else 0) for j in range(3)]))
            obstacles=[s for n,s in active.items() if n!=f['name']+'_screw']+list(refs.values())
            if any(overlap_bounds(tool,s) and tool.common(s).Volume>1e-5 for s in obstacles):tool_failures.append(f['name'])
        if tool_failures:raise ValueError(mode+'の工具経路が塞がります: '+str(tool_failures))
        force=SUPPORT.reference_mass_kg*9.80665
        center_y=-next(b for b in layout['equipment'] if b['kind']=='switch')['size'][1]/2 if installed else -183.5
        front_y,rear_y=SUPPORT.cross_centers_y
        front_force=force*(rear_y-center_y)/(rear_y-front_y);rear_force=force-front_force
        rear_post=(front_force/2*(front_y+414)+rear_force/2*(rear_y+414))/492
        front_post=force/2-rear_post
        if min(front_force,rear_force,front_post,rear_post)<0:raise ValueError('仮荷重の重心が支持点の外にあります')
        checks[mode]={'status':'passed','tool_reference_collisions':tool_failures,
                      'reference_load_distribution':{'additional_mass_kg':SUPPORT.reference_mass_kg,'front_cross_N':round(front_force,3),'rear_cross_N':round(rear_force,3),'front_post_each_N':round(front_post,3),'rear_post_each_N':round(rear_post,3),'scope':'仮荷重の静力学分配。材料の強度・たわみ・クリープ解析ではない。'},'whole_layout_collisions':collisions,'exchange_samples':len(exchange),
                      'exchange_travel_mm':500 if installed else 0,'operator_support_required':True,
                      'tray_to_switch_feet_contact_mm2':sum(contact(active['tray'],refs[b['name']],SUPPORT.rail_top+SUPPORT.tray_thickness) for b in layout['switch_support']['reference_feet']) if installed else 0}
        doc=App.newDocument('SwitchSupportAssembly');doc.Label='支持部を含む設計参照・'+mode
        scene=[]
        for name,s in active.items():
            obj=doc.addObject('Part::Feature',name);obj.Shape=s
            kind='switch_band' if name.startswith('switch_band_') else 'switch_tray' if name=='tray' else 'frame' if name.startswith('column_') else 'fastener' if name.endswith(('_screw','_nut','_washer')) else 'switch_support'
            obj.Label={'switch_band':'保持バンド・購入品の仮外形','switch_tray':'アルミ受け板・寸法仮','frame':'支持穴と上からの柱接合','fastener':'仮のM4固定具','switch_support':'荷重を段差で受ける支持梁'}[kind]+' / '+name
            obj.ViewObject.ShapeColor=(.46,.65,.48) if kind=='switch_support' else (.63,.68,.72) if kind=='switch_tray' else (.32,.43,.51) if kind=='frame' else (.65,.58,.42)
            vertices,faces=s.tessellate(.3)
            scene.append({'name':name,'kind':kind,'vertices':[[v.x,v.y,v.z] for v in vertices],'faces':faces,'label':obj.Label})
        for name,s in refs.items():
            obj=doc.addObject('Part::Feature','Reference_'+name);obj.Shape=s;obj.Label='参考外形・'+name;obj.ViewObject.Transparency=65
        doc.recompute();path=folder/('switch-support-'+mode+'.FCStd');doc.saveAs(str(path))
        if installed:Part.makeCompound(list(active.values())).exportStep(str(folder/('switch-support-'+mode+'.step')))
        expected={o.Name:o.Shape.Volume for o in doc.Objects};App.closeDocument(doc.Name);doc=App.openDocument(str(path))
        if any(abs(doc.getObject(n).Shape.Volume-v)>1e-6 for n,v in expected.items()):raise ValueError('保存後の再読込が不一致です')
        App.closeDocument(doc.Name);scenes[mode]=scene;checks[mode]['reopened']=True
    write_json(folder/'switch-support-cad-scene.json',scenes)
    write_json(folder/'switch-support-validation.json',{'status':'passed','support_parts':validation,'layouts':checks,'manufacturing_release':False})


if __name__=='__main__':
    try:
        build(Path(sys.argv[1]))
    except Exception:
        import traceback
        traceback.print_exc();sys.stderr.flush();os._exit(1)
    sys.stdout.flush();os._exit(0)
