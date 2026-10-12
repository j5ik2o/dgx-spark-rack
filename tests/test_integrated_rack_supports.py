"""一体支持棚・支持床の実形状と荷重を受ける面をFreeCADで検査する。"""
from pathlib import Path
import sys
import unittest

try:
    import FreeCAD as App
    import Part
except ImportError:
    App = None

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'models/spark-rack/source'))


@unittest.skipIf(App is None, 'FreeCAD同梱Pythonで実行してください')
class IntegratedRackSupportsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fixed_rack_layout import fixed_layout
        from integrated_rack_supports import integrated_supports
        from spark_rack_parameters import FixedRackParameters
        cls.p = FixedRackParameters()
        cls.scene = fixed_layout(parameters=cls.p)
        cls.parts, cls.metadata = integrated_supports(cls.scene, cls.p)

    def test_twelve_fixed_parts_replace_thirty_split_beam_parts(self):
        self.assertEqual(len(self.parts), 12)
        self.assertEqual(sum(p['role'] == 'node_shelf' for p in self.parts), 6)
        self.assertEqual(sum(p['role'] == 'power_floor' for p in self.parts), 6)
        self.assertEqual(len(self.metadata['replaced_cross_beams']), 10)
        self.assertEqual(self.metadata['old_split_part_count'], 30)
        self.assertTrue(all(p['role'] not in ('tray', 'power_tray') for p in self.parts))

    def test_all_parts_are_closed_single_solids_that_fit_the_printer(self):
        for item in self.parts:
            with self.subTest(part=item['name']):
                shape = item['shape']
                self.assertTrue(shape.isValid())
                self.assertTrue(shape.isClosed())
                self.assertEqual(len(shape.Solids), 1)
                bounds = shape.optimalBoundingBox(False)
                self.assertLessEqual(max(bounds.XLength, bounds.YLength, bounds.ZLength),
                                     self.p.usable_print_size + 1e-6)

    def test_parts_do_not_overlap_and_every_neighbor_has_a_bearing_lap(self):
        from validate_spark_rack_joint_coupons import contact_area
        for index, first in enumerate(self.parts):
            for second in self.parts[index + 1:]:
                with self.subTest(first=first['name'], second=second['name']):
                    self.assertLess(first['shape'].common(second['shape']).Volume, 1e-5)
        by_name = {item['name']: item['shape'] for item in self.parts}
        for level, base in enumerate((self.p.lower_base, self.p.upper_base)):
            for column in range(2):
                a, b = [by_name[f'node_shelf_{level}_{c}'] for c in (column, column + 1)]
                self.assertGreater(contact_area(a, b, base - self.p.tray_thickness - 6), 700)
        for row in range(2):
            for column in range(2):
                a, b = [by_name[f'power_floor_{row}_{c}'] for c in (column, column + 1)]
                self.assertGreater(contact_area(a, b, 20), 1000)
        for column in range(3):
            a, b = [by_name[f'power_floor_{row}_{column}'] for row in (0, 1)]
            self.assertGreater(contact_area(a, b, 20), 1000)

    def test_actual_removable_tray_rings_touch_the_fixed_support(self):
        from fixed_rack_geometry import ring_tray
        from validate_spark_rack_joint_coupons import contact_area
        for tray in self.scene['trays'] + self.scene['power_trays']:
            with self.subTest(tray=tray['name']):
                moving = ring_tray(tray)
                z = tray['origin'][2]
                contacts = sum(contact_area(item['shape'], moving, z) for item in self.parts)
                self.assertGreater(contacts, 700)
                self.assertLess(sum(item['shape'].common(moving).Volume for item in self.parts), 1e-5)
                self.assertTrue(any(surface['target'] == tray['name']
                                    for surface in self.metadata['support_surfaces']))
        main_support_z = [item['support_z'] for item in self.metadata['assemblies']
                          if item['kind'] == 'node_shelf']
        self.assertEqual(main_support_z, [200, 420])
        self.assertEqual(self.metadata['assemblies'][-1]['support_z'], 32)

    def test_main_shelves_leave_the_equipment_underside_open(self):
        for node in self.scene['nodes']:
            x = node['origin'][0] + self.p.spark_width / 2
            z = node['origin'][2] - self.p.tray_thickness - 12
            probe = Part.makeBox(120, 100, 12, App.Vector(x - 60, -126, z))
            self.assertLess(sum(item['shape'].common(probe).Volume for item in self.parts), 1e-5)

    def test_integrated_ribs_and_depth_bands_transfer_load_through_real_contact(self):
        from validate_spark_rack_joint_coupons import contact_area
        for item in self.parts:
            shape = item['shape']
            with self.subTest(part=item['name']):
                if item['role'] == 'power_floor':
                    below = shape.common(Part.makeBox(600, 500, 16, App.Vector(-300, -300, 8)))
                    above = shape.common(Part.makeBox(600, 500, 8, App.Vector(-300, -300, 24)))
                    self.assertGreater(contact_area(below, above, 24), 1000)
                else:
                    bounds = shape.BoundBox
                    for y in (-128, -22):
                        first = shape.common(Part.makeBox(600, 300 + y, 20,
                                                         App.Vector(-300, -300, bounds.ZMin)))
                        second = shape.common(Part.makeBox(600, 100 - y, 20,
                                                          App.Vector(-300, y, bounds.ZMin)))
                        faces_a = [face for face in first.Faces
                                   if abs(face.BoundBox.YMin - y) < 1e-6
                                   and abs(face.BoundBox.YMax - y) < 1e-6]
                        faces_b = [face for face in second.Faces
                                   if abs(face.BoundBox.YMin - y) < 1e-6
                                   and abs(face.BoundBox.YMax - y) < 1e-6]
                        area = sum(a.common(b).Area for a in faces_a for b in faces_b)
                        self.assertGreater(area, 150)

    def test_fastener_candidates_are_real_clearance_holes_with_material_around_them(self):
        self.assertEqual(len(self.metadata['fastener_candidates']), 15)
        for fastener in self.metadata['fastener_candidates']:
            with self.subTest(fastener=fastener):
                origin = App.Vector(*fastener['origin'])
                length = fastener['through_length_mm']
                hole = Part.makeCylinder(2.25, length, origin)
                surround = Part.makeCylinder(3, length, origin)
                selected = [item['shape'] for item in self.parts
                            if item['name'].startswith(fastener['assembly'] + '_')]
                self.assertLess(sum(shape.common(hole).Volume for shape in selected), 1e-5)
                self.assertGreater(sum(shape.common(surround).Volume for shape in selected), 40)
                self.assertIn('未確定', fastener['head_and_nut_retention'])

    def test_floor_uses_open_ribs_and_reduces_volume_without_changing_main_shelves(self):
        # 改訂前の既定寸法で実測した体積。強度・接触面の検査と併せて比較する。
        baseline_litres = {'node_shelf_0': 0.3429165929851777,
                           'node_shelf_1': 0.34291659298517774,
                           'power_floor': 1.7110375363552464}
        measured = {item['name']: item['cad_solid_volume_mm3'] / 1_000_000
                    for item in self.metadata['assemblies']}
        for name in ('node_shelf_0', 'node_shelf_1'):
            self.assertAlmostEqual(measured[name], baseline_litres[name], places=7)
        self.assertLess(measured['power_floor'], baseline_litres['power_floor'])
        for item in self.parts:
            # 密閉した内側空洞を持つソリッドは、外側と空洞側で別の殻を持つ。
            self.assertEqual(len(item['shape'].Shells), 1)
        self.assertFalse(self.metadata['assemblies'][-1]['closed_internal_cavities'])

    def test_load_band_has_less_material_and_larger_vertical_bending_second_moment(self):
        # 継ぎ目や丸角から離れた実断面を取り、以前の20×8mm矩形帯と比較する。
        points = [App.Vector(-200, y, z) for y, z in
                  ((-247, 8), (-237, 8), (-237, 32), (-247, 32), (-247, 8))]
        plane = Part.Face(Part.makePolygon(points))
        floor = next(item['shape'] for item in self.parts if item['name'] == 'power_floor_0_0')
        cross_section = floor.common(plane)
        self.assertAlmostEqual(cross_section.Area, 144, places=5)
        self.assertLess(cross_section.Area, 20 * 8)
        old_second_moment = 20 * 8 ** 3 / 12
        self.assertGreater(cross_section.MatrixOfInertia.A22, 6 * old_second_moment)

    def test_floor_clears_the_control_door_and_side_fan_removal_paths(self):
        door = self.scene['control_door_sweep']
        probe = Part.makeBox(*door['size'], App.Vector(*door['origin']))
        self.assertLess(sum(item['shape'].common(probe).Volume for item in self.parts), 1e-5)
        for x in (-310, 230):
            fan_path = Part.makeBox(80, 120, 120, App.Vector(x, -180, 28))
            self.assertLess(sum(item['shape'].common(fan_path).Volume for item in self.parts), 1e-5)

    def test_side_sockets_preserve_bearing_without_bottom_clearance(self):
        from validate_spark_rack_joint_coupons import contact_area
        walls = [Part.makeBox(self.p.section, self.p.depth, self.p.height,
                             App.Vector(x, self.p.front_y, 0))
                 for x in (-self.p.width / 2, self.p.inner_width / 2)]
        for socket in self.metadata['socket_envelopes']:
            with self.subTest(socket=socket['name']):
                self.assertEqual(socket['bottom_clearance_mm'], 0)
                self.assertEqual(socket['cut_origin'][2], socket['bearing_z'])
                self.assertAlmostEqual(socket['cut_size'][2] - socket['size'][2], self.p.fit_clearance)
                bearing = Part.makeBox(socket['size'][0], socket['size'][1], 1,
                                       App.Vector(socket['origin'][0], socket['origin'][1],
                                                  socket['bearing_z'] - 1))
                area = sum(contact_area(item['shape'], bearing, socket['bearing_z']) for item in self.parts)
                self.assertAlmostEqual(area, socket['size'][0] * socket['size'][1], places=4)
                pocket = Part.makeBox(*socket['cut_size'], App.Vector(*socket['cut_origin']))
                walls = [wall.cut(pocket) for wall in walls]
        for wall in walls:
            for item in self.parts:
                self.assertLess(wall.common(item['shape']).Volume, 1e-5)


if __name__ == '__main__':
    unittest.main()
