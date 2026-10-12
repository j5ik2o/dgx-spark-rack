"""採用する接続構成。機器の選定と、未測定の物理配線を混同しない。"""
import json
from pathlib import Path

CONFIGURATION = Path(__file__).resolve().parents[1] / 'reference/selected-network-20261012/configuration.json'


def selected_network():
    return json.loads(CONFIGURATION.read_text(encoding='utf-8'))


def final_topology(configuration=None):
    record = configuration if configuration is not None else selected_network()
    final = record['final_phase']
    switch, cable = final['switch'], final['cable']
    nodes = ('upper_left', 'upper_right', 'lower_left', 'lower_right')
    if record['node_count'] != len(nodes) or final['links_per_node'] != 1:
        raise ValueError('採用する分岐構成はSpark4台へ各1接続です。両端子を使う場合は構成の再検討が必要です。')
    ends = cable['node_ends_per_cable']
    if ends != switch['breakout_links_per_400g_port'] or ends != 2:
        raise ValueError('ケーブルの分岐数とスイッチの200ギガビット毎秒接続数が一致しません。')
    count = len(nodes) // ends
    if count > switch['physical_400g_port_count']:
        raise ValueError('採用ケーブルを接続する400ギガビット毎秒端子が不足しています。')
    if cable['routing_minimum_bend_radius_mm'] < max(cable['manufacturer_minimum_bend_radius_range_mm']):
        raise ValueError('最終ケーブルの設計曲げ半径がメーカー記載の上限値を下回っています。')
    # 左右の列へ1本ずつ割り当てる候補。物理端子の位置・配線経路は未確定。
    groups = [{'cable_number': 1, 'switch_port_number': 1, 'nodes': ['upper_left', 'lower_left']},
              {'cable_number': 2, 'switch_port_number': 2, 'nodes': ['upper_right', 'lower_right']}]
    return {'switch_model': switch['model'], 'switch_quantity': switch['quantity'],
            'cable_model': cable['model'], 'physical_cable_count': count,
            'node_connection_count': len(nodes), 'link_rate_gbps': final['link_rate_gbps'],
            'groups': groups, 'nominal_length_mm': cable['nominal_length_mm'],
            'routing_minimum_bend_radius_mm': cable['routing_minimum_bend_radius_mm'],
            'quantity_status': cable['quantity_status'],
            'routing_validated': False, 'electrical_validation': cable['electrical_validation']}


def require_breakout_measurements(configuration=None):
    record = configuration if configuration is not None else selected_network()
    cable = record['final_phase']['cable']
    fields = ('connector_envelopes_mm', 'trunk_length_mm', 'branch_lengths_mm',
              'splitter_envelope_mm', 'nominal_length_basis')
    missing = [field for field in fields if cable.get(field) is None]
    if missing:
        raise ValueError('分岐ケーブルの実経路は寸法未確定です: ' + ', '.join(missing))
    return cable
