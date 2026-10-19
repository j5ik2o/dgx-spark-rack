"""造形姿勢の反転・寸法欠け・細い角栓の見逃しを防ぐ。"""
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
class PrintOrientationTests(unittest.TestCase):
    def test_every_orientation_preserves_shape_and_lands_on_the_bed(self):
        from body_frame_print_plan import orientation,AXES
        shape=Part.makeBox(12,8,3,App.Vector(-20,10,30)).fuse(
            Part.makeBox(3,8,10,App.Vector(-20,10,30)))
        for axis in AXES:
            result=orientation(shape,axis)
            self.assertAlmostEqual(result['shape'].Volume,shape.Volume,places=6)
            b=result['shape'].BoundBox
            self.assertAlmostEqual(b.XMin,0,places=6)
            self.assertAlmostEqual(b.YMin,0,places=6)
            self.assertAlmostEqual(b.ZMin,0,places=6)
            rows=[App.Vector(*r[:3]) for r in result['matrix']]
            self.assertAlmostEqual(rows[0].cross(rows[1]).dot(rows[2]),1,places=6)

    def test_fan_pin_has_a_full_length_flat_without_standing_its_axis_up(self):
        from freecad_spark_rack import fan_pin
        from body_frame_print_plan import bed_faces
        from spark_rack_parameters import BodyFrameParameters
        fan=dict(origin=[-70,-57,50.5],size=[140,27,140],axis=[0,-1,0])
        shape=fan_pin(fan,[-62.25,-43.5,58.25],BodyFrameParameters())
        faces=bed_faces(shape,[0,0,1])
        self.assertGreater(sum(f.Area for f in faces),30)
        self.assertAlmostEqual(Part.makeCompound(faces).BoundBox.YLength,shape.BoundBox.YLength,places=6)
        self.assertAlmostEqual(shape.optimalBoundingBox(False).ZMin,58.25-1.2,places=6)
        self.assertEqual(len(shape.Solids),1)


@unittest.skipIf(App is None,'FreeCAD同梱Pythonで実行してください')
class JointSectionTests(unittest.TestCase):
    def setUp(self):
        from freecad_spark_rack import block,item
        from body_frame_joinery import design_joint
        from spark_rack_parameters import BodyFrameParameters
        a=item('left','左',block([-20,-8,10],[20,16,10]),'support')
        b=item('right','右',block([0,-8,10],[20,16,10]),'support')
        donor,receiver,male,female,key,joint=design_joint(a,b,[a,b],0)
        self.joint=joint
        self.model=dict(parts=[dict(donor,shape=male),dict(receiver,shape=female),key],
                        parameters=BodyFrameParameters(),scene=dict(screwless_assembly=dict(joints=[joint])))
        self.center=list(joint['contact_point_mm'])
        self.center[joint['normal_axis']]+=joint['insertion_axis'][joint['normal_axis']]*joint['engagement_mm']/2

    def test_metadata_cannot_hide_a_thinned_key(self):
        from body_frame_print_plan import check_joint_sections
        self.assertEqual(len(check_joint_sections(self.model)),1)
        key=self.model['parts'][-1]
        probe=Part.makeBox(.1,.1,.1,App.Vector(*[v-.05 for v in self.center]))
        key['shape']=key['shape'].cut(probe)
        with self.assertRaisesRegex(ValueError,'角栓の指定断面'):
            check_joint_sections(self.model)

    def test_remaining_wall_is_checked_in_the_actual_donor(self):
        from body_frame_print_plan import check_joint_sections
        normal=self.joint['normal_axis']
        center=list(self.center)
        half_slot=self.joint['key_shaft_width_mm']/2+self.joint['key_slot_clearance_mm']
        center[normal]+=(half_slot+self.joint['engagement_mm']/2)/2
        probe=Part.makeBox(.1,.1,.1,App.Vector(*[v-.05 for v in center]))
        donor=next(e for e in self.model['parts'] if e['name']==self.joint['donor'])
        donor['shape']=donor['shape'].cut(probe)
        with self.assertRaisesRegex(ValueError,'残り肉'):
            check_joint_sections(self.model)


if __name__=='__main__':
    unittest.main()
