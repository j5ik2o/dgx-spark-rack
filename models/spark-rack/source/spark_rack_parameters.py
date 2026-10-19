"""Spark本体ラックの寸法の正本。数値はすべてmm。"""
from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class BodyFrameParameters:
    """Spark本体を骨格に使う2段×2列の寸法候補。接触部・荷重・冷却は未実測。"""
    spark_width: float = 150
    spark_depth: float = 150
    spark_height: float = 50.5
    column_gap: float = 20
    stack_gap: float = 20
    lower_base: float = 60
    corner_inside: float = 20
    corner_outside: float = 8
    corner_grip: float = 6
    foot_grip: float = 12
    fit_clearance: float = 0.3
    top_riser: float = 16
    beam_width: float = 16
    beam_height: float = 10
    beam_overhang: float = 16
    tray_thickness: float = 4
    network_standoff: float = 63
    network_rail_depth: float = 236
    switch_front_y: float = -10
    comet_front_y: float = -40
    kvm_front_y: float = 120
    front_fan_gap: float = 30
    rear_fan_gap: float = 230
    fan_size: float = 140
    fan_depth: float = 27
    fan_pitch: float = 124.5
    fan_opening: float = 132
    fan_plate: float = 4
    fan_rim: float = 4
    fan_arm_size: float = 8
    power_fan_size: float = 120
    power_fan_pitch: float = 105
    power_fan_opening: float = 114
    power_fan_center_y: float = 234
    power_fan_center_z: float = 64
    power_fan_gap: float = 20
    power_fan_arm_overlap: float = 8
    power_first_y: float = 5
    power_row_pitch: float = 135
    power_bottom: float = 16
    power_tray_size: float = 110
    controller_offset: float = 20
    controller_right_y: float = 40
    controller_left_y: float = 106
    controller_first_z: float = 26
    controller_pitch_z: float = 50
    controller_width: float = 100
    controller_depth: float = 44
    controller_height: float = 46
    rear_connector_depth: float = 60
    fan_removal_distance: float = 110
    usable_print_size: float = 246
    cable_rear_y: float = 350
    cable_side_x: float = 260
    cable_storage_radius: float = 55
    cable_storage_center_z: float = 256
    cable_underfloor_z: float = 6
    switch_stop_height: float = 8
    switch_stop_thickness: float = 4
    switch_fit_clearance: float = .5
    switch_band_width: float = 16
    switch_band_thickness: float = 1.5
    joinery_clearance: float = .15
    joinery_max_depth: float = 5
    joint_key_min_width: float = 1.8
    joint_min_ligament: float = 1.0
    fan_pin_split_length: float = 12
    fan_pin_flat_offset: float = 1.2

    @property
    def core_width(self):
        return 2 * self.spark_width + self.column_gap

    @property
    def upper_base(self):
        return self.lower_base + self.spark_height + self.stack_gap

    @property
    def core_top(self):
        return self.upper_base + self.spark_height

    @property
    def beam_z(self):
        return self.core_top + self.top_riser

    @property
    def accessory_surface(self):
        return self.beam_z + self.beam_height

    @property
    def network_rail_z(self):
        return self.accessory_surface + self.network_standoff

    def validate(self):
        import math
        coordinates = {'switch_front_y', 'comet_front_y'}
        for key, value in asdict(self).items():
            if not math.isfinite(value) or (key not in coordinates and value <= 0):
                raise ValueError('本体連結案の寸法は有限の正の値にしてください: ' + key)
        if self.stack_gap <= 2 * self.fit_clearance:
            raise ValueError('本体間の接続部を置く隙間が不足しています')
        if self.corner_inside >= min(self.spark_width, self.spark_depth) / 2:
            raise ValueError('コーナー接続部が本体の半分以上を覆っています')
        if self.rear_fan_gap <= self.rear_connector_depth:
            raise ValueError('背面ファンが端子の仮空間へ入ります')
        if self.controller_pitch_z <= self.controller_height:
            raise ValueError('制御器の段間隔が不足しています')
        if self.spark_depth + self.rear_fan_gap - self.fan_plate <= self.cable_rear_y + 8:
            raise ValueError('背面ファンと配線区画の間隔が不足しています')
        if self.power_bottom - self.tray_thickness <= self.cable_underfloor_z + 4:
            raise ValueError('電源受けの下に配線を通す高さが不足しています')
        if self.joinery_max_depth < 2:
            raise ValueError('ほぞの最大差し込み量は2mm以上にしてください')
        if self.power_fan_arm_overlap < 8:
            raise ValueError('電源ファンの接合面の重なりは8mm以上にしてください')
        if not 5 <= self.fan_pin_split_length < self.fan_depth+self.fan_plate-5:
            raise ValueError('割りピンの弾性部は5mm以上で、根元を5mm以上残してください')
        if not 0 < self.fan_pin_flat_offset < 1.8:
            raise ValueError('割りピンの造形面は軸の半径1.8mm以内にしてください')


@dataclass(frozen=True)
class FixedRackParameters:
    """固定段と独立電源区画を持つ4台ラックの設計候補。単位mm。"""
    width: float = 544
    front_y: float = -350
    rear_y: float = 110
    height: float = 560
    section: float = 28
    skin: float = 4
    lower_base: float = 208
    row_pitch: float = 220
    column_pitch: float = 180
    spark_width: float = 150
    spark_depth: float = 150
    spark_height: float = 50.5
    spark_front_y: float = -150
    spark_front_clearance: float = 100
    spark_side_clearance: float = 20
    spark_rear_clearance: float = 400
    fan_size: float = 140
    fan_depth: float = 27
    fan_pitch: float = 124.5
    fan_opening: float = 132
    power_fan_size: float = 120
    power_fan_pitch: float = 105
    power_ceiling_z: float = 152
    power_ceiling_thickness: float = 4
    controller_origin_y: float = -302
    controller_lid_projection: float = 34.67
    controller_centers_z: tuple = (34, 79, 124)
    panel_split_y: float = -120
    panel_splits_z: tuple = (176, 396)
    lap_length: float = 24
    fit_clearance: float = 0.3
    usable_print_size: float = 246
    tray_width: float = 158
    tray_depth: float = 156
    tray_thickness: float = 8
    hand_margin: float = 12
    cable_storage_height: float = 24
    vent_slot_width: float = 7.5
    vent_rib_width: float = 2.5
    vent_slot_height: float = 24
    vent_pitch: float = 16
    vent_row_pitch: float = 34

    @property
    def depth(self):
        return self.rear_y - self.front_y

    @property
    def inner_width(self):
        return self.width - 2 * self.section

    @property
    def upper_base(self):
        return self.lower_base + self.row_pitch

    @property
    def fan_front_y(self):
        return self.front_face_y + 4

    @property
    def front_face_y(self):
        return self.controller_origin_y - self.controller_lid_projection

    @property
    def actual_fan_to_spark_gap(self):
        return self.spark_front_y - self.fan_front_y - self.fan_depth

    @property
    def switch_center_z(self):
        return self.lower_base + self.spark_height / 2 + self.row_pitch / 2

    def values(self):
        return asdict(self)

    def validate(self):
        import math
        numeric = {k: v for k, v in self.values().items() if isinstance(v, (int, float))}
        coordinates = {'front_y', 'rear_y', 'controller_origin_y', 'panel_split_y', 'spark_front_y'}
        if not all(math.isfinite(v) and (k in coordinates or v > 0) for k, v in numeric.items()):
            raise ValueError('寸法は有限の正の値にしてください')
        if not self.front_y < self.panel_split_y < self.rear_y:
            raise ValueError('側枠の奥行分割が外形に収まりません')
        if not self.front_y < self.front_face_y < self.spark_front_y:
            raise ValueError('共通の前面が枠の外へ出ています')
        if self.actual_fan_to_spark_gap < self.spark_front_clearance:
            raise ValueError('本体前方の通風予約が不足しています')
        if not 0 < self.panel_splits_z[0] < self.panel_splits_z[1] < self.height:
            raise ValueError('側枠の高さ分割が外形に収まりません')
        overlap = self.lap_length / 2
        depths = (self.panel_split_y - self.front_y + overlap, self.rear_y - self.panel_split_y + overlap)
        heights = (self.panel_splits_z[0] + overlap,
                   self.panel_splits_z[1] - self.panel_splits_z[0] + 2 * overlap,
                   self.height - self.panel_splits_z[1] + overlap)
        if max(*depths, *heights) > self.usable_print_size:
            raise ValueError('側枠の重ね継ぎを含む部品外形が造形範囲を超えます')
        if self.column_pitch < self.spark_width + self.spark_side_clearance:
            raise ValueError('本体の左右間隔が不足しています')
        if self.lower_base - (self.fan_size - self.spark_height) / 2 <= self.power_ceiling_z + self.power_ceiling_thickness:
            raise ValueError('電源区画が下段ファンの正面に重なります')
        if self.upper_base + (self.spark_height + self.fan_size) / 2 >= self.height - self.section:
            raise ValueError('上段ファンが天枠へ重なります')


@dataclass(frozen=True)
class SwitchPlacementComparisonParameters:
    """専用段の比較用寸法。手と支持の余裕は仮定で、冷却の保証値ではない。"""
    boundary_thickness: float = 4
    support_beam_height: float = 12
    support_plate_thickness: float = 8
    upper_hand_margin: float = 12
    upper_frame_height: float = 28
    node_support_height: float = 12
    switch_face_y: float = 100

    def module_height(self, switch_height):
        return (self.boundary_thickness + self.support_beam_height + self.support_plate_thickness
                + switch_height + self.upper_hand_margin + self.upper_frame_height)


@dataclass(frozen=True)
class UpperSwitchBayParameters:
    """上枠を共有する上部専用段。余裕と支持の寸法は設計仮定で、冷却・保守の指定値ではない。

    床下の積み上げは配置比較と同じ仕切り4mm、支持帯12mm、トレー8mmとする。
    preserve_front_service は、スイッチのラック前側の面へ手と部品を出す経路を残すかを表す。
    """
    floor_plate: float = 4
    support_band: float = 12
    tray_thickness: float = 8
    tray_depth: float = 240
    tray_rim: float = 16
    tray_split_gap: float = 0.3
    fence_height: float = 8
    fence_thickness: float = 4
    switch_side_clearance: float = 0.5
    side_hand_margin: float = 12
    upper_hand_margin: float = 12
    front_service_clearance: float = 4
    floor_front_gap: float = 4
    front_stop_depth: float = 6
    band_width: float = 20
    switch_face_y: float = 100
    preserve_front_service: bool = True

    @property
    def under_switch(self):
        return self.floor_plate + self.support_band + self.tray_thickness

    def validate(self):
        import math
        for key, value in asdict(self).items():
            if isinstance(value, bool):
                continue
            if not math.isfinite(value) or (key != 'switch_face_y' and value <= 0):
                raise ValueError('上部専用段の寸法は有限の正の値にしてください: ' + key)
        if self.tray_rim * 2 >= self.tray_depth:
            raise ValueError('トレーの縁が奥行を占めています')


@dataclass(frozen=True)
class RemoteConsoleParameters:
    """上下のSparkの間に置く遠隔操作機器の棚と前面板。余裕の寸法は設計仮定。

    機器の外形は未確定値の記録から読む。Comet Proは公式資料の値、TESmart切替器はユーザー提供の参考寸法。
    """
    shelf_plate: float = 4
    shelf_rib: float = 8
    panel_thickness: float = 4
    panel_center_half_width: float = 60
    window_margin: float = 3
    slot_pitch: float = 10
    comet_side_margin: float = 12
    comet_top_margin: float = 6
    comet_rear_cable_space: float = 60
    kvm_rear_face_y: float = 90
    kvm_rear_connector_space: float = 50
    kvm_front_connector_space: float = 40
    kvm_hand_margin: float = 12
    band_width: float = 20
    front_gap: float = 4
    flange_thickness: float = 4
    flange_overlap: float = 20
    sled_thickness: float = 4

    @property
    def shelf_thickness(self):
        return self.shelf_plate + self.shelf_rib

    def validate(self):
        import math
        for key, value in asdict(self).items():
            if not math.isfinite(value) or (key != 'kvm_rear_face_y' and value <= 0):
                raise ValueError('遠隔操作機器の棚の寸法は有限の正の値にしてください: ' + key)


@dataclass(frozen=True)
class FrontFinishParameters:
    """上部専用段の案の前面と天面を閉じる板。溝の寸法は前面のファン格子にそろえる。"""
    panel_thickness: float = 4
    flange_thickness: float = 4
    lid_plate: float = 4
    lid_rib: float = 8
    lid_lip: float = 6
    lid_slot_length: float = 70
    filler_flange_depth: float = 12
    slot_margin: float = 8
    edge_margin: float = 12

    def validate(self):
        import math
        for key, value in asdict(self).items():
            if not math.isfinite(value) or value <= 0:
                raise ValueError('前面と天面の板の寸法は有限の正の値にしてください: ' + key)


@dataclass(frozen=True)
class GrilleParameters:
    """前面、天板、側枠の通気の模様。slotsは縦溝、honeycombは正六角形の穴。

    壁1.6mmは0.4mmノズルの4本分。穴の対辺10mmで、角から角まで11.5mmとし、
    直径12mmの指を通さない。
    """
    style: str = 'slots'
    hex_across_flats: float = 10
    hex_wall: float = 1.6
    minimum_fragment_area: float = 12

    def validate(self):
        import math
        if self.style not in ('slots', 'honeycomb'):
            raise ValueError('通気の模様は slots か honeycomb です')
        for key in ('hex_across_flats', 'hex_wall', 'minimum_fragment_area'):
            value = getattr(self, key)
            if not math.isfinite(value) or value <= 0:
                raise ValueError('ハニカムの寸法は有限の正の値にしてください: ' + key)


@dataclass(frozen=True)
class Parameters:
    module_width: float = 210
    module_depth: float = 230
    frame_height: float = 170
    side_thickness: float = 12
    stack_gap: float = 4
    column_gap: float = 10
    fit_clearance: float = 0.3
    dgx_width: float = 150
    dgx_depth: float = 150
    dgx_height: float = 50.5
    dgx_front: float = 60
    support_top: float = 60
    fan_size: float = 140
    fan_depth: float = 27
    fan_hole_pitch: float = 124.5
    fan_mount_hole: float = 4.5
    pin_diameter: float = 4
    locator_diameter: float = 6
    window_radius: float = 3
    nut_af: float = 7
    tenon_length: float = 9
    beam_width: float = 20
    beam_height: float = 8
    cassette_plate: float = 4
    fascia_rail_width: float = 12
    controller_y: float = 114
    controller_z: float = 60

    @property
    def inner_x(self): return self.module_width / 2 - self.side_thickness
    @property
    def pin_x(self): return self.inner_x + 4
    @property
    def post_x(self): return (self.module_width-self.side_thickness)/2
    @property
    def front_y(self): return self.fan_depth + 11
    @property
    def support_front_y(self): return self.dgx_front + 22
    @property
    def support_rear_y(self): return self.dgx_front + self.dgx_depth - 12
    @property
    def upper_bar_y(self): return self.module_depth - 50
    @property
    def fan_center_z(self): return self.frame_height/2
    @property
    def cassette_upper_z(self): return self.frame_height-25
    @property
    def rim(self): return (self.fan_size+22)/2
    @property
    def column_pitch(self): return self.module_width+self.column_gap
    @property
    def row_pitch(self): return self.frame_height+self.stack_gap

    def values(self):
        return asdict(self)

    def validate(self):
        assert 0 < self.fit_clearance < 1
        assert self.side_thickness > self.tenon_length+self.fit_clearance
        assert self.module_width > self.fan_size+2*self.side_thickness
        assert self.frame_height > self.fan_size
        assert self.module_depth > self.support_rear_y+self.beam_width/2
        assert self.support_top > 30 and self.window_radius > 0
        assert 0 < self.fascia_rail_width <= self.side_thickness


def body_frame_scene(p, pending, inventory, network):
    """本体骨格案の機器・接続部・受け・端子予約の配置を定義する。"""
    from body_frame_layout import box, REFERENCES, REQUIREMENTS
    equipment, corners, boxes = [], [], []
    half = p.core_width / 2
    center_x = (p.spark_width + p.column_gap) / 2
    for col, x in enumerate((-half, p.column_gap / 2)):
        for row, z in enumerate((p.lower_base, p.upper_base)):
            equipment.append(box(f'spark_{col}_{row}', f'Spark・{"左" if col == 0 else "右"}{"下" if row == 0 else "上"}',
                                 (x, 0, z), (p.spark_width, p.spark_depth, p.spark_height), 'spark'))
    stages = (('foot', 0, p.lower_base + p.foot_grip),
              ('joint', p.lower_base + p.spark_height - p.corner_grip,
               p.stack_gap + 2 * p.corner_grip),
              ('top', p.core_top - p.corner_grip, p.corner_grip + p.top_riser))
    for stage, z, h in stages:
        for end, y in (('front', -p.corner_outside), ('back', p.spark_depth - p.corner_inside)):
            # 端子が未実測でも背面全体を開ける。背面側は側面と上下の面だけで保持する。
            depth = p.corner_inside + (p.corner_outside if end == 'front' else 0)
            for group, spans in (
                ('left', [(-half - p.corner_outside, p.corner_inside + p.corner_outside)]),
                ('pair', [(-p.column_gap / 2 - p.corner_inside, p.corner_inside + p.corner_outside),
                          (p.column_gap / 2 - p.corner_outside, p.corner_inside + p.corner_outside)]),
                ('right', [(half - p.corner_inside, p.corner_inside + p.corner_outside)])):
                pieces = [dict(origin=[x, y, z], size=[w, depth, h]) for x, w in spans]
                if group == 'pair':
                    x0, x1 = spans[0][0] + spans[0][1] - 1, spans[1][0] + 1
                    pieces.append(dict(origin=[x0, y, z], size=[x1 - x0, depth, h]))
                stage_label = {'foot': '脚', 'joint': '上下段', 'top': '上部機器'}[stage]
                group_label = {'left': '左列の外側', 'pair': '左右の列の間', 'right': '右列の外側'}[group]
                end_label = '前側' if end == 'front' else '背面側'
                corners.append(dict(name=f'core_{stage}_{group}_{end}', label=f'{stage_label}の局所接続部・{group_label}・{end_label}',
                                    kind='body_connector', pieces=pieces))
    beam_half = half + p.beam_overhang
    beam_ys = (10, p.spark_depth - p.corner_inside)
    for row, y in enumerate(beam_ys):
        for side, x in enumerate((-beam_half, 0)):
            boxes.append(box(f'accessory_beam_{row}_{side}', '周辺機器の短い横梁',
                             (x, y, p.beam_z), (beam_half, p.beam_width, p.beam_height), 'accessory_support'))
    rail_x = half + p.corner_outside - 2
    for side in (-1, 1):
        x = side * rail_x - p.beam_width / 2
        for row, y in enumerate(beam_ys):
            boxes.append(box(f'network_riser_{side}_{row}', '本体上の機器だけを支える支柱',
                             (x, y, p.accessory_surface), (p.beam_width, p.beam_width, p.network_standoff),
                             'network_support'))
        boxes.append(box(f'network_rail_{side}', 'CRS812を底面で受ける短いレール',
                         (x, beam_ys[0], p.network_rail_z),
                         (p.beam_width, p.network_rail_depth, p.beam_height), 'network_support'))
    remote = pending['remote_console']
    cw, cd, ch = remote['comet_pro']['body_mm']
    kw, kd, kh = remote['kvm_switch']['body_mm']
    device_z = p.accessory_surface + p.tray_thickness
    equipment += [
        box('comet', 'GL-RM10・前面に画面', (-cw / 2, p.comet_front_y, device_z), (cw, cd, ch), 'comet'),
        box('kvm', 'TESmart HKS401-P23・未実測の参考外形', (-kw / 2, p.kvm_front_y, device_z), (kw, kd, kh), 'kvm'),
    ]
    sw = network['final_phase']['switch']['body_envelope_mm']
    equipment.append(box('crs812', 'CRS812・耳と奥行は未実測',
                         (-sw[0] / 2, p.switch_front_y, p.network_rail_z + p.beam_height), sw, 'switch'))
    boxes.append(box('comet_tray', 'GL-RM10の小さな載せ台',
                     (-cw / 2 - 4, p.comet_front_y, p.accessory_surface),
                     (cw + 8, cd + 4, p.tray_thickness), 'accessory_tray', tray_device='comet'))
    for side, x in enumerate((-kw / 2 - 5, 0)):
        boxes.append(box(f'kvm_tray_{side}', '切替器の分割した載せ台',
                         (x, p.kvm_front_y - 4, p.accessory_surface),
                         (kw / 2 + 5, kd + 8, p.tray_thickness), 'accessory_tray',
                         tray_device='kvm', tray_side=side))
    adapter = [99.05, 98.99, 35.17]
    for col, x in enumerate((-center_x, center_x)):
        for row in range(2):
            y = p.power_first_y + row * p.power_row_pitch
            equipment.append(box(f'power_{col}_{row}', '電源アダプター・参考外形',
                                 (x - adapter[0] / 2, y, p.power_bottom), adapter, 'power'))
            size = p.power_tray_size
            boxes.append(box(f'power_tray_{col}_{row}', '電源を囲い込まない小さな受け',
                             (x - size / 2, y - (size - adapter[1]) / 2, p.power_bottom - p.tray_thickness),
                             (size, size, p.tray_thickness), 'power_tray'))
    fan_z = p.lower_base + (2 * p.spark_height + p.stack_gap) / 2
    fans = []
    for col, x in enumerate((-center_x, center_x)):
        for end, y, axis in (
                ('front', -p.front_fan_gap - p.fan_depth, [0, -1, 0]),
                ('rear', p.spark_depth + p.rear_fan_gap, [0, 1, 0])):
            fans.append(box(f'spark_fan_{col}_{end}', f'Spark列の{"前面" if end == "front" else "背面"}・140mm固定ファン',
                            (x - p.fan_size / 2, y, fan_z - p.fan_size / 2),
                            (p.fan_size, p.fan_depth, p.fan_size), 'fan',
                            axis=axis, fan_size=p.fan_size, pitch=p.fan_pitch, opening=p.fan_opening,
                            mounting='fixed_axis_aligned', mount_face=end, attachment_stage='joint'))
    side_plane = half + p.corner_outside + p.power_fan_gap
    for side in (-1, 1):
        x = side_plane + p.fan_plate if side > 0 else -side_plane - p.fan_plate - p.fan_depth
        fans.append(box(f'power_fan_{side}', '電源用・側面120mm固定ファン',
                        (x, p.power_fan_center_y - p.power_fan_size / 2,
                         p.power_fan_center_z - p.power_fan_size / 2),
                        (p.fan_depth, p.power_fan_size, p.power_fan_size), 'fan',
                        axis=[side, 0, 0], fan_size=p.power_fan_size,
                        pitch=p.power_fan_pitch, opening=p.power_fan_opening,
                        mounting='fixed_axis_aligned', mount_face='right' if side > 0 else 'left',
                        attachment_stage='foot'))
    equipment += fans
    controllers = []
    for side in (-1, 1):
        y = p.controller_right_y if side > 0 else p.controller_left_y
        u, v, w = [0, side, 0], [0, 0, 1], [side, 0, 0]
        dock_x = side * (half + p.controller_offset)
        for row in range(3):
            z = p.controller_first_z + row * p.controller_pitch_z
            x = dock_x - 3 if side > 0 else dock_x + 3 - p.controller_depth
            controller = box(f'controller_{side}_{row}', f'{"右" if side > 0 else "左"}側の{"下中上"[row]}段制御器・正立',
                             (x, y - p.controller_width / 2, z - p.controller_height / 2),
                             (p.controller_depth, p.controller_width, p.controller_height), 'controller',
                             dock_origin=[dock_x, y, z], u=u, v=v, w=w)
            controllers.append(controller)
            # 実際の取付位置は共通ドックの正本から形状生成時に求める。
            boxes.append(dict(name=f'controller_mount_{side}_{row}', label='制御器ごとの局所取付部',
                              kind='controller_mount', controller=controller['name']))
    equipment += controllers
    connectors = [
        box(f'{e["name"]}_ports', 'Spark背面の端子用の仮空間・実端子未確認',
            (e['origin'][0], p.spark_depth, e['origin'][2]),
            (p.spark_width, p.rear_connector_depth, p.spark_height), 'connector_space')
        for e in equipment if e['kind'] == 'spark'
    ]
    connectors += [
        box('comet_ports', 'GL-RM10の背面配線用の仮空間',
            (-cw / 2, p.comet_front_y + cd, device_z), (cw, 60, ch), 'connector_space'),
        box('kvm_ports', '切替器の背面配線用の仮空間',
            (-kw / 2, p.kvm_front_y + kd, device_z), (kw, 60, kh), 'connector_space'),
    ]
    models={'spark':'DGX Spark','switch':'CRS812','comet':'GL-RM10','kvm':'TESmart HKS401-P23'}
    for entry in equipment:
        if entry['kind'] in models:
            entry['model']=models[entry['kind']]
    scene = dict(parameters=asdict(p), equipment=equipment, corners=corners, boxes=boxes,
                connectors=connectors, references=list(REFERENCES) + [REQUIREMENTS],
                expected_inventory={'spark': 4, 'switch': 1, 'comet': 1, 'kvm': 1,
                                    'power': 4, 'controller': inventory['controllers']['quantity'],
                                    'fan_140': inventory['fans'][0]['quantity'],
                                    'fan_120': inventory['fans'][1]['quantity']},
                assumptions=[
                    'Sparkの箱の参考外形へ局所接続部を当てる。外装へ荷重を掛けることはメーカー確認・実測前。',
                    'CRS812の奥行は資料間の不一致が残るため268mmを参考値とする。足と取付耳は未確認。',
                    'TESmartの300×117×30mmは検索要約に基づく未実測の参考値。',
                    '背面ファンは直線方向へ外して端子へアクセスする。斜め取付やヒンジは使わない。',
                    'Spark下段の交換は、上の機器と上段を先に外す手順が必要。独立した引き出し式ではない。',
                ], manufacturing_geometry=False, physical_validation=False)
    return scene


def body_frame_routing(scene, p):
    """本体骨格案の配線・余長・留め部の配置を定義する。"""
    import math
    from body_frame_cables import rounded_path
    equipment = {e['name']: e for e in scene['equipment']}
    paths, mounts, storage = [], [], []

    def route(name, label, family, points, radius, diameter, endpoints, **extra):
        segments, length = rounded_path(points, radius)
        paths.append(dict(name=name, label=label, family=family, points=points,
                          segments=segments, centerline_length_mm=length,
                          radius_mm=radius, diameter_mm=diameter, endpoints=endpoints,
                          exact_port_positions_verified=False, length_fit_verified=False, **extra))

    def mount(name, label, origin, size, slots=False):
        mounts.append(dict(name=name, label=label, origin=origin, size=size,
                           kind='cable_mount', slots=slots))

    rear, outside = p.cable_rear_y, p.cable_side_x
    kvm_signal_z = equipment['kvm']['origin'][2]+19
    switch_network_z = equipment['crs812']['origin'][2]+22
    switch_power_z = equipment['crs812']['origin'][2]+26
    for col, side in enumerate((-1, 1)):
        side_label = '左' if side < 0 else '右'
        anchor_x = p.core_width / 2 + 4
        mount(f'cable_tie_arm_{col}', side_label + 'の中間接続部へ留める短い配線腕',
              [anchor_x if side > 0 else -anchor_x - 4, p.spark_depth,
               p.lower_base+p.spark_height+p.stack_gap/2-4], [4, 66, 8])
        mount(f'cable_tie_plate_{col}', side_label + 'の解除式結束バンドを通す束の留め板',
              [anchor_x if side > 0 else -anchor_x - 4, 216, 70], [4, 16, 104])
        mounts[-1]['tie_plate'] = True
        # 全段をつなぐ柱にはせず、上部の横梁だけから支持する。
        edge = p.core_width / 2 + p.beam_overhang
        arm_outer = outside + 42
        mount(f'cable_outreach_{col}', side_label + 'の上部横梁から出す短い腕',
              [edge if side > 0 else -(outside + 26), 134, p.beam_z],
              [outside + 26 - edge, 16, 10])
        mount(f'cable_side_arm_{col}', side_label + 'の余長受けだけを支える腕',
              [outside + 26 if side > 0 else -arm_outer, 134, p.beam_z],
              [16, 224, 10])
        mount(f'cable_storage_floor_{col}', side_label + 'の開放式余長受け・結束バンド用の穴',
              [outside - 32 if side > 0 else -arm_outer, 180, p.beam_z - 4],
              [74, 178, 4], slots=True)
        mounts[-1].update(feed_x=side * outside, feed_y=340)
        for turn in range(3):
            storage.append(dict(name=f'network_storage_{col}_{turn}',
                                label=side_label + f'の余長予約・{turn + 1}周目（実配線ではない）',
                                kind='cable_storage', family='network',
                                center=[side * (outside - 12 + turn * 12), 295, p.cable_storage_center_z],
                                normal=[1, 0, 0], radius=p.cable_storage_radius, diameter=8,
                                length_mm=2 * math.pi * p.cable_storage_radius))
        rear_tray = next(b for b in scene['boxes'] if b['name'] == f'power_tray_{col}_1')
        tray_back = rear_tray['origin'][1] + rear_tray['size'][1]
        mount(f'signal_storage_floor_{col}', side_label + 'の映像・USBの余長受け',
              [rear_tray['origin'][0], tray_back, 10],
              [rear_tray['size'][0], 366 - tray_back, 4], slots=True)
        mounts[-1].update(feed_x=side * 140, feed_y=338)
        for level in range(4):
            for radius in (30, 45):
                storage.append(dict(name=f'signal_storage_{col}_{level}_{radius}',
                                    label=side_label + 'の映像・USB余長の予約（実配線ではない）',
                                    kind='cable_storage', family='signal',
                                    center=[side * 85, 310, 20 + level * 13], normal=[0, 0, 1],
                                    radius=radius, diameter=12, length_mm=2 * math.pi * radius))
        split = [side * outside, rear, 200]
        for row in range(2):
            spark = equipment[f'spark_{col}_{row}']
            z = spark['origin'][2] + 22
            x = side * (140 - 10 * row)
            route(f'network_branch_{col}_{row}', f'{side_label}{"下" if row == 0 else "上"}段のネットワーク経路',
                  'network', [[x, p.spark_depth + 35, z], [x, rear, z],
                              [side * outside, rear, z], split], 42, 8,
                  [spark['name'], f'network_split_{col}'], cable_group=f'breakout_{col}')
            # 映像線とUSB線は同じ束の予約。束の内部で個別端子へ配る部分は未採寸。
            vx = side * (140 + 5 * row)
            route(f'video_usb_{col}_{row}', f'{side_label}{"下" if row == 0 else "上"}段の映像・USBの束',
                  'signal', [[vx, 150, z + 8], [vx, 300 + row * 20, z + 8],
                             [vx, 300 + row * 20, kvm_signal_z], [vx, 237, kvm_signal_z]],
                  20, 12, [spark['name'], 'kvm'], nominal_length_mm=1500)
            power = equipment[f'power_{col}_{row}']
            y, zpower = power['origin'][1], power['origin'][2] + 17
            px = side * (85 + row * 12)
            # 受けを8mm持ち上げ、下を通す。端子面は仮定で、現物に合わせる。
            route(f'spark_dc_{col}_{row}', side_label + f'の電源{row + 1}から本体への直流配線',
                  'dc', [[px, y, zpower], [px, y - 25, zpower], [px, y - 25, p.cable_underfloor_z],
                         [px, 320, p.cable_underfloor_z], [side * 140, 320, p.cable_underfloor_z],
                         [side * 140, 350, p.cable_underfloor_z],
                         [side * 140, 350, z + 15], [side * 140, 150, z + 15]],
                  10, 6, [power['name'], spark['name']])
            ac_y = y if row == 0 else y + power['size'][1]
            guide_y = -95 if row == 0 else 370
            outlet = [350 + col * 24 + row * 12, 0 if row == 0 else 90, 25]
            route(f'adapter_ac_{col}_{row}', side_label + f'の電源{row + 1}の交流配線',
                  'ac', [[side * 85, ac_y, zpower], [side * 85, guide_y, zpower],
                         [outlet[0], guide_y, zpower], [outlet[0], outlet[1], zpower]],
                  20, 8, [power['name'], 'external_power_strip'])
        route(f'network_trunk_{col}', side_label + 'の分岐点からCRS812への主線', 'network',
              [split, [side * outside, rear, switch_network_z],
               [side * 130, rear, switch_network_z], [side * 130, 293, switch_network_z]],
              42, 10, [f'network_split_{col}', 'crs812'], cable_group=f'breakout_{col}')
        route(f'switch_ac_{col}', f'CRS812の交流電源{col + 1}', 'ac',
              [[side * 170, -10, switch_power_z], [side * 170, -95, switch_power_z],
               [side * 240, -95, switch_power_z], [side * 240, -95, 30],
               [440 + col * 25, -95, 30], [440 + col * 25, 0, 30]],
              25, 8, ['crs812', 'external_power_strip'])
        for row in range(3):
            controller = equipment[f'controller_{side}_{row}']
            cy = controller['dock_origin'][1]
            cz = controller['dock_origin'][2]
            start = [side * (p.core_width / 2 + p.controller_offset + 41), cy, cz]
            disconnect = [side * 240, -65 if row == 0 else 355, 210 if row < 2 else 160]
            route(f'fan_feed_{col}_{row}', side_label + f'の制御器{row + 1}から着脱コネクターまで', 'control',
                  [start, [side * 240, cy, cz], [side * 240, cy, disconnect[2]], disconnect],
                  6, 4, [controller['name'], f'fan_disconnect_{col}_{row}'])
            fan_name = f'spark_fan_{col}_{"front" if row == 0 else "rear"}' if row < 2 else f'power_fan_{side}'
            fan = equipment[fan_name]
            if row < 2:
                fy = fan['origin'][1] + p.fan_depth / 2
                end = [side * 150, fy, fan['origin'][2]+fan['size'][2]-4.5]
                tail = [disconnect, [side * 150, disconnect[1], disconnect[2]],
                        [side * 150, fy, disconnect[2]], end]
            else:
                end = [side * 219, 290, 108]
                tail = [disconnect, [side * 240, 290, 160], [side * 240, 290, 108], end]
            route(f'fan_tail_{col}_{row}', side_label + f'のファン{row + 1}の取り外す短線', 'control',
                  tail, 6, 4, [f'fan_disconnect_{col}_{row}', fan_name], detachable_with=fan_name)
            route(f'controller_supply_{col}_{row}', side_label + f'の制御器{row + 1}の給電・センサー用経路予約', 'control',
                  [[start[0], cy + 10, cz], [side * 250, cy + 10, cz],
                   [side * 250, cy + 10, 170], [side * 250, 355, 170]],
                  6, 5, [controller['name'], 'auxiliary_supply_and_sensors'], unfinished_terminal=True)
    route('comet_video_usb', 'GL-RM10と切替器の映像・キーボード操作の束', 'signal',
          [[0, 44, 225], [0, 90, 225], [185, 90, 225], [185, 280, 225],
           [40, 280, 225], [40, 237, 225]], 18, 12, ['comet', 'kvm'])
    route('comet_ethernet', 'GL-RM10の管理用有線ネットワーク', 'signal',
          [[25, 44, 235], [25, 90, 235], [195, 90, 235], [195, 340, 235],
           [195, 340, 285], [195, 258, 285]], 15, 6, ['comet', 'crs812'])
    for name, x, y, z in [('comet', -25, 44, 240), ('kvm', -140, 237, 225)]:
        route(name + '_dc', name + 'の低電圧給電', 'dc',
              [[x, y, z], [x, y + 30, z], [-210, y + 30, z],
               [-210, 355, z], [-210, 355, 170]], 10, 5,
              [name, 'external_peripheral_adapters'], unfinished_terminal=True)
    airflow = [dict(name=f'airflow_{col}', label='Spark列の中央を開ける仮の排気通路',
                    origin=[side * 85 - 40, 210, 65], size=[80, p.spark_depth + p.rear_fan_gap - 4 - 210, 105])
               for col, side in enumerate((-1, 1))]
    return dict(paths=paths, storage=storage, mounts=mounts, airflow_spaces=airflow,
                endpoint_status='端子位置とプラグ形状は仮定。各端子への短い接続区間は未採寸。',
                path_scope='束の通過領域。束同士の重なりは許し、固定物と着脱経路との干渉を検査する。',
                external_regions=[dict(name='external_power_strip', label='机上別置きタップ・8口以上、補助電源と電源線余長の予約',
                                       origin=[320, 0, 0], size=[360, 90, 90],
                                       kind='external_reservation', purchased_product=False)],
                service_sequence=['電源を切り、対象ファンの着脱コネクターを外す。',
                                  '対象ファンの短線の留め具を開放し、短線をファン側へ寄せる。',
                                  '保持部の抜け止め用の角栓を外し、ファンと保持部を軸方向へ110mmまっすぐ引く。',
                                  '機器交換時は対象の結束バンドのロックを解除する。面ファスナーを併用した箇所も開放し、上部から順に分解する。'],
                unresolved=['端子中心、プラグ外形、実線径と束の内部配置',
                            '2m分岐ケーブルの主線・分岐線の長さ、分岐点の実寸と位置',
                            '電源タップの製品・定格・差込間隔、補助電源と周辺機器用アダプターの外形',
                            '制御器の給電仕様と温度センサーの取付・末端配線',
                            '保持帯と着脱コネクターの実物、実機での組立と冷却'])


def body_frame_switch_plan(scene, p):
    switch = next(e for e in scene['equipment'] if e['name'] == 'crs812')
    x, y, z = switch['origin']
    width, depth, height = switch['size']
    clearance, wall = p.switch_fit_clearance, p.switch_stop_thickness
    front, rear = y - clearance - wall, y + depth + clearance + wall
    middle = (front + rear) / 2
    original = [r for r in scene['boxes'] if r['name'].startswith('network_rail_')]
    scene['boxes'] = [r for r in scene['boxes'] if r not in original]
    rails = []
    for rail in original:
        side = 1 if rail['origin'][0] > 0 else -1
        for end, lo, hi, keeper_y in (
                ('front', front, middle, y + 60),
                ('rear', middle, rear, y + depth - 48)):
            recipe = dict(rail, name=rail['name'] + '_' + end,
                          label='CRS812の低い抜け止め付き支持レール・' + ('前側' if end == 'front' else '後側'),
                          origin=[rail['origin'][0], lo, rail['origin'][2]],
                          size=[rail['size'][0], hi - lo, rail['size'][2]],
                          switch_keeper=dict(side=side, end=end, keeper_y=keeper_y))
            rails.append(recipe)
    scene['boxes'] += rails
    bands = []
    for number, band_y in enumerate((y + 80, y + depth - 68)):
        bands.append(dict(name=f'switch_band_{number}', label='CRS812と支持レールを一緒に抱く保持ベルト',
                          kind='switch_band', y=band_y, width=p.switch_band_width,
                          inner_x=[x - clearance, x + width + clearance],
                          inner_z=[p.network_rail_z, z + height], thickness=p.switch_band_thickness,
                          buckle_origin=[-15, band_y - 2, z + height + p.switch_band_thickness],
                          buckle_size=[30, p.switch_band_width + 4, 8]))
    return dict(target='crs812', scope='スイッチ単体の横滑り・落下を抑える簡易固定。机への固定は対象外。',
                rail_names=[r['name'] for r in rails], bands=bands,
                horizontal_clearance_mm=clearance, stop_height_mm=p.switch_stop_height,
                buckle_status='非伸縮の保持ベルトとバックルの参考形状。製品・締付け・耐荷重は未確定。',
                disassembly=['電源を切り、端子からケーブルを外す。',
                             '2本のベルトのバックルを開いて緩める。',
                             '低い抜け止めを越えるまで持ち上げ、CRS812を取り出す。'],
                physical_validation=False, seismic_rating_verified=False,
                requirement_reference='models/spark-rack/reference/body-frame-switch-retention-20261019.json')
