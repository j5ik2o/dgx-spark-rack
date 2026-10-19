"""曲げの成立条件、必要配線の欠落、未採寸値の誤った合格扱いを拒否する。"""
from pathlib import Path
import math
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'models/spark-rack/source'))
from body_frame_cables import rounded_path, validate_routing
from body_frame_layout import layout


class CableRoutingTests(unittest.TestCase):
    def setUp(self):
        self.scene = layout()

    def test_short_segments_cannot_hide_a_too_tight_bend(self):
        with self.assertRaisesRegex(ValueError, '短過ぎ'):
            rounded_path([[0, 0, 0], [0, 40, 0], [100, 40, 0]], 42)

    def test_arc_is_tangent_and_preserves_requested_radius(self):
        segments, length = rounded_path([[0, 0, 0], [0, 60, 0], [60, 60, 0]], 42)
        arc = next(s for s in segments if s['type'] == 'arc')
        for key in ('start', 'middle', 'end'):
            self.assertAlmostEqual(math.dist(arc[key], arc['center']), 42)
        self.assertAlmostEqual(length, 36 + math.pi * 42 / 2)

    def test_network_bend_below_reference_limit_is_rejected(self):
        path = next(r for r in self.scene['cable_management']['paths'] if r['family'] == 'network')
        path['radius_mm'] = 30
        path['segments'], path['centerline_length_mm'] = rounded_path(path['points'], 30)
        with self.assertRaisesRegex(ValueError, '42mm'):
            validate_routing(self.scene)

    def test_missing_branch_cannot_pass(self):
        self.scene['cable_management']['paths'] = [p for p in self.scene['cable_management']['paths']
                                                    if p['name'] != 'network_branch_1_0']
        with self.assertRaisesRegex(ValueError, '欠け'):
            validate_routing(self.scene)

    def test_nominal_two_metres_is_not_a_verified_branch_length(self):
        report = validate_routing(self.scene)
        self.assertEqual(report['nominal_length_fit'], '未判定')
        self.assertEqual(report['actual_ports_fit'], '未判定')
        self.scene['cable_management']['paths'][0]['length_fit_verified'] = True
        with self.assertRaisesRegex(ValueError, '未採寸'):
            validate_routing(self.scene)

    def test_controller_feed_and_storage_cannot_be_dropped_to_pass(self):
        paths = self.scene['cable_management']['paths']
        removed = paths.pop(next(i for i, p in enumerate(paths) if p['name'] == 'controller_supply_0_1'))
        with self.assertRaisesRegex(ValueError, '欠け'):
            validate_routing(self.scene)
        paths.append(removed)
        self.scene['cable_management']['storage'].pop()
        with self.assertRaisesRegex(ValueError, '余長予約'):
            validate_routing(self.scene)

    def test_stale_arc_record_is_rejected(self):
        self.scene['cable_management']['paths'][0]['points'][0][1] += 1
        with self.assertRaisesRegex(ValueError, '実経路'):
            validate_routing(self.scene)


if __name__ == '__main__':
    unittest.main()
