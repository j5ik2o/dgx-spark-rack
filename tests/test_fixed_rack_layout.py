"""固定段、独立電源区画、交換空間の退行を検査する。"""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'models/spark-rack/source'))
from fixed_rack_layout import fixed_layout, check_fixed_layout
from spark_rack_parameters import FixedRackParameters


class FixedRackLayoutTests(unittest.TestCase):
    def test_same_node_and_fan_positions_in_both_phases(self):
        ring, final = fixed_layout('ring'), fixed_layout('crs812')
        self.assertEqual(ring['nodes'], final['nodes'])
        self.assertEqual(ring['fans'], final['fans'])
        self.assertEqual(ring['cross_beams'], final['cross_beams'])
        self.assertEqual(sorted(n['origin'][2] for n in ring['nodes']), [208, 208, 428, 428])
        self.assertIsNone(ring['switch'])
        self.assertEqual(final['switch']['size'], [443, 268, 44])
        for s in (ring, final):
            check_fixed_layout(s)
            self.assertEqual(sum(f['size_mm'] == 140 for f in s['fans']), 4)
            self.assertEqual(sum(f['size_mm'] == 120 for f in s['fans']), 2)
            self.assertEqual(len(s['power_trays']), 4)
            self.assertEqual(sum(i['kind'] == 'controller' for i in s['equipment']), 6)

    def test_old_vertical_separator_is_rejected_in_lower_intake(self):
        scene = deepcopy(fixed_layout())
        scene['separator']['origin'] = [-180, -230, 208]
        scene['separator']['size'] = [360, 2, 138]
        with self.assertRaisesRegex(ValueError, 'fixed_air_obstructions'):
            check_fixed_layout(scene)

    def test_storage_cannot_block_rear_exchange(self):
        scene = deepcopy(fixed_layout())
        scene['cable_storage_spaces'][0]['origin'][2] = 230
        with self.assertRaisesRegex(ValueError, 'rear_service_obstructions'):
            check_fixed_layout(scene)

    def test_installed_case_may_fit_while_service_path_does_not(self):
        scene = deepcopy(fixed_layout())
        obstacle = {'name': 'behind_node', 'label': '背面側の固定障害物',
                    'origin': [-140, 70, 220], 'size': [10, 10, 10], 'kind': 'obstacle'}
        scene['equipment'].append(obstacle)
        with self.assertRaisesRegex(ValueError, 'rear_service_obstructions'):
            check_fixed_layout(scene)

    def test_side_panel_laps_are_included_in_print_envelope(self):
        p = FixedRackParameters()
        p.validate()
        with self.assertRaisesRegex(ValueError, '造形範囲'):
            replace(p, usable_print_size=240).validate()
        with self.assertRaisesRegex(ValueError, '下段ファン'):
            replace(p, power_ceiling_z=166).validate()

    def test_installation_space_is_larger_than_the_frame(self):
        s = fixed_layout()
        self.assertEqual(s['frame_outer_mm'], [544, 460, 560])
        self.assertEqual(s['installation_depth_to_rear_clearance_mm'], 750)
        self.assertGreater(s['installation_depth_to_rear_clearance_mm'], s['frame_outer_mm'][1])
        self.assertFalse(s['manufacturing_geometry'])


if __name__ == '__main__':
    unittest.main()
