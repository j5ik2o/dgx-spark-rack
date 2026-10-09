"""仮配置の画面・配線計算・参照CADを新しい実行フォルダへ生成する。"""
import argparse
from dataclasses import replace
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import uuid
from zoneinfo import ZoneInfo

from four_node_layout import LayoutParameters, SWITCHES, evaluate

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(__file__).parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def build(*, cad=True):
    stamp = datetime.now(ZoneInfo('Asia/Tokyo')).strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8]
    out = ROOT / 'build/spark-rack/four-node-layout' / stamp
    out.mkdir(parents=True, exist_ok=False)
    sources = [SOURCE / name for name in ('four_node_layout.py', 'freecad_four_node_layout.py',
                                         'build_four_node_layout.py', 'four_node_layout.html')]
    sources.append(ROOT / 'models/spark-rack/reference/four-node-layout-assumptions.json')
    sources.append(ROOT / 'models/spark-rack/reference/prepared-fans-and-cable.json')
    sources.append(ROOT / 'models/fan-controller/source/freecad_fan_controller.py')
    sources.append(ROOT / 'tools/cad/controller_mount.py')
    sources.append(SOURCE / 'rack_candidate_datums.py')
    sources.append(ROOT / 'models/spark-rack/reference/pending-mount-measurements.json')
    hashes = {str(p.relative_to(ROOT)): digest(p) for p in sources}
    report = {'ring': evaluate(replace(LayoutParameters(), row_pitch=160), include_switch=False)}
    report.update({key: evaluate(LayoutParameters(), key) for key in SWITCHES})
    manifest = {'status': 'running', 'purpose': '配置検討。印刷用生成物ではない。',
                'sources_sha256': hashes, 'physical_validation': '未検証'}
    try:
        write_json(out / 'layout-report.json', report)
        payload = json.dumps(report, ensure_ascii=False).replace('<', '\\u003c')
        template = (SOURCE / 'four_node_layout.html').read_text(encoding='utf-8')
        if template.count('__LAYOUT_DATA__') != 1:
            raise ValueError('画面テンプレートのデータ挿入位置が不正です')
        (out / 'four-node-layout.html').write_text(template.replace('__LAYOUT_DATA__', payload), encoding='utf-8')
        checks = {key: value['checks'] for key, value in report.items()}
        if any(c['equipment_and_shelf_collisions'] or c['outside_envelope']
               or c['rear_space_overflow'] or not c['switch_assignment_found'] for c in checks.values()):
            raise ValueError('初期配置の収容範囲または機器・支持範囲の干渉検査に失敗しました')
        if cad:
            python = Path(os.environ.get('FREECAD_PYTHON', '/Applications/FreeCAD.app/Contents/Resources/bin/python'))
            lib = Path(os.environ.get('FREECAD_LIB', '/Applications/FreeCAD.app/Contents/Resources/lib'))
            env = os.environ.copy()
            env['PYTHONPATH'] = str(lib) + os.pathsep + env.get('PYTHONPATH', '')
            run = subprocess.run([str(python), str(SOURCE / 'freecad_four_node_layout.py'), str(out)],
                                 cwd=ROOT, env=env, capture_output=True, text=True)
            (out / 'cad.log').write_text(run.stdout + run.stderr, encoding='utf-8')
            if run.returncode or not (out / 'cad-validation.json').exists():
                raise RuntimeError('参照CADの生成に失敗しました: ' + str(out / 'cad.log'))
        if hashes != {str(p.relative_to(ROOT)): digest(p) for p in sources}:
            raise ValueError('生成中に正本が変更されました')
        write_json(out / 'validation.json', {'status': 'passed', 'layout_checks': checks,
                   'cad_generated': cad, 'physical_validation': '未検証',
                   'scope': '仮収容範囲、機器・支持範囲の干渉、配線計算。実端子・実曲げ条件は未検証。'})
        manifest.update(status='generated', outputs_sha256={str(p.relative_to(out)): digest(p)
                        for p in sorted(out.iterdir()) if p.is_file()})
    except Exception as error:
        manifest.update(status='failed', error=str(error))
        raise
    finally:
        write_json(out / 'manifest.json', manifest)
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--without-cad', action='store_true', help='画面と配線計算だけを生成')
    args = parser.parse_args()
    print(build(cad=not args.without_cad))
