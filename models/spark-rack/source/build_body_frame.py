"""本体連結案の参考形状と検査結果を新しい実行フォルダへ出力する。印刷用データは出さない。"""
from datetime import datetime
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


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def publish_latest(folder):
    """生成が完了した実行への案内だけを更新し、過去の生成物は変更しない。"""
    manifest = json.loads((folder/'manifest.json').read_text())
    html = folder/'body-frame.html'
    if manifest.get('status') != 'generated' or not html.is_file() or '__BODY_FRAME_DATA__' in html.read_text():
        raise ValueError('生成が完了していない表示ページは公開できません')
    latest = folder.parent/'latest'
    if latest.exists() and not latest.is_symlink():
        raise ValueError('最新モデルの案内先に既存のファイルまたはフォルダがあります: '+str(latest))
    pending = folder.parent/('.latest-'+uuid.uuid4().hex)
    try:
        pending.symlink_to(folder.name,target_is_directory=True)
        os.replace(pending,latest)
    finally:
        pending.unlink(missing_ok=True)


def worker(folder):
    import FreeCAD as App
    import FreeCADGui as Gui
    import Part
    from freecad_spark_rack import create_body_frame
    from body_frame_geometry import COLORS
    from validate_body_frame import validate
    Gui.showMainWindow()
    doc, model = create_body_frame()
    report = validate(model)
    from body_frame_supports import build_support_plan
    support_plan,support_meshes = build_support_plan(model)
    report['support_removal'] = {k:support_plan[k] for k in (
        'status','printed_parts','parts_with_regions','region_count','removal_steps','protected_face_count',
        'physical_validation','slicer_validated','manufacturing_geometry')}
    expected = {o.Name: o.Shape.Volume for o in doc.Objects if hasattr(o, 'Shape')}
    by_name = {o.Name: o for o in doc.Objects}
    for fan in (e for e in model['scene']['equipment'] if e['kind'] == 'fan'):
        obj = by_name['Reference_' + fan['name'].replace('-', 'N')]
        obj.addProperty('App::PropertyVector', 'MountAxis', 'Design')
        obj.MountAxis = App.Vector(*fan['axis'])
        obj.addProperty('App::PropertyBool', 'FixedMount', 'Design')
        obj.FixedMount = True
    doc.saveAs(str(folder / 'body-frame-reference.FCStd'))
    Part.export([o for o in doc.Objects if hasattr(o, 'Shape')], str(folder / 'body-frame-reference.step'))
    meshes = []
    for entry in model['parts'] + model['references'] + model['cables'] + model['cable_storage'] + model['external_reservations'] + model['assembly_details']:
        points, faces = entry['shape'].tessellate(1 if entry['kind'].startswith('cable_') else .35)
        bounds = entry['shape'].BoundBox
        meshes.append(dict(name=entry['name'], label=entry['label'], kind=entry['kind'],
                           candidate=entry in model['parts'],
                           members=entry.get('integrated_members', [entry['name']]),
                           unlockBefore=entry.get('unlock_before'),
                           bounds=[[bounds.XMin,bounds.YMin,bounds.ZMin],[bounds.XMax,bounds.YMax,bounds.ZMax]],
                           vertices=[[round(v.x, 5), round(v.y, 5), round(v.z, 5)] for v in points],
                           faces=faces, color=entry.get('color', COLORS.get(entry['kind'], (.4, .4, .4)))))
    write(folder / 'body-frame-scene.json', meshes)
    write(folder / 'layout.json', model['scene'])
    write(folder / 'cable-routing.json', model['scene']['cable_management'])
    write(folder / 'switch-retention.json', dict(design=model['scene']['switch_retention'], validation=report['switch_retention']))
    write(folder / 'screwless-assembly.json', dict(design=model['scene']['screwless_assembly'],
                                                 validation=report['screwless_assembly']))
    write(folder / 'assembly-plan.json', dict(model['assembly_plan'],validation=report['assembly_order']))
    write(folder / 'finger-access.json', report['assembly_order']['finger_access'])
    write(folder / 'print-plan.json', model['print_plan'])
    write(folder / 'support-plan.json', support_plan)
    write(folder / 'support-scene.json', support_meshes)
    App.closeDocument(doc.Name)
    reopened = App.openDocument(str(folder / 'body-frame-reference.FCStd'))
    for name, volume in expected.items():
        shape = reopened.getObject(name).Shape
        if not shape.isValid() or abs(shape.Volume - volume) > 1e-5:
            raise ValueError('保存後の再読込で形状が一致しません: ' + name)
    for fan in (e for e in model['scene']['equipment'] if e['kind'] == 'fan'):
        obj = reopened.getObject('Reference_' + fan['name'].replace('-', 'N'))
        if not obj.FixedMount or list(obj.MountAxis) != fan['axis']:
            raise ValueError('保存後のファン取付軸が一致しません: ' + fan['name'])
    App.closeDocument(reopened.Name)
    report['reopened'] = True
    write(folder / 'validation.json', report)
    write(folder / 'freecad-version.json', App.Version())


def build():
    from body_frame_layout import REFERENCES, REQUIREMENTS
    folder = ROOT / 'build/spark-rack/body-frame' / (
        datetime.now(ZoneInfo('Asia/Tokyo')).strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8])
    sources = [SOURCE / n for n in (
        'freecad_spark_rack.py', 'spark_rack_parameters.py', 'body_frame_layout.py',
        'body_frame_geometry.py', 'validate_body_frame.py', 'build_body_frame.py', 'body_frame_view.html')]
    sources += [SOURCE / n for n in ('body_frame_cables.py', 'body_frame_cable_geometry.py', 'validate_body_frame_cables.py',
                                    'body_frame_switch_retention.py', 'body_frame_screwless.py', 'body_frame_joinery.py',
                                    'body_frame_assembly.py','validate_body_frame_assembly.py','body_frame_controller_assembly.py',
                                    'body_frame_access.py','body_frame_print_plan.py','body_frame_support_regions.py',
                                    'body_frame_support_removal.py','body_frame_supports.py')]
    sources += [ROOT / name for name in REFERENCES + (REQUIREMENTS,)]
    sources += [ROOT / name for name in (
        'models/spark-rack/reference/tesmart-hks401-p23-dimensions-20261014.png',
        'models/fan-controller/source/freecad_fan_controller.py',
        'tools/cad/controller_mount.py', 'tools/cad/edge_finishing.py',
        'tests/test_body_frame_layout.py', 'tests/test_body_frame_geometry.py',
        'tests/test_body_frame_cables.py',
        'tests/test_body_frame_joinery.py',
        'tests/test_body_frame_assembly.py',
        'tests/test_body_frame_access.py',
        'tests/test_body_frame_print_plan.py',
        'tests/test_body_frame_supports.py',
        'print-projects/README.md',
        'models/spark-rack/reference/body-frame-print-assumptions-20261019.json',
        'models/spark-rack/reference/body-frame-support-assumptions-20261019.json',
        'tests/check_body_frame_view.cjs')]
    sources += [ROOT/'tests/check_body_frame_entry.cjs',ROOT/'tests/test_body_frame_latest.py']
    inputs = {str(p.relative_to(ROOT)): digest(p) for p in sources}
    folder.mkdir(parents=True, exist_ok=False)
    manifest = dict(status='running', purpose='Spark本体を骨格に使う2段×2列の参考配置',
                    sources_sha256=inputs, manufacturing_geometry=False, physical_validation=False)
    try:
        env = os.environ.copy()
        env['PYTHONPATH'] = os.environ.get('FREECAD_LIB', '/Applications/FreeCAD.app/Contents/Resources/lib')
        python = os.environ.get('FREECAD_PYTHON', '/Applications/FreeCAD.app/Contents/Resources/bin/python')
        result = subprocess.run([python, str(Path(__file__).resolve()), '--worker', str(folder)],
                                cwd=ROOT, env=env, capture_output=True, text=True)
        (folder / 'freecad.log').write_text(result.stdout + result.stderr, encoding='utf-8')
        if result.returncode or not (folder / 'validation.json').exists():
            raise RuntimeError('本体連結案の形状検査に失敗しました: ' + str(folder / 'freecad.log'))
        payload = dict(meshes=json.loads((folder / 'body-frame-scene.json').read_text()),
                       scene=json.loads((folder / 'layout.json').read_text()),
                       assembly=json.loads((folder / 'assembly-plan.json').read_text()),
                       printPlan=json.loads((folder / 'print-plan.json').read_text()),
                       supportPlan=json.loads((folder / 'support-plan.json').read_text()),
                       supportMeshes=json.loads((folder / 'support-scene.json').read_text()),
                       validation=json.loads((folder / 'validation.json').read_text()))
        template = (SOURCE / 'body_frame_view.html').read_text()
        if template.count('__BODY_FRAME_DATA__') != 1:
            raise ValueError('表示用データの挿入位置が不正です')
        (folder / 'body-frame.html').write_text(template.replace('__BODY_FRAME_DATA__',
            json.dumps(payload, ensure_ascii=False).replace('<', '\\u003c')), encoding='utf-8')
        if inputs != {str(p.relative_to(ROOT)): digest(p) for p in sources}:
            raise ValueError('生成中に設計入力が変更されました')
        manifest.update(status='generated', outputs_sha256={
            p.name: digest(p) for p in sorted(folder.iterdir()) if p.is_file()})
    except Exception as error:
        manifest.update(status='failed', error=str(error))
        raise
    finally:
        write(folder / 'manifest.json', manifest)
    publish_latest(folder)
    return folder


if __name__ == '__main__':
    if sys.argv[1:2] == ['--worker']:
        code = 0
        try:
            worker(Path(sys.argv[2]))
        except Exception:
            import traceback
            traceback.print_exc()
            code = 1
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(code)
    print(build())
