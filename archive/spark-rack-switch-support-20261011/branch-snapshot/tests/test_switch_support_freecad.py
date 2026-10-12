"""支持部の受け面と、ねじが実際の相手へ届くことを検査する。"""
from pathlib import Path
import sys
import unittest

try:
    import FreeCAD
except ImportError:
    FreeCAD=None
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'models/spark-rack/source'))


@unittest.skipIf(FreeCAD is None,'FreeCAD同梱Pythonで実行してください')
class SwitchSupportGeometryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from freecad_switch_support import build_shapes
        cls.shapes,cls.fixtures=build_shapes()

    def test_load_bearings_and_downward_insertion(self):
        from build_switch_support_cad import validate
        result=validate(self.shapes,self.fixtures)
        self.assertGreater(min(result['bearing_contact_mm2'].values()),200)
        self.assertEqual(result['insertion_samples'],504)
        self.assertEqual(len(result['fasteners']),20)

    def test_short_screw_cannot_be_accepted_as_reaching_nut(self):
        from build_switch_support_cad import validate
        from freecad_switch_support import bore
        fixtures=[dict(f) for f in self.fixtures]
        fixtures[0]['length']=10
        f=fixtures[0];start=list(f['start']);start[f['axis']]-=f['sign']*4
        shapes=dict(self.shapes)
        shapes[f['name']+'_screw']=bore(f['start'],2,10,f['axis'],f['sign']).fuse(bore(start,4,4,f['axis'],f['sign']))
        with self.assertRaisesRegex(ValueError,'ナットを貫通'):
            validate(shapes,fixtures)


if __name__=='__main__':unittest.main()
