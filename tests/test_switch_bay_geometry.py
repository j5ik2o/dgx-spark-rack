"""上部専用段の床とトレーの実形状をFreeCADで検査する。"""
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
class SwitchBayGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fixed_rack_layout import fixed_layout
        from switch_bay_geometry import switch_bay_parts
        from upper_switch_bay import bay_layout, rack_parameters
        cls.p = rack_parameters()
        cls.bay = bay_layout(cls.p)
        cls.scene = fixed_layout('crs812', cls.p, cls.bay)
        cls.parts, cls.metadata = switch_bay_parts(cls.scene, cls.p, cls.bay)
        cls.by_name = {item['name']: item['shape'] for item in cls.parts}
        cls.floor = [item['shape'] for item in cls.parts if item['role'] == 'bay_floor']

    def test_six_floor_tiles_and_two_trays_fit_the_printer(self):
        self.assertEqual(len(self.floor), 6)
        self.assertEqual(sum(item['role'] == 'switch_tray' for item in self.parts), 2)
        for item in self.parts:
            with self.subTest(part=item['name']):
                shape = item['shape']
                self.assertTrue(shape.isValid())
                self.assertTrue(shape.isClosed())
                self.assertEqual(len(shape.Solids), 1)
                bounds = shape.optimalBoundingBox(False)
                self.assertLessEqual(max(bounds.XLength, bounds.YLength, bounds.ZLength),
                                     self.p.usable_print_size + 1e-6)

    def test_floor_tiles_overlap_only_by_contact(self):
        from validate_spark_rack_joint_coupons import contact_area
        for index, first in enumerate(self.parts):
            for second in self.parts[index + 1:]:
                with self.subTest(first=first['name'], second=second['name']):
                    self.assertLess(first['shape'].common(second['shape']).Volume, 1e-5)
        z = self.bay['floor_z'] + (self.bay['switch_z'] - self.bay['floor_z']) / 2
        for row in range(2):
            for column in range(2):
                a, b = (self.by_name[f'switch_floor_{row}_{c}'] for c in (column, column + 1))
                self.assertGreater(contact_area(a, b, z), 500)
        for column in range(3):
            a, b = (self.by_name[f'switch_floor_{r}_{column}'] for r in (0, 1))
            self.assertGreater(contact_area(a, b, z), 500)

    def test_trays_rest_on_the_floor_and_slide_out_without_collision(self):
        from validate_spark_rack_joint_coupons import contact_area
        floor = self.floor[0].multiFuse(self.floor[1:])
        travel = self.p.rear_y - self.bay['switch_back_y'] + 20
        for name in ('switch_tray_left', 'switch_tray_right'):
            with self.subTest(tray=name):
                tray = self.by_name[name]
                self.assertGreater(contact_area(floor, tray, self.bay['support_z']), 5000)
                for step in range(0, int(travel) + 1, 20):
                    moved = tray.copy()
                    moved.translate(App.Vector(0, step, 0))
                    self.assertLess(moved.common(floor).Volume, 1e-5)

    def test_side_frames_receive_the_floor_on_level_bearings(self):
        from fixed_rack_geometry import side_tiles
        from integrated_rack_supports import integrated_supports
        from fixed_rack_geometry import merge_bay
        from validate_fixed_rack import horizontal_contact
        _, metadata = integrated_supports(self.scene, self.p)
        metadata = merge_bay(metadata, self.metadata)
        for right in (False, True):
            panels = side_tiles(self.p, right, metadata, self.bay)
            self.assertEqual(len(panels), 6)
            area = 0
            for panel in panels:
                shape = panel['shape']
                self.assertTrue(shape.isValid())
                self.assertEqual(len(shape.Solids), 1)
                bounds = shape.optimalBoundingBox(False)
                self.assertLessEqual(max(bounds.XLength, bounds.YLength, bounds.ZLength), self.p.usable_print_size + 1e-6)
                area += sum(horizontal_contact(shape, tile, self.bay['floor_z']) for tile in self.floor)
                self.assertLess(sum(shape.common(tile).Volume for tile in self.floor), 1e-5)
            self.assertGreater(area, 3000)

    def test_retention_screws_and_open_questions_are_recorded(self):
        retention = [f for f in self.metadata['fastener_candidates'] if f['assembly'] == 'switch_tray_retention']
        self.assertEqual(len(retention), 2)
        self.assertTrue(all(f['removable'] for f in retention))
        self.assertIn('未確定', retention[0]['head_and_nut_retention'])
        self.assertEqual(self.metadata['removed_cross_beams'], ['switch_rail_front', 'switch_rail_rear'])


if __name__ == '__main__':
    unittest.main()
