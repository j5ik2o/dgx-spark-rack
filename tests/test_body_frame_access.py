"""栓だけ通っても指が途中でぶつかる場合と、指を離せない場合を検出する。"""
from pathlib import Path
import sys
import unittest

try:
    import FreeCAD as App
    import Part
except ImportError:
    App = None

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'models/spark-rack/source'))


@unittest.skipIf(App is None, 'FreeCAD同梱Pythonで実行してください')
class FingerAccessTests(unittest.TestCase):
    def make_grip(self, offset=0):
        from body_frame_access import key_grip
        return key_grip([0, 0, 20], 0, 1, 1, 0, 1.8, offset)

    def test_key_passes_but_fingers_hit_between_clear_endpoints(self):
        from body_frame_assembly import MotionCheck
        from body_frame_access import grip_path
        shape, grip = self.make_grip()
        obstacle = Part.makeBox(4, 1, 2, App.Vector(-2, 22, 34))
        items = {'key':dict(shape=shape), 'obstacle':dict(shape=obstacle)}
        path = [[0, 40, 0], [0, 0, 0]]
        self.assertIsNone(MotionCheck(items).path({'key'}, {'obstacle'}, path))
        self.assertFalse(grip_path(items, 'key', grip, {'obstacle'}, path))

    def test_fingers_must_also_leave_after_key_is_seated(self):
        from body_frame_access import grip_path
        shape, grip = self.make_grip()
        obstacle = Part.makeBox(4, 1, 2, App.Vector(-2, 22, 34))
        items = {'key':dict(shape=shape), 'obstacle':dict(shape=obstacle)}
        self.assertFalse(grip_path(items, 'key', grip, {'obstacle'}, [[0, 0, 40], [0, 0, 0]]))

    def test_offset_grip_moves_fingers_away_from_integral_guard(self):
        from body_frame_access import grip_path
        obstacle = Part.makeBox(3, 10, 3, App.Vector(4, 3, 34))
        for offset, expected in ((0, False), (-8, True)):
            shape, grip = self.make_grip(offset)
            items = {'key':dict(shape=shape), 'guard':dict(shape=obstacle)}
            self.assertEqual(grip_path(items, 'key', grip, {'guard'}, [[0, 40, 0], [0, 0, 0]]), expected)

    def test_finger_boxes_never_fill_the_tab_itself_on_any_axis(self):
        from body_frame_access import key_grip, finger_shape
        for axis in range(3):
            for normal in (i for i in range(3) if i != axis):
                for sign in (-1, 1):
                    for offset in (0, -8, 8):
                        shape, grip = key_grip([20, 20, 20], 20, axis, sign, normal, 1.8, offset)
                        self.assertTrue(shape.isValid())
                        self.assertEqual(len(shape.Solids), 1)
                        self.assertLess(shape.common(finger_shape(grip)).Volume, 1e-5)

    def test_missing_fan_blades_cannot_create_false_finger_access(self):
        from body_frame_access import grip_path, fan_key_path
        shape, grip = self.make_grip()
        fan = Part.makeBox(40, 2, 50, App.Vector(-20, 20, 0)).cut(
            Part.makeBox(38, 4, 48, App.Vector(-19, 19, 1)))
        items = {'key':dict(shape=shape, grip=grip, kind='joint_key'),
                 'fan':dict(shape=fan, kind='fan')}
        self.assertTrue(grip_path(items, 'key', grip, {'fan'}, [[0,0,0],[0,12,0]]))
        self.assertFalse(fan_key_path(items, 'key'))


if __name__ == '__main__':
    unittest.main()
