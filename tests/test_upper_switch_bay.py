"""上部専用段の高さ、予約、前側の作業空間の条件を、中央の既定案と混同せずに検査する。"""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'models/spark-rack/source'))
from fixed_rack_layout import check_fixed_layout, fixed_layout
from spark_rack_parameters import FixedRackParameters, UpperSwitchBayParameters
from upper_switch_bay import bay_layout, rack_parameters, variants


class UpperSwitchBayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = variants()
        cls.rows = {r['key']: r for r in cls.report['rows']}
        cls.p = rack_parameters()
        cls.bay = bay_layout(cls.p)
        cls.scene = fixed_layout('crs812', cls.p, cls.bay)

    def test_shared_top_frame_is_lower_than_stacking_and_keeps_spark_levels(self):
        heights = {key: row['height_mm'] for key, row in self.rows.items()}
        self.assertEqual(heights, {'stacked': 668, 'integrated': 618, 'integrated_lowest': 599})
        self.assertEqual(self.report['recommendation'], 'integrated')
        self.assertEqual(self.rows['integrated']['height_saved_vs_stacked_mm'], 50)
        for row in self.rows.values():
            self.assertEqual(row['spark_bottoms_mm'], [208, 428])
            self.assertEqual(row['layout_checks'], 'passed')

    def test_lowest_floor_blocks_the_front_service_path_over_the_upper_fans(self):
        self.assertEqual(self.rows['integrated']['front_service'], 'passed')
        self.assertEqual(self.rows['stacked']['front_service'], 'passed')
        lowest = self.rows['integrated_lowest']
        self.assertEqual(lowest['front_service'], 'blocked')
        self.assertIn('upper_left_carrier', lowest['front_service_obstructions'])
        self.assertEqual(lowest['binding_constraint'], 'upper_spark_rear_exchange')
        self.assertEqual(self.rows['integrated']['binding_constraint'], 'switch_front_service_over_fan_carriers')

    def test_floor_sits_behind_the_fans_and_above_the_upper_spark_exchange(self):
        p, bay = self.p, self.bay
        self.assertGreater(bay['floor_front_y'], p.fan_front_y + p.fan_depth)
        self.assertGreater(bay['floor_z'], p.upper_base + p.spark_height + p.hand_margin)
        carrier_top = max(c['origin'][2] + c['size'][2] for c in self.scene['carriers'])
        self.assertGreaterEqual(bay['switch_z'], carrier_top + UpperSwitchBayParameters().front_service_clearance)
        self.assertEqual(self.scene['switch']['origin'][2], bay['switch_z'])
        self.assertEqual(self.scene['frame_outer_mm'], [544, 460, 618])
        top = [b for b in self.scene['cross_beams'] if b['name'].startswith('frame_top_')]
        self.assertTrue(all(b['origin'][2] + b['size'][2] == 618 for b in top))

    def test_central_default_is_unchanged(self):
        default = fixed_layout('crs812')
        self.assertEqual(default['frame_outer_mm'], [544, 460, 560])
        self.assertNotIn('switch_bay', default)
        self.assertIn('switch_rail_front', [b['name'] for b in default['cross_beams']])
        self.assertNotIn('switch_rail_front', [b['name'] for b in self.scene['cross_beams']])
        self.assertEqual(default['nodes'], self.scene['nodes'])
        self.assertEqual(default['fans'], self.scene['fans'])

    def test_bay_needs_the_raised_frame(self):
        with self.assertRaisesRegex(ValueError, '全高'):
            fixed_layout('crs812', FixedRackParameters(), self.bay)

    def test_rear_removal_rejects_a_fixed_obstacle_but_moves_the_trays(self):
        check_fixed_layout(self.scene)
        scene = deepcopy(self.scene)
        scene['switch_bay']['objects'].append({'name': 'rear_obstacle', 'label': '背面の障害物',
                                               'origin': [-50, 102, 560], 'size': [6, 6, 6], 'kind': 'bay_floor'})
        with self.assertRaisesRegex(ValueError, "'switch_removal', 'rear_obstacle'"):
            check_fixed_layout(scene)

    def test_required_front_service_rejects_an_obstacle(self):
        scene = deepcopy(self.scene)
        scene['switch_bay']['objects'].append({'name': 'front_obstacle', 'label': '前側の障害物',
                                               'origin': [-50, -300, 550], 'size': [10, 10, 10], 'kind': 'bay_floor'})
        with self.assertRaisesRegex(ValueError, r"'obstructions': \['front_obstacle'\]"):
            check_fixed_layout(scene)

    def test_unmeasured_switch_values_are_not_invented(self):
        self.assertFalse(self.report['physical_validation'])
        self.assertFalse(self.report['manufacturing_geometry'])
        self.assertIn('スイッチの電源とファンがどちらの面にあるか', self.report['decision_dependencies'])
        self.assertIn('未確認', self.bay['front_service_dependency'])
        self.assertFalse(self.bay['physical_validation'])

    def test_extra_hand_space_raises_the_frame(self):
        p = rack_parameters(replace(UpperSwitchBayParameters(), upper_hand_margin=24))
        self.assertEqual(p.height, 630)

    def test_changed_hand_space_applies_to_all_three_variants(self):
        report = variants(replace(UpperSwitchBayParameters(), upper_hand_margin=24))
        heights = {row['key']: row['height_mm'] for row in report['rows']}
        self.assertEqual(heights, {'stacked': 680, 'integrated': 630, 'integrated_lowest': 611})

    def test_invalid_dimensions_are_rejected(self):
        with self.assertRaises(ValueError):
            rack_parameters(replace(UpperSwitchBayParameters(), tray_thickness=0))


if __name__ == '__main__':
    unittest.main()
