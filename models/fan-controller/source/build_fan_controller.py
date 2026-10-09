"""ケースを生成し、実行ごとのフォルダに形状・検査・由来を保存する。"""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import runpy
import sys
import uuid

import FreeCAD as App
import MeshPart
import Part

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tools/cad'))
from check_stl import inspect
from controller_mount import hardware_bom


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    out = ROOT / 'build/fan-controller' / (datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8])
    out.mkdir(parents=True, exist_ok=False)
    sources = {str(p.relative_to(ROOT)): digest(p) for p in sorted(SOURCE.iterdir()) if p.is_file()}
    sources['tools/cad/check_stl.py'] = digest(ROOT / 'tools/cad/check_stl.py')
    sources['tools/cad/controller_mount.py'] = digest(ROOT / 'tools/cad/controller_mount.py')
    sources['tools/cad/edge_finishing.py'] = digest(ROOT / 'tools/cad/edge_finishing.py')
    try:
        model = runpy.run_path(str(SOURCE / 'freecad_fan_controller.py'))
        doc = model['doc']
        report = {'status': 'passed', 'physical_fit_verified': False, 'parts': {},
                  'clamp_checks': model['clamp_validation'],
                  'printed_bom': {'CaseBody': 1, 'CaseLid': 1, 'PCBClamp': 4},
                  'rack_mount_hardware': hardware_bom(),
                  'fasteners': {'lid': {'count': 4, 'nominal_diameter_mm': 2, 'length_mm': model['SCREW_LENGTH']},
                                'pcb_clamps': {'count': 4, 'nominal_diameter_mm': 2,
                                               'length_mm': model['CLAMP_SCREW_LENGTH'],
                                               'max_head_diameter_mm': model['CLAMP_HEAD_DIAMETER'],
                                               'max_head_height_mm': model['CLAMP_HEAD_HEIGHT']}}}
        (out / 'stl').mkdir()
        for name in model['PRINT_PARTS']:
            shape = doc.getObject(name).Shape
            if not shape.isValid() or len(shape.Solids) != 1 or not shape.isClosed():
                raise ValueError(f'{name}: 有効な閉ソリッドではありません')
            Part.export([doc.getObject(name)], str(out / (name + '.step')))
            printable = shape.copy()
            if name == 'CaseLid':
                printable.rotate(App.Vector(), App.Vector(1, 0, 0), 180)
            bounds = printable.BoundBox
            printable.translate(App.Vector(-bounds.XMin, -bounds.YMin, -bounds.ZMin))
            mesh = MeshPart.meshFromShape(Shape=printable, LinearDeflection=0.05, AngularDeflection=0.15, Relative=False)
            mesh_bounds = mesh.BoundBox
            mesh.translate(-mesh_bounds.XMin, -mesh_bounds.YMin, -mesh_bounds.ZMin)
            target = out / 'stl' / (name + '.stl')
            mesh.write(str(target))
            report['parts'][name] = {'volume_mm3': shape.Volume, 'stl': inspect(target)}
        report['body_lid_overlap_mm3'] = model['body_final'].common(model['lid_final']).Volume
        if report['body_lid_overlap_mm3'] > 1e-6:
            raise ValueError('本体と蓋が干渉しています')
        doc.saveAs(str(out / 'FanControllerCase.FCStd'))
        reopened = App.openDocument(str(out / 'FanControllerCase.FCStd'))
        try:
            for name, result in report['parts'].items():
                shape = reopened.getObject(name).Shape
                if not shape.isValid() or abs(shape.Volume - result['volume_mm3']) > 1e-6:
                    raise ValueError(f'{name}: 保存後の再読込検査に失敗しました')
        finally:
            App.closeDocument(reopened.Name)
        save_json(out / 'validation.json', report)
        save_json(out / 'manifest.json', {
            'status': 'passed', 'freecad_version': list(App.Version()), 'sources_sha256': sources,
            'outputs_sha256': {str(p.relative_to(out)): digest(p) for p in sorted(out.rglob('*')) if p.is_file()},
            'limitations': 'USB/JST開口等に仮寸法あり。実物適合・操作性・ラックへの取付は未検証。',
        })
    except Exception as error:
        save_json(out / 'failure.json', {'status': 'failed', 'error': str(error)})
        raise
    App.Console.PrintMessage(f'生成・検査完了: {out}\n')
    return out


if __name__ == '__main__':
    build()
