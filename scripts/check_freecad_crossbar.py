"""FreeCAD支持棒の履歴・寸法変更・形状一致・再読込・出力を検証する。"""

import hashlib
import json
import math
from pathlib import Path
import sys
import time

import FreeCAD as App
import FreeCADGui as Gui
import MeshPart
import Part


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "comparison/freecad-native-crossbar"
sys.path.insert(0, str(ROOT / "scripts"))
from freecad_crossbar import CELLS, INPUTS, DERIVED


def inspect(doc, length, pin_x, hole_diameter, thickness):
    doc.recompute()
    body = doc.Crossbar
    assert body.EvaluationTag == "dgx-native-crossbar-v1"
    shape = body.Shape.copy(True, False)
    assert len(shape.Solids) == 1 and shape.isValid() and shape.isClosed()
    assert body.Tip == doc.ThroughHoles and doc.ThroughHoles.Type == "ThroughAll"
    states = {o.Name: list(o.State) for o in doc.Objects}
    assert all(s == ["Up-to-date"] for s in states.values()), states
    sketches = [doc.Outline, doc.PinHoles]
    assert all(s.FullyConstrained and s.solve() == 0 for s in sketches)
    box = shape.BoundBox
    bounds = [box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax]
    expected_bounds = [-length / 2, -10, 0, length / 2, 10, thickness]
    assert max(abs(a - b) for a, b in zip(bounds, expected_bounds)) < 1e-6, bounds
    cylinders = sorted((f.Surface for f in shape.Faces if isinstance(f.Surface, Part.Cylinder)),
                       key=lambda surface: surface.Center.x)
    assert len(cylinders) == 2
    for surface, x in zip(cylinders, (-pin_x, pin_x)):
        assert abs(surface.Center.x - x) < 1e-6 and abs(surface.Center.y) < 1e-6
        assert abs(surface.Radius * 2 - hole_diameter) < 1e-6
        assert abs(abs(surface.Axis.z) - 1) < 1e-9
    expected_volume = (length * 20 - 2 * math.pi * (hole_diameter / 2) ** 2) * thickness
    assert abs(shape.Volume - expected_volume) < 1e-5
    return {
        "dimensions_mm": [box.XLength, box.YLength, box.ZLength],
        "hole_center_x_mm": [s.Center.x for s in cylinders],
        "hole_diameter_mm": [s.Radius * 2 for s in cylinders],
        "volume_mm3": shape.Volume, "solid_valid_closed": True,
        "fully_constrained_sketches": [s.Name for s in sketches], "object_states": states,
    }


def geometry_difference(doc, reference):
    actual = doc.Crossbar.Shape.copy(True, False)
    lost = reference.cut(actual).Volume
    added = actual.cut(reference).Volume
    assert lost < 1e-5 and added < 1e-5, (lost, added)
    return {"missing_volume_mm3": lost, "added_volume_mm3": added, "tolerance_mm3": 1e-5}


def change_and_restore(doc, parameter, value, expected):
    sheet = doc.Parameters
    cell = CELLS[parameter]
    original = sheet.getContents(cell)
    try:
        started = time.perf_counter()
        sheet.set(cell, value)
        doc.recompute()
        elapsed = time.perf_counter() - started
        record = inspect(doc, **expected)
        return {"parameter": parameter, "value": value, "recompute_seconds": elapsed, "geometry": record}
    finally:
        sheet.set(cell, original)
        doc.recompute()
        inspect(doc, 204, 97, 4.6, 8)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    output = OUT / "crossbar-native.FCStd"
    if output.exists():
        raise FileExistsError("新規評価用の出力先を指定してください")
    report_path = OUT / "validation.json"
    report = {"status": "running", "evaluation_only": True}
    report_path.write_text(json.dumps(report) + "\n", encoding="utf-8")
    try:
        doc = App.activeDocument()
        assert doc and doc.getObject("Crossbar") and doc.Crossbar.EvaluationTag == "dgx-native-crossbar-v1"
        source = ROOT / "DGX-SPARK-RACK-FUSION-v1.f3d"
        expected_sha = json.loads((ROOT / "exports/fusion/roundtrip.json").read_text())["file_sha256"]
        assert hashlib.sha256(source.read_bytes()).hexdigest() == expected_sha
        reference = Part.Shape()
        reference.read(str(OUT / "fusion_crossbar_reference.step"))
        report.update({"freecad_version": App.Version(), "source_f3d_sha256": expected_sha,
                       "baseline": inspect(doc, 204, 97, 4.6, 8),
                       "fusion_boolean_comparison": geometry_difference(doc, reference)})
        cases = [
            ("ModuleWidth", "214 mm", {"length": 208, "pin_x": 99, "hole_diameter": 4.6, "thickness": 8}),
            ("FitClearance", "0.4 mm", {"length": 204, "pin_x": 97, "hole_diameter": 4.8, "thickness": 8}),
            ("BeamThickness", "10 mm", {"length": 204, "pin_x": 97, "hole_diameter": 4.6, "thickness": 10}),
        ]
        report["parameter_changes"] = [change_and_restore(doc, *case) for case in cases]
        report["restored_geometry"] = geometry_difference(doc, reference)
        doc.saveAs(str(output))
        App.closeDocument(doc.Name)
        doc = App.openDocument(str(output))
        report["reopened_baseline"] = inspect(doc, 204, 97, 4.6, 8)
        report["reopened_edit"] = change_and_restore(doc, *cases[0])
        report["reopened_restored_geometry"] = geometry_difference(doc, reference)
        report["parameter_sheet"] = {
            name: {"cell": CELLS[name], "contents": doc.Parameters.getContents(CELLS[name]), "description": meaning}
            for name, _, meaning in INPUTS + DERIVED}
        report["feature_expressions"] = {
            name: list(doc.getObject(name).ExpressionEngine)
            for name in ("Outline", "Thickness", "PinHoles", "ThroughHoles")}
        doc.save()
        shape = doc.Crossbar.Shape.copy(True, False)
        shape.exportStep(str(OUT / "crossbar-native.step"))
        box = shape.BoundBox
        shape.translate(App.Vector(-box.XMin, -box.YMin, -box.ZMin))
        mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.02, AngularDeflection=0.15, Relative=False)
        mesh.write(str(OUT / "crossbar-native.stl"), "STL")
        report["stl"] = {"units": "mm", "orientation": "flat, minimum XYZ = 0", "linear_deflection_mm": 0.02,
                         "angular_deflection_rad": 0.15, "triangles": mesh.CountFacets}
        for o in (doc.Outline, doc.Thickness, doc.PinHoles):
            o.Visibility = False
        doc.Crossbar.ViewObject.ShapeColor = (0.35, 0.55, 0.72)
        doc.ThroughHoles.ViewObject.ShapeColor = (0.35, 0.55, 0.72)
        view = Gui.activeDocument().activeView()
        view.viewIsometric()
        view.fitAll()
        Gui.updateGui()
        view.saveImage(str(OUT / "crossbar-native.png"), 1800, 650, "White")
        doc.recompute()
        doc.save()
        report["files_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in (output, OUT / "crossbar-native.step", OUT / "crossbar-native.stl")}
        report["fusion_master_unchanged"] = hashlib.sha256(source.read_bytes()).hexdigest() == expected_sha
        assert report["fusion_master_unchanged"]
        report["status"] = "passed"
        report["physical_validation"] = "造形、接合、荷重、冷却は未検証"
    except Exception as error:
        report["status"] = "failed"
        report["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "output": str(output),
                      "boolean_comparison": report["fusion_boolean_comparison"],
                      "parameter_changes": len(report["parameter_changes"]), "reopened_edit": "passed"}))


if __name__ == "__main__":
    main()
