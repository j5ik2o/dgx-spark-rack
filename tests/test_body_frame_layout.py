"""維持する機器、2段×2列、斜め取付の拒否を検査する。"""
from dataclasses import replace
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

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

    def test_integral_float_fan_dimensions_keep_the_same_inventory(self):
        scene=layout(replace(BodyFrameParameters(),fan_size=140.0,power_fan_size=120.0))
        self.assertEqual(validate_layout(scene)['inventory'],validate_layout(self.scene)['inventory'])

    def test_fractional_fan_dimensions_do_not_round_to_a_supported_size(self):
        with self.assertRaisesRegex(ValueError,'個数'):
            validate_layout(layout(replace(BodyFrameParameters(),fan_size=140.5)))

    def assert_requirement_change_rejected(self,change):
        import body_frame_layout
        data=json.loads((body_frame_layout.ROOT/body_frame_layout.REQUIREMENTS).read_text())
        change(data)
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'requirements.json'
            path.write_text(json.dumps(data))
            with patch.object(body_frame_layout,'REQUIREMENTS',str(path)):
                with self.assertRaisesRegex(ValueError,'設計条件'):
                    validate_layout(layout())

    def test_changed_row_requirement_is_not_ignored(self):
        self.assert_requirement_change_rejected(lambda d:d.update(spark_rows=3))

    def test_changed_equipment_requirement_is_not_ignored(self):
        self.assert_requirement_change_rejected(lambda d:d.update(maintained_equipment=[]))

    def test_changed_fastener_requirement_is_not_ignored(self):
        self.assert_requirement_change_rejected(lambda d:d['assembly_fasteners'].update(screws=1))

    def test_changed_model_requirement_is_not_ignored(self):
        self.assert_requirement_change_rejected(lambda d:d['maintained_equipment'][0].update(model='別の本体'))

    def test_changed_fan_mounting_requirement_is_not_ignored(self):
        self.assert_requirement_change_rejected(lambda d:d['fan_mounting'].update(mode='hinged_open'))


if __name__ == '__main__':
    unittest.main()
