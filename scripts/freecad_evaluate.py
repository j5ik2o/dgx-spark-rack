"""既存STEPをFreeCADへ移し、Fusion基準値と照合する比較試験。正本は変更しない。"""

from collections import Counter
import hashlib
import json
from pathlib import Path
import time

import FreeCAD as App
import Import
import Part


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "comparison/freecad"


def fingerprint(shape):
    # 描画後のBoundBoxは表示用三角形を参照する。比較にはメッシュを除いた形状を使う。
    shape = shape.copy(True, False)
    box = shape.BoundBox
    return {
        "minimum_mm": [box.XMin, box.YMin, box.ZMin],
        "maximum_mm": [box.XMax, box.YMax, box.ZMax],
        "center_of_mass_mm": list(shape.CenterOfMass),
        "volume_mm3": shape.Volume, "area_mm2": shape.Area,
        "faces": len(shape.Faces), "valid": shape.isValid(), "closed": shape.isClosed(),
    }


def document_shape(doc):
    shapes = [Part.getShape(o) for o in doc.RootObjects]
    # RootObjectsから集約し、親の形状と子の形状を二重に数えない。
    return Part.makeCompound([s for s in shapes if not s.isNull()])


def compare(reference, actual):
    assert len(reference) == len(actual), "ソリッド数が異なります"
    remaining = list(actual)
    matches = []
    for expected in reference:
        def distance(candidate):
            return max(abs(a - b) for key in ("minimum_mm", "maximum_mm")
                       for a, b in zip(expected[key], candidate[key]))
        selected = min(remaining, key=distance)
        remaining.remove(selected)
        matches.append({
            "source_path": expected.get("path", "FCStd再読込"),
            "bbox_max_error_mm": distance(selected),
            "center_max_error_mm": max(abs(a - b) for a, b in
                zip(expected["center_of_mass_mm"], selected["center_of_mass_mm"])),
            "volume_relative_error": abs(selected["volume_mm3"] / expected["volume_mm3"] - 1),
            "area_relative_error": abs(selected["area_mm2"] / expected["area_mm2"] - 1),
            "faces_equal": expected["faces"] == selected["faces"],
            "valid_closed": selected["valid"] and selected["closed"],
        })
    result = {"matched_solids": len(matches), "all_valid_closed": all(m["valid_closed"] for m in matches),
              "all_face_counts_equal": all(m["faces_equal"] for m in matches)}
    for key in ("bbox_max_error_mm", "center_max_error_mm", "volume_relative_error", "area_relative_error"):
        result[key] = max(m[key] for m in matches)
    result["passed"] = (result["all_valid_closed"] and result["bbox_max_error_mm"] < 0.001
                        and result["center_max_error_mm"] < 0.001
                        and result["volume_relative_error"] < 0.00002
                        and result["area_relative_error"] < 0.00002)
    return result, matches


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    baseline = json.loads((OUT / "fusion_baseline.json").read_text())
    source = ROOT / "DGX-SPARK-RACK-FUSION-v1.f3d"
    step = ROOT / "exports/fusion/DGX-SPARK-RACK-FUSION-v1.step"
    assert hashlib.sha256(source.read_bytes()).hexdigest() == baseline["f3d_sha256"]
    assert hashlib.sha256(step.read_bytes()).hexdigest() == baseline["step_sha256"]
    output = OUT / "DGX-SPARK-RACK-STEP-evaluation.FCStd"
    # 比較ファイルの上書きも明示的な判断にする。
    if output.exists():
        raise FileExistsError(output)
    doc = App.newDocument("DgxStepEvaluation")
    doc.Label = "DGX Spark rack - STEP evaluation"
    started = time.perf_counter()
    Import.insert(str(step), doc.Name)
    doc.recompute()
    import_seconds = time.perf_counter() - started
    for obj in doc.Objects:
        obj.Visibility = obj.TypeId in {"Part::Feature", "App::Part"}
    shape = document_shape(doc)
    actual = [fingerprint(s) for s in shape.Solids]
    comparison, details = compare(baseline["bodies"], actual)
    types = dict(Counter(o.TypeId for o in doc.Objects))
    box = shape.BoundBox
    started = time.perf_counter()
    doc.saveAs(str(output))
    save_seconds = time.perf_counter() - started
    App.closeDocument(doc.Name)
    started = time.perf_counter()
    reopened = App.openDocument(str(output))
    reopened.recompute()
    reopen_seconds = time.perf_counter() - started
    roundtrip, _ = compare(actual, [fingerprint(s) for s in document_shape(reopened).Solids])
    report = {
        "status": "passed" if comparison["passed"] and roundtrip["passed"] else "failed",
        "freecad_version": App.Version(), "open_cascade_version": Part.OCC_VERSION,
        "source_f3d_sha256": baseline["f3d_sha256"], "source_step_sha256": baseline["step_sha256"],
        "fcstd_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "conversion": "Import.insert (CLI)", "evaluation_only": True,
        "objects": len(reopened.Objects), "object_types": types,
        "dimensions_mm": [box.XLength, box.YLength, box.ZLength],
        "total_solid_volume_mm3": sum(s["volume_mm3"] for s in actual),
        "tolerances": {"coordinate_mm": 0.001, "volume_and_area_relative": 0.00002},
        "fusion_comparison": comparison, "fcstd_roundtrip": roundtrip,
        "timing_seconds": {"step_import_and_recompute": import_seconds,
                           "fcstd_save": save_seconds, "fcstd_open_and_recompute": reopen_seconds},
        "timing_scope": "単一試行、起動・描画・MCP通信は含まない。OSキャッシュは未制御。",
        "history": {"fusion_user_parameters": len(baseline["signature"]["parameters"]),
                    "fusion_timeline_items": baseline["signature"]["timeline"],
                    "freecad_sketches": types.get("Sketcher::SketchObject", 0),
                    "freecad_spreadsheets": types.get("Spreadsheet::Sheet", 0),
                    "freecad_partdesign_features": sum(n for t, n in types.items() if t.startswith("PartDesign::")),
                    "fusion_parameter_history_retained": False},
        "matched_body_details": details,
    }
    report["fusion_master_unchanged"] = hashlib.sha256(source.read_bytes()).hexdigest() == baseline["f3d_sha256"]
    (OUT / "validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    assert report["status"] == "passed", comparison
    assert report["fusion_master_unchanged"]
    print(json.dumps({k: v for k, v in report.items() if k != "matched_body_details"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
