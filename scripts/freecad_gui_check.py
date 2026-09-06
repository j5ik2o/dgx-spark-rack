"""FreeCADのGUI内でSTEPの読込時間とFCStd表示を確認する。MCPから実行する。"""

import json
import hashlib
import importlib
from pathlib import Path
import sys
import time

import FreeCAD as App
import FreeCADGui as Gui
import ImportGui
import Part


def main():
    root = Path(__file__).resolve().parents[1]
    out = root / "comparison/freecad"
    sys.path.insert(0, str(root / "scripts"))
    import freecad_evaluate
    importlib.reload(freecad_evaluate)
    from freecad_evaluate import document_shape, fingerprint, compare
    runs = []
    for _ in range(3):
        doc = App.newDocument("DgxImportBenchmark")
        try:
            started = time.perf_counter()
            ImportGui.insert(str(root / "exports/fusion/DGX-SPARK-RACK-FUSION-v1.step"), doc.Name)
            doc.recompute()
            seconds = time.perf_counter() - started
            Gui.updateGui()
            shape = document_shape(doc)
            runs.append({"seconds": seconds, "solids": len(shape.Solids), "valid": shape.isValid()})
        finally:
            App.closeDocument(doc.Name)
    source = out / "DGX-SPARK-RACK-STEP-evaluation.FCStd"
    doc = next((d for d in App.listDocuments().values() if d.FileName == str(source)), None)
    if doc is None:
        doc = App.openDocument(str(source))
    App.setActiveDocument(doc.Name)
    # CLIで保存した文書にはGUIの表示状態がないため、組立とソリッドを表示する。
    for obj in doc.Objects:
        obj.Visibility = obj.TypeId in {"Part::Feature", "App::Part"}
    view = Gui.activeDocument().activeView()
    view.viewIsometric()
    view.fitAll()
    Gui.updateGui()
    view.saveImage(str(out / "freecad_preview.png"), 1600, 1200, "White")
    shape = document_shape(doc)
    baseline = json.loads((out / "fusion_baseline.json").read_text())
    comparison, _ = compare(baseline["bodies"], [fingerprint(s) for s in shape.Solids])
    doc.save()
    validation = json.loads((out / "validation.json").read_text())
    validation["fcstd_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    validation["gui_visibility_saved"] = True
    (out / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {"status": "passed", "freecad_version": App.Version(),
              "operation": "ImportGui.insert + recompute", "runs": runs,
              "fcstd_gui_open": True, "solids": len(shape.Solids), "shape_valid": shape.isValid(),
              "preview": "freecad_preview.png", "gui_visibility_saved": True,
              "fusion_comparison_after_gui_save": comparison,
              "scope": "起動・MCP通信・明示的描画更新は計測外。キャッシュ未制御。"}
    report["status"] = "passed" if (all(r["solids"] == 128 and r["valid"] for r in runs)
                                       and report["solids"] == 128 and report["shape_valid"]
                                       and comparison["passed"]) else "failed"
    (out / "freecad_gui_check.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    assert all(r["solids"] == 128 and r["valid"] for r in runs), runs
    assert report["solids"] == 128 and report["shape_valid"] and comparison["passed"], comparison
    print(json.dumps(report))


if __name__ == "__main__":
    main()
