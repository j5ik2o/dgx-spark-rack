"""前面と天面の板の配置、外せる板と扉の開く範囲の扱いを検査する。"""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'models/spark-rack/source'))
from fixed_rack_layout import check_fixed_layout, fixed_layout
from upper_switch_bay import upper_scene


class RackFinishTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p, cls.bay, cls.acc, cls.scene = upper_scene()
        cls.finish = cls.scene['finish']
        cls.by_name = {b['name']: b for b in cls.finish['objects']}

    def test_lid_raises_the_overall_height_by_its_thickness(self):
        self.assertEqual(self.finish['overall_height_mm'], 622)
        self.assertEqual(self.scene['frame_outer_mm'], [544, 460, 622])
        scene = deepcopy(self.scene)
        scene['finish']['overall_height_mm'] = self.p.height
        with self.assertRaisesRegex(ValueError, "'outside_frame': \\['top_lid'"):
            check_fixed_layout(scene)

    def test_bay_covers_fill_the_front_between_the_fans_and_the_top_frame(self):
        z0, z1 = self.finish['cover_z']
        upper_top = max(c['origin'][2] + c['size'][2] for c in self.scene['carriers'] if c['name'].startswith('upper_'))
        self.assertGreater(z0, upper_top)
        self.assertEqual(z1, self.p.height - self.p.section)
        widths = [self.by_name[n]['size'][0] for n in self.finish['removable_covers']]
        self.assertEqual(widths, [184, 120, 184])

    def test_removable_covers_do_not_block_the_switch_front_service_but_fixed_ones_would(self):
        result = check_fixed_layout(self.scene)
        self.assertEqual(result['conditional_front_service'][0]['obstructions'], [])
        scene = deepcopy(self.scene)
        for b in scene['finish']['objects']:
            if b['name'] == 'bay_cover_center':
                b['kind'] = 'fixed_cover'
        with self.assertRaisesRegex(ValueError, 'bay_cover_center'):
            check_fixed_layout(scene)

    def test_lower_fillers_stay_behind_the_door_sweep(self):
        door = self.scene['control_panel']
        for name in ('lower_filler_left', 'lower_filler_right'):
            filler = self.by_name[name]
            self.assertGreater(filler['origin'][1], door['origin'][1] + door['size'][1])
        self.assertAlmostEqual(self.finish['filler_recess_mm'], 49.97, places=2)
        scene = deepcopy(self.scene)
        for b in scene['finish']['objects']:
            if b['name'] == 'lower_filler_left':
                b['origin'][1] = self.p.front_face_y
        with self.assertRaisesRegex(ValueError, "'control_door_sweep_obstructions': \\['lower_filler_left'\\]"):
            check_fixed_layout(scene)

    def test_finish_needs_the_bay_and_shelf_and_leaves_the_default_alone(self):
        default = fixed_layout('crs812')
        self.assertNotIn('finish', default)
        self.assertEqual(default['frame_outer_mm'], [544, 460, 560])
        with self.assertRaisesRegex(ValueError, '前面と天面の板'):
            fixed_layout('crs812', self.p, self.bay, None, self.finish)

    def test_declined_alternatives_are_recorded(self):
        notes = self.finish['notes']
        self.assertIn('外せる', notes['bay_cover'])
        self.assertEqual(len(notes['declined']), 3)
        self.assertFalse(self.finish['physical_validation'])


if __name__ == '__main__':
    unittest.main()
