"""新案は接合試験片だけを造形用に出力する。未測定の全体部品は出力しない。"""
from datetime import datetime
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(__file__).parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def worker(folder):
    import FreeCAD as App
    import FreeCADGui as Gui
    import MeshPart
    import Part
    sys.path.insert(0, str(ROOT / 'tools/cad'))
    from check_stl import inspect
    from freecad_spark_rack_joint_coupons import CouponParameters, parts, corner_assembly, airflow_preview, box
    from validate_spark_rack_joint_coupons import verify
    Gui.showMainWindow()
    p = CouponParameters()
    shapes = parts(p)
    corner = corner_assembly(shapes)
    validation = verify(shapes, corner)
    (folder / 'stl').mkdir()
    meshes = {}
    for name, shape in shapes.items():
        positioned = shape.copy()
        if name in ('beam_lower_tenon', 'beam_upper_tenon', 'beam_drop_blade'):
            positioned.rotate(App.Vector(), App.Vector(0, 1, 0), 90)
        b = positioned.optimalBoundingBox(False)
        positioned.translate(App.Vector(-b.XMin, -b.YMin, -b.ZMin))
        mesh = MeshPart.meshFromShape(Shape=positioned, LinearDeflection=0.03, AngularDeflection=0.15, Relative=False)
        target = folder / 'stl' / (name + '.stl'); mesh.write(str(target), 'STL')
        meshes[name] = inspect(target)
    write_json(folder / 'stl-validation.json', meshes)
    doc = App.newDocument('InterlockCoupons')
    doc.Label = '28mm角・凹凸接合試験片'
    for name, shape in corner:
        obj = doc.addObject('Part::Feature', name); obj.Label = name; obj.Shape = shape
        obj.ViewObject.ShapeColor = (0.26, 0.43, 0.52)
    straight = []
    for name in ('beam_fork', 'beam_drop_blade'):
        shape = shapes[name].copy(); shape.translate(App.Vector(100, 0, 0))
        obj = doc.addObject('Part::Feature', name); obj.Label = '直線の接合試験片・' + name; obj.Shape = shape
        obj.ViewObject.ShapeColor = (0.28, 0.50, 0.62)
        straight.append(shape)
    doc.recompute(); cad = folder / 'joint-coupons.FCStd'; doc.saveAs(str(cad))
    Part.makeCompound([shape for _, shape in corner]).exportStep(str(folder / 'corner-coupons.step'))
    Part.makeCompound(straight).exportStep(str(folder / 'straight-coupons.step'))
    expected = {obj.Name: obj.Shape.Volume for obj in doc.Objects}
    App.closeDocument(doc.Name); doc = App.openDocument(str(cad))
    for name, volume in expected.items():
        if abs(doc.getObject(name).Shape.Volume - volume) > 1e-6:
            raise ValueError('試験片の再読込が不一致です')
    App.closeDocument(doc.Name)
    validation['reopened'] = True
    colors = [(0.30, 0.36, 0.40), (0.70, 0.52, 0.29), (0.28, 0.50, 0.62)]

    def scene(name, items):
        payload = []
        for i, (_, shape) in enumerate(items):
            vertices, faces = shape.tessellate(0.2)
            payload.append({'vertices': [[round(v.x, 4), round(v.y, 4), round(v.z, 4)] for v in vertices],
                            'faces': faces, 'color': colors[i % 3], 'alpha': 1.0})
        write_json(folder / (name + '-scene.json'), payload)

    scene('corner-assembled', corner)
    exploded = [(name, shape.copy()) for name, shape in corner]
    exploded[1][1].translate(App.Vector(0, 0, 35)); exploded[2][1].translate(App.Vector(0, 0, 70))
    scene('corner-insertion-order', exploded)
    scene('straight-assembled', [('fork', shapes['beam_fork']), ('blade', shapes['beam_drop_blade'])])
    duct = airflow_preview()
    if not duct.isValid() or not duct.isClosed():
        raise ValueError('導風検討形状が無効です')
    preview = App.newDocument('AirGuidePreview')
    for name, shape in [('AirGuide', duct), ('FanEnvelope', box(-70, -202, -70, 140, 27, 140)),
                        ('SparkEnvelope', box(-75, -150, -25.25, 150, 150, 50.5))]:
        obj = preview.addObject('Part::Feature', name); obj.Shape = shape; obj.Label = '未測定の導風形状・参考外形'
    preview.recompute(); preview.saveAs(str(folder / 'air-guide-preview.FCStd'))
    App.closeDocument(preview.Name)
    scene('air-guide-preview', [('duct', duct)])
    validation['airflow_preview'] = '形状検討のみ。保持部との一体化、通気口、風向、冷却効果は未検証。造形データには出力していない。'
    write_json(folder / 'validation.json', validation)
    write_json(folder / 'coupon-report.json', {'status': 'coupon_only', 'parameters': asdict(p),
               'print_part_names': list(shapes), 'target_frame_part_count': 72,
               'print_orientation': '差し込み側の梁3種類は、太い端面を造形面へ向けた試験用の向き。全長部材の造形方向は未確定。',
               'target_frame_part_count_status': '数量目標。全体形状・強度・全体組立順は未検証。',
               'mount_holes_generated': False, 'switch_support_generated': False,
               'scope': '短い接合試験片のみ。136個案は不採用、72個全体の造形データは未生成。'})
    write_json(folder / 'freecad-version.json', App.Version())


def build():
    folder = ROOT / 'build/spark-rack/joint-coupons' / (datetime.now(ZoneInfo('Asia/Tokyo')).strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8])
    folder.mkdir(parents=True, exist_ok=False)
    sources = [SOURCE / name for name in ('freecad_spark_rack_joint_coupons.py', 'validate_spark_rack_joint_coupons.py',
                                         'build_spark_rack_joint_coupons.py', 'rack_candidate_datums.py',
                                         'joint_coupons.html', 'run_spark_rack_joint_coupons.FCMacro')]
    sources += [ROOT / 'tools/cad/check_stl.py', ROOT / 'tools/cad/render_mesh_scene.py',
                ROOT / 'models/spark-rack/reference/pending-mount-measurements.json']
    hashes = {str(path.relative_to(ROOT)): digest(path) for path in sources}
    manifest = {'status': 'running', 'purpose': '凹凸の接合試験片のみ。全体の印刷は保留。', 'sources_sha256': hashes}
    try:
        env = os.environ.copy(); env['PYTHONPATH'] = os.environ.get('FREECAD_LIB', '/Applications/FreeCAD.app/Contents/Resources/lib')
        python = os.environ.get('FREECAD_PYTHON', '/Applications/FreeCAD.app/Contents/Resources/bin/python')
        result = subprocess.run([python, str(Path(__file__)), '--worker', str(folder)], cwd=ROOT, env=env, capture_output=True, text=True)
        (folder / 'freecad.log').write_text(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError('接合試験片の検査に失敗しました: ' + str(folder / 'freecad.log'))
        rendered = subprocess.run(['uv', 'run', '--script', str(ROOT / 'tools/cad/render_mesh_scene.py'), str(folder)], cwd=ROOT, capture_output=True, text=True)
        (folder / 'render.log').write_text(rendered.stdout + rendered.stderr)
        if rendered.returncode or len(list(folder.glob('*.png'))) != 4:
            raise RuntimeError('試験片図の生成に失敗しました')
        (folder / 'joint-coupons.html').write_text((SOURCE / 'joint_coupons.html').read_text(), encoding='utf-8')
        if hashes != {str(path.relative_to(ROOT)): digest(path) for path in sources}:
            raise ValueError('生成中に入力コードが変更されました')
        manifest.update(status='generated', outputs_sha256={str(path.relative_to(folder)): digest(path)
                        for path in sorted(folder.rglob('*')) if path.is_file()})
    except Exception as error:
        manifest.update(status='failed', error=str(error)); raise
    finally:
        write_json(folder / 'manifest.json', manifest)
    return folder


if __name__ == '__main__':
    if sys.argv[1:2] == ['--worker']:
        try:
            worker(Path(sys.argv[2]))
        except Exception:
            import traceback
            traceback.print_exc(); sys.stderr.flush(); os._exit(1)
        sys.stdout.flush(); os._exit(0)
    print(build())
