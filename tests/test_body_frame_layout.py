"""維持する機器、2段×2列、斜め取付の拒否を検査する。"""
from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'models/spark-rack/source'))
from body_frame_layout import layout, validate_layout
from spark_rack_parameters import BodyFrameParameters


class BodyFrameLayoutTests(unittest.TestCase):
    def setUp(self):
        self.scene = layout()

    def test_equipment_is_retained_in_two_columns_of_two(self):
        report = validate_layout(self.scene)
        self.assertEqual(report['inventory'], dict(spark=4, switch=1, comet=1, kvm=1, power=4,
                                                   controller=6, fan_140=4, fan_120=2))
        sparks = [e for e in self.scene['equipment'] if e['kind'] == 'spark']
        self.assertEqual(len({e['origin'][0] for e in sparks}), 2)
        self.assertEqual(len({e['origin'][2] for e in sparks}), 2)
        self.assertFalse(self.scene['physical_validation'])
        self.assertFalse(self.scene['manufacturing_geometry'])

    def test_dropping_a_fan_cannot_make_the_layout_pass(self):
        self.scene['equipment'] = [e for e in self.scene['equipment'] if e['name'] != 'spark_fan_0_rear']
        with self.assertRaisesRegex(ValueError, '個数'):
            validate_layout(self.scene)

    def test_diagonal_fan_axes_are_rejected(self):
        fan = next(e for e in self.scene['equipment'] if e['kind'] == 'fan')
        fan['axis'] = [0.5, -0.5, 0]
        with self.assertRaisesRegex(ValueError, '斜め'):
            validate_layout(self.scene)

    def test_signed_but_wrong_mounting_face_is_rejected(self):
        fan = next(e for e in self.scene['equipment'] if e['name'] == 'spark_fan_0_front')
        fan['axis'] = [1, 0, 0]
        with self.assertRaisesRegex(ValueError, '取付面'):
            validate_layout(self.scene)

    def test_hinged_operating_pose_is_not_an_accepted_mount(self):
        fan = next(e for e in self.scene['equipment'] if e['kind'] == 'fan')
        fan['mounting'] = 'hinged_open'
        with self.assertRaisesRegex(ValueError, '正立固定'):
            validate_layout(self.scene)

    def test_component_collisions_are_not_ignored(self):
        spark = next(e for e in self.scene['equipment'] if e['kind'] == 'spark')
        kvm = next(e for e in self.scene['equipment'] if e['kind'] == 'kvm')
        kvm['origin'] = list(spark['origin'])
        with self.assertRaisesRegex(ValueError, '干渉'):
            validate_layout(self.scene)

    def test_rear_corners_leave_the_whole_rear_face_open(self):
        p = BodyFrameParameters()
        rear = [r for r in self.scene['corners'] if r['name'].endswith('_back')]
        for recipe in rear:
            for piece in recipe['pieces']:
                self.assertLessEqual(piece['origin'][1] + piece['size'][1], p.spark_depth)

    def test_rear_fan_cannot_be_moved_into_the_connector_reservation(self):
        with self.assertRaisesRegex(ValueError, '端子'):
            layout(replace(BodyFrameParameters(), rear_fan_gap=40))

    def test_assembly_cannot_add_a_screw_or_nut(self):
        for field in ('assembly_screws', 'assembly_nuts'):
            self.scene['screwless_requirement'][field] = 1
            with self.assertRaisesRegex(ValueError, 'ビス・ナットは0'):
                validate_layout(self.scene)
            self.scene['screwless_requirement'][field] = 0


if __name__ == '__main__':
    unittest.main()
