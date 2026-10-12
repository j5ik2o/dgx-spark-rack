"""前面、天板、側枠のハニカムの穴、ファン格子の開口、従来の縦の格子との互換をFreeCADで検査する。"""
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

    def test_side_plane_holes_run_across_the_frame(self):
        from grille_patterns import honeycomb_in_rect
        holes = honeycomb_in_rect(0, 100, 0, 60, 5, 30, 'yz', 10, 1.6)
        self.assertGreater(len(holes), 10)
        for hole in holes:
            b = hole.BoundBox
            self.assertAlmostEqual(b.XMin, 5, places=6)
            self.assertAlmostEqual(b.XMax, 35, places=6)
            self.assertGreaterEqual(b.YMin, -1e-6)
            self.assertLessEqual(b.YMax, 100 + 1e-6)
            self.assertGreaterEqual(b.ZMin, -1e-6)
            self.assertLessEqual(b.ZMax, 60 + 1e-6)
            # 頂点を上下へ向けるため、縦の長さが対辺より長い。
            self.assertGreater(b.ZLength, b.YLength)

    def test_side_frames_use_the_honeycomb_and_keep_the_shelf_band(self):
        from fixed_rack_geometry import side_pattern
        for right in (False, True):
            with self.subTest(right=right):
                frame = side_pattern(self.p, right, None, self.bay, self.acc, self.pattern)
                self.assertTrue(frame.isValid())
                x = self.p.width / 2 - self.p.skin if right else -self.p.width / 2
                # 電源区画の横の通気範囲で、外板の開きを縦溝の約36%より大きくする。
                skin = Part.makeBox(self.p.skin, 80, 75, App.Vector(x, -300, 55))
                self.assertGreater(1 - frame.common(skin).Volume / skin.Volume, .5)
                x = self.p.width / 2 - self.p.section if right else -self.p.width / 2
                band = Part.makeBox(self.p.section, 40, 6, App.Vector(x, -60, self.acc['shelf_z'] - 6))
                self.assertAlmostEqual(frame.common(band).Volume, band.Volume, delta=1)

    def test_honeycomb_side_tiles_are_single_solids(self):
        from fixed_rack_geometry import merge_bay, side_pattern, side_tiles
        from integrated_rack_supports import integrated_supports
        from switch_bay_geometry import switch_bay_parts
        from accessory_geometry import accessory_parts
        _, metadata = integrated_supports(self.scene, self.p)
        metadata = merge_bay(metadata, switch_bay_parts(self.scene, self.p, self.bay)[1])
        metadata = merge_bay(metadata, accessory_parts(self.scene, self.p, self.acc)[1], 'accessories')
        tiles = side_tiles(self.p, False, metadata, self.bay, self.acc, self.pattern)
        self.assertEqual(len(tiles), 6)
        for tile in tiles:
            with self.subTest(part=tile['name']):
                self.assertTrue(tile['shape'].isValid())
                self.assertEqual(len(tile['shape'].Solids), 1)
        frame = side_pattern(self.p, False, metadata, self.bay, self.acc, self.pattern)
        self.assertAlmostEqual(sum(t['shape'].Volume for t in tiles), frame.Volume, delta=1)

    def test_power_fan_grille_keeps_most_of_the_opening(self):
        from fixed_rack_geometry import power_carrier
        from grille_patterns import honeycomb_clipped_to_circle
        for right in (False, True):
            with self.subTest(right=right):
                carrier = power_carrier(self.p, right, self.pattern)
                self.assertTrue(carrier.isValid())
                self.assertEqual(len(carrier.Solids), 1)
                x = self.p.width / 2 - 4 if right else -self.p.width / 2
                probe = Part.makeCylinder(57, 4, App.Vector(x, -120, 88), App.Vector(1, 0, 0))
                self.assertGreater(1 - probe.common(carrier).Volume / probe.Volume, .70)
                holes = honeycomb_clipped_to_circle(-120, 88, 57, x - 1, 6, 'yz', 10, 1.6, 12)
                self.assertTrue(all(h.Volume / 6 >= 12 for h in holes))
                self.assertTrue(all(abs(h.BoundBox.XMin - (x - 1)) < 1e-6 for h in holes))

    def test_default_fan_grille_is_unchanged_without_a_pattern(self):
        from fixed_rack_geometry import fan_carrier, power_carrier, side_pattern
        from spark_rack_parameters import GrilleParameters
        slots = GrilleParameters(style='slots')
        node = next(n for n in self.scene['nodes'] if n['name'] == 'lower_right')
        pairs = [(fan_carrier(node, self.p), fan_carrier(node, self.p, slots)),
                 (power_carrier(self.p, True), power_carrier(self.p, True, slots)),
                 (side_pattern(self.p, False, None, self.bay, self.acc),
                  side_pattern(self.p, False, None, self.bay, self.acc, slots))]
        for before, after in pairs:
            self.assertAlmostEqual(before.Volume, after.Volume, places=6)
            self.assertLess(before.cut(after).Volume + after.cut(before).Volume, 1e-6)

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
