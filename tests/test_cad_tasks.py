"""未検査・古い・改変済みの生成物を3MFに流用させない。"""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('cad_tasks', Path(__file__).resolve().parents[1] / 'tools/tasks/cad.py')
cad = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cad)


class BuildIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.folder = self.root / 'build/fan-controller/run'
        (self.folder / 'stl').mkdir(parents=True)
        (self.root / 'source.py').write_text('original source')
        (self.folder / 'stl/part.stl').write_bytes(b'original mesh')
        self.manifest = {
            'status': 'passed',
            'sources_sha256': {'source.py': cad.digest(self.root / 'source.py')},
            'outputs_sha256': {'stl/part.stl': cad.digest(self.folder / 'stl/part.stl')},
        }
        self.save()
        self.patcher = patch.object(cad, 'ROOT', self.root)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def save(self):
        (self.folder / 'manifest.json').write_text(json.dumps(self.manifest))

    def test_successful_unchanged_build_is_accepted(self):
        self.assertEqual(cad.checked_build('fan-controller', self.folder), self.manifest)

    def test_changed_source_is_rejected(self):
        (self.root / 'source.py').write_text('new design')
        with self.assertRaisesRegex(ValueError, '設計コード'):
            cad.checked_build('fan-controller', self.folder)

    def test_changed_mesh_is_rejected(self):
        (self.folder / 'stl/part.stl').write_bytes(b'altered mesh')
        with self.assertRaisesRegex(ValueError, '生成物が変更'):
            cad.checked_build('fan-controller', self.folder)

    def test_failed_build_is_rejected(self):
        self.manifest['status'] = 'failed'
        self.save()
        with self.assertRaisesRegex(ValueError, '成功した'):
            cad.checked_build('fan-controller', self.folder)

    def test_other_model_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'build/spark-rack'):
            cad.checked_build('spark-rack', self.folder)

    def test_missing_output_is_rejected(self):
        (self.folder / 'stl/part.stl').unlink()
        with self.assertRaises(FileNotFoundError):
            cad.checked_build('fan-controller', self.folder)


class ProjectValidationTests(unittest.TestCase):
    def check_project(self, objects, copies, **changes):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'project.3mf'
            config = {'printer_settings_id': 'Bambu Lab X1 Carbon 0.4 nozzle',
                      'curr_bed_type': 'Textured PEI Plate', 'wall_loops': '4',
                      'layer_height': '0.2', 'filament_type': ['PLA']}
            config.update(changes)
            model = '<model xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><build>'
            model += '<item objectid="1"/>' * objects
            model += '</build></model>'
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('Metadata/project_settings.config', json.dumps(config))
                archive.writestr('3D/3dmodel.model', model)
            return cad.inspect_3mf(path, copies)

    def test_requested_copy_count_is_checked(self):
        self.assertEqual(self.check_project(2, 2)['objects'], 2)
        with self.assertRaisesRegex(ValueError, '個数'):
            self.check_project(1, 2)

    def test_wrong_material_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'PLA'):
            self.check_project(1, 1, filament_type=['ABS'])

    def test_wrong_plate_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'curr_bed_type'):
            self.check_project(1, 1, curr_bed_type='Cool Plate')


if __name__ == '__main__':
    unittest.main()
