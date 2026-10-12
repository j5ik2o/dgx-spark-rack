"""専用段の高さ、既存機器の予約、未実測条件を比較から落とさない。"""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'models/spark-rack/source'))
from switch_placement_comparison import comparison, check_candidate
from spark_rack_parameters import SwitchPlacementComparisonParameters


class SwitchPlacementComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = comparison()
        cls.cases = {c['key']: c for c in cls.report['cases']}

    def test_upper_adds_a_dedicated_bay_without_moving_the_spark_or_power(self):
        upper, central = self.cases['upper'], self.cases['central']
        self.assertEqual(upper['metrics']['frame_size_mm'], [544, 460, 668])
        self.assertEqual(upper['metrics']['spark_bottoms_from_new_base_mm'], [208, 428])
        self.assertEqual(upper['common_objects'], central['common_objects'])
        self.assertEqual(upper['checks']['status'], 'passed')

    def test_lower_gap_is_rejected_by_support_and_exchange_geometry(self):
        lower = self.cases['lower_gap']
        self.assertEqual(self.report['lower_available_height_mm'], 32)
        self.assertEqual(self.report['lower_height_shortfall_before_support_mm'], 12)
        self.assertIn(['switch', 'node_support_0'], lower['checks']['new_object_collisions'])
        self.assertTrue(lower['checks']['exchange_obstructions'])
        self.assertEqual(lower['checks']['status'], 'rejected')

    def test_lower_extension_changes_height_from_new_base_instead_of_claiming_fixed_levels(self):
        lower = self.cases['lower_extension']
        self.assertEqual(lower['checks']['status'], 'passed')
        self.assertFalse(lower['metrics']['spark_bottoms_preserved'])
        self.assertEqual(lower['metrics']['spark_bottoms_from_new_base_mm'], [316, 536])
        self.assertEqual(lower['metrics']['frame_size_mm'][2], 668)

    def test_fan_and_power_exchange_details_are_not_invented(self):
        self.assertFalse(self.report['physical_validation'])
        self.assertFalse(self.report['manufacturing_geometry'])
        for case in self.cases.values():
            self.assertIsNone(case['metrics']['mass_kg'])
            self.assertFalse(case['checks']['cooling_verified'])
            self.assertFalse(case['metrics']['cable_routing_verified'])
            self.assertFalse(case['endpoint_distance_bounds']['routing_validated'])
        self.assertEqual(self.report['network']['physical_cable_count'], 2)
        self.assertEqual(self.report['network']['routing_minimum_bend_radius_mm'], 42)

    def test_a_back_obstacle_is_rejected_even_if_it_does_not_touch_the_installed_switch(self):
        case = deepcopy(self.cases['upper'])
        case['objects'].append({'name': 'back_obstacle', 'label': '交換方向の障害物',
                                'origin': [-100, 120, 600], 'size': [10, 10, 10], 'kind': 'obstacle'})
        self.assertIn(['switch_removal', 'back_obstacle'], check_candidate(case)['exchange_obstructions'])

    def test_an_air_obstruction_is_rejected(self):
        case = deepcopy(self.cases['upper'])
        case['new_objects'].append({'name': 'air_obstacle', 'label': '本体排気の障害物',
                                   'origin': [-100, 100, 450], 'size': [10, 10, 10], 'kind': 'obstacle'})
        self.assertTrue(check_candidate(case)['spark_air_reservation_obstructions'])

    def test_extra_hand_space_changes_total_height_and_does_not_vanish_from_the_report(self):
        report = comparison(q=replace(SwitchPlacementComparisonParameters(), upper_hand_margin=24))
        upper = next(c for c in report['cases'] if c['key'] == 'upper')
        self.assertEqual(upper['metrics']['frame_size_mm'][2], 680)
        self.assertEqual(upper['switch_service']['size'][2], 76)
        self.assertEqual(upper['checks']['status'], 'passed')

    def test_invalid_dimensions_are_rejected(self):
        with self.assertRaises(ValueError):
            comparison(q=replace(SwitchPlacementComparisonParameters(), support_plate_thickness=-1))


if __name__ == '__main__':
    unittest.main()
