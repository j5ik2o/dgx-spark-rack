"""配線長の検討で誤って到達可能と扱わないための幾何検査。"""
from dataclasses import replace
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'models/spark-rack/source'))
from four_node_layout import LayoutParameters, evaluate, route


class FourNodeLayoutTest(unittest.TestCase):
    def test_arc_length_and_endpoints(self):
        p = LayoutParameters()
        result = route((0, 0, 0), (200, 0, 0), p)
        expected = 200 + 2 * p.straight_lead + (math.pi - 2) * p.bend_radius
        self.assertAlmostEqual(result['route_length_mm'], expected)
        self.assertEqual(result['points'][0], [0, 0, 0])
        self.assertEqual(result['points'][-1], [200, 0, 0])
        # 表示折線は円弧に内接するため、解析長よりわずかに短い。
        polygon_length = sum(math.dist(a, b) for a, b in zip(result['points'], result['points'][1:]))
        self.assertLess(polygon_length, expected)
        self.assertLess(expected - polygon_length, 0.1)

    def test_depth_offset_adds_to_route(self):
        p = LayoutParameters()
        flat = route((0, 0, 0), (200, 0, 0), p)
        recessed = route((0, 0, 0), (200, -40, 0), p)
        self.assertAlmostEqual(recessed['route_length_mm'] - flat['route_length_mm'], 40)

    def test_radius_not_silently_reduced(self):
        self.assertEqual(route((0, 0, 0), (30, 0, 0), LayoutParameters())['screening'], 'needs_reroute')

    def test_recommended_layout_for_both_switches(self):
        for key in ('crs812', 'crs804'):
            report = evaluate(switch_key=key)
            self.assertEqual(len(report['nodes']), 4)
            self.assertEqual(len(report['ring_cables']), 4)
            self.assertEqual(len(report['switch_cables']), 4)
            self.assertEqual(len({c['switch_port'] for c in report['switch_cables']}), 4)
            self.assertFalse(report['checks']['equipment_and_shelf_collisions'])
            self.assertFalse(report['checks']['outside_envelope'])
            self.assertFalse(report['checks']['rear_space_overflow'])
            for cable in report['ring_cables'] + report['switch_cables']:
                self.assertGreaterEqual(cable['margin_mm'], 0)
                self.assertAlmostEqual(cable['required_length_mm'] - cable['route_length_mm'], 70)
            used = [(c[side], tuple(c[end])) for c in report['ring_cables'] for side, end in [('from', 'start'), ('to', 'end')]]
            self.assertEqual(len(set(used)), 8)
            self.assertIn('未検証', report['physical_validation'])

    def test_stricter_cable_can_fail_conservative_screen(self):
        baseline = replace(LayoutParameters(), cable_length=550)
        self.assertTrue(all(c['margin_mm'] >= 0 for c in evaluate(baseline)['switch_worst_cases']))
        report = evaluate(replace(baseline, straight_lead=50, bend_radius=30))
        self.assertTrue(any(c['margin_mm'] < 0 for c in report['switch_worst_cases']))

    def test_shifted_switch_reports_overlap(self):
        report = evaluate(replace(LayoutParameters(), switch_z_offset=-70))
        self.assertTrue(report['checks']['equipment_and_shelf_collisions'])

    def test_prepared_fans_and_controller_spaces(self):
        report = evaluate()
        self.assertEqual([fan['size_mm'] for fan in report['fans']], [140, 140, 140, 140])
        self.assertEqual(report['adapter_cooling']['fan_size_mm'], 120)
        self.assertEqual(report['adapter_cooling']['fan_count'], 2)
        self.assertEqual(len(report['fan_holders']), 4)
        self.assertEqual(len(report['fan_guards']), 4)
        self.assertEqual(len(report['controllers']), 4)
        report_without_fans = evaluate(replace(LayoutParameters(), include_fans=False))
        self.assertEqual(report_without_fans['fans'], [])
        self.assertEqual(report_without_fans['controllers'], [])

    def test_old_pitch_causes_fan_holder_collision(self):
        report = evaluate(replace(LayoutParameters(), row_pitch=180))
        self.assertTrue(report['checks']['equipment_and_shelf_collisions'])

    def test_compact_ring_keeps_fans_and_more_cable_margin(self):
        compact = evaluate(replace(LayoutParameters(), row_pitch=160), include_switch=False)
        self.assertFalse(compact['checks']['equipment_and_shelf_collisions'])
        self.assertFalse(compact['checks']['outside_envelope'])
        self.assertEqual(len(compact['fans']), 4)
        self.assertNotIn('switch_shelf', [s['name'] for s in compact['shelves']])
        longest = max(c['required_length_mm'] for c in compact['ring_cables'])
        self.assertAlmostEqual(longest, 312.8318530717959)
        stricter = evaluate(replace(LayoutParameters(), row_pitch=160, straight_lead=50,
                           bend_radius=30), include_switch=False)
        self.assertTrue(all(c['margin_mm'] > 0 for c in stricter['ring_cables']))

    def test_invalid_values_rejected(self):
        for changes in ({'bend_radius': 0}, {'column_pitch': math.nan}, {'service_slack': -1}):
            with self.assertRaises(ValueError):
                evaluate(replace(LayoutParameters(), **changes))


if __name__ == '__main__':
    unittest.main()
