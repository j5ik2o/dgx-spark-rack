"""Spark本体ラックの寸法の正本。数値はすべてmm。"""
from dataclasses import dataclass, asdict


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

    機器の外形は未確定値の記録から読む。Comet Proは公式資料の値、切替器は仮の箱。
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
