"""実形状の接触関係と、メタデータだけで斜め取付を隠せないことを検査する。"""
from pathlib import Path
import sys
import unittest

try:
    import FreeCAD as App
except ImportError:
    App = None

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'models/spark-rack/source'))


@unittest.skipIf(App is None, 'FreeCAD同梱Pythonで実行してください')
class BodyFrameGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from freecad_spark_rack import create_body_frame
        from validate_body_frame import validate
        cls.doc, cls.model = create_body_frame()
        cls.report = validate(cls.model)

    @classmethod
    def tearDownClass(cls):
        App.closeDocument(cls.doc.Name)

    def test_spark_cases_are_needed_to_complete_the_contact_graph(self):
        self.assertEqual(self.report['contact_components_with_sparks'], 1)
        self.assertGreater(self.report['contact_components_without_sparks'], 1)
        self.assertEqual(len(self.report['reference_bearing_contacts']), 8)
        self.assertEqual(len(self.report['fan_straight_removal']), 6)
        self.assertEqual(self.report['connector_obstructions'], [])
        self.assertFalse(self.report['manufacturing_geometry'])
        self.assertFalse(self.report['physical_validation'])

    def test_a_physically_rotated_fan_is_rejected_even_with_unchanged_metadata(self):
        from validate_body_frame import validate
        model = dict(self.model, references=[dict(e) for e in self.model['references']])
        fan = next(e for e in model['references'] if e['name'] == 'spark_fan_0_front')
        rotated = fan['shape'].copy()
        rotated.rotate(rotated.BoundBox.Center, App.Vector(0, 0, 1), 30)
        fan['shape'] = rotated
        with self.assertRaisesRegex(ValueError, '実形状.*取付軸'):
            validate(model)

    def cable_model_with_probe(self, name, origin, size):
        from freecad_spark_rack import block
        model = dict(self.model, cables=[dict(e) for e in self.model['cables']])
        cable = next(e for e in model['cables'] if e['name'] == name)
        cable['shape'] = block(origin, size)
        return model

    def test_continuous_removal_catches_a_wire_beyond_the_stationary_fan(self):
        from validate_body_frame_cables import validate_cables
        model = self.cable_model_with_probe('kvm_dc', [-86, 430, 116], [2, 2, 2])
        with self.assertRaisesRegex(ValueError, '連続した着脱'):
            validate_cables(model)

    def test_a_cable_in_the_reserved_air_passage_is_rejected(self):
        from validate_body_frame_cables import validate_cables
        model = self.cable_model_with_probe('kvm_dc', [-86, 250, 80], [2, 2, 2])
        with self.assertRaisesRegex(ValueError, '排気通路'):
            validate_cables(model)

    def test_owner_exemption_does_not_allow_a_wire_through_the_whole_case(self):
        from validate_body_frame_cables import validate_cables
        model = self.cable_model_with_probe('spark_dc_1_0', [84, 80, 80], [2, 2, 2])
        with self.assertRaisesRegex(ValueError, '固定物の干渉'):
            validate_cables(model)

    def test_switch_is_captured_horizontally_and_from_above(self):
        report = self.report['switch_retention']
        self.assertEqual(report['bands'], 2)
        self.assertEqual(len(report['checked_displacements']), 5)
        self.assertFalse(report['seismic_rating_verified'])

    def test_missing_switch_band_cannot_pass(self):
        from body_frame_switch_retention import validate_retention
        model = dict(self.model, references=[e for e in self.model['references'] if e['name'] != 'switch_band_0'])
        with self.assertRaisesRegex(ValueError, '欠け'):
            validate_retention(model)

    def test_plain_rails_cannot_pass_as_actual_sliding_stops(self):
        from freecad_spark_rack import block
        from body_frame_switch_retention import validate_retention
        recipes = {r['name']: r for r in self.model['scene']['boxes'] if r.get('switch_keeper')}
        parts = [e for e in self.model['parts'] if not set(e.get('integrated_members', [e['name']])) & recipes.keys()]
        parts += [dict(name=name, shape=block(recipe['origin'], recipe['size'])) for name,recipe in recipes.items()]
        model = dict(self.model, parts=parts)
        with self.assertRaisesRegex(ValueError, '移動を止めません'):
            validate_retention(model)

    def test_screwless_model_has_no_assembly_screws_or_nuts(self):
        report = self.report['screwless_assembly']
        self.assertEqual(report['assembly_screws'], 0)
        self.assertEqual(report['assembly_nuts'], 0)
        self.assertEqual(report['fan_pins'], 24)
        self.assertGreater(report['tenon_joints'], 0)

    def test_missing_square_key_cannot_pass(self):
        from body_frame_joinery import validate_screwless
        name = self.model['scene']['screwless_assembly']['joints'][0]['key']
        model = dict(self.model, parts=[e for e in self.model['parts'] if e['name'] != name])
        with self.assertRaisesRegex(ValueError, '角栓が欠け'):
            validate_screwless(model)

    def test_missing_fan_pin_cannot_pass(self):
        from body_frame_joinery import validate_screwless
        name = next(e['name'] for e in self.model['parts'] if e['kind'] == 'fan_pin')
        model = dict(self.model, parts=[e for e in self.model['parts'] if e['name'] != name])
        with self.assertRaisesRegex(ValueError, '割りピンが欠け'):
            validate_screwless(model)

    def test_missing_controller_band_cannot_pass(self):
        from body_frame_joinery import validate_screwless
        name = next(e['name'] for e in self.model['references'] if e['kind'] == 'controller_band')
        model = dict(self.model, references=[e for e in self.model['references'] if e['name'] != name])
        with self.assertRaisesRegex(ValueError, '解除式バンドが欠け'):
            validate_screwless(model)

    def test_shared_mount_check_covers_all_screwless_controller_cases(self):
        report=self.report['controller_mounts']
        self.assertEqual(report['controllers'],6)
        self.assertTrue(all(case['side_clearance_mm']>=.29 for case in report['cases']))
        self.assertTrue(all(case['bands']==2 for case in report['cases']))
        self.assertFalse(report['physical_validation'])

    def test_shared_mount_check_rejects_a_missing_controller_band(self):
        from check_controller_mounts import check_screwless_mounts
        name=next(e['name'] for e in self.model['references'] if e['kind']=='controller_band')
        model=dict(self.model,references=[e for e in self.model['references'] if e['name']!=name])
        with self.assertRaisesRegex(ValueError,'解除式バンドが不足'):
            check_screwless_mounts(model)

    def test_assembly_order_covers_the_whole_rigid_inventory(self):
        from body_frame_assembly import SOFT_KINDS
        expected={e['name'] for e in self.model['parts']+self.model['references'] if e['kind'] not in SOFT_KINDS}
        self.assertEqual(set(self.model['assembly_plan']['all_rigid_names']),expected)
        report=self.report['assembly_order']
        self.assertEqual(report['rigid_objects'],len(expected))
        self.assertEqual(report['bench_join_operations'],self.report['screwless_assembly']['tenon_joints'])
        self.assertEqual(report['controller_preassembly']['status'],'passed')
        self.assertFalse(report['physical_validation'])

    def test_wrong_last_mating_direction_cannot_pass_the_plan(self):
        from copy import deepcopy
        from validate_body_frame_assembly import validate_plan
        plan=deepcopy(self.model['assembly_plan'])
        step=plan['bench_steps'][0]
        step['offsets'][-2]=[-v for v in step['offsets'][-2]]
        with self.assertRaisesRegex(ValueError,'差し込み方向'):
            validate_plan(self.model,plan)

    def test_roof_cannot_be_installed_after_its_switch(self):
        from copy import deepcopy
        from validate_body_frame_assembly import validate_plan
        plan=deepcopy(self.model['assembly_plan'])
        steps=plan['mount_steps']
        top=next(i for i,s in enumerate(steps) if s['phase']==5)
        switch=next(i for i,s in enumerate(steps) if s['moving']==['crs812'])
        steps.insert(top,steps.pop(switch))
        with self.assertRaisesRegex(ValueError,'搭載順|先行部品'):
            validate_plan(self.model,plan)


if __name__ == '__main__':
    unittest.main()
