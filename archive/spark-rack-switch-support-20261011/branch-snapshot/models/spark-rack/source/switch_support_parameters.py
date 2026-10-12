"""中央段の支持部。実機寸法が未確定でも、荷重経路と交換経路を仮設計する。"""
from dataclasses import asdict, dataclass

from four_node_layout import box
from rack_candidate_datums import DATUMS


@dataclass(frozen=True)
class SwitchSupportParameters:
    rail_top: float = 182.25
    rail_height: float = 28
    cross_height: float = 20
    cross_centers_y: tuple = (-322, 16)
    tray_width: float = 452
    tray_front_y: float = -395
    tray_depth: float = 423
    tray_thickness: float = 3
    foot_allowance: float = 2
    clearance: float = 0.3
    reference_mass_kg: float = 5

    def validate(self):
        if self.rail_height != 28 or self.cross_height != 20:
            raise ValueError('この支持部の梁断面は、奥行梁28mm・横梁20mmの固定形状です')
        if min(self.tray_width,self.tray_depth,self.tray_thickness,self.foot_allowance,self.clearance) <= 0:
            raise ValueError('支持部の寸法と隙間は正の値にしてください')
        if self.tray_width >= DATUMS.frame_inner_width or self.tray_depth > 464:
            raise ValueError('受け板が四隅の柱を通過する内のりに収まりません')
        if self.rail_top + self.tray_thickness + self.foot_allowance + 44 > 236.25:
            raise ValueError('上段ファンとの離隔が不足します。段間隔も見直してください')


SUPPORT = SwitchSupportParameters()


def support_outline(mode, switch, p=SUPPORT):
    p.validate()
    if mode != 'ring' and (switch['size'][0]+4 > p.tray_width or switch['size'][1] > p.tray_depth):
        raise ValueError('スイッチの外形が受け板の収容範囲を超えています')
    supports = []
    z = p.rail_top - p.rail_height
    for side, x in (('left', -256), ('right', 228)):
        y = -400
        for i, length in enumerate((180, 142, 142)):
            supports.append(box(f'switch_rail_{side}_{i}', '中央段の奥行梁・柱の段差で受ける',
                                [x, y, z], [28, length, 28], 'switch_support'))
            y += length
    for i, y in enumerate(p.cross_centers_y):
        for side, x in (('left', -220), ('right', 0)):
            supports.append(box(f'switch_cross_{i}_{side}', '受け板を下から支える横梁',
                                [x, y-14, p.rail_top-p.cross_height], [220, 28, p.cross_height], 'switch_support'))
    installed = mode != 'ring'
    tray = box('switch_tray', '交換するアルミ受け板・452×423×3mmの仮設計',
               [-p.tray_width/2, p.tray_front_y, p.rail_top],
               [p.tray_width, p.tray_depth, p.tray_thickness], 'switch_tray')
    feet = []
    bands = []
    if installed:
        width, depth, _ = switch['size']
        for i, x in enumerate((-width/2+15, width/2-30)):
            for j, y in enumerate((-depth+15, -30)):
                feet.append(box(f'switch_reference_foot_{i}_{j}', 'スイッチ底面の脚・位置と高さは仮定',
                                [x, y, p.rail_top+p.tray_thickness], [15, 15, p.foot_allowance], 'switch_foot'))
        case_top=switch['origin'][2]+switch['size'][2]
        section=[[-p.tray_width/2,p.rail_top],[p.tray_width/2,p.rail_top],
                 [p.tray_width/2,p.rail_top+p.tray_thickness],[width/2,case_top],
                 [-width/2,case_top],[-p.tray_width/2,p.rail_top+p.tray_thickness]]
        for i,y in enumerate((-depth*.65,-60)):
            bands.append({'name':f'switch_band_{i}','section_xz':section,'center_y':y,
                          'width':20,'thickness':1,'label':'保持バンド・位置と材質は仮定'})
    return {'parameters': asdict(p), 'supports': supports, 'tray': tray, 'reference_feet': feet,
            'bands':bands,
            'tray_installed': installed, 'column_split_mm': [p.rail_top, DATUMS.frame_height-p.rail_top],
            'installation': 'リング時から受け梁を組み、受け板は上段を220mm間隔へ移動した後に載せる。',
            'load_path': ['仮の底面脚', 'アルミ受け板', '横梁2本', '左右の奥行梁', '四隅の柱', '脚'],
            'retention': '後ろ側のM4ねじ2本で受け板を固定し、スイッチは保持バンド2本で受け板へ留める。',
            'service': '電源と通信ケーブル、保持ねじを外し、受け板を下から支えながら後方へ取り出す。',
            'reference_load_note': '5kgは接触点の荷重分配を確認する仮荷重。耐荷重の保証値ではない。',
            'release_for_print': False}
