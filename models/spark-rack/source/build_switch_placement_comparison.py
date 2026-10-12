"""スイッチ専用段の外形比較、参考CAD、検査記録を新しい実行先へ保存する。"""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
from zoneinfo import ZoneInfo

from switch_placement_comparison import comparison

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(__file__).parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def cad_worker(out):
    import FreeCAD as App
    import FreeCADGui as Gui
    import Part
    report = json.loads((out / 'comparison.json').read_text())
    Gui.showMainWindow()
    doc = App.newDocument('SwitchPlacementComparison')
    expected = {}
    for case in report['cases']:
        if case['checks']['status'] != 'passed':
            continue
        group = doc.addObject('App::DocumentObjectGroup', case['key'])
        group.Label = case['label']
        objects = []
        for index, b in enumerate(case['objects']):
            obj = doc.addObject('Part::Feature', case['key'] + '_' + str(index))
            obj.Label = b['label'] + '・外形予約'
            origin = list(b['origin'])
            origin[2] -= case['frame']['origin'][2]
            obj.Shape = Part.makeBox(*b['size'], App.Vector(*origin))
            if not obj.Shape.isValid() or not obj.Shape.isClosed() or len(obj.Shape.Solids) != 1:
                raise ValueError('比較用の外形箱が無効です: ' + obj.Name)
            expected[obj.Name] = obj.Shape.Volume
            obj.addProperty('App::PropertyString', 'ReferenceScope')
            obj.ReferenceScope = '配置の外形箱。詳細部品、支持強度、通風開口、接合と実機冷却は未検証。'
            obj.ViewObject.ShapeColor = {'spark': (.75, .59, .30), 'switch': (.49, .43, .64),
                                         'bay_boundary': (.40, .59, .65), 'fan': (.78, .68, .56)}.get(b['kind'], (.48, .51, .54))
            group.addObject(obj)
            objects.append(obj)
        doc.recompute()
        Part.export(objects, str(out / (case['key'] + '-reference.step')))
        group.Visibility = case['key'] == report['recommendation']
    doc.recompute()
    saved = out / 'switch-placement-reference.FCStd'
    doc.saveAs(str(saved))
    App.closeDocument(doc.Name)
    reopened = App.openDocument(str(saved))
    for name, volume in expected.items():
        shape = reopened.getObject(name).Shape
        if not shape.isValid() or abs(shape.Volume - volume) > 1e-6:
            raise ValueError('再読込した比較用の外形が不一致です: ' + name)
    App.closeDocument(reopened.Name)
    write_json(out / 'cad-validation.json', {'status': 'passed', 'reference_shapes': len(expected),
               'reopened': True, 'scope': '比較用の閉じた外形箱と保存再読込。詳細部品・接合・印刷分割・実冷却の検査ではない。'})


def build():
    out = ROOT / 'build/spark-rack/switch-placement' / (datetime.now(ZoneInfo('Asia/Tokyo')).strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8])
    out.mkdir(parents=True, exist_ok=False)
    inputs = [SOURCE / name for name in ('spark_rack_parameters.py', 'fixed_rack_layout.py', 'four_node_layout.py',
                                        'network_configuration.py', 'rack_candidate_datums.py',
                                        'switch_placement_comparison.py', 'build_switch_placement_comparison.py',
                                        'switch_placement_comparison.html')]
    inputs += [ROOT / 'models/adapter-rack/source/adapter_rack_parameters.py',
               ROOT / 'models/spark-rack/reference/selected-network-20261012/configuration.json',
               ROOT / 'models/spark-rack/reference/pending-mount-measurements.json',
               ROOT / 'tests/test_switch_placement_comparison.py', ROOT / 'tests/check_switch_placement_comparison.cjs']
    hashes = {str(p.relative_to(ROOT)): digest(p) for p in inputs}
    manifest = {'status': 'running', 'purpose': '中央・上部・下部のスイッチ外形比較',
                'sources_sha256': hashes, 'manufacturing_geometry': False, 'physical_validation': False}
    try:
        report = comparison()
        expected = {'central': 'passed', 'upper': 'passed', 'lower_extension': 'passed', 'lower_gap': 'rejected'}
        actual = {c['key']: c['checks']['status'] for c in report['cases']}
        if expected != actual:
            raise ValueError('配置比較の期待する成立・不成立が変わりました: ' + str(actual))
        if any(max(report['print_split_screening'][name]) > report['parameters']['usable_print_size']
               for name in ('side_panel_envelope_mm', 'boundary_tile_envelope_mm', 'support_tile_envelope_mm')):
            raise ValueError('専用段の分割寸法枠が造形範囲を超えています')
        write_json(out / 'comparison.json', report)
        env = os.environ.copy()
        env['PYTHONPATH'] = os.environ.get('FREECAD_LIB', '/Applications/FreeCAD.app/Contents/Resources/lib')
        python = os.environ.get('FREECAD_PYTHON', '/Applications/FreeCAD.app/Contents/Resources/bin/python')
        run = subprocess.run([python, str(Path(__file__)), '--cad-worker', str(out)], env=env, cwd=ROOT, capture_output=True, text=True)
        (out / 'freecad.log').write_text(run.stdout + run.stderr, encoding='utf-8')
        if run.returncode or not (out / 'cad-validation.json').exists():
            raise RuntimeError('比較用の参考CAD生成に失敗しました: ' + str(out / 'freecad.log'))
        template = (SOURCE / 'switch_placement_comparison.html').read_text(encoding='utf-8')
        if template.count('__SWITCH_PLACEMENT_DATA__') != 1:
            raise ValueError('画面のデータ挿入位置が不正です')
        (out / 'switch-placement.html').write_text(template.replace('__SWITCH_PLACEMENT_DATA__',
            json.dumps(report, ensure_ascii=False).replace('<', '\\u003c')), encoding='utf-8')
        write_json(out / 'validation.json', {'status': 'passed', 'expected_case_statuses': actual,
                   'candidate_checks': {c['key']: c['checks'] for c in report['cases']},
                   'cad_reference_shapes': json.loads((out / 'cad-validation.json').read_text()),
                   'print_envelope_screening': 'passed', 'manufacturing_geometry': False, 'physical_validation': False})
        if hashes != {str(p.relative_to(ROOT)): digest(p) for p in inputs}:
            raise ValueError('生成中に入力が変更されました')
        manifest.update(status='generated', outputs_sha256={p.name: digest(p) for p in sorted(out.iterdir()) if p.is_file()})
    except Exception as error:
        manifest.update(status='failed', error=str(error))
        raise
    finally:
        write_json(out / 'manifest.json', manifest)
    return out


if __name__ == '__main__':
    if sys.argv[1:2] == ['--cad-worker']:
        try:
            cad_worker(Path(sys.argv[2]))
        except Exception:
            import traceback
            traceback.print_exc()
            sys.stderr.flush()
            os._exit(1)
        sys.stdout.flush()
        os._exit(0)
    print(build())
