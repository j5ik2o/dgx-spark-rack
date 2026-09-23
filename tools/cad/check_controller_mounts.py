"""3モデルをコードから組み立て、共通ドックとケースの取付を検査する。"""
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import runpy
import sys
import traceback
import uuid

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/cad'))
for model in ('spark-rack','adapter-rack'):
    sys.path.insert(0,str(ROOT/'models'/model/'source'))


def main():
    import FreeCAD as App
    import FreeCADGui as Gui
    Gui.showMainWindow()
    import Part
    from pivy import coin
    from PySide6.QtWidgets import QApplication
    from controller_mount import dock,place,THICKNESS,RACK_PITCH,RACK_U,CASE_PITCH,STANDOFF,hardware_bom,case_mount_bolt
    from spark_rack_parameters import Parameters
    from freecad_spark_rack import shapes,assembly_shapes,LAYOUTS
    from freecad_adapter_rack import create as create_adapter
    from validate_adapter_rack import visible_links,show_layout,value

    out=ROOT/'build/fan-controller'/('mount-check-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8])
    out.mkdir(parents=True,exist_ok=False)
    sources=[ROOT/'tools/cad/controller_mount.py',Path(__file__),ROOT/'tools/cad/freecad_features.py']
    for model in ('spark-rack','adapter-rack','fan-controller'):
        sources.extend((ROOT/'models'/model/'source').glob('*.py'))
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    model=runpy.run_path(str(ROOT/'models/fan-controller/source/freecad_fan_controller.py'))
    cx=(model['envelope_x']+model['outer_right'])/2
    cy=(model['envelope_y']+model['envelope_back'])/2
    shift=App.Vector(-cx,-cy,THICKNESS-model['bottom_z'])
    normalized=[]
    for name,s in [('body',model['body_final']),('lid',model['lid_final'])]+[(f'clamp{i}',s) for i,s in enumerate(model['clamps'])]:
        s=s.copy();s.translate(shift);normalized.append((name,s))
    App.closeDocument(model['doc'].Name)
    adapter=create_adapter()
    p=Parameters()
    spark=shapes(p)
    report={'status':'running','physical_validation':False,'layouts':{},'hardware_per_case':hardware_bom()}

    def overlap(a,b):
        aa,bb=a.BoundBox,b.BoundBox
        if any(min(getattr(aa,k+'Max'),getattr(bb,k+'Max'))-max(getattr(aa,k+'Min'),getattr(bb,k+'Min'))<=1e-7 for k in 'XYZ'):
            return 0.0
        return a.common(b).Volume

    def cylinder(u,v,w,r,h):
        return Part.makeCylinder(r,h,App.Vector(u,v,w))

    def nut(u,v,w,af,thickness,bore):
        radius=af/math.sqrt(3)
        vertices=[App.Vector(u+radius*math.cos(i*math.pi/3),v+radius*math.sin(i*math.pi/3),w) for i in range(7)]
        return Part.Face(Part.makePolygon(vertices)).extrude(App.Vector(0,0,thickness)).cut(cylinder(u,v,w-1,bore,thickness+2))

    def verify(rack_name,layout,rack_items,mounts):
        cases=[];bolts=[];zones=[]
        for index,(origin,u,v,w) in enumerate(mounts):
            expected=place(dock(),origin,u,v,w)
            actual=[s for n,s in rack_items if 'Dock' in n or 'controller_dock' in n]
            assert any(expected.cut(s).Volume<0.001 and s.cut(expected).Volume<0.001 for s in actual),'ドックの配置不一致'
            for name,s in normalized:
                cases.append((f'case{index}_{name}',place(s,origin,u,v,w)))
            # ボルト軸と頭。M4はドックから側枠へ、M3は外耳からドックへ。
            for yy in (-RACK_PITCH/2,RACK_PITCH/2):
                bolt=cylinder(RACK_U,yy,3.5-25,2,25).fuse(cylinder(RACK_U,yy,3.5,4,4))
                bolts.append((f'rack_bolt{index}_{yy}',place(bolt,origin,u,v,w)))
                bolts.append((f'rack_nut{index}_{yy}',place(nut(RACK_U,yy,-STANDOFF-12-3.2,7,3.2,2.1),origin,u,v,w)))
            for xx in (-CASE_PITCH/2,CASE_PITCH/2):
                bolt=case_mount_bolt(xx)
                bolts.append((f'case_bolt{index}_{xx}',place(bolt,origin,u,v,w)))
                bolts.append((f'case_nut{index}_{xx}',place(nut(xx,0,0.2,5.5,2.4,1.6),origin,u,v,w)))
            # 配線用の設計余白（プラグ実測値ではない）。筐体端から30mm。
            for key in ('USB_PORT','TERMINAL_PORT','FAN_PORT','NTC_PORT'):
                face,yy,zz,_,_=model[key]
                start=model['envelope_x']-30 if face=='X_MIN' else model['outer_right']
                zone=Part.makeBox(30,20,14,App.Vector(start,yy-10,zz-7))
                zone.translate(shift)
                zone=place(zone,origin,u,v,w)
                assert zone.BoundBox.ZMin>=-1e-6,(rack_name,layout,key,'配線余白が床より下')
                zones.append((f'case{index}_{key}',zone))
        failures=[]
        for name,s in cases+bolts:
            for other,t in rack_items:
                if overlap(s,t)>0.001:failures.append((name,other))
        for i,(name,s) in enumerate(cases+bolts):
            for other,t in (cases+bolts)[i+1:]:
                if overlap(s,t)>0.001:failures.append((name,other))
        assert not failures,(rack_name,layout,failures)
        for name,zone in zones:
            for other,s in rack_items+bolts+cases:
                assert overlap(zone,s)<0.001,(rack_name,layout,name,other,'配線余白')
        # ケースを外向きに30mm動かした範囲もラックや他ケースに干渉しない。
        for index,(origin,u,v,w) in enumerate(mounts):
            group=[s for name,s in cases if name.startswith(f'case{index}_')]
            b=Part.makeCompound(group).optimalBoundingBox(False)
            dx=30*w[0]
            sweep=Part.makeBox(b.XLength+abs(dx),b.YLength,b.ZLength,
                               App.Vector(b.XMin+min(0,dx),b.YMin,b.ZMin))
            for other,s in rack_items+[(n,s) for n,s in cases if not n.startswith(f'case{index}_')]:
                assert overlap(sweep,s)<0.001,(rack_name,layout,'ケース取り外し',other)
        report['layouts'][rack_name+'_'+layout]={'controllers':len(mounts),'collisions':[],
                    'cable_zone_mm':[30,20,14],'outward_removal_mm':30,
                    'rack_and_case_screw_paths':'passed',
                    'cable_clearance_includes':['rack','case','mounting_bolts','mounting_nuts']}
        return rack_items+cases+bolts

    try:
        scenes={}
        for layout,(columns,rows) in LAYOUTS.items():
            mounts=[]
            for col in range(columns):
                sign=-1 if col==0 else 1
                for row in range(rows):
                    mounts.append((((col-(columns-1)/2)*p.column_pitch+sign*(p.module_width/2+STANDOFF),
                                    p.controller_y,row*p.row_pitch+p.controller_z-RACK_U),
                                   (0,0,1),(0,-sign,0),(sign,0,0)))
            items=assembly_shapes(p,spark,columns,rows)
            scenes['spark_'+layout]=verify('spark',layout,items,mounts)
            show_layout(adapter,columns,rows)
            mounts=[]
            for col in range(columns):
                sign=-1 if col==0 else 1
                mounts.append(((col*value(adapter,'ColumnPitch')+sign*(value(adapter,'ModuleWidth')/2+STANDOFF),
                                -value(adapter,'PostY')-RACK_U,value(adapter,'ModuleHeight')/2),
                               (0,1,0),(0,0,sign),(sign,0,0)))
            scenes['adapter_'+layout]=verify('adapter',layout,visible_links(adapter),mounts)
        # 分解詳細は外観確認用。取付検査の8構成とは区別する。
        detail=[('dock',dock())]
        for label,shape in normalized:
            shape=shape.copy()
            shape.translate(App.Vector(0,0,38 if label=='lid' else 26 if label.startswith('clamp') else 15))
            detail.append(('case_'+label,shape))
        scenes['mount_detail']=detail
        doc=App.newDocument('ControllerMountChecks')
        for name,items in scenes.items():
            group=doc.addObject('App::Part',name)
            for i,(label,shape) in enumerate(items):
                obj=doc.addObject('Part::Feature',name+'_'+str(i));obj.Label=label;obj.Shape=shape
                group.addObject(obj)
                # 本番の色構成。筐体は黒系、ファンはベージュ／ブラウン。
                color=(0.12,0.13,0.15)
                if label.startswith('case'):
                    color=(0.18,0.19,0.21) if '_lid' in label else (0.10,0.11,0.13)
                elif 'Dock' in label or 'dock' in label:
                    color=(0.22,0.23,0.25)
                elif 'REF_FAN' in label or label.startswith('Fan0') or label.startswith('Fan1'):
                    color=(0.76,0.66,0.49)
                elif 'REF_DGX' in label or label.startswith('Adapter'):
                    color=(0.55,0.56,0.58)
                elif 'bolt' in label or 'nut' in label or 'SCREW' in label or 'NUT' in label:
                    color=(0.48,0.49,0.51)
                obj.ViewObject.ShapeColor=color
                obj.ViewObject.LineColor=(0.07,0.08,0.09)
            group.Visibility=False
        for scene in ('spark_two_horizontal','adapter_four_units','mount_detail'):
            doc.getObject(scene).Visibility=True
            doc.recompute();Gui.updateGui();QApplication.processEvents()
            Gui.activeDocument().activeView().viewAxonometric()
            QApplication.processEvents()
            Gui.activeDocument().activeView().fitAll();Gui.updateGui();QApplication.processEvents()
            camera=Gui.activeDocument().activeView().getCameraNode()
            camera.nearDistance.setValue(0.1);camera.farDistance.setValue(10000)
            Gui.activeDocument().activeView().saveImage(str(out/(scene+'.png')),1500,1000,'White')
            doc.getObject(scene).Visibility=False
        doc.spark_two_horizontal.Visibility=True
        doc.recompute();doc.saveAs(str(out/'ControllerMountChecks.FCStd'))
        report['status']='passed'
        assert hashes=={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
        (out/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        (out/'manifest.json').write_text(json.dumps({'status':'passed','sources_sha256':hashes,
            'outputs_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()}},ensure_ascii=False,indent=2)+'\n')
        print(out,flush=True)
    except Exception as error:
        report.update(status='failed',error=str(error))
        (out/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        raise
    finally:
        for name in list(App.listDocuments()):App.closeDocument(name)


if __name__=='__main__':
    try:main()
    except Exception:
        traceback.print_exc();sys.stdout.flush();sys.stderr.flush();os._exit(1)
    sys.stdout.flush();sys.stderr.flush();os._exit(0)
