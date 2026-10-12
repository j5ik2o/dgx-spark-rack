"""4本の独立ケーブルと2本の分岐ケーブルを混同しないための検査。"""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'models/spark-rack/source'))
from network_configuration import final_topology, require_breakout_measurements, selected_network


class NetworkConfigurationTests(unittest.TestCase):
    def test_two_physical_cables_connect_four_distinct_nodes(self):
        result = final_topology()
        self.assertEqual(result['physical_cable_count'], 2)
        self.assertEqual(result['node_connection_count'], 4)
        self.assertEqual(result['nominal_length_mm'], 2000)
        self.assertEqual(len({g['switch_port_number'] for g in result['groups']}), 2)
        self.assertEqual(sorted(n for g in result['groups'] for n in g['nodes']),
                         ['lower_left', 'lower_right', 'upper_left', 'upper_right'])
        self.assertTrue(all(len(g['nodes']) == 2 for g in result['groups']))
        self.assertFalse(result['routing_validated'])

    def test_four_ring_cables_remain_initial_phase_only(self):
        record = selected_network()
        self.assertEqual(record['initial_phase']['physical_cable_count'], 4)
        self.assertEqual(record['initial_phase']['nominal_length_mm'], 400)
        self.assertEqual(record['final_phase']['switch']['model'], 'CRS812-8DS-2DQ-2DDQ-RM')

    def test_missing_branch_lengths_do_not_pass_as_two_metre_legs(self):
        with self.assertRaisesRegex(ValueError, 'branch_lengths_mm'):
            require_breakout_measurements()

    def test_old_twenty_mm_bend_assumption_is_rejected(self):
        record = deepcopy(selected_network())
        record['final_phase']['cable']['routing_minimum_bend_radius_mm'] = 20
        with self.assertRaisesRegex(ValueError, '曲げ半径'):
            final_topology(record)

    def test_dual_connections_are_not_silently_assumed(self):
        record = deepcopy(selected_network())
        record['final_phase']['links_per_node'] = 2
        with self.assertRaisesRegex(ValueError, '両端子'):
            final_topology(record)

    def test_insufficient_switch_ports_are_rejected(self):
        record = deepcopy(selected_network())
        record['final_phase']['switch']['physical_400g_port_count'] = 1
        with self.assertRaisesRegex(ValueError, '端子が不足'):
            final_topology(record)


if __name__ == '__main__':
    unittest.main()
