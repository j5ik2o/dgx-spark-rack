"""設計コードからアダプタースタンドを生成し、検査と来歴を保存する。"""

from datetime import datetime
import hashlib
import json
from pathlib import Path
import uuid

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools/cad"))

import FreeCAD as App

from freecad_adapter_stand import create
from export_adapter_stand import main as export

ROOT = Path(__file__).resolve().parents[3]
SOURCES = (
    "archive/adapter-stand-v1/source/run_adapter_stand.FCMacro",
    "archive/adapter-stand-v1/source/build_adapter_stand.py",
    "archive/adapter-stand-v1/source/adapter_stand_parameters.py",
    "archive/adapter-stand-v1/source/freecad_adapter_stand.py",
    "tools/cad/freecad_features.py",
    "archive/adapter-stand-v1/source/export_adapter_stand.py",
    "tools/cad/check_stl.py",
    "archive/adapter-stand-v1/reference/adapter_spec.json",
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(output_dir=None, *, render_images=True):
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = Path(output_dir) if output_dir is not None else (
        ROOT / "archive/build-history/adapter-stand" / f"{stamp}-{uuid.uuid4().hex[:8]}"
    )
    out = out.resolve()
    if out.exists():
        raise FileExistsError(f"既存の出力は上書きしません: {out}")
    sources = {name: sha256(ROOT / name) for name in SOURCES}
    doc = create()
    created_name = doc.Name
    try:
        report = export(doc, out, render_images=render_images)
        if sources != {name: sha256(ROOT / name) for name in SOURCES}:
            raise RuntimeError("生成中に設計コードが変更されました。再実行してください")
        manifest = {
            "status": "passed",
            "design": "adapter-stand",
            "freecad_version": App.Version(),
            "sources_sha256": sources,
            "outputs_sha256": {
                str(path.relative_to(out)): sha256(path)
                for path in sorted(out.rglob("*")) if path.is_file()
            },
            "validation_status": report["status"],
            "physical_validation": "造形後の適合・耐荷重・冷却性能は別途確認する",
        }
        (out / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    except Exception:
        # エクスポートが再読込した場合も、この実行の文書だけを閉じる。
        for opened in list(App.listDocuments().values()):
            if opened.Name == created_name or (opened.FileName and Path(opened.FileName).parent == out):
                App.closeDocument(opened.Name)
        raise
    print(f"生成・検査完了: {out}")
    return out
