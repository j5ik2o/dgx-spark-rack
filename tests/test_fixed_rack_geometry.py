"""固定段ラックの分割形状をFreeCADで検査する。"""
from pathlib import Path
import sys
import unittest

try:
    import FreeCAD as App
except ImportError:
    App = None

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'models/spark-rack/source'))


@unittest.skipIf(App is None, 'FreeCAD同梱Pythonで実行してください')
class FixedRackGeometryTests(unittest.TestCase):
    def test_power_fan_can_pass_outward_without_removing_the_side_frame(self):
        import Part
        from fixed_rack_geometry import side_pattern
        from spark_rack_parameters import FixedRackParameters
        p = FixedRackParameters()
        probe = Part.makeBox(90, 120, 120, App.Vector(-310, -180, 28))
        self.assertLess(side_pattern(p, False).common(probe).Volume, 1e-5)

    def test_side_panels_are_valid_single_solids_within_print_size(self):
        from fixed_rack_geometry import side_tiles
        from spark_rack_parameters import FixedRackParameters
        p = FixedRackParameters()
        for right in (False, True):
            panels = side_tiles(p, right)
            self.assertEqual(len(panels), 6)
            for panel in panels:
                with self.subTest(panel=panel['name']):
                    s = panel['shape']
                    self.assertTrue(s.isValid())
                    self.assertTrue(s.isClosed())
                    self.assertEqual(len(s.Solids), 1)
                    b = s.optimalBoundingBox(False)
                    self.assertLessEqual(max(b.XLength, b.YLength, b.ZLength), p.usable_print_size + 1e-6)

    def test_split_parts_preserve_the_side_frame_without_overlap(self):
        from fixed_rack_geometry import side_pattern, side_tiles
        from spark_rack_parameters import FixedRackParameters
        p = FixedRackParameters()
        shapes = [i['shape'] for i in side_tiles(p, False)]
        self.assertAlmostEqual(sum(s.Volume for s in shapes), side_pattern(p, False).Volume, places=3)
        for i, a in enumerate(shapes):
            for b in shapes[i + 1:]:
                self.assertLess(a.common(b).Volume, 1e-5)

    def test_cross_beam_laps_have_contact_without_collision(self):
        from fixed_rack_geometry import beam_segments
        from fixed_rack_layout import cross_beams
        from spark_rack_parameters import FixedRackParameters
        from validate_spark_rack_joint_coupons import contact_area
        p = FixedRackParameters()
        for recipe in cross_beams(p):
            pieces = [i['shape'] for i in beam_segments(recipe, p)]
            for s in pieces:
                self.assertTrue(s.isValid())
                self.assertEqual(len(s.Solids), 1)
            for a, b in zip(pieces, pieces[1:]):
                self.assertLess(a.common(b).Volume, 1e-5)
                self.assertGreater(contact_area(a, b, recipe['origin'][2] + recipe['size'][2] / 2), 350)


if __name__ == '__main__':
    unittest.main()
