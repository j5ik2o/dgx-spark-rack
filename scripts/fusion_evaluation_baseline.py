"""FreeCAD比較用にFusion正本の形状を読み取る。正本へ書き込まない。"""

import hashlib
import json
from pathlib import Path
import sys

import adsk.fusion as fusion


def run(_context: str):
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "scripts"))
    import fusion_rack as rack
    rack.active()
    records = []
    for path, body in rack.assembly_bodies():
        box = body.preciseBoundingBox
        physical = body.getPhysicalProperties(fusion.CalculationAccuracy.VeryHighCalculationAccuracy)
        records.append({
            "path": path, "body": body.name, "solid": body.isSolid,
            "faces": body.faces.count,
            "minimum_mm": [getattr(box.minPoint, c) * 10 for c in "xyz"],
            "maximum_mm": [getattr(box.maxPoint, c) * 10 for c in "xyz"],
            "center_of_mass_mm": [v * 10 for v in physical.centerOfMass.asArray()],
            "volume_mm3": physical.volume * 1000,
            "area_mm2": physical.area * 100,
        })
    source = root / "DGX-SPARK-RACK-FUSION-v1.f3d"
    step = root / "exports/fusion/DGX-SPARK-RACK-FUSION-v1.step"
    report = {
        "fusion_version": rack.APP.version,
        "f3d_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "step_sha256": hashlib.sha256(step.read_bytes()).hexdigest(),
        "measurement_accuracy": "VeryHighCalculationAccuracy",
        "signature": rack.geometry_signature(), "bodies": records,
    }
    folder = root / "comparison/freecad"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "fusion_baseline.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"bodies": len(records), "parameters": len(report["signature"]["parameters"]),
                      "timeline": report["signature"]["timeline"]}))
