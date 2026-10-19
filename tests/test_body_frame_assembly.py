"""移動の両端だけでは見つからない途中の干渉と、方向転換を検査する。"""
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
class AssemblyMotionTests(unittest.TestCase):
    def test_swept_volume_detects_an_obstacle_between_clear_endpoints(self):
        from body_frame_assembly import MotionCheck
        moving = Part.makeBox(1, 1, 1)
        obstacle = Part.makeBox(.2, 1, 1, App.Vector(2.2, 0, 0))
        check = MotionCheck({'moving':{'shape':moving},'obstacle':{'shape':obstacle}})
        self.assertEqual(check.path({'moving'},{'obstacle'},[[0,0,0],[5,0,0]]),['moving','obstacle'])

    def test_negative_insertion_also_checks_between_endpoints(self):
        from body_frame_assembly import MotionCheck
        moving=Part.makeBox(1,1,1,App.Vector(5,0,0))
        obstacle=Part.makeBox(.2,1,1,App.Vector(2.2,0,0))
        check=MotionCheck({'moving':{'shape':moving},'obstacle':{'shape':obstacle}})
        self.assertEqual(check.path({'moving'},{'obstacle'},[[0,0,0],[-5,0,0]]),['moving','obstacle'])

    def test_axial_cylinder_does_not_fill_empty_corners_of_its_box(self):
        from body_frame_assembly import MotionCheck
        cylinder = Part.makeCylinder(1, 2, App.Vector(0,0,0), App.Vector(1,0,0))
        obstacle = Part.makeBox(1, .1, .1, App.Vector(3, .85, .85))
        check = MotionCheck({'moving':{'shape':cylinder},'obstacle':{'shape':obstacle}})
        self.assertIsNone(check.path({'moving'},{'obstacle'},[[0,0,0],[5,0,0]]))

    def test_key_can_turn_after_clearing_its_socket(self):
        from body_frame_assembly import MotionCheck, escape
        items = {'key':{'shape':Part.makeBox(2,2,2)},
                 'obstacle':{'shape':Part.makeBox(2,2,2,App.Vector(20,0,0))}}
        check = MotionCheck(items)
        path = escape(check, {'key'}, {'obstacle'}, [1,0,0], 3)
        self.assertIsNotNone(path)
        self.assertEqual(path[1],[3,0,0])
        self.assertGreater(path[2][2],0)
        self.assertIsNone(check.path({'key'},{'obstacle'},path))

    def test_diagonal_pose_is_not_a_straight_insertion(self):
        from body_frame_assembly import MotionCheck
        check = MotionCheck({'part':{'shape':Part.makeBox(1,1,1)}})
        with self.assertRaisesRegex(ValueError,'1軸'):
            check.path({'part'},set(),[[0,0,0],[1,1,0]])

    def test_rounded_hole_keeps_its_center_open_during_axial_motion(self):
        from body_frame_assembly import MotionCheck
        ring=Part.makeTorus(4.4,.4,App.Vector(),App.Vector(1,0,0))
        knob=Part.makeCylinder(3.5,6,App.Vector(-1,0,0),App.Vector(1,0,0))
        check=MotionCheck({'ring':{'shape':ring},'knob':{'shape':knob}})
        self.assertIsNone(check.path({'ring'},{'knob'},[[0,0,0],[3,0,0]]))

    def test_rounded_rim_still_catches_an_obstacle_between_endpoints(self):
        from body_frame_assembly import MotionCheck
        ring=Part.makeTorus(4.4,.4,App.Vector(),App.Vector(1,0,0))
        obstacle=Part.makeBox(.2,.2,.2,App.Vector(1.5,4.3,-.1))
        check=MotionCheck({'ring':{'shape':ring},'obstacle':{'shape':obstacle}})
        self.assertEqual(check.path({'ring'},{'obstacle'},[[0,0,0],[3,0,0]]),['ring','obstacle'])

    def test_planar_faces_after_a_rounded_rim_keep_the_full_negative_motion(self):
        from body_frame_assembly import MotionCheck
        ring=Part.makeTorus(4.4,.4,App.Vector(5,0,0),App.Vector(1,0,0))
        tab=Part.makeBox(1,1,1,App.Vector(5,8,0))
        moving=Part.makeCompound([ring,tab])
        obstacle=Part.makeBox(.2,.2,.2,App.Vector(.5,8.2,.2))
        self.assertEqual(moving.common(obstacle).Volume,0)
        end=moving.copy()
        end.translate(App.Vector(-10,0,0))
        self.assertEqual(end.common(obstacle).Volume,0)
        check=MotionCheck({'moving':{'shape':moving},'obstacle':{'shape':obstacle}})
        self.assertEqual(check.path({'moving'},{'obstacle'},[[0,0,0],[-10,0,0]]),['moving','obstacle'])


if __name__ == '__main__':
    unittest.main()
