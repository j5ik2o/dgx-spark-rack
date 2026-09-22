"""Spark本体ラックの寸法の正本。数値はすべてmm。"""
from dataclasses import dataclass, asdict


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
