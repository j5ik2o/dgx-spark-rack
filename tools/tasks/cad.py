"""CADの生成・検査とBambu Studio用3MFの生成をまとめる。"""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[2]
MODELS = ('spark-rack', 'adapter-rack', 'fan-controller')
PROFILE = ROOT / 'print-projects/profiles/pla-prototype.json'


def settings():
    paths = {
        'python': Path(os.environ.get('FREECAD_PYTHON', '/Applications/FreeCAD.app/Contents/Resources/bin/python')),
        'lib': Path(os.environ.get('FREECAD_LIB', '/Applications/FreeCAD.app/Contents/Resources/lib')),
        'bambu': Path(os.environ.get('BAMBU_STUDIO', '/Applications/BambuStudio.app/Contents/MacOS/BambuStudio')),
        'profiles': Path(os.environ.get('BAMBU_PROFILES', '/Applications/BambuStudio.app/Contents/Resources/profiles/BBL')),
    }
    return {key: path.expanduser().resolve() for key, path in paths.items()}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def require_paths(*paths):
    for path in paths:
        if not path.exists():
            raise ValueError(f'見つかりません: {path}（環境変数の設定は docs/タスクランナー.md を参照）')


def checked_build(model, folder):
    folder = folder.resolve()
    if folder.parent != (ROOT / 'build' / model).resolve():
        raise ValueError(f'build/{model}/<実行ID> を指定してください')
    manifest = json.loads((folder / 'manifest.json').read_text())
    if manifest.get('status') != 'passed':
        raise ValueError('成功したCAD生成物だけを使用できます')
    for name, expected in manifest['sources_sha256'].items():
        if digest(ROOT / name) != expected:
            raise ValueError(f'設計コードが生成時から変わっています。buildを再実行してください: {name}')
    for name, expected in manifest['outputs_sha256'].items():
        if digest(folder / name) != expected:
            raise ValueError(f'生成物が変更されています: {folder / name}')
    if not list((folder / 'stl').glob('*.stl')):
        raise ValueError('STLがありません')
    return manifest


def build(model):
    cfg = settings()
    require_paths(cfg['python'], cfg['lib'])
    env = os.environ.copy()
    env['PYTHONPATH'] = str(cfg['lib']) + os.pathsep + env.get('PYTHONPATH', '')
    print(f'{model}: CADを生成・検査しています…', flush=True)
    with tempfile.TemporaryDirectory(prefix='dgx-cad-') as temporary:
        result = Path(temporary) / 'result.json'
        run = subprocess.run([str(cfg['python']), str(ROOT / 'tools/tasks/cad_worker.py'), model, str(result)],
                             cwd=ROOT, env=env, capture_output=True, text=True)
        if run.returncode or not result.exists():
            raise RuntimeError(f'FreeCADの生成に失敗しました:\n{run.stdout}\n{run.stderr}')
        output = Path(json.loads(result.read_text())['output'])
    checked_build(model, output)
    print(f'CAD: {output}', flush=True)
    return output


def inspect_3mf(path, copies, expected=None):
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError(f'3MFが破損しています: {path}')
        config = json.loads(archive.read('Metadata/project_settings.config'))
        expected = expected or {'printer_settings_id': 'Bambu Lab X1 Carbon 0.4 nozzle',
                    'curr_bed_type': 'Textured PEI Plate', 'wall_loops': '4', 'layer_height': '0.2', 'filament_type': ['PLA']}
        for key, value in expected.items():
            if config.get(key) != value:
                raise ValueError(f'{path.name}: {key} が指定設定と異なります')
        model = ET.fromstring(archive.read('3D/3dmodel.model'))
        items = model.findall('{*}build/{*}item')
        if len(items) != copies:
            raise ValueError(f'個数が不一致です: {len(items)} != {copies}')
        return {'objects': len(items), 'settings': {key: config[key] for key in expected}, 'filament': config['filament_type']}


def print_settings(model, purpose, cfg):
    if purpose == 'prototype':
        return PROFILE, cfg['profiles'] / 'filament/Bambu PLA Basic @BBL X1C.json', None
    if purpose != 'production':
        raise ValueError('試作／本番を指定してください')
    recipe = ROOT / 'print-projects/profiles/production' / (model + '.json')
    if not recipe.exists():
        raise ValueError(f'本番用の素材・印刷条件は未設定です: {recipe}')
    data = json.loads(recipe.read_text())
    expected = data['expected_settings']
    required = ('printer_settings_id', 'filament_type', 'curr_bed_type', 'layer_height', 'wall_loops')
    if any(not expected.get(key) for key in required):
        raise ValueError('本番設定にはプリンター・素材・プレート・積層・壁数の検査値が必要です')
    if expected['printer_settings_id'] != 'Bambu Lab X1 Carbon 0.4 nozzle':
        raise ValueError('現在の対応機種はX1 Carbon・0.4mmノズルです')
    if not isinstance(expected['filament_type'], list):
        raise ValueError('filament_type は素材名の配列で指定してください')
    return (ROOT / data['process_profile']).resolve(), (ROOT / data['filament_profile']).resolve(), expected


def project(model, folder=None, part=None, copies=1, *, purpose):
    cfg = settings()
    machine = cfg['profiles'] / 'machine/Bambu Lab X1 Carbon 0.4 nozzle.json'
    profile, filament, expected = print_settings(model, purpose, cfg)
    require_paths(cfg['bambu'], machine, filament, profile)
    folder = folder.resolve() if folder else build(model)
    checked_build(model, folder)
    parts = sorted((folder / 'stl').glob('*.stl'))
    if part:
        parts = [p for p in parts if p.stem == part]
        if not parts:
            raise ValueError(f'部品がありません: {part}')
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8]
    output = ROOT / 'print-projects' / model / purpose / 'generated' / stamp
    output.mkdir(parents=True, exist_ok=False)
    report = {'status': 'running', 'model': model, 'purpose': purpose, 'cad_build': str(folder.relative_to(ROOT)),
              'cad_manifest_sha256': digest(folder / 'manifest.json'), 'copies_per_part': copies,
              'sliced': False, 'parts': {}, 'profile_sha256': digest(profile),
              'machine_profile_sha256': digest(machine), 'filament_profile_sha256': digest(filament),
              'generator_sha256': digest(Path(__file__)),
              'bambu_binary': str(cfg['bambu'])}
    try:
        for stl in parts:
            target = output / (stl.stem + '.3mf')
            command = [str(cfg['bambu']), '--debug', '1', '--load-settings', f'{machine};{profile}',
                       '--load-filaments', str(filament), '--arrange', '1', '--orient', '0',
                       '--clone-objects', str(copies), '--export-3mf', target.name,
                       '--outputdir', str(output), str(stl)]
            run = subprocess.run(command, cwd=output, capture_output=True, text=True)
            (output / (stl.stem + '.log')).write_text(run.stdout + run.stderr)
            if run.returncode or not target.exists():
                raise RuntimeError(f'{stl.stem} の3MF生成に失敗しました: {output / (stl.stem + ".log")}')
            report['parts'][stl.stem] = {**inspect_3mf(target, copies, expected),
                                        'stl_sha256': digest(stl), '3mf_sha256': digest(target)}
            print(f'3MF: {target}', flush=True)
        checked_build(model, folder)
        if digest(profile) != report['profile_sha256']:
            raise ValueError('生成中に印刷プロファイルが変更されました')
        report['status'] = 'passed'
    except Exception as error:
        report.update(status='failed', error=str(error))
        raise
    finally:
        write_json(output / 'manifest.json', report)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('build', '3mf', 'doctor'))
    parser.add_argument('model', nargs='?', choices=(*MODELS, 'all'), default='all')
    parser.add_argument('--build-dir', type=Path, help='検査済みのCAD出力を再利用（単一モデルのみ）')
    parser.add_argument('--part', help='STL拡張子を除いた部品名（3MFのみ）')
    parser.add_argument('--copies', type=int, default=1, help='各部品の個数（既定1、3MFのみ）')
    parser.add_argument('--purpose', choices=('prototype', 'production'), help='3MFの用途（必須）')
    args = parser.parse_args()
    if args.action == '3mf' and not args.purpose:
        parser.error('--purpose prototype または production を指定してください')
    if args.action != '3mf' and args.purpose:
        parser.error('--purpose は3mf専用です')
    if args.copies < 1 or (args.build_dir and args.model == 'all'):
        parser.error('個数は1以上、--build-dirは単一モデルを指定してください')
    if args.action != '3mf' and (args.build_dir or args.part or args.copies != 1):
        parser.error('--build-dir/--part/--copies は3mf専用です')
    if args.action == 'doctor':
        for key, path in settings().items():
            require_paths(path)
            print(f'{key}: {path}')
        return
    for model in MODELS if args.model == 'all' else (args.model,):
        if args.action == 'build':
            build(model)
        else:
            project(model, args.build_dir, args.part, args.copies, purpose=args.purpose)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, RuntimeError, OSError, KeyError) as error:
        print(f'エラー: {error}', file=sys.stderr)
        sys.exit(1)
