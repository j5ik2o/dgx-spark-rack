"""中段の機器棚と前面板の実形状をFreeCADで検査する。"""
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
class AccessoryGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from accessory_geometry import accessory_parts
        from upper_switch_bay import upper_scene
        cls.p, cls.bay, cls.acc, cls.scene = upper_scene()
        cls.parts, cls.metadata = accessory_parts(cls.scene, cls.p, cls.acc)
        cls.by_name = {item['name']: item['shape'] for item in cls.parts}
        cls.shelf = [item['shape'] for item in cls.parts if item['name'].startswith('accessory_shelf_')]

    def test_six_shelf_tiles_three_panels_and_a_sled_fit_the_printer(self):
        self.assertEqual(len(self.shelf), 6)
        self.assertEqual(sum(item['role'] == 'mid_panel' for item in self.parts), 3)
        self.assertIn('remote_kvm_sled', self.by_name)
        for item in self.parts:
            with self.subTest(part=item['name']):
                shape = item['shape']
                self.assertTrue(shape.isValid())
                self.assertTrue(shape.isClosed())
                self.assertEqual(len(shape.Solids), 1)
                bounds = shape.optimalBoundingBox(False)
                self.assertLessEqual(max(bounds.XLength, bounds.YLength, bounds.ZLength),
                                     self.p.usable_print_size + 1e-6)

    def test_parts_touch_without_overlap(self):
        from validate_spark_rack_joint_coupons import contact_area
        for index, first in enumerate(self.parts):
            for second in self.parts[index + 1:]:
                with self.subTest(first=first['name'], second=second['name']):
                    self.assertLess(first['shape'].common(second['shape']).Volume, 1e-5)
        z = self.acc['shelf_z'] + (self.acc['support_z'] - self.acc['shelf_z']) / 2
        for row in range(2):
            for column in range(2):
                a, b = (self.by_name[f'accessory_shelf_{row}_{c}'] for c in (column, column + 1))
                self.assertGreater(contact_area(a, b, z), 300)
        for column in range(3):
            a, b = (self.by_name[f'accessory_shelf_{r}_{column}'] for r in (0, 1))
            self.assertGreater(contact_area(a, b, z), 300)

    def test_screen_window_and_side_slots(self):
        comet = next(b for b in self.scene['equipment'] if b['name'] == 'remote_kvm')
        x, _, z = comet['origin']
        w, _, h = comet['size']
        t = self.acc['parameters']['panel_thickness']
        probe = Part.makeBox(w, t, h, App.Vector(x, self.acc['panel_y'], z))
        covered = probe.common(self.by_name['mid_panel_center']).Volume
        self.assertGreater(1 - covered / probe.Volume, .75)
        left = self.by_name['mid_panel_left']
        solid = Part.makeBox(184, t, self.acc['panel_z'][1] - self.acc['panel_z'][0],
                             App.Vector(-self.p.inner_width / 2, self.acc['panel_y'], self.acc['panel_z'][0]))
        self.assertLess(left.common(solid).Volume, solid.Volume * .7)

    def test_comet_slides_out_once_the_center_panel_is_removed(self):
        comet = next(b for b in self.scene['equipment'] if b['name'] == 'remote_kvm')
        body = Part.makeBox(*comet['size'], App.Vector(*comet['origin']))
        fixed = [item['shape'] for item in self.parts if item['name'] != 'mid_panel_center']
        travel = comet['origin'][1] + comet['size'][1] - (self.p.front_y - 110)
        for step in range(0, int(travel) + 1, 20):
            moved = body.copy()
            moved.translate(App.Vector(0, -step, 0))
            self.assertLess(sum(moved.common(s).Volume for s in fixed), 1e-5)
        self.assertGreater(self.by_name['mid_panel_center'].common(body.copy().translated(App.Vector(0, -40, 0))).Volume, 0)

    def test_side_frames_receive_the_shelf_on_level_bearings(self):
        from fixed_rack_geometry import merge_bay, side_tiles
        from integrated_rack_supports import integrated_supports
        from switch_bay_geometry import switch_bay_parts
        from validate_fixed_rack import horizontal_contact
        _, metadata = integrated_supports(self.scene, self.p)
        metadata = merge_bay(metadata, switch_bay_parts(self.scene, self.p, self.bay)[1])
        metadata = merge_bay(metadata, self.metadata, 'accessories')
        for right in (False, True):
            panels = side_tiles(self.p, right, metadata, self.bay, self.acc)
            area = 0
            for panel in panels:
                shape = panel['shape']
                self.assertTrue(shape.isValid())
                self.assertEqual(len(shape.Solids), 1)
                area += sum(horizontal_contact(shape, tile, self.acc['shelf_z']) for tile in self.shelf)
                self.assertLess(sum(shape.common(tile).Volume for tile in self.shelf), 1e-5)
            self.assertGreater(area, 3000)

    def test_removable_panel_screws_are_recorded(self):
        screws = [f for f in self.metadata['fastener_candidates'] if f['assembly'] == 'mid_panel']
        self.assertEqual(len(screws), 6)
        self.assertTrue(all(f['removable'] for f in screws))
        # 受け板と棚の前の帯を合わせて貫く長さを記録する。
        for screw in screws:
            self.assertEqual(screw['origin'][2], self.acc['shelf_z'])
            self.assertEqual(screw['through_length_mm'],
                             self.acc['support_z'] - self.acc['shelf_z'] + self.acc['parameters']['flange_thickness'])

    def test_side_frame_band_below_the_shelf_is_solid(self):
        from fixed_rack_geometry import side_pattern
        for right in (False, True):
            pattern = side_pattern(self.p, right, None, self.bay, self.acc)
            x = self.p.width / 2 - self.p.section if right else -self.p.width / 2
            # 棚の受け面の下6mmを全厚で残す。従来の中段の帯は293.25mmからで、この範囲を覆わない。
            probe = Part.makeBox(self.p.section, 40, 6, App.Vector(x, -60, self.acc['shelf_z'] - 6))
            self.assertAlmostEqual(pattern.common(probe).Volume, probe.Volume, delta=1)

    def test_ring_phase_with_the_bay_and_shelf_validates(self):
        from fixed_rack_geometry import shapes
        from upper_switch_bay import upper_scene
        from validate_fixed_rack import validate
        p, bay, acc, scene = upper_scene('ring')
        result = validate(shapes(p, 'ring', bay, acc, scene['finish']))
        self.assertEqual(result['status'], 'passed')
        self.assertNotIn('switch_front_service', result['exchange_envelopes'])


if __name__ == '__main__':
    unittest.main()
