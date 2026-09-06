"""左側板の寸法追随・履歴・形状一致・再読込を検査し、評価用ファイルを出力する。"""

import hashlib
import json
from pathlib import Path
import sys
import time

import FreeCAD as App
import FreeCADGui as Gui
import MeshPart
import Part
# getCameraNodeが返すSWIG型を登録する。
from pivy import coin


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "comparison/freecad-native-sideplate"
sys.path.insert(0, str(ROOT / "scripts"))
from freecad_sideplate import CELLS, INPUTS, DERIVED
from freecad_sideplate_oracle import build as expected_shape


def inputs(doc):
    return {name: doc.Parameters.evalExpression(name).Value for name, _, _ in INPUTS}


def difference(actual, reference):
    actual, reference = actual.copy(True, False), reference.copy(True, False)
    assert len(actual.Solids) == 1 and actual.isValid() and actual.isClosed()
    assert len(reference.Solids) == 1 and reference.isValid() and reference.isClosed()
    added, missing = actual.cut(reference).Volume, reference.cut(actual).Volume
    assert abs(added) < 0.0001 and abs(missing) < 0.0001, (added, missing)
    return {"added_volume_mm3": added, "missing_volume_mm3": missing, "tolerance_mm3": 0.0001}


def inspect(doc):
    doc.recompute()
    assert doc.Sideplate.EvaluationTag == "dgx-native-sideplate-v1"
    assert doc.Sideplate.Tip == doc.NutCut
    states = {o.Name: list(o.State) for o in doc.Objects}
    assert all(s == ["Up-to-date"] for s in states.values()), states
    sketches = [o for o in doc.Objects if o.TypeId == "Sketcher::SketchObject"]
    assert len(sketches) == 10 and all(s.FullyConstrained and s.solve() == 0 for s in sketches)
    p = inputs(doc)
    shape = doc.Sideplate.Shape.copy(True, False)
    comparison = difference(shape, expected_shape(p))
    box = shape.BoundBox
    actual_bounds = [box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax]
    expected_bounds = [-p["ModuleWidth"] / 2, p["FanDepth"] + 11, 0,
                       -p["ModuleWidth"] / 2 + p["SideThickness"], p["ModuleDepth"], p["FrameHeight"]]
    assert max(abs(a - b) for a, b in zip(actual_bounds, expected_bounds)) < 1e-6
    rounded = [f.Surface for f in doc.WindowFillet.Shape.Faces if isinstance(f.Surface, Part.Cylinder)]
    assert len(rounded) == 8 and all(abs(s.Radius - p["WindowRadius"]) < 1e-6 for s in rounded)
    # 素板の厚みを変えても窓が貫通し、差込口の外壁が残ることを検査用形状と照合する。
    return {"inputs_mm": p, "dimensions_mm": [box.XLength, box.YLength, box.ZLength],
            "volume_mm3": shape.Volume, "fully_constrained_sketches": len(sketches),
            "window_corner_radii_mm": [s.Radius for s in rounded],
            "solid_valid_closed": True, "independent_geometry_comparison": comparison,
            "object_states": states}


def perturb(doc, parameter, value):
    cell = CELLS[parameter]
    original = doc.Parameters.getContents(cell)
    try:
        started = time.perf_counter()
        doc.Parameters.set(cell, value)
        doc.recompute()
        elapsed = time.perf_counter() - started
        return {"parameter": parameter, "value": value, "recompute_seconds": elapsed, "geometry": inspect(doc)}
    finally:
        doc.Parameters.set(cell, original)
        doc.recompute()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    output = OUT / "side-L-native.FCStd"
    if output.exists():
        raise FileExistsError("新規評価用の出力先を指定してください")
    report = {"status": "running", "evaluation_only": True}
    try:
        doc = App.activeDocument()
        assert doc and doc.getObject("Sideplate") and doc.Sideplate.EvaluationTag == "dgx-native-sideplate-v1"
        source = ROOT / "DGX-SPARK-RACK-FUSION-v1.f3d"
        source_sha = json.loads((OUT / "fusion_sideplate_definition.json").read_text())["master_sha256"]
        assert hashlib.sha256(source.read_bytes()).hexdigest() == source_sha
        reference = Part.Shape()
        reference.read(str(OUT / "fusion_sideplate_reference.step"))
        baseline = inspect(doc)
        report.update({"freecad_version": App.Version(), "source_f3d_sha256": source_sha,
                       "baseline": baseline, "fusion_boolean_comparison": difference(doc.Sideplate.Shape, reference)})
        cases = [("FrameHeight", "174 mm"), ("ModuleDepth", "234 mm"), ("FitClearance", "0.4 mm"),
                 ("WindowRadius", "4 mm"), ("SupportTop", "64 mm"), ("SideThickness", "14 mm"), ("ModuleWidth", "214 mm")]
        report["parameter_changes"] = []
        for parameter, value in cases:
            report["parameter_changes"].append(perturb(doc, parameter, value))
            difference(doc.Sideplate.Shape, reference)
        report["restored_geometry"] = inspect(doc)
        doc.saveAs(str(output))
        App.closeDocument(doc.Name)
        doc = App.openDocument(str(output))
        report["reopened_baseline"] = inspect(doc)
        report["reopened_edits"] = [perturb(doc, "WindowRadius", "4 mm"), perturb(doc, "FrameHeight", "174 mm")]
        report["reopened_restored_geometry"] = difference(doc.Sideplate.Shape, reference)
        report["parameter_sheet"] = {name: {"cell": CELLS[name], "contents": doc.Parameters.getContents(CELLS[name]), "description": description}
                                     for name, _, description in INPUTS + DERIVED}
        report["feature_expressions"] = {o.Name: list(o.ExpressionEngine) for o in doc.Objects if o.ExpressionEngine}
        shape = doc.Sideplate.Shape.copy(True, False)
        shape.exportStep(str(OUT / "side-L-native.step"))
        outer_point = App.Vector(shape.BoundBox.XMin, shape.BoundBox.YMin, shape.BoundBox.ZMin)
        outer_print_z = App.Rotation(App.Vector(0, 1, 0), -90).multVec(outer_point).z
        shape.rotate(App.Vector(0, 0, 0), App.Vector(0, 1, 0), -90)
        box = shape.BoundBox
        assert abs(outer_print_z - box.ZMin) < 1e-6
        shape.translate(App.Vector(-box.XMin, -box.YMin, -box.ZMin))
        mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.02, AngularDeflection=0.15, Relative=False)
        mesh.write(str(OUT / "side-L-native.stl"), "STL")
        report["stl"] = {"units": "mm", "orientation": "outer face down, minimum XYZ = 0",
                         "linear_deflection_mm": 0.02, "angular_deflection_rad": 0.15, "triangles": mesh.CountFacets,
                         "outer_face_at_bed_verified": True}
        doc.NutCut.ViewObject.ShapeColor = (0.35, 0.55, 0.72)
        doc.Sideplate.ViewObject.ShapeColor = (0.35, 0.55, 0.72)
        view = Gui.activeDocument().activeView()
        # 視点切替アニメーションの途中を保存しないよう、カメラへ直接向きを指定する。
        rotation = App.Rotation(App.Vector(0.74290609, 0.30772209, 0.59447283), 69.73561)
        view.getCameraNode().orientation.setValue(*rotation.Q)
        view.fitAll()
        Gui.updateGui()
        view.saveImage(str(OUT / "side-L-native.png"), 1300, 1100, "White")
        report["preview_render"] = "camera orientation set directly without view animation"
        doc.recompute()
        doc.save()
        report["files_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in (output, OUT / "side-L-native.step", OUT / "side-L-native.stl")}
        report["fusion_master_unchanged"] = hashlib.sha256(source.read_bytes()).hexdigest() == source_sha
        assert report["fusion_master_unchanged"]
        report["status"] = "passed"
        report["physical_validation"] = "造形、接合、荷重、冷却は未検証"
    except Exception as error:
        report["status"] = "failed"
        report["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        (OUT / "validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "output": str(output), "parameter_changes": len(cases),
                      "fusion_difference": report["fusion_boolean_comparison"], "reopened_edits": len(report["reopened_edits"])}))


if __name__ == "__main__":
    main()
