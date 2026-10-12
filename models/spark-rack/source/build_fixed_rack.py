"""固定段と独立電源区画の形状候補を新規出力する。造形用データは出さない。

--switch-bay upper を付けると、上枠を共有する上部専用段の案を別の出力先へ作る。
"""
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
VARIANTS = {None: ('fixed-rack', '固定段・独立電源区画の形状候補'),
            'upper': ('upper-switch-bay', '上枠を共有する上部専用段の形状候補')}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def worker(folder, variant=None):
    import FreeCAD as App
    import FreeCADGui as Gui
    import Part
    from freecad_spark_rack import create_fixed_rack
    from fixed_rack_geometry import ROLE_COLORS
    from validate_fixed_rack import validate
    Gui.showMainWindow()
    if variant == 'upper':
        from upper_switch_bay import bay_layout, rack_parameters
        parameters = rack_parameters()
        doc, model = create_fixed_rack(parameters, 'crs812', bay_layout(parameters))
    else:
        doc, model = create_fixed_rack()
    validation = validate(model)
    objects = [o for o in doc.Objects if hasattr(o, 'Shape')]
    expected = {o.Name: o.Shape.Volume for o in objects}
    doc.saveAs(str(folder / 'fixed-rack-candidate.FCStd'))
    Part.export(objects, str(folder / 'fixed-rack-candidate.step'))
    meshes = []
    for item in model['parts'] + model['references']:
        vertices, faces = item['shape'].tessellate(.4)
        color = ROLE_COLORS.get(item['role'], (.22, .26, .29))
        meshes.append({'name': item['name'], 'label': item['label'], 'role': item['role'],
                       'vertices': [[round(v.x, 5), round(v.y, 5), round(v.z, 5)] for v in vertices],
                       'faces': faces, 'color': color, 'alpha': 1.0})
    write_json(folder / 'fixed-rack-scene.json', meshes)
    write_json(folder / 'layout.json', model['scene'])
    write_json(folder / 'support-system.json', model['supports'])
    write_json(folder / 'controller-face.json', {'metadata': model['controller_face']['metadata'],
               'validation': model['controller_face']['validation']})
    App.closeDocument(doc.Name)
    reopened = App.openDocument(str(folder / 'fixed-rack-candidate.FCStd'))
    for name, volume in expected.items():
        shape = reopened.getObject(name).Shape
        if not shape.isValid() or abs(shape.Volume - volume) > 1e-6:
            raise ValueError('再読込した形状が不一致です: ' + name)
    App.closeDocument(reopened.Name)
    validation['reopened'] = True
    write_json(folder / 'validation.json', validation)
    write_json(folder / 'freecad-version.json', App.Version())


def build(variant=None):
    folder, purpose = VARIANTS[variant]
    out = ROOT / 'build/spark-rack' / folder / (datetime.now(ZoneInfo('Asia/Tokyo')).strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8])
    out.mkdir(parents=True, exist_ok=False)
    files = [SOURCE / n for n in ('spark_rack_parameters.py', 'freecad_spark_rack.py', 'fixed_rack_layout.py',
             'fixed_rack_geometry.py', 'validate_fixed_rack.py', 'build_fixed_rack.py', 'network_configuration.py',
             'four_node_layout.py', 'rack_candidate_datums.py', 'fixed_rack_view.html')]
    files += [SOURCE / 'integrated_rack_supports.py', SOURCE / 'controller_front_face.py',
              ROOT / 'tests/test_integrated_rack_supports.py', ROOT / 'tests/test_controller_front_face.py']
    files += [ROOT / 'models/spark-rack/reference/selected-network-20261012/configuration.json',
              ROOT / 'models/spark-rack/reference/pending-mount-measurements.json',
              ROOT / 'models/adapter-rack/source/adapter_rack_parameters.py',
              ROOT / 'models/fan-controller/source/freecad_fan_controller.py',
              ROOT / 'tools/cad/controller_mount.py', ROOT / 'tools/cad/edge_finishing.py',
              ROOT / 'tools/cad/render_mesh_scene.py', ROOT / 'tests/check_fixed_rack_view.cjs',
              ROOT / 'tests/test_fixed_rack_layout.py', ROOT / 'tests/test_fixed_rack_geometry.py']
    if variant == 'upper':
        files += [SOURCE / n for n in ('upper_switch_bay.py', 'switch_bay_geometry.py',
                                       'switch_placement_comparison.py')]
        files += [ROOT / 'tests/test_upper_switch_bay.py', ROOT / 'tests/test_switch_bay_geometry.py']
    hashes = {str(f.relative_to(ROOT)): digest(f) for f in files}
    manifest = {'status': 'running', 'purpose': purpose,
                'sources_sha256': hashes, 'manufacturing_geometry': False, 'physical_validation': False}
    try:
        env = os.environ.copy()
        env['PYTHONPATH'] = os.environ.get('FREECAD_LIB', '/Applications/FreeCAD.app/Contents/Resources/lib')
        python = os.environ.get('FREECAD_PYTHON', '/Applications/FreeCAD.app/Contents/Resources/bin/python')
        if variant == 'upper':
            from upper_switch_bay import variants
            write_json(out / 'upper-bay-variants.json', variants())
        command = [python, str(Path(__file__)), '--worker', str(out)] + ([variant] if variant else [])
        run = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True)
        (out / 'freecad.log').write_text(run.stdout + run.stderr)
        if run.returncode or not (out / 'validation.json').exists():
            raise RuntimeError('固定段ラックの形状検査に失敗しました: ' + str(out / 'freecad.log'))
        payload = {'meshes': json.loads((out / 'fixed-rack-scene.json').read_text()),
                   'layout': json.loads((out / 'layout.json').read_text()),
                   'validation': json.loads((out / 'validation.json').read_text())}
        if variant == 'upper':
            payload['variants'] = json.loads((out / 'upper-bay-variants.json').read_text())
        template = (SOURCE / 'fixed_rack_view.html').read_text()
        if template.count('__FIXED_RACK_DATA__') != 1:
            raise ValueError('表示用データの挿入位置が不正です')
        (out / 'fixed-rack.html').write_text(template.replace('__FIXED_RACK_DATA__',
            json.dumps(payload, ensure_ascii=False).replace('<', '\\u003c')))
        if hashes != {str(f.relative_to(ROOT)): digest(f) for f in files}:
            raise ValueError('生成中に入力が変更されました')
        manifest.update(status='generated', outputs_sha256={f.name: digest(f) for f in sorted(out.iterdir()) if f.is_file()})
    except Exception as error:
        manifest.update(status='failed', error=str(error))
        raise
    finally:
        write_json(out / 'manifest.json', manifest)
    return out


if __name__ == '__main__':
    if sys.argv[1:2] == ['--worker']:
        try:
            worker(Path(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else None)
        except Exception:
            import traceback
            traceback.print_exc(); sys.stderr.flush(); os._exit(1)
        sys.stdout.flush(); os._exit(0)
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--switch-bay', choices=['upper'], help='上部専用段の案を生成する')
    print(build(parser.parse_args().switch_bay))
