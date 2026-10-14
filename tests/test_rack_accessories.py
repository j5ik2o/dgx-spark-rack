"""中段の遠隔操作機器棚の高さ、交換経路、未確定値を検査する。"""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'models/spark-rack/source'))
from fixed_rack_layout import check_fixed_layout, fixed_layout
from rack_accessories import accessory_layout, devices
from spark_rack_parameters import RemoteConsoleParameters
from upper_switch_bay import upper_scene


class RackAccessoriesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p, cls.bay, cls.acc, cls.scene = upper_scene()
        cls.by_name = {b['name']: b for b in cls.scene['equipment'] + cls.acc['objects']}

    def test_shelf_sits_above_cable_storage_and_lower_fan_carriers(self):
        self.assertEqual((self.acc['shelf_z'], self.acc['support_z']), (298, 310))
        self.assertGreater(self.acc['shelf_z'], self.acc['storage_top_mm'])
        self.assertGreater(self.acc['support_z'], self.acc['lower_carrier_top_mm'])
        comet = self.by_name['remote_kvm']
        self.assertLess(comet['origin'][2] + comet['size'][2], self.acc['front_top_limit_mm'])

    def test_comet_screen_sits_right_behind_the_window_on_a_sled(self):
        comet = self.by_name['remote_kvm']
        sled = self.by_name['remote_kvm_sled']
        self.assertEqual(comet['size'], [93, 84, 47])
        self.assertLess(self.acc['screen_recess_mm'], 1)
        cx, cz = self.acc['window']['center']
        self.assertAlmostEqual(cz, comet['origin'][2] + comet['size'][2] / 2)
        # 載せ台の前の部分は、下段ファン保持部の上を片持ちで延びる。
        self.assertEqual(sled['origin'][2] + sled['size'][2], comet['origin'][2])
        self.assertGreater(sled['origin'][2], self.acc['lower_carrier_top_mm'])
        self.assertLess(sled['origin'][1], self.p.fan_front_y + self.p.fan_depth)

    def test_both_phases_pass_with_the_shelf(self):
        for mode in ('ring', 'crs812'):
            _, _, _, scene = upper_scene(mode)
            result = check_fixed_layout(scene)
            self.assertEqual(result['accessory_service_obstructions'], [])
            self.assertEqual(result['accessory_connector_obstructions'], [])

    def test_central_default_cannot_take_the_shelf(self):
        default = fixed_layout('crs812')
        self.assertNotIn('accessories', default)
        with self.assertRaisesRegex(ValueError, '上部専用段'):
            fixed_layout('crs812', None, None, self.acc)

    def test_comet_removal_moves_the_center_panel_but_rejects_other_obstacles(self):
        check_fixed_layout(self.scene)
        scene = deepcopy(self.scene)
        scene['accessories']['objects'].append({'name': 'front_obstacle', 'label': '前の障害物',
                                                'origin': [-10, -346, 330], 'size': [6, 2, 6], 'kind': 'mid_panel'})
        with self.assertRaisesRegex(ValueError, "'remote_kvm_removal', 'front_obstacle'"):
            check_fixed_layout(scene)

    def test_kvm_removal_rejects_a_rear_obstacle(self):
        scene = deepcopy(self.scene)
        scene['accessories']['objects'].append({'name': 'rear_obstacle', 'label': '後ろの障害物',
                                                'origin': [-10, 100, 330], 'size': [6, 6, 6], 'kind': 'mid_panel'})
        with self.assertRaisesRegex(ValueError, "'kvm_switch_removal', 'rear_obstacle'"):
            check_fixed_layout(scene)

    def test_reference_switcher_dimensions_do_not_imply_physical_measurement(self):
        info = devices()
        self.assertFalse(info['kvm_measured'])
        self.assertTrue(info['kvm_body_known'])
        self.assertEqual(info['kvm_size_basis'], 'user_supplied_search_summary')
        self.assertEqual(info['record']['kvm_switch']['body_mm'], [300, 117, 30])
        self.assertEqual(self.by_name['kvm_switch']['size'], [300, 117, 30])
        self.assertEqual(self.by_name['kvm_switch']['origin'], [-150, -27, 310])
        self.assertIn('参考寸法・未実測', self.by_name['kvm_switch']['label'])
        self.assertEqual(info['kvm_model'], 'HKS401-P23')
        self.assertEqual(info['kvm_selection_status'], 'planned')
        self.assertIn('TESmart HKS401-P23', self.by_name['kvm_switch']['label'])
        self.assertEqual(info['record']['comet_pro']['operating_temperature_c'], [0, 40])
        self.assertIsNone(info['record']['spark_rear_ports']['hdmi_and_usb_positions_mm'])
        self.assertFalse(self.acc['physical_validation'])

    def test_taller_hand_space_is_rejected_instead_of_hitting_the_fan_rail(self):
        with self.assertRaisesRegex(ValueError, '横梁'):
            accessory_layout(self.p, fixed_layout('crs812', self.p, self.bay),
                             replace(RemoteConsoleParameters(), comet_top_margin=20))


if __name__ == '__main__':
    unittest.main()
