"""既存の制御器6ケースを覆う共通操作面。実物の指の操作は未検証。

ケースと蓋、共通ドックは変更しない。表示窓とつまみの位置・高さは
ファンコントローラーの正本から導く。既存蓋の前面へ共通面をそろえ、
各蓋を面内の開口に収める。元の露出とねじへのアクセスを保持する。
"""
from functools import lru_cache
import math
from pathlib import Path
import runpy
import sys

import FreeCAD as App
import Part

from spark_rack_parameters import FixedRackParameters

ROOT = Path(__file__).resolve().parents[3]
CASE_SOURCE = ROOT / 'models/fan-controller/source/freecad_fan_controller.py'
sys.path.insert(0, str(ROOT / 'tools/cad'))
from controller_mount import THICKNESS, place

FACE_THICKNESS = 2.0
LID_PERIMETER_CLEARANCE = 0.3
FINGER_PROBE_RADIUS = 12.0
ADDED_FACE_VIEW_ANGLE_DEGREES = 30.0
SEAM_GAP = 0.4
STEM_RADIUS = 7.0
MOUNT_RADIUS = 2.25
NUT_ACROSS_FLATS = 7.3       # M4六角ナットの対辺7mmに仮の片側0.15mmを加える
NUT_POCKET_LENGTH = 3.6     # 厚さ3.2mmに仮の片側0.2mmを加える
MOUNT_SCREW_LENGTH = 40.0   # 頭下長。背面取付板12mmを通り、前面手前で止まる
BACKING_THICKNESS = 12.0
EPSILON = 1e-5


def _box(origin, size):
    return Part.makeBox(*size, App.Vector(*origin))


def _cylinder(origin, radius, length, axis=(0, 1, 0)):
    return Part.makeCylinder(radius, length, App.Vector(*origin), App.Vector(*axis))


def _rounded_opening(x, y, z, width, depth, height, radius=1.0):
    shape = _box((x, y, z), (width, depth, height))
    edges = [edge for edge in shape.Edges
             if abs(edge.BoundBox.YLength - depth) < EPSILON]
    return shape.makeFillet(radius, edges)


@lru_cache(maxsize=1)
def load_case_model():
    """実コードの寸法と形状を読む。参照生成の文書は必ず閉じる。"""
    model = runpy.run_path(str(CASE_SOURCE))
    App.closeDocument(model['doc'].Name)
    return model


def _rect_wire(x, y, z, width, height):
    points = [App.Vector(x, y, z), App.Vector(x + width, y, z),
              App.Vector(x + width, y, z + height), App.Vector(x, y, z + height)]
    return Part.makePolygon(points + points[:1])


def _nut_pocket(x, y, z, side):
    radius = NUT_ACROSS_FLATS / math.sqrt(3)
    vertices = [App.Vector(x + radius * math.cos(i * math.pi / 3), y,
                           z + radius * math.sin(i * math.pi / 3)) for i in range(6)]
    hexagon = Part.Face(Part.makePolygon(vertices + vertices[:1])).extrude(
        App.Vector(0, NUT_POCKET_LENGTH, 0))
    slot_x = x if side > 0 else x - STEM_RADIUS - 1
    entry = _box((slot_x, y, z - NUT_ACROSS_FLATS / 2),
                 (STEM_RADIUS + 1, NUT_POCKET_LENGTH, NUT_ACROSS_FLATS))
    return hexagon.fuse(entry)


def controller_front_face(parameters=None, case_model=None):
    """扉とともに動く左右2部品、参考つまみ・表示器、取付穴と検査情報を返す。

    partsの名称は既存の扉回転対象であるcontrol_panel_から始める。
    mount_holesは背面取付板へ追加すべき通し穴。前面にはねじ頭を出さない。
    """
    p = parameters or FixedRackParameters()
    source = case_model if case_model is not None else load_case_model()
    cx = (source['envelope_x'] + source['outer_right']) / 2
    cy = (source['envelope_y'] + source['envelope_back']) / 2
    w_shift = THICKNESS - source['bottom_z']
    lid_y = p.controller_origin_y - source['lid_top_z'] - w_shift
    front_y = lid_y
    rear_y = front_y + FACE_THICKNESS
    backing_y = p.controller_origin_y + 3
    width, z_bottom, height = 360.0, 8.0, 140.0
    mounts = [{'x': sign * x, 'z': z} for sign in (-1, 1)
              for x in (15.0, 168.0) for z in (18.0, 138.0)]
    nut_y = backing_y + BACKING_THICKNESS - MOUNT_SCREW_LENGTH + 1.2
    # ねじ先端の向こうに約1mmの逃げを残し、前面を貫通させない。
    blind_start_y = rear_y + 4.0
    controls, tools, references = [], [], []
    for row, center_z in enumerate(p.controller_centers_z):
        for col, center_x in enumerate((-90.0, 90.0)):
            window = {'x': center_x + source['window_x'] - cx,
                      'z': center_z + source['window_y'] - cy,
                      'width': source['window_length'], 'height': source['window_width']}
            knob_x = center_x + source['ENCODER_X'] - cx
            knob_z = center_z + source['ENCODER_Y'] - cy
            knob_tip_y = p.controller_origin_y - source['KNOB_TOP_Z'] - w_shift
            # 蓋全体とそのねじを露出したまま面内に収める。開口幅を軸穴だけに
            # 限定しないため、つまみの露出と指の横からの接触を失わない。
            clearance = LID_PERIMETER_CLEARANCE
            opening_x = center_x + source['envelope_x'] - cx - clearance
            opening_z = center_z + source['envelope_y'] - cy - clearance
            opening_width = source['envelope_length'] + 2 * clearance
            opening_height = source['envelope_width'] + 2 * clearance
            tools.append(_rounded_opening(opening_x, front_y - 1, opening_z,
                                          opening_width, FACE_THICKNESS + 8,
                                          opening_height,
                                          source['OUTER_CORNER_RADIUS'] + clearance))
            controls.append({'row': row, 'column': col, 'window': window,
                             'knob_center_xz_mm': [knob_x, knob_z],
                             'knob_tip_y_mm': knob_tip_y,
                             'knob_diameter_mm': source['KNOB_PASS_DIAMETER'],
                             'knob_exposure_above_existing_lid_mm': lid_y - knob_tip_y,
                             'knob_projection_ahead_of_added_face_mm': front_y - knob_tip_y,
                             'lid_opening': {'x': opening_x, 'z': opening_z,
                                             'width': opening_width, 'height': opening_height,
                                             'perimeter_clearance_mm': clearance},
                             'lid_screw_centers_xz_mm': [
                                 [center_x + x - cx, center_z + y - cy]
                                 for x, y in source['screw_centers']]})
            references.append({'name': f'case_{row}_{col}_knob',
                               'label': '既存つまみの露出部・正本の先端高さによる参考外形',
                               'shape': _cylinder((knob_x, knob_tip_y, knob_z),
                                                  source['KNOB_PASS_DIAMETER'] / 2,
                                                  lid_y - knob_tip_y),
                               'role': 'controller_knob_reference'})
            display_y = p.controller_origin_y - source['DISPLAY_TOP_Z'] - w_shift
            references.append({'name': f'case_{row}_{col}_display',
                               'label': '既存表示器の表示側・実測外形による参考面',
                               'shape': _box((center_x + source['DISPLAY_X'] - cx, display_y,
                                              center_z + source['DISPLAY_Y'] - cy),
                                             (source['DISPLAY_LENGTH'], 0.4, source['DISPLAY_WIDTH'])),
                               'role': 'controller_display_reference'})
    parts = []
    for col, sign in enumerate((-1, 1)):
        x0, x1 = (-width / 2, -SEAM_GAP / 2) if sign < 0 else (SEAM_GAP / 2, width / 2)
        shape = _box((x0, front_y, z_bottom), (x1 - x0, FACE_THICKNESS, height))
        # 外周と中央の背面リブ。上段ケースの上端143.8mmを避ける。
        for z in (z_bottom, z_bottom + height - 3):
            shape = shape.fuse(_box((x0, rear_y, z), (x1 - x0, 6, 3)))
        for x in (x0, x1 - 3):
            shape = shape.fuse(_box((x, rear_y, z_bottom), (3, 6, height)))
        for mount in (m for m in mounts if m['x'] * sign > 0):
            x, z = mount['x'], mount['z']
            stem = _cylinder((x, rear_y - 0.1, z), STEM_RADIUS,
                             backing_y - rear_y + 0.1)
            stem = stem.cut(_cylinder((x, blind_start_y, z), MOUNT_RADIUS,
                                      backing_y - blind_start_y + 1))
            stem = stem.cut(_nut_pocket(x, nut_y, z, sign))
            shape = shape.fuse(stem)
        for tool in tools:
            shape = shape.cut(tool)
        parts.append({'name': f'control_panel_face_{col}',
                      'label': ('左' if sign < 0 else '右') + 'の共通操作面・背面から固定する支柱付き',
                      'shape': shape.removeSplitter(), 'role': 'controller_face'})
    metadata = {'case_source': str(CASE_SOURCE.relative_to(ROOT)),
                'axes': {'u': [1, 0, 0], 'v': [0, 0, 1], 'w': [0, -1, 0]},
                'case_origin_y_mm': p.controller_origin_y,
                'case_normalization': {'center_x_mm': cx, 'center_y_mm': cy,
                                       'height_shift_mm': w_shift},
                'face_front_y_mm': front_y, 'face_rear_y_mm': rear_y,
                'existing_lid_front_y_mm': lid_y,
                'lid_perimeter_clearance_mm': LID_PERIMETER_CLEARANCE,
                'face_thickness_mm': FACE_THICKNESS, 'face_width_mm': width,
                'face_height_mm': height, 'split_count': 2, 'seam_gap_mm': SEAM_GAP,
                'controls': controls, 'existing_lids_flush_with_common_face': True,
                'finger_probe_diameter_mm': 2 * FINGER_PROBE_RADIUS,
                'added_face_view_angle_degrees': ADDED_FACE_VIEW_ANGLE_DEGREES,
                'view_scope': '各蓋を面内の開口へ収め、既存蓋の窓の前方視線を追加面が妨げないこと。表示器から既存蓋までの視野と実際の視認性は未検証。',
                'mounting': {'backing_front_y_mm': backing_y,
                             'backing_thickness_mm': BACKING_THICKNESS,
                             'screw': 'M4×40mm六角穴付きねじ・頭下長',
                             'screw_count': len(mounts), 'nut': 'M4六角ナット',
                             'nut_count': len(mounts), 'nut_pocket_y_mm': nut_y,
                             'nut_pocket_length_mm': NUT_POCKET_LENGTH,
                             'blind_hole_front_y_mm': blind_start_y,
                             'rear_access_required': True},
                'physical_validation': '表示器の視認、指の操作、ねじとナットの適合、支柱の強度、印刷後の組立は未検証。'}
    mount_holes = [{'origin': [m['x'], backing_y - 1, m['z']],
                    'radius': MOUNT_RADIUS, 'length': BACKING_THICKNESS + 2,
                    'axis': [0, 1, 0]} for m in mounts]
    result = {'parts': parts, 'references': references, 'mount_holes': mount_holes,
              'metadata': metadata}
    result['validation'] = validate_front_face(result, source, p)
    return result


def operation_probes(metadata):
    """追加操作面で確保する空間。指は仮の直径24mm円柱として扱う。"""
    probes = []
    lid_y, front_y = metadata['existing_lid_front_y_mm'], metadata['face_front_y_mm']
    depth = lid_y - front_y + 0.2
    expand = depth * math.tan(math.radians(metadata['added_face_view_angle_degrees']))
    for control in metadata['controls']:
        x, z = control['knob_center_xz_mm']
        name = f"{control['row']}_{control['column']}"
        probes.append({'name': 'finger_' + name, 'kind': 'finger',
                       'shape': _cylinder((x, front_y - 0.1, z), FINGER_PROBE_RADIUS, depth)})
        w = control['window']
        narrow = _rect_wire(w['x'], lid_y + 0.1, w['z'], w['width'], w['height'])
        wide = _rect_wire(w['x'] - expand, front_y - 0.1, w['z'] - expand,
                          w['width'] + 2 * expand, w['height'] + 2 * expand)
        probes.append({'name': 'display_' + name, 'kind': 'display',
                       'shape': Part.makeLoft([narrow, wide], True)})
        for index, (screw_x, screw_z) in enumerate(control['lid_screw_centers_xz_mm']):
            probes.append({'name': f'lid_screw_{name}_{index}', 'kind': 'lid_screw',
                           'shape': _cylinder((screw_x, lid_y - 20, screw_z),
                                              2.25, 20.1)})
    return probes


def validate_front_face(result, source=None, parameters=None):
    """印刷外形、元ケースとの干渉、表示と指の仮空間を実形状で確認する。"""
    source = source if source is not None else load_case_model()
    p = parameters or FixedRackParameters()
    metadata = result['metadata']
    parts = result['parts']
    records = []
    for part in parts:
        shape = part['shape']
        if not shape.isValid() or not shape.isClosed() or len(shape.Solids) != 1:
            raise ValueError('共通操作面が閉じた単一部品ではありません: ' + part['name'])
        bounds = shape.optimalBoundingBox(False)
        dimensions = [bounds.XLength, bounds.YLength, bounds.ZLength]
        if max(dimensions) > p.usable_print_size + EPSILON:
            raise ValueError('共通操作面が造形範囲を超えています: ' + part['name'])
        records.append({'name': part['name'], 'dimensions_mm': dimensions})
    if parts[0]['shape'].common(parts[1]['shape']).Volume > EPSILON:
        raise ValueError('左右の共通操作面が干渉しています')
    normalization = metadata['case_normalization']
    shift = App.Vector(-normalization['center_x_mm'], -normalization['center_y_mm'],
                       normalization['height_shift_mm'])
    normalized = []
    for name in ('body_final', 'lid_final'):
        shape = source[name].copy()
        shape.translate(shift)
        normalized.append(shape)
    for control in metadata['controls']:
        if control['knob_projection_ahead_of_added_face_mm'] <= 0:
            raise ValueError('つまみ先端が追加面へ埋まっています')
        for shape in normalized:
            placed = place(shape, ((-90, 90)[control['column']], p.controller_origin_y,
                                   p.controller_centers_z[control['row']]),
                           (1, 0, 0), (0, 0, 1), (0, -1, 0))
            for part in parts:
                if part['shape'].common(placed).Volume > EPSILON:
                    raise ValueError('共通操作面と既存ケースが干渉しています')
    probes = operation_probes(metadata)
    for probe in probes:
        for part in parts:
            if part['shape'].common(probe['shape']).Volume > EPSILON:
                raise ValueError('共通操作面が表示または指の空間を塞いでいます: ' + probe['name'])
    mounting = metadata['mounting']
    tip_y = mounting['backing_front_y_mm'] + BACKING_THICKNESS - MOUNT_SCREW_LENGTH
    if tip_y - mounting['blind_hole_front_y_mm'] < 0.5:
        raise ValueError('操作面の固定ねじ先端に逃げがありません')
    if not (tip_y < mounting['nut_pocket_y_mm'] and
            mounting['nut_pocket_y_mm'] + NUT_POCKET_LENGTH < mounting['backing_front_y_mm']):
        raise ValueError('操作面の固定ねじがナットを通過しません')
    return {'status': 'passed', 'parts': records, 'existing_case_collision': False,
            'display_viewing_corridor_count': 6, 'finger_access_probe_count': 6,
            'existing_lid_screw_access_count': 24,
            'existing_knob_exposure_preserved': True,
            'finger_probe_diameter_mm': 2 * FINGER_PROBE_RADIUS,
            'mount_screw_tip_clearance_mm': tip_y - mounting['blind_hole_front_y_mm'],
            'scope': '追加面と既存ケースの干渉、表示窓の前方視線、仮の指の空間、固定ねじ長さの幾何検査。実物の操作性と強度は未検証。'}
