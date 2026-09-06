"""Fusion由来のSTEPから、4台の組立と印刷部品を持つFreeCAD文書を生成する。"""

import hashlib
import json
from pathlib import Path
import re
import sys

import FreeCAD as App
import FreeCADGui as Gui
import ImportGui
import Part
# CADビューのSWIG型を登録する。
from pivy import coin


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "exports/freecad"
TARGET = ROOT / "DGX-SPARK-RACK-FREECAD-v1.FCStd"
sys.path.insert(0, str(ROOT / "scripts"))
from freecad_evaluate import compare, fingerprint

COLORS = {
    "frame": (130 / 255, 138 / 255, 148 / 255),
    "pin": (140 / 255, 174 / 255, 113 / 255),
    "dgx": (205 / 255, 164 / 255, 87 / 255),
    "fan": (80 / 255, 86 / 255, 95 / 255),
    "metal": (210 / 255, 215 / 255, 224 / 255),
}


def color(part):
    if part in {"locking_pin", "stack_locator", "bridge_clip"}:
        return COLORS["pin"]
    if part == "REF_DGX":
        return COLORS["dgx"]
    if part == "REF_FAN":
        return COLORS["fan"]
    if part in {"REF_GUARD", "REF_SCREW", "REF_NUT"}:
        return COLORS["metal"]
    return COLORS["frame"]


def style(obj, part):
    obj.addProperty("App::PropertyString", "SourcePart", "FusionSource")
    obj.SourcePart = part
    obj.ViewObject.ShapeColor = color(part)
    obj.ViewObject.DiffuseColor = [color(part)]
    obj.ViewObject.LineColor = (0.18, 0.2, 0.23)


def check(doc, assembly_name, baseline, part_manifest):
    doc.recompute()
    assembly = doc.getObject(assembly_name)
    shape = Part.getShape(assembly)
    result, _ = compare(baseline["bodies"], [fingerprint(s) for s in shape.Solids])
    assert result["passed"], result
    parts = {}
    for obj in doc.PrintParts.Group:
        source = obj.SourcePart
        assert source in part_manifest
        s = obj.Shape.copy(True, False)
        assert len(s.Solids) == 1 and s.isValid() and s.isClosed(), source
        assert not obj.Visibility, "初期表示に印刷部品が重なっています"
        reference = Part.Shape()
        reference.read(str(OUT / part_manifest[source]["step"]))
        match, _ = compare([fingerprint(reference.Solids[0])], [fingerprint(s)])
        assert match["passed"], (source, match)
        parts[source] = fingerprint(s)
    assert set(parts) == set(part_manifest) and len(parts) == 12
    return {"assembly": result, "print_parts": parts}


def write_report(doc):
    manifest = json.loads((OUT / "source_manifest.json").read_text())
    baseline = json.loads((ROOT / "comparison/freecad/fusion_baseline.json").read_text())
    source = ROOT / "DGX-SPARK-RACK-FUSION-v1.f3d"
    assert doc.FileName == str(TARGET)
    assembly = next(o for o in doc.RootObjects if getattr(o, "SourceArchive", None) == source.name)
    checked = check(doc, assembly.Name, baseline, manifest["print_parts"])
    preserved = hashlib.sha256(source.read_bytes()).hexdigest() == manifest["f3d_sha256"]
    assert preserved
    report = {"status": "passed", "file": TARGET.name, "freecad_version": App.Version(),
              "file_sha256": hashlib.sha256(TARGET.read_bytes()).hexdigest(),
              "source_f3d_sha256": manifest["f3d_sha256"], "source_step_sha256": baseline["step_sha256"],
              "fusion_source_preserved": preserved, "assembly_units": 4, "assembly_solids": 128,
              "print_part_types": 12, "reference_parameters": len(manifest["parameters"]),
              "fusion_feature_history_transferred": False, "reopened_successfully": True,
              "geometry_checks": checked}
    (OUT / "conversion.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"file": str(TARGET), "units": 4, "assembly_solids": 128, "print_part_types": 12, "status": "passed"}))


def main():
    if TARGET.exists():
        raise FileExistsError(TARGET)
    manifest = json.loads((OUT / "source_manifest.json").read_text())
    baseline = json.loads((ROOT / "comparison/freecad/fusion_baseline.json").read_text())
    source = ROOT / "DGX-SPARK-RACK-FUSION-v1.f3d"
    step = ROOT / manifest["assembly_step"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == manifest["f3d_sha256"] == baseline["f3d_sha256"]
    assert hashlib.sha256(step.read_bytes()).hexdigest() == baseline["step_sha256"]
    doc = App.newDocument("DGXSparkRackFreeCAD")
    doc.Label = "DGX Spark Rack - FreeCAD"
    ImportGui.insert(str(step), doc.Name)
    doc.recompute()
    assembly = next(o for o in doc.RootObjects if o.TypeId == "App::Part")
    assembly.Label = "ラック_4台組立"
    assembly.addProperty("App::PropertyString", "SourceArchive", "FusionSource")
    assembly.SourceArchive = source.name
    assembly.addProperty("App::PropertyString", "SourceSHA256", "FusionSource")
    assembly.SourceSHA256 = manifest["f3d_sha256"]
    assembly.addProperty("App::PropertyString", "HistoryTransfer", "FusionSource")
    assembly.HistoryTransfer = "STEP geometry and placement only; Fusion feature history is not transferred."
    names = list(manifest["print_parts"]) + ["REF_DGX", "REF_FAN", "REF_GUARD", "REF_SCREW", "REF_NUT"]
    for obj in doc.Objects:
        if obj.TypeId == "Part::Feature":
            part = next(n for n in names if re.fullmatch(re.escape(n) + r"\d*", obj.Label))
            style(obj, part)
    units = [o for o in assembly.Group if o.TypeId == "App::Part"]
    assert len(units) == 4
    for unit in units:
        box = Part.getShape(unit).BoundBox
        unit.Label = ("左" if box.Center.x < 0 else "右") + ("下" if box.ZMin < 100 else "上") + "_DGXユニット"
    library = doc.addObject("App::Part", "PrintParts")
    library.Label = "印刷部品_12種類_個別表示用"
    for part, record in manifest["print_parts"].items():
        path = OUT / record["step"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"]
        shape = Part.Shape()
        shape.read(str(path))
        assert len(shape.Solids) == 1 and shape.isValid(), part
        obj = doc.addObject("Part::Feature", "Print_" + part)
        obj.Label = part
        obj.Shape = shape.Solids[0]
        library.addObject(obj)
        style(obj, part)
    library.Visibility = True
    for obj in library.Group:
        obj.Visibility = False
    sheet = doc.addObject("Spreadsheet::Sheet", "FusionParametersReference")
    sheet.Label = "変換元の寸法_参考用_形状には非連動"
    sheet.set("A1", "Fusionのパラメーター")
    sheet.set("B1", "元の値・式（記録用）")
    sheet.set("C1", "この表を編集しても形状は更新されません")
    for row, (name, expression) in enumerate(manifest["parameters"].items(), 2):
        sheet.set(f"A{row}", name)
        sheet.set(f"B{row}", "'" + expression)
    sheet.setColumnWidth("A", 220)
    sheet.setColumnWidth("B", 400)
    sheet.setColumnWidth("C", 420)
    sheet.setStyle("A1:C1", "bold", "add")
    doc.recompute()
    Gui.updateGui()
    check(doc, assembly.Name, baseline, manifest["print_parts"])
    rotation = App.Rotation(App.Vector(0.74290609, 0.30772209, 0.59447283), 69.73561)
    view = Gui.activeDocument().activeView()
    view.getCameraNode().orientation.setValue(*rotation.Q)
    view.fitAll()
    Gui.updateGui()
    view.saveImage(str(OUT / "four_units.png"), 1500, 1200, "White")
    doc.saveAs(str(TARGET))
    App.closeDocument(doc.Name)
    doc = App.openDocument(str(TARGET))
    write_report(doc)


if __name__ == "__main__":
    main()
