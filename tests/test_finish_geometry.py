"""前面と天面の板の実形状をFreeCADで検査する。"""
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
class FinishGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from finish_geometry import finish_parts
        from fixed_rack_geometry import beam_segments
        from upper_switch_bay import upper_scene
        cls.p, cls.bay, cls.acc, cls.scene = upper_scene()
        cls.finish = cls.scene['finish']
        cls.parts, cls.metadata = finish_parts(cls.scene, cls.p, cls.finish)
        cls.by_name = {item['name']: item['shape'] for item in cls.parts}
        cls.beams = {}
        for recipe in cls.scene['cross_beams']:
            if recipe['name'].startswith('frame_top_'):
                for item in beam_segments(recipe, cls.p):
                    cls.beams[item['name']] = item['shape']

    def test_eleven_parts_are_single_solids_within_the_printer(self):
        self.assertEqual(len(self.parts), 11)
        for item in self.parts:
            with self.subTest(part=item['name']):
                shape = item['shape']
                self.assertTrue(shape.isValid())
                self.assertTrue(shape.isClosed())
                self.assertEqual(len(shape.Solids), 1)
                bounds = shape.optimalBoundingBox(False)
                self.assertLessEqual(max(bounds.XLength, bounds.YLength, bounds.ZLength),
                                     self.p.usable_print_size + 1e-6)

    def test_parts_and_top_frame_touch_without_overlap(self):
        shapes = list(self.by_name.items()) + list(self.beams.items())
        for index, (a_name, a) in enumerate(shapes):
            for b_name, b in shapes[index + 1:]:
                with self.subTest(first=a_name, second=b_name):
                    self.assertLess(a.common(b).Volume, 1e-5)

    def test_covers_hang_from_the_top_frame_and_slide_forward(self):
        from validate_fixed_rack import horizontal_contact
        z = self.finish['cover_z'][1]
        beams = [s for n, s in self.beams.items() if n.startswith('frame_top_front_')]
        for name in self.finish['removable_covers']:
            cover = self.by_name[name]
            self.assertGreater(sum(horizontal_contact(cover, beam, z) for beam in beams), 200)
            for step in range(0, 121, 20):
                moved = cover.copy()
                moved.translate(App.Vector(0, -step, 0))
                self.assertLess(sum(moved.common(beam).Volume for beam in beams), 1e-5)

    def test_lid_rests_on_the_top_frame_and_has_vent_slots(self):
        from validate_fixed_rack import horizontal_contact
        lid = [s for n, s in self.by_name.items() if n.startswith('top_lid_')]
        self.assertEqual(len(lid), 6)
        area = sum(horizontal_contact(beam, tile, self.p.height) for beam in self.beams.values() for tile in lid)
        self.assertGreater(area, 20000)
        plate = Part.makeBox(self.p.width, self.p.depth, 4, App.Vector(-self.p.width / 2, self.p.front_y, self.p.height))
        solid = sum(tile.common(plate).Volume for tile in lid)
        self.assertLess(solid, plate.Volume * .85)

    def test_fillers_rest_on_the_power_floor(self):
        from integrated_rack_supports import integrated_supports
        from validate_fixed_rack import horizontal_contact
        supports, _ = integrated_supports(self.scene, self.p)
        floor = [i['shape'] for i in supports if i['name'].startswith('power_floor_')]
        for name in ('lower_filler_left', 'lower_filler_right'):
            filler = self.by_name[name]
            self.assertGreater(sum(horizontal_contact(tile, filler, 32) for tile in floor), 300)
            self.assertLess(sum(tile.common(filler).Volume for tile in floor), 1e-5)

    def test_removable_cover_screws_are_recorded(self):
        screws = [f for f in self.metadata['fastener_candidates'] if f['assembly'] == 'bay_cover']
        self.assertEqual(len(screws), 6)
        self.assertTrue(all(f['removable'] for f in screws))


if __name__ == '__main__':
    unittest.main()
