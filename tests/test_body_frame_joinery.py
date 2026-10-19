"""ほぞ・角栓の実形状と、ねじ穴を持たない制御器ケースを検査する。"""
from pathlib import Path
import runpy
import sys
import unittest

try:
    import FreeCAD as App
    import Part
except ImportError:
    App = None

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'models/spark-rack/source'))
sys.path.insert(0, str(ROOT/'tools/cad'))


@unittest.skipIf(App is None, 'FreeCAD同梱Pythonで実行してください')
class JoineryTests(unittest.TestCase):
    def setUp(self):
        from body_frame_geometry import block, item
        from body_frame_joinery import design_joint
        a = item('left', '左', block([-20, -8, 10], [20, 16, 10]), 'support')
        b = item('right', '右', block([0, -8, 10], [20, 16, 10]), 'support')
        self.joint = design_joint(a, b, [a, b], 0)
        self.assertIsNotNone(self.joint)

    def test_tenon_and_socket_have_shoulders_without_overlap(self):
        from validate_body_frame import shared_area
        _, _, male, female, key, _ = self.joint
        self.assertLess(male.common(female).Volume, 1e-5)
        self.assertGreater(shared_area(male, female), 2)
        self.assertLess(key['shape'].common(male).Volume, 1e-5)
        self.assertLess(key['shape'].common(female).Volume, 1e-5)

    def test_inserted_square_key_blocks_withdrawal(self):
        _, _, male, _, key, record = self.joint
        shifted = male.copy()
        shifted.translate(App.Vector(*[-.5*n for n in record['insertion_axis']]))
        self.assertGreater(shifted.common(key['shape']).Volume, 1e-5)

    def test_removing_key_allows_isolated_joint_to_withdraw(self):
        _, _, male, female, _, record = self.joint
        for d in (.2, record['engagement_mm']/2, record['engagement_mm']+.5):
            shifted = male.copy()
            shifted.translate(App.Vector(*[-d*n for n in record['insertion_axis']]))
            self.assertLess(shifted.common(female).Volume, 1e-5)

    def test_larger_contact_face_does_not_choose_a_trapped_insertion_axis(self):
        from body_frame_geometry import block,item,fuse
        from body_frame_joinery import design_joint
        a=item('wrap','上下の段差が相手を挟む部品',fuse([
            block([-20,-8,10],[20,16,20]),block([0,-8,10],[15,16,4]),
            block([0,-8,26],[15,16,4])]),'support')
        b=item('inside','段差の間へ横から入れる部品',block([0,-8,14],[20,16,12]),'support')
        joint=design_joint(a,b,[a,b],0)
        self.assertIsNotNone(joint)
        self.assertEqual(joint[-1]['normal_axis'],0)

    def test_integral_guard_cannot_trap_the_square_key(self):
        from body_frame_geometry import block,item,fuse
        from body_frame_joinery import design_joint
        a=item('guarded','栓の片側に一体ガイドがある部品',fuse([
            block([-20,-8,10],[20,16,10]),block([-20,-18,10],[26,4,10]),
            block([-20,-18,10],[4,10,10]),
            block([1,-14,10],[5,2,10])]),'support')
        b=item('receiver','受け部品',block([0,-8,10],[20,16,10]),'support')
        joint=design_joint(a,b,[a,b],0)
        self.assertIsNotNone(joint)
        self.assertEqual(joint[-1]['key_axis'],[0,1,0])


@unittest.skipIf(App is None, 'FreeCAD同梱Pythonで実行してください')
class ScrewlessCaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = runpy.run_path(str(ROOT/'models/fan-controller/source/freecad_fan_controller.py'))
        cls.case = cls.source['screwless_case_parts']()
        App.closeDocument(cls.source['doc'].Name)

    def test_old_lid_screw_positions_are_solid(self):
        s = self.source
        for x, y in s['screw_centers']:
            for shape, z, h in ((self.case['body'], s['lid_z']-4, 3),
                                (self.case['lid'], s['lid_z']+.2, 1.6)):
                probe = Part.makeCylinder(.4, h, App.Vector(x, y, z))
                self.assertAlmostEqual(shape.common(probe).Volume, probe.Volume, places=5)

    def test_pcb_retainers_are_integral_with_lid(self):
        s = self.source
        for x, y in s['clamp_screw_centers']:
            probe = Part.makeCylinder(.4, s['lid_z']-s['retainer_bottom_z'],
                                      App.Vector(x, y, s['retainer_bottom_z']+.05))
            self.assertAlmostEqual(self.case['lid'].common(probe).Volume, probe.Volume, places=5)
        self.assertEqual(self.case['assembly_screws'], 0)
        self.assertEqual(self.case['assembly_nuts'], 0)

    def test_new_cradle_has_no_old_mounting_bores_or_nut_traps(self):
        from controller_mount import screwless_cradle, CASE_PITCH, RACK_U, RACK_PITCH, STANDOFF, THICKNESS
        s = self.source
        cradle = screwless_cradle(s['envelope_length'], s['envelope_width'])
        for u, v, w, length in [(-CASE_PITCH/2, 0, 0, THICKNESS),
                                (CASE_PITCH/2, 0, 0, THICKNESS),
                                (RACK_U, -RACK_PITCH/2, -STANDOFF, THICKNESS+STANDOFF),
                                (RACK_U, RACK_PITCH/2, -STANDOFF, THICKNESS+STANDOFF)]:
            probe = Part.makeCylinder(.4, length, App.Vector(u, v, w))
            self.assertAlmostEqual(cradle.common(probe).Volume, probe.Volume, places=5)


if __name__ == '__main__':
    unittest.main()
