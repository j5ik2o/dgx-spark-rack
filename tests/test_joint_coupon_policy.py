"""不採用案の生成を止め、未測定値を製造穴へ使わないことを確認する。"""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'models/spark-rack/source'))
from rack_candidate_datums import DATUMS, controller_box, require_spark_mount_measurements, require_switch_measurements
from build_four_node_structure import build as rejected_build
from four_node_layout import LayoutParameters, evaluate


class JointPolicyTest(unittest.TestCase):
    def test_rejected_full_frame_is_not_default_build(self):
        with self.assertRaisesRegex(ValueError, '不採用'):
            rejected_build()

    def test_unknown_mount_points_are_blocked(self):
        with self.assertRaisesRegex(ValueError, '実測前'):
            require_spark_mount_measurements({'spark': {'adopted_pair_offset_mm': None}})
        values = {'port_centers_from_left_and_bottom_mm': [[90, 25], [110, 25]],
                  'feet_contact_areas_mm': [[5, 5, 10, 10]], 'adopted_pair_offset_mm': 0}
        self.assertEqual(require_spark_mount_measurements({'spark': values})['adopted_pair_offset_mm'], 0)

    def test_switch_ear_width_cannot_be_ignored(self):
        values = {'overall_width_with_ears_mm': 482.6, 'adopted_depth_mm': 268,
                  'mass_kg': 3, 'support_interface': '測定済み支持面'}
        with self.assertRaisesRegex(ValueError, '456mm'):
            require_switch_measurements({'switches': {'crs812': values}}, 'crs812')
        values['overall_width_with_ears_mm'] = 443
        self.assertEqual(require_switch_measurements({'switches': {'crs812': values}}, 'crs812')['adopted_depth_mm'], 268)

    def test_one_height_and_controller_reference(self):
        report = evaluate()
        self.assertEqual(report['parameters']['lower_base'], DATUMS.lower_base)
        for name, node in report['nodes'].items():
            expected = controller_box(name, node['origin'][2] + 25.25)
            actual = next(item for item in report['controllers'] if item['name'] == expected['name'])
            self.assertEqual(actual['origin'], expected['origin'])
        self.assertFalse(report['mount_holes_committed'])


if __name__ == '__main__':
    unittest.main()
