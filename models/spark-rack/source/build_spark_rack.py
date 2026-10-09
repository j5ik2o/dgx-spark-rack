"""Pythonの形状定義からFCStd・STEP・STLと検証結果を生成する。"""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
import uuid

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/cad'))

import FreeCAD as App
import FreeCADGui as Gui
import MeshPart
import Part
from pivy import coin

from spark_rack_parameters import Parameters
from freecad_spark_rack import create,shapes,assembly_shapes,show_layout,PRINT_PARTS,LAYOUTS
from validate_spark_rack import validate,dimensions
from check_stl import inspect as inspect_stl

SOURCES=["models/spark-rack/source/"+name for name in (
    "spark_rack_parameters.py","freecad_spark_rack.py","validate_spark_rack.py",
    "build_spark_rack.py","run_spark_rack.FCMacro")]+["tools/cad/check_stl.py","tools/cad/controller_mount.py","tools/cad/edge_finishing.py"]


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def save_json(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def print_shape(name,shape):
    shape=shape.copy()
    if name=='side_L' or name.startswith('fit_coupon_'):
        shape.rotate(App.Vector(),App.Vector(0,1,0),-90)
    elif name=='side_R':shape.rotate(App.Vector(),App.Vector(0,1,0),90)
    elif name in ('locking_pin','bridge_clip','controller_dock'):shape.rotate(App.Vector(),App.Vector(1,0,0),180)
    elif name=='fan_cassette':shape.rotate(App.Vector(),App.Vector(1,0,0),90)
    b=shape.optimalBoundingBox(False)
    shape.translate(App.Vector(-b.XMin,-b.YMin,-b.ZMin))
    return shape


def render(doc,path):
    Gui.updateGui()
    view=Gui.activeDocument().activeView()
    view.viewAxonometric();view.fitAll();Gui.updateGui()
    camera=view.getCameraNode()
    camera.nearDistance.setValue(0.1);camera.farDistance.setValue(10000)
    view.saveImage(str(path),1500,1000,'White')


def build(output_dir=None,*,parameters=None,render_images=True):
    p=parameters or Parameters()
    out=Path(output_dir).resolve() if output_dir is not None else ROOT/'build/spark-rack'/(
        datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8])
    if out.exists():raise FileExistsError(out)
    sources={name:digest(ROOT/name) for name in SOURCES}
    report={"status":"running","physical_validation":"実物の強度・冷却性能は未検証"}
    out.mkdir(parents=True)
    doc=None
    try:
        report.update(validate(p))
        doc=create(p)
        part_shapes={name:doc.getObject('Print_'+name).Shape for name in PRINT_PARTS}
        (out/'stl').mkdir();(out/'step').mkdir()
        stls={}
        for name,shape in part_shapes.items():
            oriented=print_shape(name,shape)
            oriented.exportStep(str(out/'step'/(name+'.step')))
            mesh=MeshPart.meshFromShape(Shape=oriented,LinearDeflection=0.02,AngularDeflection=0.15,Relative=False)
            path=out/'stl'/(name+'.stl');mesh.write(str(path),'STL')
            stls[name]=inspect_stl(path)
        save_json(out/'stl_validation.json',stls)
        for name,layout in LAYOUTS.items():
            Part.makeCompound([s for _,s in assembly_shapes(p,part_shapes,*layout)]).exportStep(str(out/(name+'.step')))
            show_layout(doc,name)
            if render_images:render(doc,out/(name+'.png'))
        show_layout(doc,'four_units')
        target=out/'DGX-SPARK-RACK.FCStd'
        doc.saveAs(str(target));App.closeDocument(doc.Name);doc=App.openDocument(str(target))
        for name in PRINT_PARTS:
            actual=doc.getObject('Print_'+name).Shape
            assert actual.isValid() and actual.isClosed()
            assert abs(actual.Volume-report['parts'][name]['volume_mm3'])<1e-6,name
        report.update(status='passed',parameters=p.values(),reopened=True,
                      parameter_editing='Pythonの寸法定義を変更し、再生成する。FCStdの表は生成時の記録。')
        save_json(out/'validation.json',report)
        assert sources=={name:digest(ROOT/name) for name in SOURCES},'生成中にソースが変更されました'
        save_json(out/'manifest.json',{
            'status':'passed','design':'spark-rack-python','freecad_version':App.Version(),
            'sources_sha256':sources,
            'outputs_sha256':{str(f.relative_to(out)):digest(f) for f in sorted(out.rglob('*')) if f.is_file()},
        })
    except Exception as error:
        report.update(status='failed',error=f'{type(error).__name__}: {error}')
        save_json(out/'validation.json',report)
        raise
    print(f'生成・検査完了: {out}',flush=True)
    return out
