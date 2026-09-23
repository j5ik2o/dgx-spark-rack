"""FreeCAD環境で、接合開口の保護とファン板の表裏処理を検査する。"""
from pathlib import Path
import sys
import unittest

try:
    import FreeCAD as App
    import Part
except ImportError:
    App = None

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/cad'))
sys.path.insert(0, str(ROOT / 'models/spark-rack/source'))


@unittest.skipIf(App is None, 'FreeCAD同梱Pythonで実行してください')
class EdgeFinishingTests(unittest.TestCase):
    def test_open_mating_channel_is_unchanged(self):
        from edge_finishing import chamfer, extrema
        from spark_rack_parameters import Parameters
        p = Parameters()
        opening = 2*p.side_thickness+p.column_gap+2*p.fit_clearance
        source = Part.makeBox(opening+8,16,20,App.Vector(-opening/2-4,0,0)).cut(
            Part.makeBox(opening,18,17.5,App.Vector(-opening/2,-1,-1)))
        finished = chamfer(source, extrema(source,'X')+[('Z',20)])
        protected = Part.makeBox(opening+1,18,18,App.Vector(-opening/2-.5,-1,-1))
        self.assertLess(source.cut(finished).common(protected).Volume,1e-6)
        self.assertLess(finished.Volume,source.Volume)

    def test_closed_slot_rims_require_explicit_opt_in(self):
        from edge_finishing import chamfer, extrema
        source = Part.makeBox(40,30,4).cut(Part.makeBox(10,10,6,App.Vector(15,10,-1)))
        protected = Part.makeBox(12,12,6,App.Vector(14,9,-1))
        finished = chamfer(source,extrema(source,'Z'))
        self.assertLess(source.cut(finished).common(protected).Volume,1e-6)
        intentional = chamfer(source,[('Z',4)],allow_openings=True)
        self.assertGreater(source.cut(intentional).common(protected).Volume,0.1)

    def test_cassette_front_and_rear_plate_edges_are_finished(self):
        from freecad_spark_rack import cassette, shapes
        from spark_rack_parameters import Parameters
        p = Parameters()
        source = cassette(p)
        finished = shapes(p)['fan_cassette']
        for y in (.05,p.cassette_plate-.05):
            point = App.Vector(p.module_width/2-.05,y,p.fan_center_z)
            self.assertTrue(source.isInside(point,1e-7,False))
            self.assertFalse(finished.isInside(point,1e-7,False))
        peg = App.Vector(p.post_x+4-.05,p.front_y+8-.05,24)
        self.assertTrue(source.isInside(peg,1e-7,False))
        self.assertTrue(finished.isInside(peg,1e-7,False))


if __name__ == '__main__':
    unittest.main()
