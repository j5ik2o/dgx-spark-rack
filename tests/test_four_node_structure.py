"""支持段の切替と部品分割の整合、旧STL検査の既定条件を確認する。"""
from dataclasses import replace
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'models/spark-rack/source'))
sys.path.insert(0, str(ROOT / 'tools/cad'))
from four_node_structure_parameters import StructureParameters, instances
from check_stl import inspect


class StructureRecipeTests(unittest.TestCase):
    def test_same_parts_at_both_upper_positions(self):
        ring, switch = instances('ring'), instances('crs812')
        self.assertEqual(ring['part_counts'], switch['part_counts'])
        self.assertEqual(ring['part_counts']['tray'], 4)
        self.assertEqual(ring['part_counts']['fan_carrier'], 4)
        ring_trays = sorted(x['origin'][2] for x in ring['instances'] if x['part'] == 'tray')
        switch_trays = sorted(x['origin'][2] for x in switch['instances'] if x['part'] == 'tray')
        self.assertEqual(ring_trays, [64, 64, 224, 224])
        self.assertEqual(switch_trays, [64, 64, 284, 284])

    def test_split_lengths_and_print_size(self):
        p = StructureParameters()
        p.validate()
        with self.assertRaises(ValueError):
            replace(p, column_lengths=(105, 223, 93)).validate()
        with self.assertRaises(ValueError):
            replace(p, usable_print_size=200).validate()

    def test_larger_parts_require_explicit_stl_limit(self):
        points = [(0, 0, 0), (244, 0, 0), (244, 20, 0), (0, 20, 0),
                  (0, 0, 10), (244, 0, 10), (244, 20, 10), (0, 20, 10)]
        triangles = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
                     (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
                     (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'beam.stl'
            data = bytes(80) + struct.pack('<I', 12)
            for triangle in triangles:
                data += struct.pack('<12fH', 0, 0, 0, *[value for index in triangle for value in points[index]], 0)
            path.write_bytes(data)
            with self.assertRaises(AssertionError):
                inspect(path)
            result = inspect(path, max_dimension=246)
            self.assertEqual(result['dimensions_mm'], [244, 20, 10])
            self.assertEqual(result['non_manifold_edges'], 0)


if __name__ == '__main__':
    unittest.main()
