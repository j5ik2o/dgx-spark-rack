"""支持禁止面と、他の支持材が途中を塞ぐ除去順を検査する。"""
from pathlib import Path
import sys
import unittest

try:
    import FreeCAD as App
    import Part
except ImportError:
    App = None

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'models/spark-rack/source'))


@unittest.skipIf(App is None,'FreeCAD同梱Pythonで実行してください')
class SupportRemovalTests(unittest.TestCase):
    def channel(self):
        return Part.makeBox(30,4,12).fuse(Part.makeBox(30,4,12,App.Vector(0,16,0))).fuse(
            Part.makeBox(4,20,12)).fuse(Part.makeBox(30,20,2,App.Vector(0,0,-2))).fuse(
            Part.makeBox(30,20,2,App.Vector(0,0,12)))

    def regions(self):
        return [dict(name='a_inner',shape=Part.makeBox(7,6,10,App.Vector(8,7,0))),
                dict(name='b_outer',shape=Part.makeBox(7,6,10,App.Vector(20,7,0)))]

    def test_remove_outer_region_before_reaching_the_inner_region(self):
        from body_frame_support_removal import removal_plan,validate_removal
        shape,regions=self.channel(),self.regions()
        steps,blocked=removal_plan(shape,regions)
        self.assertEqual(blocked,[])
        self.assertEqual([s['region'] for s in steps],['b_outer','a_inner'])
        validate_removal(shape,regions,steps)

    def test_reversing_the_removal_order_does_not_pass(self):
        from body_frame_support_removal import removal_plan,validate_removal
        shape,regions=self.channel(),self.regions()
        steps,_=removal_plan(shape,regions)
        with self.assertRaisesRegex(ValueError,'除去経路'):
            validate_removal(shape,regions,list(reversed(steps)))

    def test_closed_cavity_cannot_be_called_removable(self):
        from body_frame_support_removal import removal_plan
        shell=Part.makeBox(20,20,20).cut(Part.makeBox(12,12,12,App.Vector(4,4,4)))
        regions=[dict(name='trapped',shape=Part.makeBox(6,6,6,App.Vector(7,7,7)))]
        steps,blocked=removal_plan(shell,regions)
        self.assertEqual(steps,[])
        self.assertEqual(blocked,['trapped'])

    def test_a_short_motion_inside_the_part_is_not_removal(self):
        from body_frame_support_removal import removal_plan,validate_removal
        shape,regions=self.channel(),self.regions()
        steps,_=removal_plan(shape,regions)
        steps[0]=dict(steps[0],offsets_mm=[[0,0,0],[.1,0,0]])
        with self.assertRaisesRegex(ValueError,'外まで'):
            validate_removal(shape,regions,steps)


@unittest.skipIf(App is None,'FreeCAD同梱Pythonで実行してください')
class SupportPlacementTests(unittest.TestCase):
    def overhang(self):
        return Part.makeBox(4,20,20).fuse(Part.makeBox(20,20,4,App.Vector(0,0,20)))

    def test_open_non_precision_overhang_gets_accessible_regions(self):
        from body_frame_support_regions import planar_regions
        from body_frame_support_removal import removal_plan
        shape=self.overhang()
        regions,reviews=planar_regions(shape,[])
        self.assertTrue(regions)
        for region in regions:
            self.assertLess(region['shape'].common(shape).Volume,1e-5)
        _,blocked=removal_plan(shape,regions)
        self.assertEqual(blocked,[])

    def test_precision_contact_face_is_not_used_for_support(self):
        from body_frame_support_regions import planar_regions
        guard=dict(name='fit',mode='contact',shape=Part.makeBox(18,22,2,App.Vector(3,-1,19)))
        regions,reviews=planar_regions(self.overhang(),[guard])
        self.assertEqual(regions,[])
        self.assertGreater(sum(r['protected'] for r in reviews),0)

    def test_a_keyway_cannot_be_filled_even_if_contacts_are_outside_it(self):
        from body_frame_support_regions import planar_regions
        shape=self.overhang()
        guard=dict(name='keyway',mode='volume',shape=Part.makeBox(18,22,1,App.Vector(3,-1,10)))
        regions,reviews=planar_regions(shape,[guard])
        self.assertEqual(regions,[])
        self.assertGreater(sum(r['protected'] for r in reviews),0)


if __name__=='__main__':
    unittest.main()
