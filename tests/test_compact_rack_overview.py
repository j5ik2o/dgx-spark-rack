"""統合する電源とファンが、両スイッチの予約範囲を侵さないことを確認する。"""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'models/spark-rack/source'))
from build_rack_candidate_overview import check_scene, scene
from rack_candidate_datums import DATUMS


class CompactOverviewTest(unittest.TestCase):
    def test_both_switches_and_ring_fit_reference_volume(self):
        for mode in ('ring', 'crs812', 'crs804'):
            with self.subTest(mode=mode):
                data = scene(mode)
                check_scene(data)
                self.assertEqual(data['frame_outer_mm'], [DATUMS.frame_outer_width,
                                 DATUMS.frame_rear_y - DATUMS.frame_front_y, DATUMS.frame_height])
                self.assertEqual(len(data['adapter_layout']['adapters']), 4)
                self.assertEqual(len(data['adapter_layout']['fans']), 2)
                self.assertEqual(sum(b['kind'] == 'controller' for b in data['equipment']), 6)
                self.assertFalse(data['switch_support_generated'])
                self.assertFalse(data['manufacturing_geometry'])

    def test_power_moved_into_switch_is_rejected(self):
        data = deepcopy(scene('crs804'))
        adapter = next(b for b in data['equipment'] if b['kind'] == 'adapter')
        adapter['origin'][2] = 200
        with self.assertRaisesRegex(ValueError, 'outer_box_collisions'):
            check_scene(data)

    def test_controller_outside_frame_is_rejected(self):
        data = deepcopy(scene('ring'))
        controller = next(b for b in data['equipment'] if b['kind'] == 'controller')
        controller['origin'][0] = 250
        with self.assertRaisesRegex(ValueError, 'outside_frame_volume'):
            check_scene(data)

    def test_obstacle_between_cable_points_is_rejected(self):
        data = deepcopy(scene('ring'))
        data['cables'] = [{'label': '途中に障害物がある配線', 'from': 'test_source', 'to': 'test_target',
                           'points': [[-50, 50, 200], [50, 50, 200]]}]
        data['feet'].append({'name': 'midpoint_obstacle', 'label': '線分途中の障害物',
                             'origin': [-2, 48, 198], 'size': [4, 4, 4], 'kind': 'foot'})
        with self.assertRaisesRegex(ValueError, 'cable_reference_tube_collisions'):
            check_scene(data)


if __name__ == '__main__':
    unittest.main()
