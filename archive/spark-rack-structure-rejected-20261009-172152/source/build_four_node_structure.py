"""4台用ラックの部品検討案を新しいフォルダへ生成する。"""
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
sys.path.append(str(ROOT / 'models/spark-rack/source'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def generate(folder):
    import FreeCAD as App
    import FreeCADGui as Gui
    import MeshPart
    import Part
    sys.path.insert(0, str(ROOT / 'tools/cad'))
    from check_stl import inspect
    from four_node_structure_parameters import StructureParameters
    from freecad_four_node_structure import shapes, assembly, box, bore
    from validate_four_node_structure import validate_parts, validate_assembly
    from PySide6 import QtWidgets
    Gui.showMainWindow()
    Gui.activateWorkbench('PartWorkbench')
    QtWidgets.QApplication.processEvents()

    def render(path):
        scene = []
        for obj in App.ActiveDocument.Objects:
            if hasattr(obj, 'Shape') and obj.Visibility:
                vertices, faces = obj.Shape.tessellate(0.25)
                scene.append({'vertices': [[round(v.x, 4), round(v.y, 4), round(v.z, 4)] for v in vertices],
                              'faces': faces, 'color': list(obj.ViewObject.ShapeColor[:3]),
                              'alpha': 0.22 if obj.Name.startswith('Reference') else 1.0})
        write_json(path.with_name(path.stem + '-scene.json'), scene)
    p = StructureParameters()
    parts = shapes(p)
    part_report = validate_parts(parts, p)
    (folder / 'stl').mkdir()
    (folder / 'parts').mkdir()
    mesh_report = {}
    for name, shape in parts.items():
        oriented = shape.copy()
        if name.startswith('corner') or name == 'fan_carrier':
            oriented.rotate(App.Vector(), App.Vector(1, 0, 0), 90)
        if name.startswith('cross_'):
            oriented.rotate(App.Vector(), App.Vector(0, 0, 1), 45)
        b = oriented.optimalBoundingBox(False)
        oriented.translate(App.Vector(-b.XMin, -b.YMin, -b.ZMin))
        oriented.exportStep(str(folder / 'parts' / (name + '.step')))
        mesh = MeshPart.meshFromShape(Shape=oriented, LinearDeflection=0.03, AngularDeflection=0.15, Relative=False)
        target = folder / 'stl' / (name + '.stl')
        mesh.write(str(target), 'STL')
        mesh_report[name] = inspect(target, max_dimension=p.usable_print_size)
    write_json(folder / 'stl-validation.json', mesh_report)
    reports = {}
    checks = {}
    groups = {'frame': (0.17, 0.19, 0.22), 'joint': (0.32, 0.40, 0.46),
              'support': (0.30, 0.51, 0.64), 'fan': (0.25, 0.28, 0.31), 'controller': (0.25, 0.33, 0.38)}
    for mode in ('ring', 'crs812', 'crs804'):
        print(mode + ': 部品・機器・締結経路の干渉を検査', flush=True)
        report, items = assembly(p, parts, mode)
        reports[mode] = report
        checks[mode] = validate_assembly(report, items, p)
        write_json(folder / 'assembly-validation.json', checks)
        if checks[mode]['status'] != 'passed':
            raise ValueError(mode + ': 干渉または締結穴の不一致。assembly-validation.jsonを参照。')
        doc = App.newDocument('FourNodeStructure')
        doc.Label = '4台ラック部品案・' + mode
        for item, shape in items:
            obj = doc.addObject('Part::Feature', item['id'])
            obj.Label = item['label'] + ' / ' + item['part']
            obj.Shape = shape
            obj.ViewObject.ShapeColor = groups[item['group']]
            obj.addProperty('App::PropertyString', 'PartType')
            obj.PartType = item['part']
        refs = []
        layout = report['layout']
        references = [*layout['nodes'].values(), *layout['fans'], *layout['controllers']]
        if mode != 'ring':
            references.append(layout['switch'])
        for i, e in enumerate(references):
            obj = doc.addObject('Part::Feature', 'Reference' + str(i + 1))
            obj.Label = '参考・' + e['label']
            obj.Shape = box(*e['origin'], *e['size'])
            obj.ViewObject.Transparency = 50
            obj.ViewObject.ShapeColor = (0.76, 0.61, 0.30) if e['kind'] == 'spark' else (0.74, 0.65, 0.50) if e['kind'] == 'fan' else (0.5, 0.55, 0.6)
            refs.append(obj)
        doc.recompute()
        path = folder / ('four-node-structure-' + mode + '.FCStd')
        doc.saveAs(str(path))
        write_json(folder / 'generation-progress.json', {'mode': mode, 'stage': 'step_export'})
        Part.makeCompound([shape for _, shape in items]).exportStep(str(folder / ('four-node-structure-' + mode + '.step')))
        write_json(folder / 'generation-progress.json', {'mode': mode, 'stage': 'render'})
        render(folder / (mode + '-assembly.png'))
        for obj in refs:
            obj.Visibility = False
        QtWidgets.QApplication.processEvents()
        render(folder / (mode + '-frame.png'))
        for obj in refs:
            obj.Visibility = True
        Gui.updateGui()
        expected = {obj.Name: (obj.Shape.Volume, obj.Shape.Length) for obj in doc.Objects}
        App.closeDocument(doc.Name)
        doc = App.openDocument(str(path))
        for name, (volume, length) in expected.items():
            actual = doc.getObject(name).Shape
            if not actual.isValid() or abs(actual.Volume - volume) > 1e-6 or abs(actual.Length - length) > 1e-6:
                raise ValueError('保存後の形状が不一致: ' + name)
        App.closeDocument(doc.Name)
        checks[mode]['reopened'] = True
    for name in ('tray', 'fan_carrier', 'splice'):
        doc = App.newDocument('PartDetail')
        obj = doc.addObject('Part::Feature', 'Detail')
        obj.Shape = parts[name]
        obj.ViewObject.ShapeColor = (0.30, 0.42, 0.50)
        doc.recompute()
        render(folder / (name + '-detail.png'))
        App.closeDocument(doc.Name)
    write_json(folder / 'structure-report.json', reports)
    write_json(folder / 'assembly-validation.json', checks)
    write_json(folder / 'validation.json', {'status': 'passed', 'part_shapes': part_report,
               'assemblies': checks, 'physical_validation': '未検証',
               'scope': '部品の形状・閉じたSTL・造形外形・部品間干渉・締結経路・参照機器との干渉・再読込。'})
    template = (SOURCE / 'four_node_structure.html').read_text(encoding='utf-8')
    payload = json.dumps({'reports': reports, 'checks': checks, 'parts': part_report}, ensure_ascii=False).replace('<', '\\u003c')
    (folder / 'four-node-structure.html').write_text(template.replace('__STRUCTURE_DATA__', payload), encoding='utf-8')
    return App.Version()


def build(*, historical=False):
    if not historical:
        raise ValueError("136部品案は不採用です。接合試験片はmise run joint:spark-rackで生成してください。")
    stamp = datetime.now(ZoneInfo('Asia/Tokyo')).strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8]
    folder = ROOT / 'archive/build-history/four-node-structure-not-adopted' / stamp
    folder.mkdir(parents=True, exist_ok=False)
    names = ['four_node_structure_parameters.py', 'freecad_four_node_structure.py',
             'validate_four_node_structure.py', 'build_four_node_structure.py',
             'four_node_structure.html', 'run_four_node_structure.FCMacro', 'render_four_node_structure.py']
    paths = [SOURCE / name for name in names]
    paths += [ROOT / 'models/spark-rack/source/four_node_layout.py',
              ROOT / 'models/spark-rack/source/rack_candidate_datums.py',
              ROOT / 'tools/cad/edge_finishing.py',
              ROOT / 'tools/cad/check_stl.py', ROOT / 'tools/cad/controller_mount.py',
              ROOT / 'models/spark-rack/reference/prepared-fans-and-cable.json']
    hashes = {str(path.relative_to(ROOT)): digest(path) for path in paths}
    manifest = {'status': 'running', 'purpose': '4台共通枠の部品検討案。量産採用前。', 'sources_sha256': hashes}
    try:
        python = os.environ.get('FREECAD_PYTHON', '/Applications/FreeCAD.app/Contents/Resources/bin/python')
        env = os.environ.copy()
        env['PYTHONPATH'] = os.environ.get('FREECAD_LIB', '/Applications/FreeCAD.app/Contents/Resources/lib') + os.pathsep + env.get('PYTHONPATH', '')
        result = subprocess.run([python, str(Path(__file__)), '--worker', str(folder)], env=env, cwd=ROOT,
                                capture_output=True, text=True)
        (folder / 'freecad.log').write_text(result.stdout + result.stderr, encoding='utf-8')
        if result.returncode:
            raise RuntimeError('部品案の生成に失敗しました（終了コード' + str(result.returncode) + '）: ' + str(folder / 'freecad.log'))
        rendered = subprocess.run(['uv', 'run', '--script', str(SOURCE / 'render_four_node_structure.py'), str(folder)],
                                  cwd=ROOT, capture_output=True, text=True)
        (folder / 'render.log').write_text(rendered.stdout + rendered.stderr, encoding='utf-8')
        if rendered.returncode or len(list(folder.glob('*.png'))) != 9:
            raise RuntimeError('組立図の生成に失敗しました: ' + str(folder / 'render.log'))
        if hashes != {str(path.relative_to(ROOT)): digest(path) for path in paths}:
            raise ValueError('生成中に正本が変更されました')
        manifest.update(status='generated', outputs_sha256={str(path.relative_to(folder)): digest(path)
                        for path in sorted(folder.rglob('*')) if path.is_file()})
    except Exception as error:
        manifest.update(status='failed', error=str(error))
        raise
    finally:
        write_json(folder / 'manifest.json', manifest)
    return folder


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--worker':
        try:
            version = generate(Path(sys.argv[2]))
            write_json(Path(sys.argv[2]) / 'freecad-version.json', version)
        except Exception:
            import traceback
            traceback.print_exc()
            sys.stderr.flush()
            os._exit(1)
        sys.stdout.flush()
        os._exit(0)
    if sys.argv[1:] != ["--historical"]:
        raise SystemExit("不採用案の全体生成は停止しました。mise run joint:spark-rackを使用してください。")
    print(build(historical=True))
