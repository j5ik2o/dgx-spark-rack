"""前面と天板のハニカムの穴、ファン格子の開口、従来の縦の格子との互換をFreeCADで検査する。"""
from itertools import combinations
import math
from pathlib import Path
import sys
import unittest

try:
    import FreeCAD as App
    import Part
except ImportError:
    App = None

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'models/spark-rack/source'))


@unittest.skipIf(App is None, 'FreeCAD同梱Pythonで実行してください')
class GrillePatternTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from spark_rack_parameters import GrilleParameters
        from upper_switch_bay import upper_scene
        cls.pattern = GrilleParameters(style='honeycomb')
        cls.pattern.validate()
        cls.p, cls.bay, cls.acc, cls.scene = upper_scene()

    def test_rect_holes_stay_inside_and_keep_the_wall(self):
        from grille_patterns import honeycomb_in_rect
        holes = honeycomb_in_rect(0, 160, 0, 50, 0, 4, 'xz', 10, 1.6)
        self.assertGreater(len(holes), 10)
        for hole in holes:
            b = hole.BoundBox
            self.assertGreaterEqual(b.XMin, -1e-6)
            self.assertLessEqual(b.XMax, 160 + 1e-6)
            self.assertGreaterEqual(b.ZMin, -1e-6)
            self.assertLessEqual(b.ZMax, 50 + 1e-6)
        centers = [(h.BoundBox.Center.x, h.BoundBox.Center.z) for h in holes]
        nearest = min(math.dist(a, b) for a, b in combinations(centers, 2))
        self.assertGreaterEqual(nearest, 10 + 1.6 - 1e-6)

    def test_fan_grille_keeps_most_of_the_opening_without_tiny_fragments(self):
        from fixed_rack_geometry import fan_carrier
        node = next(n for n in self.scene['nodes'] if n['name'] == 'upper_left')
        carrier = fan_carrier(node, self.p, self.pattern)
        self.assertTrue(carrier.isValid())
        self.assertEqual(len(carrier.Solids), 1)
        x = node['origin'][0] + self.p.spark_width / 2
        z = node['origin'][2] + self.p.spark_height / 2
        probe = Part.makeCylinder(self.p.fan_opening / 2, 4, App.Vector(x, self.p.front_face_y, z), App.Vector(0, 1, 0))
        open_fraction = 1 - probe.common(carrier).Volume / probe.Volume
        self.assertGreater(open_fraction, .70)
        from grille_patterns import honeycomb_clipped_to_circle
        holes = honeycomb_clipped_to_circle(x, z, self.p.fan_opening / 2, self.p.front_face_y - 1, 6, 'xz', 10, 1.6, 12)
        self.assertTrue(all(h.Volume / 6 >= 12 for h in holes))

    def test_default_fan_grille_is_unchanged_without_a_pattern(self):
        from fixed_rack_geometry import fan_carrier
        from spark_rack_parameters import GrilleParameters
        node = next(n for n in self.scene['nodes'] if n['name'] == 'lower_right')
        before = fan_carrier(node, self.p)
        slots = fan_carrier(node, self.p, GrilleParameters(style='slots'))
        self.assertAlmostEqual(before.Volume, slots.Volume, places=6)
        self.assertLess(before.cut(slots).Volume + slots.cut(before).Volume, 1e-6)

    def test_honeycomb_panels_and_lid_are_single_solids(self):
        from accessory_geometry import accessory_parts
        from finish_geometry import finish_parts
        parts = accessory_parts(self.scene, self.p, self.acc, self.pattern)[0]
        parts += finish_parts(self.scene, self.p, self.scene['finish'], self.pattern)[0]
        names = [i['name'] for i in parts if i['role'] in ('mid_panel', 'removable_cover', 'lower_filler', 'top_lid')]
        self.assertEqual(len(names), 14)
        for item in parts:
            if item['name'] not in names:
                continue
            with self.subTest(part=item['name']):
                shape = item['shape']
                self.assertTrue(shape.isValid())
                self.assertEqual(len(shape.Solids), 1)
                bounds = shape.optimalBoundingBox(False)
                self.assertLessEqual(max(bounds.XLength, bounds.YLength, bounds.ZLength), self.p.usable_print_size + 1e-6)

    def test_invalid_pattern_is_rejected(self):
        from spark_rack_parameters import GrilleParameters
        with self.assertRaises(ValueError):
            GrilleParameters(style='waves').validate()
        with self.assertRaises(ValueError):
            GrilleParameters(style='honeycomb', hex_wall=0).validate()


if __name__ == '__main__':
    unittest.main()
