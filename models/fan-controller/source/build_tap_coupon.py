"""M2後加工用の試験片。FreeCADのPythonで実行する。ねじ山は造形しない。"""
from datetime import datetime
from pathlib import Path
import hashlib
import json
import runpy
import sys
import uuid

import FreeCAD as App
import Part
import MeshPart

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/cad'))
from check_stl import inspect


def build():
    source = Path(__file__).resolve().with_name('freecad_fan_controller.py')
    model = runpy.run_path(str(source))
    out = ROOT / 'build/fan-controller' / ('tap-coupon-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8])
    out.mkdir(parents=True, exist_ok=False)
    doc = App.newDocument('TapCoupon')
    # 手前左角を切り欠いて識別。左穴=蓋、右穴=押さえ。
    shape = Part.makeBox(24, 10, 10).cut(Part.makeBox(2, 2, 10))
    holes = []
    for x, prefix in ((6, 'SCREW'), (18, 'CLAMP')):
        diameter = model[prefix + '_PILOT_DIAMETER']
        depth = model[prefix + '_PILOT_DEPTH']
        tool = Part.makeCylinder(diameter / 2, depth + 0.1, App.Vector(x, 5, 10 - depth))
        shape = shape.cut(tool)
        holes.append({'x_mm': x, 'diameter_mm': diameter, 'depth_mm': depth})
    assert shape.isValid() and len(shape.Solids) == 1
    obj = doc.addObject('Part::Feature', 'TapCoupon')
    obj.Shape = shape
    doc.recompute()
    doc.saveAs(str(out / 'TapCoupon.FCStd'))
    mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.03, AngularDeflection=0.15, Relative=False)
    stl = out / 'TapCoupon.stl'
    mesh.write(str(stl))
    report = {'status': 'passed', 'physical_fit_verified': False, 'holes': holes, 'stl': inspect(stl),
              'limitation': '下穴の加工性を確認する試験片。ケース壁の締結強度は再現しない。'}
    (out / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    manifest = {'status': 'passed', 'sources_sha256': {str(p.relative_to(ROOT)): digest(p) for p in
                [source, Path(__file__).resolve(), *sorted((ROOT / 'tools/cad').glob('*.py'))]},
                'outputs_sha256': {p.name: digest(p) for p in out.iterdir() if p.is_file()}}
    (out / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(out, flush=True)
    return out


if __name__ == '__main__':
    build()
