"""設定できる寸法が試験片の形状と受け面の検査に反映されることを確認する。"""
from pathlib import Path
import sys
import unittest

try:
    import FreeCAD
except ImportError:
    FreeCAD = None

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'models/spark-rack/source'))


@unittest.skipIf(FreeCAD is None, 'FreeCAD同梱Pythonで実行してください')
class JointCouponGeometryTest(unittest.TestCase):
    def test_changed_fork_floor_has_matching_bearing_validation(self):
        from freecad_spark_rack_joint_coupons import CouponParameters, parts, corner_assembly
        from validate_spark_rack_joint_coupons import verify
        parameters = CouponParameters(fork_floor=6, stub_length=45)
        shapes = parts(parameters)
        validation = verify(shapes, corner_assembly(shapes), fork_floor=parameters.fork_floor)
        self.assertEqual(validation['status'], 'passed')
        self.assertAlmostEqual(validation['bearing_contact']['straight_bearing_mm2'], 288)
        self.assertAlmostEqual(shapes['beam_fork'].BoundBox.XMin, -45)

    def test_fixed_joint_dimensions_are_not_editable_settings(self):
        from freecad_spark_rack_joint_coupons import CouponParameters
        with self.assertRaises(TypeError):
            CouponParameters(root_depth=9)


if __name__ == '__main__':
    unittest.main()
