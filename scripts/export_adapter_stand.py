"""DGX Spark純正アダプター用スタンドを確認し、FreeCADとSTLへ保存する。"""

import hashlib
import json
from pathlib import Path
import sys

import FreeCAD as App
import FreeCADGui as Gui
import MeshPart
import Part
# カメラのSWIG型を登録する。
from pivy import coin

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "exports/adapter-stand"
TARGET = ROOT / "DGX-SPARK-ADAPTER-STAND-v1.FCStd"
sys.path.insert(0, str(ROOT / "scripts"))
from freecad_adapter_stand import CELLS, INPUTS, DERIVED, show_units

PRINT_PARTS = {"Saddle": "saddle", "Rail": "rail", "LockPin": "locking_pin", "JoinClip": "join_clip"}


def inspect(doc, count):
    show_units(doc, count)
    Gui.updateGui()
    doc.recompute()
    sketches = [o for o in doc.Objects if o.TypeId == "Sketcher::SketchObject"]
    assert len(sketches) == 17 and all(s.FullyConstrained and s.solve() == 0 for s in sketches)
    for name in list(PRINT_PARTS) + ["REFAdapter"]:
        shape = doc.getObject(name).Shape
        assert len(shape.Solids) == 1 and shape.isValid() and shape.isClosed(), name
    assembly = Part.getShape(doc.StandAssembly).copy(True, False)
    solids = assembly.Solids
    assert len(solids) == count * 9 + (count - 1) * 2, len(solids)
    collisions = []
    for i, a in enumerate(solids):
        for j in range(i + 1, len(solids)):
            b = solids[j]
            aa, bb = a.BoundBox, b.BoundBox
            overlaps = [min(getattr(aa, axis + "Max"), getattr(bb, axis + "Max"))
                        - max(getattr(aa, axis + "Min"), getattr(bb, axis + "Min")) for axis in "XYZ"]
            if min(overlaps) <= 1e-6:
                continue
            volume = a.common(b).Volume
            if volume > 0.001:
                collisions.append({"solids": [i, j], "volume_mm3": volume})
    assert not collisions, collisions
    # 写真で確認した両端の入出力に、設計上の配線余白を確保する。
    def value(name):
        return doc.Parameters.evalExpression(name).Value
    width, length, height, lift, pitch = [value(n) for n in
        ("AdapterWidth", "AdapterLength", "AdapterHeight", "LiftHeight", "ModulePitch")]
    cable_overlaps = []
    for unit in range(count):
        for end, y in (("AC", -length / 2 - 40), ("USB-C", length / 2)):
            zone = Part.makeBox(width + 20, 40, height + 20,
                                App.Vector(unit * pitch - width / 2 - 10, y, lift - 10))
            overlap = assembly.common(zone).Volume
            if overlap > 0.001:
                cable_overlaps.append({"unit": unit + 1, "end": end, "volume_mm3": overlap})
    assert not cable_overlaps, cable_overlaps
    box = assembly.BoundBox
    return {"visible_units": count, "solids_with_adapter_references": len(solids),
            "dimensions_mm": [box.XLength, box.YLength, box.ZLength],
            "fully_constrained_sketches": len(sketches), "interference_threshold_mm3": 0.001,
            "cable_exit_clearance": {"outward_mm": 40, "side_and_vertical_margin_mm": 10,
                                     "basis": "design allowance, not manufacturer connector dimensions",
                                     "interferences": cable_overlaps},
            "interferences": collisions, "part_volumes_mm3": {name: doc.getObject(name).Shape.Volume for name in PRINT_PARTS}}


def render(doc, count, path):
    show_units(doc, count)
    Gui.updateGui()
    view = Gui.activeDocument().activeView()
    q = App.Rotation(App.Vector(0.74290609, 0.30772209, 0.59447283), 69.73561).Q
    view.getCameraNode().orientation.setValue(*q)
    view.fitAll()
    Gui.updateGui()
    view.saveImage(str(path), 1500, 900, "White")


def main(*, update_existing=False):
    if TARGET.exists() and not update_existing:
        raise FileExistsError(TARGET)
    OUT.mkdir(parents=True, exist_ok=True)
    doc = App.ActiveDocument
    assert doc and doc.getObject("StandAssembly") and doc.getObject("REFAdapter")
    if update_existing:
        assert Path(doc.FileName).resolve() == TARGET.resolve(), "更新対象のスタンド文書が一致しません"
    spec = json.loads((OUT / "adapter_spec.json").read_text())
    report = {"status": "running", "fit_status": "published_measurements_based",
              "dimension_basis": spec["dimension_basis"], "published_reference_model": spec["model"],
              "design_adapter_dimensions_mm": {axis: doc.Parameters.evalExpression(name).Value
                  for axis, name in (("width_x", "AdapterWidth"), ("length_y", "AdapterLength"), ("height_z", "AdapterHeight"))},
              "side_clearance_mm": doc.Parameters.evalExpression("SideGap").Value,
              "connector_layout": spec["connector_layout"],
              "sources": spec["sources"], "physical_fit_tested": False,
              "physical_validation": "造形後の適合、荷重、樹脂の耐熱、冷却は未検証"}
    try:
        report["two_units"] = inspect(doc, 2)
        report["four_units"] = inspect(doc, 4)
        original = {name: doc.Parameters.getContents(CELLS[name])
                    for name in ("AdapterWidth", "AdapterLength", "AdapterHeight", "LiftHeight")}
        try:
            for name, value in (("AdapterWidth", "110 mm"), ("AdapterLength", "110 mm"),
                                ("AdapterHeight", "40 mm"), ("LiftHeight", "35 mm")):
                doc.Parameters.set(CELLS[name], value)
            doc.recompute()
            report["alternate_dimensions"] = inspect(doc, 2)
        finally:
            for name, value in original.items():
                doc.Parameters.set(CELLS[name], value)
            doc.recompute()
            show_units(doc, 2)
        restored = inspect(doc, 2)
        assert max(abs(a - b) for a, b in zip(restored["dimensions_mm"], report["two_units"]["dimensions_mm"])) < 1e-6
        render(doc, 4, OUT / "four_units.png")
        for i in range(4):
            doc.getObject(f"Adapter{i}").Visibility = False
        render(doc, 2, OUT / "stand_only.png")
        for i in range(4):
            doc.getObject(f"Adapter{i}").Visibility = True
        render(doc, 2, OUT / "two_units.png")
        doc.saveAs(str(TARGET))
        App.closeDocument(doc.Name)
        doc = App.openDocument(str(TARGET))
        report["reopened"] = inspect(doc, 2)
        assert max(abs(a - b) for a, b in zip(report["reopened"]["dimensions_mm"], restored["dimensions_mm"])) < 1e-6
        report["parameters"] = {name: {"cell": CELLS[name], "contents": doc.Parameters.getContents(CELLS[name]), "description": text}
                                for name, _, text in INPUTS + DERIVED}
        directory = OUT / "stl"
        directory.mkdir(exist_ok=True)
        report["stl"] = {}
        for name, filename in PRINT_PARTS.items():
            shape = doc.getObject(name).Shape.copy(True, False)
            if name == "Saddle":
                shape.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), 90)
            box = shape.BoundBox
            shape.translate(App.Vector(-box.XMin, -box.YMin, -box.ZMin))
            mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.02, AngularDeflection=0.15, Relative=False)
            path = directory / (filename + ".stl")
            mesh.write(str(path), "STL")
            report["stl"][filename] = {"triangles": mesh.CountFacets, "units": "mm", "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        report["bom"] = {"two_units": {"saddle": 4, "rail": 4, "locking_pin": 8, "join_clip": 2},
                         "four_units": {"saddle": 8, "rail": 8, "locking_pin": 16, "join_clip": 6}}
        report["fan_mount"] = {"fan_included": False, "bracket_included": False, "hole_diameter_mm": 4.5,
                               "hole_pitch_mm": 28, "nut_pocket_af_mm": 7.5, "nut_pocket_depth_mm": 3.5,
                               "location": "横一列の外端レール。内側の同じ穴は横連結クリップが使用する"}
        report["file_sha256"] = hashlib.sha256(TARGET.read_bytes()).hexdigest()
        report["status"] = "passed_for_published_dimensions"
    except Exception as error:
        report["status"] = "failed"
        report["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        (OUT / "validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "file": str(TARGET), "fit_confirmed": False,
                      "two_units_mm": report["two_units"]["dimensions_mm"], "four_units_mm": report["four_units"]["dimensions_mm"]}))


if __name__ == "__main__":
    main()
