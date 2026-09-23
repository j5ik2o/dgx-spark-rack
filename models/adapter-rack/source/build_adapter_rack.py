"""アダプターラックv2を新規生成し、FCStd・STEP・STLと検証記録を出力する。"""

from datetime import datetime
import hashlib
import json
from pathlib import Path
import uuid

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools/cad"))

import FreeCAD as App
import FreeCADGui as Gui
import MeshPart
import Part
from pivy import coin

from adapter_rack_parameters import INPUTS, DERIVED, CELLS
from freecad_adapter_rack import create, PRINT_PARTS, LAYOUTS, show_layout
from validate_adapter_rack import validate, inspect, visible_links, assert_equivalent
from check_stl import inspect as inspect_stl

ROOT = Path(__file__).resolve().parents[3]
SOURCES = [
    "models/adapter-rack/source/run_adapter_rack.FCMacro", "models/adapter-rack/source/build_adapter_rack.py",
    "models/adapter-rack/source/freecad_adapter_rack.py", "models/adapter-rack/source/adapter_rack_parameters.py",
    "models/adapter-rack/source/validate_adapter_rack.py", "tools/cad/freecad_features.py", "tools/cad/check_stl.py",
    "models/adapter-rack/reference/adapter_spec.json", "models/adapter-rack/reference/components.json",
    "tools/cad/controller_mount.py",
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")


def print_shape(obj):
    shape = obj.Shape.copy(True, False)
    if obj.Name == "SideL" or obj.Name.startswith("FitCoupon"):
        shape.rotate(App.Vector(), App.Vector(0, 1, 0), -90)
    elif obj.Name in ("SideR", "StackStrap"):
        shape.rotate(App.Vector(), App.Vector(0, 1, 0), 90)
    elif obj.Name == 'AccessoryPlate':
        shape.rotate(App.Vector(), App.Vector(0, 1, 0), -90)
    elif obj.Name == "FanPlate":
        shape.rotate(App.Vector(), App.Vector(1, 0, 0), 90)
    box = shape.optimalBoundingBox(False)
    shape.translate(App.Vector(-box.XMin, -box.YMin, -box.ZMin))
    if obj.Name in ("SideL", "SideR") or obj.Name.startswith("FitCoupon"):
        # 差込口が造形面側へ伏せられていないことを確かめる。
        height = shape.BoundBox.ZLength
        bottom = sum(f.Area for f in shape.Faces if f.BoundBox.ZLength < 1e-6 and abs(f.CenterOfMass.z) < 1e-6)
        top = sum(f.Area for f in shape.Faces if f.BoundBox.ZLength < 1e-6 and abs(f.CenterOfMass.z-height) < 1e-6)
        assert bottom > top, (obj.Name, "差込口の向き", bottom, top)
    return shape


def render(doc, path):
    Gui.updateGui()
    view = Gui.activeDocument().activeView()
    view.viewAxonometric()
    view.fitAll()
    Gui.updateGui()
    # 構成切替直後の古いクリッピング距離で奥の柱が欠けるのを防ぐ。
    camera = view.getCameraNode()
    camera.nearDistance.setValue(0.1)
    camera.farDistance.setValue(10000)
    view.saveImage(str(path), 1500, 1000, "White")


def bom(columns, rows):
    units = columns*rows
    joints = columns if rows == 2 else 0
    return {
        "printed": {"side_L": units, "side_R": units, "support_beam": 2*units,
                    "locking_pin": 4*units, "stack_pin": 4*joints, "stack_strap": 2*joints,
                    "join_bridge": 2*rows if columns == 2 else 0,
                    "fan_plate": columns, "accessory_plate": columns},
        "purchased": {"120mm_PWM_fan": columns, "120mm_guard": columns,
                      "fan_fixing_positions": 4*columns, "M4x25_rack_screws": 4*columns+4*joints,
                      "M4x25_accessory_screws": 2*columns,
                      "M3x12_case_screws": 2*columns, "M3_case_nuts": 2*columns,
                      "M4_nuts_excluding_fan": 4*columns+4*joints+2*columns},
    }


def build(output_dir=None, *, render_images=True):
    out = Path(output_dir).resolve() if output_dir is not None else ROOT/"build/adapter-rack"/(
        datetime.now().strftime("%Y%m%d-%H%M%S")+"-"+uuid.uuid4().hex[:8])
    if out.exists():
        raise FileExistsError(out)
    hashes = {name: digest(ROOT/name) for name in SOURCES}
    out.mkdir(parents=True)
    report = {"status": "running", "physical_fit_tested": False, "thermal_tested": False,
              "controller_case_status": "共通ドック対応。1列のファンにつき1ケース、ケースは別生成"}
    doc = None
    try:
        doc = create()
        report["layouts"] = validate(doc)
        (out/"step").mkdir()
        (out/"stl").mkdir()
        for name, (columns, rows) in LAYOUTS.items():
            show_layout(doc, columns, rows)
            Part.makeCompound([s for _, s in visible_links(doc)]).exportStep(str(out/(name+".step")))
            if render_images:
                render(doc, out/(name+".png"))
        show_layout(doc)
        if render_images:
            refs = [o for o in doc.Objects if o.TypeId == "App::Link" and o.LinkedObject.Name.startswith("REF")]
            for obj in refs:
                obj.Visibility = False
            render(doc, out/"frame_only.png")
            for obj in refs:
                obj.Visibility = True
        target = out/"DGX-SPARK-ADAPTER-RACK-v2.FCStd"
        doc.saveAs(str(target))
        App.closeDocument(doc.Name)
        doc = App.openDocument(str(target))
        report["reopened"] = inspect(doc, 1, 2)
        assert_equivalent(report["reopened"], report["layouts"]["two_vertical"])
        meshes = {}
        for name, filename in PRINT_PARTS.items():
            shape = print_shape(doc.getObject(name))
            shape.exportStep(str(out/"step"/(filename+".step")))
            mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.02, AngularDeflection=0.15, Relative=False)
            path = out/"stl"/(filename+".stl")
            mesh.write(str(path), "STL")
            meshes[filename] = inspect_stl(path)
        save_json(out/"stl_validation.json", meshes)
        report["parameters"] = {name: {"value": doc.Parameters.getContents(CELLS[name]), "description": text}
                                for name, _, text in INPUTS+DERIVED}
        report["bom"] = {name: bom(*layout) for name, layout in LAYOUTS.items()}
        report["status"] = "passed_cad_checks"
        save_json(out/"validation.json", report)
        if hashes != {name: digest(ROOT/name) for name in SOURCES}:
            raise RuntimeError("生成中にソースが変わりました")
        save_json(out/"manifest.json", {
            "status": "passed", "design": "adapter-rack-v2", "freecad_version": App.Version(),
            "sources_sha256": hashes,
            "outputs_sha256": {str(p.relative_to(out)): digest(p) for p in sorted(out.rglob("*")) if p.is_file()},
        })
    except Exception as error:
        report.update(status="failed", error=f"{type(error).__name__}: {error}")
        save_json(out/"validation.json", report)
        if doc and doc.Name in App.listDocuments():
            App.closeDocument(doc.Name)
        raise
    print(f"生成・検査完了: {out}")
    return out
