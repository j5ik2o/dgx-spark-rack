"""共通操作面が既存の表示・つまみ・蓋を塞がないことを形状で検査する。"""
from pathlib import Path
import sys
import unittest

try:
    import FreeCAD as App
except ImportError:
    App = None

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'models/spark-rack/source'))


@unittest.skipIf(App is None, 'FreeCAD同梱Pythonで実行してください')
class ControllerFrontFaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from controller_front_face import controller_front_face
        cls.face = controller_front_face()

    def test_two_printable_faces_hide_the_case_outline_and_keep_blind_front(self):
        self.assertEqual(len(self.face['parts']), 2)
        for part in self.face['parts']:
            shape = part['shape']
            self.assertTrue(shape.isValid())
            self.assertEqual(len(shape.Solids), 1)
            bounds = shape.optimalBoundingBox(False)
            self.assertLessEqual(max(bounds.XLength, bounds.YLength, bounds.ZLength), 246)
        metadata = self.face['metadata']
        y = metadata['face_front_y_mm'] + 0.1
        for hole in self.face['mount_holes']:
            x, _, z = hole['origin']
            self.assertTrue(any(part['shape'].isInside(App.Vector(x, y, z), 1e-6, False)
                                for part in self.face['parts']))

    def test_full_display_windows_have_an_unobstructed_added_viewing_corridor(self):
        from controller_front_face import operation_probes
        probes = [probe for probe in operation_probes(self.face['metadata']) if probe['kind'] == 'display']
        self.assertEqual(len(probes), 6)
        for probe in probes:
            for part in self.face['parts']:
                self.assertLess(part['shape'].common(probe['shape']).Volume, 1e-5)

    def test_knobs_project_forward_and_fingers_reach_original_lid(self):
        from controller_front_face import operation_probes
        metadata = self.face['metadata']
        for control in metadata['controls']:
            self.assertAlmostEqual(control['knob_exposure_above_existing_lid_mm'], 2.83, places=5)
            self.assertAlmostEqual(control['knob_projection_ahead_of_added_face_mm'], 2.83, places=5)
            self.assertAlmostEqual(control['lid_opening']['perimeter_clearance_mm'], 0.3)
        self.assertTrue(metadata['existing_lids_flush_with_common_face'])
        probes = [probe for probe in operation_probes(metadata) if probe['kind'] == 'finger']
        self.assertEqual(len(probes), 6)
        for probe in probes:
            self.assertGreaterEqual(probe['shape'].BoundBox.YMax, metadata['existing_lid_front_y_mm'])
            for part in self.face['parts']:
                self.assertLess(part['shape'].common(probe['shape']).Volume, 1e-5)

    def test_mounts_use_rear_access_and_screws_do_not_break_the_front(self):
        mounting = self.face['metadata']['mounting']
        self.assertEqual(len(self.face['mount_holes']), 8)
        self.assertTrue(mounting['rear_access_required'])
        self.assertGreater(self.face['validation']['mount_screw_tip_clearance_mm'], 1)
        self.assertEqual(self.face['validation']['status'], 'passed')

    def test_all_original_lid_screws_remain_accessible_from_front(self):
        from controller_front_face import operation_probes
        probes = [probe for probe in operation_probes(self.face['metadata'])
                  if probe['kind'] == 'lid_screw']
        self.assertEqual(len(probes), 24)
        for probe in probes:
            for part in self.face['parts']:
                self.assertLess(part['shape'].common(probe['shape']).Volume, 1e-5)


if __name__ == '__main__':
    unittest.main()
