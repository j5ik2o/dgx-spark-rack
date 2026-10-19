"""寸法と幾何演算から本体ラックを作る。FCStd・STEP・STLを入力にしない。"""
import math
import runpy
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tools/cad'))
from controller_mount import dock, place, RACK_PITCH, RACK_U, STANDOFF, THICKNESS, screwless_cradle
from edge_finishing import chamfer, extrema, round_pin_ends, round_opening

import FreeCAD as App
import Part

from spark_rack_parameters import Parameters, BodyFrameParameters
from body_frame_layout import ROOT, layout, validate_layout

PRINT_PARTS = ("side_L", "side_R", "crossbar", "locking_pin", "stack_locator", "bridge_clip",
               "fan_cassette", "fit_coupon_020", "fit_coupon_030", "fit_coupon_040", "bar_coupon", "hardware_coupon", "controller_dock")
LAYOUTS = {"single": (1, 1), "two_horizontal": (2, 1), "two_vertical": (1, 2), "four_units": (2, 2)}


def create_fixed_rack(parameters=None, mode='crs812', bay=None, accessories=None, finish=None, pattern=None):
    """現行の再設計。固定段と独立電源区画の形状候補を作る。bayで上部専用段、accessoriesで中段の機器棚を加える。"""
    from fixed_rack_geometry import create as create_fixed
    return create_fixed(parameters, mode, bay, accessories, finish, pattern)


def box(x, y, z, dx, dy, dz):
    return Part.makeBox(dx, dy, dz, App.Vector(x, y, z))


def cylinder(x, y, z, radius, length, axis="Z"):
    return Part.makeCylinder(radius, length, App.Vector(x, y, z),
                             App.Vector(*{"X": (1,0,0), "Y": (0,1,0), "Z": (0,0,1)}[axis]))


def hex_prism(x, y, z, af, length, axis="Y"):
    r = af/math.sqrt(3)
    points = []
    for i in range(7):
        a, b = r*math.cos(i*math.pi/3), r*math.sin(i*math.pi/3)
        points.append(App.Vector(x+a, y if axis == "Y" else y+b, z+b if axis == "Y" else z))
    return Part.Face(Part.makePolygon(points)).extrude(App.Vector(0,length,0) if axis == "Y" else App.Vector(0,0,length))


def move(shape, x=0, y=0, z=0):
    result = shape.copy()
    result.translate(App.Vector(x,y,z))
    return result


def side(p, right=False):
    sign = 1 if right else -1
    x = p.inner_x if right else -p.module_width/2
    shape = box(x,p.front_y,0,p.side_thickness,p.module_depth-p.front_y,p.frame_height)
    for z, height in ((18,p.support_top-30),(p.support_top+12,p.frame_height-p.support_top-30)):
        tool = box(x-1,p.front_y+20,z,p.side_thickness+2,p.module_depth-p.front_y-40,height)
        edges = [e for e in tool.Edges if len(e.Vertexes)==2 and abs(e.Vertexes[0].Point.x-e.Vertexes[1].Point.x)>p.side_thickness]
        shape = shape.cut(tool.makeFillet(p.window_radius,edges))
    c = p.fit_clearance
    for y,z in ((p.support_front_y,p.support_top-p.beam_height),
                (p.support_rear_y,p.support_top-p.beam_height),(p.upper_bar_y,p.frame_height-10)):
        pocket_x = p.inner_x-1 if right else -p.inner_x-p.tenon_length-c
        shape = shape.cut(box(pocket_x,y-p.beam_width/2-c,z-c,
                              p.tenon_length+c+1,p.beam_width+2*c,p.beam_height+2*c))
        pin_start = p.support_top-20 if y != p.upper_bar_y else p.frame_height-22
        shape = shape.cut(cylinder(sign*p.pin_x,y,pin_start,p.pin_diameter/2+c,44))
    for y in (p.front_y+8,p.module_depth-8):
        for z in (0,p.frame_height-8.3):
            shape = shape.cut(cylinder(sign*p.post_x,y,z,p.locator_diameter/2+c,8.3))
    shape = shape.cut(box(sign*p.post_x-4-c,p.front_y,20-c,8+2*c,8+c,8+2*c))
    shape = shape.cut(cylinder(sign*p.post_x,p.front_y,p.cassette_upper_z,2.25,18,"Y"))
    shape = shape.cut(hex_prism(sign*p.post_x,p.front_y+12.4,p.cassette_upper_z,p.nut_af+0.5,8.1))
    for y in (p.controller_y-RACK_PITCH/2,p.controller_y+RACK_PITCH/2):
        shape = shape.cut(cylinder(x-1,y,p.controller_z,2.25,p.side_thickness+2,'X'))
    return shape.removeSplitter()


def crossbar(p):
    end = p.inner_x+p.tenon_length
    shape = box(-end,-p.beam_width/2,0,2*end,p.beam_width,p.beam_height)
    for x in (-p.pin_x,p.pin_x):
        shape = shape.cut(cylinder(x,0,-1,p.pin_diameter/2+p.fit_clearance,p.beam_height+2))
    return shape.removeSplitter()


def cassette(p):
    zc, r = p.fan_center_z,p.rim
    shape = box(-r,0,zc-r,2*r,p.cassette_plate,2*r)
    shape = shape.cut(cylinder(0,-1,zc,p.fan_size/2-2,p.cassette_plate+2,"Y"))
    # 前面の外周をラック幅へ揃え、側枠と同じ12mm幅の連続した輪郭にする。
    rail=p.fascia_rail_width
    fascia=box(-p.module_width/2,0,zc-r,p.module_width,p.cassette_plate,2*r)
    fascia=fascia.cut(box(-p.module_width/2+rail,-1,zc-r+rail,
                         p.module_width-2*rail,p.cassette_plate+2,2*r-2*rail))
    shape=shape.fuse(fascia)
    # 下側の腕（Z=18）と外周枠の間に残る小窓だけを閉じ、縦の主開口を残す。
    lower_frame_top=zc-r+rail
    side_gap=p.module_width/2-rail-r
    if lower_frame_top < 18 and side_gap > 0:
        for x in (-p.module_width/2+rail,r):
            shape=shape.fuse(box(x,0,lower_frame_top,side_gap,p.cassette_plate,18-lower_frame_top))
    for x in (-p.fan_hole_pitch/2,p.fan_hole_pitch/2):
        for z in (zc-p.fan_hole_pitch/2,zc+p.fan_hole_pitch/2):
            shape = shape.fuse(cylinder(x,p.cassette_plate,z,5,4,"Y"))
            shape = shape.cut(cylinder(x,-1,z,p.fan_mount_hole/2,p.cassette_plate+6,"Y"))
    for sign in (-1,1):
        for z,h in ((p.cassette_upper_z-12,24),(18,12)):
            inner = r-2
            outer = p.module_width/2
            # 前板から前柱へ伸ばすL字の腕。
            if sign==1:
                arm = box(inner,0,z,outer-inner,10,h).fuse(box(outer-12,10,z,12,p.front_y-10,h))
            else:
                arm = box(-outer,0,z,outer-inner,10,h).fuse(box(-outer,10,z,12,p.front_y-10,h))
            shape = shape.fuse(arm)
        shape = shape.fuse(box(sign*p.post_x-4,p.front_y,20,8,8,8))
        shape = shape.cut(cylinder(sign*p.post_x,-1,p.cassette_upper_z,2.25,p.front_y+2,"Y"))
    return shape.removeSplitter()


def shapes(p):
    p.validate()
    left = side(p)
    right = side(p, right=True)
    bar = crossbar(p)
    pin = cylinder(0,0,0,p.pin_diameter/2,20).fuse(cylinder(0,0,20,4,3)).removeSplitter()
    locator = cylinder(0,0,0,p.locator_diameter/2,16+p.stack_gap).fuse(cylinder(0,0,8,5,p.stack_gap)).removeSplitter()
    opening = 2*p.side_thickness+p.column_gap+2*p.fit_clearance
    clip = box(-opening/2-4,0,0,opening+8,16,20).cut(box(-opening/2,-1,-1,opening,18,17.5)).removeSplitter()
    result = {"side_L":left,"side_R":right,"crossbar":bar,"locking_pin":pin,
              "stack_locator":locator,"bridge_clip":clip,"fan_cassette":cassette(p),"controller_dock":dock()}
    for name, c in (("020",0.2),("030",0.3),("040",0.4)):
        block = box(-p.module_width/2,p.support_front_y-15,p.support_top-12,p.side_thickness,30,24)
        block = block.cut(box(-p.inner_x-p.tenon_length-c,p.support_front_y-10-c,p.support_top-8-c,
                              p.tenon_length+c+1,20+2*c,8+2*c))
        block = block.cut(cylinder(-p.pin_x,p.support_front_y,p.support_top-20,p.pin_diameter/2+c,44))
        result["fit_coupon_"+name] = block.removeSplitter()
    result["bar_coupon"] = bar.common(box(-p.inner_x-p.tenon_length,-20,-1,22,40,10)).removeSplitter()
    hardware = box(0,0,0,96,44,8)
    for x,hole,af,locator_d in ((16,4.3,7.3,6.4),(48,4.5,7.5,6.6),(80,4.7,7.7,6.8)):
        hardware=hardware.cut(cylinder(x,12,-1,hole/2,10)).cut(hex_prism(x,12,4.3,af,4,"Z"))
        hardware=hardware.cut(cylinder(x,32,-1,locator_d/2,10))
    result["hardware_coupon"] = hardware.removeSplitter()
    for name,shape in list(result.items()):
        bounds=shape.optimalBoundingBox(False)
        if name=='controller_dock':
            continue  # 共通ドック生成時にフィレット・面取り済み
        if name in ('locking_pin','stack_locator'):
            result[name]=round_pin_ends(shape)
            continue
        if name=='side_L': planes=[('X',bounds.XMin)]
        elif name=='side_R': planes=[('X',bounds.XMax)]
        elif name=='fan_cassette': planes=[('Y',0),('Y',p.cassette_plate)]
        elif name=='bridge_clip': planes=extrema(shape,'X')+[('Z',bounds.ZMax)]
        elif name=='hardware_coupon': planes=extrema(shape,'XY')
        elif name.startswith('fit_coupon'): planes=[('X',bounds.XMin)]  # 側枠と同じ外側面だけ処理
        else: planes=extrema(shape,'YZ')
        result[name]=chamfer(shape,planes)
        if name=='fan_cassette':
            result[name]=round_opening(result[name],'Y',bounds.YMin,p.fan_size/2-2)
    return result


def references(p):
    dgx=box(-p.dgx_width/2,p.dgx_front,p.support_top,p.dgx_width,p.dgx_depth,p.dgx_height)
    dgx=dgx.makeFillet(5,dgx.Edges)
    fan=box(-p.fan_size/2,8,p.fan_center_z-p.fan_size/2,p.fan_size,p.fan_depth,p.fan_size)
    fan=fan.cut(cylinder(0,7,p.fan_center_z,p.fan_size/2-5,p.fan_depth+2,"Y"))
    for x in (-p.fan_hole_pitch/2,p.fan_hole_pitch/2):
        for z in (p.fan_center_z-p.fan_hole_pitch/2,p.fan_center_z+p.fan_hole_pitch/2):
            fan=fan.cut(cylinder(x,7,z,p.fan_mount_hole/2,p.fan_depth+2,"Y"))
    fan_parts=[fan,cylinder(0,14,p.fan_center_z,19,15,"Y"),
               box(-64,20,p.fan_center_z-8,128,2,16),box(-8,20,p.fan_center_z-64,16,2,128)]
    guard=[cylinder(0,-2,p.fan_center_z,r,2,"Y").cut(cylinder(0,-3,p.fan_center_z,r-1,4,"Y"))
           for r in (68,56,44,32,20,8)]
    guard += [box(-69,-2,p.fan_center_z-0.7,138,2,1.4),box(-0.7,-2,p.fan_center_z-69,1.4,2,138)]
    screw=cylinder(0,-5,0,8,5,"Y").fuse(cylinder(0,-0.2,0,2,60.2,"Y")).removeSplitter()
    nut=hex_prism(0,0,0,p.nut_af,3.2).cut(cylinder(0,-1,0,2,5.2,"Y"))
    return {"REF_DGX":dgx,"REF_FAN":Part.makeCompound(fan_parts),"REF_GUARD":Part.makeCompound(guard),
            "REF_SCREW":screw,"REF_NUT":nut}


def assembly_shapes(p, parts, columns, rows, include_visual=True):
    refs=references(p)
    items=[]
    for col in range(columns):
        base_x=(col-(columns-1)/2)*p.column_pitch
        for row in range(rows):
            base_z=row*p.row_pitch
            def add(name,shape,x=0,y=0,z=0):
                items.append((f"unit_{col}_{row}_{name}",move(shape,base_x+x,y,base_z+z)))
            for name in ("side_L","side_R","fan_cassette"):
                add(name,parts[name])
            add("REF_DGX",refs["REF_DGX"])
            if include_visual:
                for name in ("REF_FAN","REF_GUARD"):add(name,refs[name])
            for i,(y,z,pinz) in enumerate(((p.support_front_y,p.support_top-8,p.support_top-8),
                                          (p.support_rear_y,p.support_top-8,p.support_top-8),
                                          (p.upper_bar_y,p.frame_height-10,p.frame_height-20))):
                add(f"crossbar_{i}",parts["crossbar"],y=y,z=z)
                for sign in (-1,1):add(f"pin_{i}_{sign}",parts["locking_pin"],x=sign*p.pin_x,y=y,z=pinz)
            for sign in (-1,1):
                add(f"REF_SCREW_{sign}",refs["REF_SCREW"],x=sign*p.post_x,z=p.cassette_upper_z)
                add(f"REF_NUT_{sign}",refs["REF_NUT"],x=sign*p.post_x,y=p.front_y+12.6,z=p.cassette_upper_z)
        for row in range(rows-1):
            for sign in (-1,1):
                for y in (p.front_y+8,p.module_depth-8):
                    items.append((f"locator_{col}_{row}_{sign}_{y}",move(parts["stack_locator"],base_x+sign*p.post_x,y,
                                                                                    row*p.row_pitch+p.frame_height-8)))
    for col in range(columns-1):
        for row in range(rows):
            for y in (100,145):
                items.append((f"clip_{col}_{row}_{y}",move(parts["bridge_clip"],(col-(columns-2)/2)*p.column_pitch,y,
                                                                      row*p.row_pitch+p.frame_height-16.5)))
    for col in range(columns):
        sign = -1 if col == 0 else 1
        for row in range(rows):
            origin=((col-(columns-1)/2)*p.column_pitch+sign*(p.module_width/2+STANDOFF),
                    p.controller_y,row*p.row_pitch+p.controller_z-RACK_U)
            items.append((f'controller_dock_{col}_{row}',place(parts['controller_dock'],origin,
                         (0,0,1),(0,-sign,0),(sign,0,0))))
    return items


def create(parameters=None):
    p=parameters or Parameters()
    parts=shapes(p)
    doc=App.newDocument("DGXSparkRack")
    doc.Label="Spark本体ラック_Python生成"
    try:
        sheet=doc.addObject("Spreadsheet::Sheet","Parameters")
        sheet.Label="生成時の寸法記録_編集はPythonへ"
        for row,(name,value) in enumerate(p.values().items(),1):
            sheet.set(f"A{row}",name);sheet.set(f"B{row}",f"{value} mm")
        library=doc.addObject("App::Part","PartLibrary")
        library.Label="印刷部品_13種類"
        for name,shape in parts.items():
            obj=doc.addObject("PartDesign::Feature","Print_"+name)
            obj.Label=name;obj.Shape=shape;library.addObject(obj)
        library.Visibility=False
        for name,(columns,rows) in LAYOUTS.items():
            group=doc.addObject("App::Part",name)
            group.Label=name
            for label,shape in assembly_shapes(p,parts,columns,rows):
                obj=doc.addObject("PartDesign::Feature",name+"_"+label)
                obj.Label=label;obj.Shape=shape;group.addObject(obj)
                obj.ViewObject.ShapeColor=(0.66,0.52,0.30) if "REF_DGX" in label else (
                    (0.77,0.65,0.48) if "REF_FAN" in label else (0.28,0.30,0.32))
            group.Visibility=name=="four_units"
        doc.recompute()
        return doc
    except Exception:
        App.closeDocument(doc.Name)
        raise


def show_layout(doc,name):
    if name not in LAYOUTS:raise ValueError(name)
    for key in LAYOUTS:doc.getObject(key).Visibility=key==name
    doc.PartLibrary.Visibility=False
    doc.recompute()


COLORS = {
    'spark': (.66, .56, .37), 'body_connector': (.10, .30, .42),
    'accessory_support': (.20, .28, .34), 'network_support': (.20, .28, .34),
    'accessory_tray': (.26, .34, .40), 'power_tray': (.26, .34, .40),
    'fan_holder': (.13, .24, .30), 'controller_mount': (.16, .29, .36),
    'dock': (.20, .28, .34), 'fan': (.12, .13, .15),
    'controller': (.34, .38, .42), 'controller_lid': (.47, .50, .53),
    'knob': (.12, .14, .16), 'display': (.15, .38, .45),
    'switch': (.63, .66, .69), 'comet': (.18, .23, .28),
    'kvm': (.23, .25, .28), 'power': (.24, .27, .29),
    'cable_mount': (.15, .35, .43), 'cable_network': (.12, .55, .68),
    'cable_signal': (.48, .31, .72), 'cable_dc': (.90, .55, .12),
    'cable_ac': (.70, .25, .20), 'cable_control': (.25, .62, .37),
    'cable_storage': (.31, .68, .73), 'external_reservation': (.75, .75, .67),
    'switch_band': (.18, .40, .60), 'switch_buckle': (.35, .40, .45),
    'fan_pin': (.85, .48, .16), 'joint_key': (.85, .48, .16),
    'controller_band': (.18, .40, .60),
    'joint_detail_donor': (.18, .42, .56), 'joint_detail_receiver': (.43, .55, .62),
    'joint_detail_key': (.85, .48, .16),
}


def block(origin, size):
    return Part.makeBox(*size, App.Vector(*origin))


def fuse(shapes):
    result = shapes[0]
    for shape in shapes[1:]:
        result = result.fuse(shape)
    return result.removeSplitter()


def item(name, label, shape, kind, **extra):
    return dict(name=name, label=label, shape=shape, kind=kind, **extra)


def corner_shape(recipe, scene, p):
    shape = fuse([block(piece['origin'], piece['size']) for piece in recipe['pieces']])
    for spark in (e for e in scene['equipment'] if e['kind'] == 'spark'):
        x, y, z = spark['origin']
        dx, dy, dz = spark['size']
        c = p.fit_clearance
        shape = shape.cut(block((x - c, y - c, z), (dx + 2 * c, dy + 2 * c, dz)))
    return shape.removeSplitter()


def tray_shape(recipe, p):
    shape = block(recipe['origin'], recipe['size'])
    x, y, z = recipe['origin']
    dx, dy, dz = recipe['size']
    if recipe['kind'] == 'power_tray':
        walls = [block((x, y, z + dz), (4, dy, 8)),
                 block((x + dx - 4, y, z + dz), (4, dy, 8))]
    elif recipe['name'] == 'comet_tray':
        walls = [block((x, y, z + dz), (3.7, dy, 8)),
                 block((x + dx - 3.7, y, z + dz), (3.7, dy, 8))]
    else:
        wall_x = x if recipe['tray_side'] == 0 else x + dx - 4.7
        walls = [block((wall_x, y, z + dz), (4.7, dy, 8))]
        walls.append(block((x, y, z + dz), (dx, 3.7, 6)))
    return fuse([shape] + walls)


def fan_holder(fan, p):
    x, y, z = fan['origin']
    dx, dy, dz = fan['size']
    r = p.fan_rim
    if fan['axis'][1]:
        plane = y + dy if fan['axis'][1] < 0 else y - p.fan_plate
        shape = block((x - r, plane, z - r), (dx + 2 * r, p.fan_plate, dz + 2 * r))
        center = (x + dx / 2, plane - 1, z + dz / 2)
        shape = shape.cut(Part.makeCylinder(fan['opening'] / 2, p.fan_plate + 2,
                                           App.Vector(*center), App.Vector(0, 1, 0)))
        for hx in (-fan['pitch'] / 2, fan['pitch'] / 2):
            for hz in (-fan['pitch'] / 2, fan['pitch'] / 2):
                shape = shape.cut(Part.makeCylinder(2.25, p.fan_plate + 2,
                    App.Vector(center[0] + hx, plane - 1, center[2] + hz), App.Vector(0, 1, 0)))
        # ファン保持部は中間の接続部だけへ付ける。脚と上部を支える独立フレームにはしない。
        a = p.fan_arm_size
        back = -p.corner_outside if fan['axis'][1] < 0 else p.spark_depth
        start, end = (plane + p.fan_plate, back) if fan['axis'][1] < 0 else (back, plane)
        arms = [block((center[0] + offset - a / 2, start, center[2] - a / 2),
                      (a, end - start, a)) for offset in (-fan['fan_size'] / 2, fan['fan_size'] / 2)]
        shape = fuse([shape] + arms)
    else:
        plane = x - p.fan_plate if fan['axis'][0] > 0 else x + dx
        shape = block((plane, y - r, z - r), (p.fan_plate, dy + 2 * r, dz + 2 * r))
        center = (plane - 1, y + dy / 2, z + dz / 2)
        shape = shape.cut(Part.makeCylinder(fan['opening'] / 2, p.fan_plate + 2,
                                           App.Vector(*center), App.Vector(1, 0, 0)))
        for hy in (-fan['pitch'] / 2, fan['pitch'] / 2):
            for hz in (-fan['pitch'] / 2, fan['pitch'] / 2):
                shape = shape.cut(Part.makeCylinder(2.25, p.fan_plate + 2,
                    App.Vector(plane - 1, center[1] + hy, center[2] + hz), App.Vector(1, 0, 0)))
    return shape.removeSplitter()


def power_fan_arms(p):
    half = p.core_width / 2
    plane = half + p.corner_outside + p.power_fan_gap
    result = []
    rear = p.spark_depth
    fan_edge = p.power_fan_center_y - p.power_fan_size / 2 - p.fan_rim
    for side in (-1, 1):
        for row, z in enumerate((8, p.lower_base - 4)):
            def mirror(x, width):
                return x if side > 0 else -x - width
            outer = p.corner_outside - p.fit_clearance
            a = block((mirror(half + p.fit_clearance, outer), rear, z),
                      (outer, fan_edge + p.power_fan_arm_overlap - rear, 8))
            b = block((mirror(half + 8, p.power_fan_gap), fan_edge - 4, z),
                      (p.power_fan_gap, 4+p.power_fan_arm_overlap, 8))
            result.append(item(f'power_fan_arm_{side}_{row}', '電源ファンを脚の接続部へ留める短い腕',
                               fuse([a, b]), 'fan_holder'))
    return result


def fan_shape(fan):
    """外枠・ハブ・支持桟による参考形状。取付軸は常に座標軸と一致する。"""
    origin, size, axis = fan['origin'], fan['size'], fan['axis']
    a = next(i for i, v in enumerate(axis) if v)
    uv = [i for i in range(3) if i != a]
    center = [origin[i] + size[i] / 2 for i in range(3)]
    cut_base = list(center)
    cut_base[a] = origin[a] - 1
    positive_axis = [int(i == a) for i in range(3)]
    radius = fan['opening'] / 2
    shape = block(origin, size).cut(Part.makeCylinder(radius, size[a] + 2,
                                   App.Vector(*cut_base), App.Vector(*positive_axis)))
    cut_base[a] = origin[a]
    hub = Part.makeCylinder(18, size[a], App.Vector(*cut_base), App.Vector(*positive_axis))
    bars = []
    for direction in uv:
        o, d = list(center), list(size)
        for i in range(3):
            if i == a:
                o[i], d[i] = origin[i], size[i]
            elif i == direction:
                o[i], d[i] = origin[i], size[i]
            else:
                o[i], d[i] = center[i] - 3, 6
        bars.append(block(o, d))
    return fuse([shape, hub] + bars)


def controller_shapes(scene):
    """ケースと共通ドックは現在の正本を使い、左右の面へ正立配置する。"""
    source = runpy.run_path(str(ROOT / 'models/fan-controller/source/freecad_fan_controller.py'))
    App.closeDocument(source['doc'].Name)
    cx = (source['envelope_x'] + source['outer_right']) / 2
    cy = (source['envelope_y'] + source['envelope_back']) / 2
    shift = App.Vector(-cx, -cy, THICKNESS - source['bottom_z'])
    screwless = source['screwless_case_parts']()
    scene['controller_case_assembly'] = {key:value for key,value in screwless.items() if key not in ('body', 'lid')}
    scene['controller_case_assembly']['reference_shift'] = list(shift)
    body, lid = screwless['body'].copy(), screwless['lid'].copy()
    body.translate(shift)
    lid.translate(shift)
    knob = Part.makeCylinder(source['KNOB_PASS_DIAMETER'] / 2,
                            source['KNOB_TOP_Z'] - source['lid_top_z'],
                            App.Vector(source['ENCODER_X'], source['ENCODER_Y'], source['lid_top_z']))
    knob.translate(shift)
    display = block((source['DISPLAY_X'], source['DISPLAY_Y'], source['DISPLAY_TOP_Z']),
                    (source['DISPLAY_LENGTH'], source['DISPLAY_WIDTH'], .4))
    display.translate(shift)
    parts, references = [], []
    dock_shape = screwless_cradle(source['envelope_length'], source['envelope_width'])
    for controller in (e for e in scene['equipment'] if e['kind'] == 'controller'):
        args = (controller['dock_origin'], controller['u'], controller['v'], controller['w'])
        name = controller['name']
        parts.append(item(name + '_dock', controller['label'] + '・共通ドック', place(dock_shape, *args), 'dock'))
        for suffix, shape, kind in (('body', body, 'controller'), ('lid', lid, 'controller_lid'),
                                     ('knob', knob, 'knob'), ('display', display, 'display')):
            suffix_label = {'body': 'ケース本体', 'lid': '蓋', 'knob': 'つまみ', 'display': '表示器'}[suffix]
            references.append(item(name + '_' + suffix, controller['label'] + '・' + suffix_label,
                                   place(shape, *args), kind, group=name))
        references += controller_bands(controller, source)
    return parts, references


def create_body_frame(parameters=None):
    p = parameters or BodyFrameParameters()
    scene = layout(p)
    scene['layout_validation'] = validate_layout(scene)
    parts = [item(r['name'], r['label'], corner_shape(r, scene, p), r['kind'])
             for r in scene['corners']]
    for recipe in scene['boxes']:
        if recipe['kind'] == 'controller_mount':
            controller = next(e for e in scene['equipment'] if e['name'] == recipe['controller'])
            side = controller['w'][0]
            center = [controller['dock_origin'][i] + controller['u'][i] * RACK_U
                      for i in range(3)]
            dock_back = controller['dock_origin'][0] - side * STANDOFF
            core_edge = side * (p.core_width / 2 + p.corner_outside)
            recipe.update(origin=[min(dock_back, core_edge), center[1] - 9, center[2] - 21],
                          size=[abs(dock_back - core_edge), 18, 42])
        if recipe.get('switch_keeper'):
                    shape = rail_shape(recipe, scene, p)
        else:
            shape = tray_shape(recipe, p) if recipe['kind'] in ('accessory_tray', 'power_tray') else block(recipe['origin'], recipe['size'])
        parts.append(item(recipe['name'], recipe['label'], shape, recipe['kind']))
    fans = [e for e in scene['equipment'] if e['kind'] == 'fan']
    parts += [item(f['name'] + '_holder', '正立固定するファン保持部', fan_holder(f, p), 'fan_holder')
              for f in fans]
    parts += power_fan_arms(p)
    docks, references = controller_shapes(scene)
    parts += docks
    for equipment in scene['equipment']:
        if equipment['kind'] == 'controller':
            continue
        shape = fan_shape(equipment) if equipment['kind'] == 'fan' else block(equipment['origin'], equipment['size'])
        if equipment['kind'] == 'fan':
            shape, centers = fan_holes(shape, equipment)
            parts += [item(equipment['name']+f'_pin_{n}', 'ファン固定用のねじ山のない樹脂割りピン',
                           fan_pin(equipment, center, p), 'fan_pin', moves_with=equipment['name'])
                      for n, center in enumerate(centers)]
        references.append(item(equipment['name'], equipment['label'], shape, equipment['kind']))
    mounts, cables, storage = create_cable_geometry(scene)
    parts += mounts
    references += band_shapes(scene)
    from body_frame_screwless import integrate_small_parts
    lap_storage_floors(parts)
    protected = {f['name']+'_holder' for f in fans} | {e['name'] for e in parts if e['kind'] == 'fan_pin'}
    parts = integrate_small_parts(parts, p, protected)
    from body_frame_joinery import connect_parts
    parts, scene['screwless_assembly'] = connect_parts(parts, references, p)
    from body_frame_joinery import joint_detail
    details = joint_detail(parts, scene)
    external = [item(r['name'], r['label'], block(r['origin'], r['size']), r['kind'])
                for r in scene['cable_management']['external_regions']]
    doc = App.newDocument('SparkBodyFrameCandidate')
    for group, items in (('Candidate', parts), ('Reference', references), ('Cable', cables),
                         ('Storage', storage), ('Reservation', external)):
        for entry in items:
            obj = doc.addObject('Part::Feature', group + '_' + entry['name'].replace('-', 'N'))
            obj.Label = entry['label']
            obj.Shape = entry['shape']
            if App.GuiUp:
                obj.ViewObject.ShapeColor = entry.get('color', COLORS.get(entry['kind'], (.4, .4, .4)))
    doc.recompute()
    return doc, dict(parameters=p, scene=scene, parts=parts, references=references,
                     cables=cables, cable_storage=storage, external_reservations=external,
                     assembly_details=details)


TAB_WIDTH = 10
TAB_START = 4
TAB_END = 10


def fan_pin(fan, center, p):
    """ねじ山のない割りピン。返しの弾性、材料と積層方向は実物確認前。"""
    direction = App.Vector(*fan['axis'])
    inward = direction * -1
    a = next(i for i, v in enumerate(fan['axis']) if v)
    outer = list(center)
    outer[a] = fan['origin'][a] + (fan['size'][a] if fan['axis'][a] > 0 else 0)
    start = App.Vector(*outer)
    length = p.fan_depth + p.fan_plate
    shaft = Part.makeCylinder(1.8, length, start, inward)
    head = Part.makeCylinder(3.4, 1.6, start, direction)
    barb = Part.makeCone(2.7, 1.8, 2.4, start + inward*length, inward)
    shape = shaft.fuse(head).fuse(barb)
    # 返し側を二股にする。圧縮して穴を通し、内側の返しで抜けを抑える候補。
    base = start + inward*(length-p.fan_pin_split_length)
    tangent = next(i for i in range(3) if i != a)
    bed_axis = next(i for i in range(3) if i not in (a, tangent))
    lo, size = [base.x-4, base.y-4, base.z-4], [8, 8, 8]
    lo[a] = min(base[a], (start+inward*(length+3))[a])
    size[a] = p.fan_pin_split_length+3
    lo[tangent], size[tangent] = base[tangent]-.45, .9
    slot = Part.makeBox(*size, App.Vector(*lo))
    root = list(base)
    root[bed_axis] -= 4
    slot = slot.fuse(Part.makeCylinder(.45, 8, App.Vector(*root),
                    App.Vector(*[int(i==bed_axis) for i in range(3)])))
    shape = shape.cut(slot).removeSplitter()
    # 軸と二股の曲げ方向を層の面内へ置き、全長を同じ平面へ接地する。
    b = shape.BoundBox
    low, high = [b.XMin-1,b.YMin-1,b.ZMin-1], [b.XMax+1,b.YMax+1,b.ZMax+1]
    high[bed_axis] = start[bed_axis]-p.fan_pin_flat_offset
    shape = shape.cut(Part.makeBox(*[high[i]-low[i] for i in range(3)], App.Vector(*low))).removeSplitter()
    return shape



def fan_holes(shape, fan):
    a = next(i for i, v in enumerate(fan['axis']) if v)
    uv = [i for i in range(3) if i != a]
    axis = App.Vector(*[int(i == a) for i in range(3)])
    centers = []
    for first in (-1, 1):
        for second in (-1, 1):
            center = [fan['origin'][i]+fan['size'][i]/2 for i in range(3)]
            center[uv[0]] += first*fan['pitch']/2
            center[uv[1]] += second*fan['pitch']/2
            base = list(center)
            base[a] = fan['origin'][a]-1
            shape = shape.cut(Part.makeCylinder(2.25, fan['size'][a]+2, App.Vector(*base), axis))
            centers.append(center)
    return shape.removeSplitter(), centers



def controller_bands(controller, source):
    from controller_mount import THICKNESS, place
    from controller_mount import WIDTH
    width = WIDTH
    height = source['lid_top_z']-source['bottom_z']
    cx = (source['envelope_x']+source['outer_right'])/2
    result = []
    for number, pcb_x in enumerate((5, 70)):
        u, v, w = pcb_x-cx, width/2, THICKNESS+height
        outer = block([u-2.4, -v-1.2, -1.2], [4.8, 2*v+2.4, w+2.4])
        inner = block([u-3, -v, 0], [6, 2*v, w])
        shape = place(outer.cut(inner), controller['dock_origin'], controller['u'], controller['v'], controller['w'])
        result.append(item(controller['name']+f'_band_{number}', '制御器ケースと受け台を抱く解除式結束バンド',
                           shape, 'controller_band', group=controller['name']))
    return result



def lap_storage_floors(parts):
    """薄い受け同士の端面だけでつながず、下へ重ねて段差で受ける。"""
    by_name = {e['name']: e for e in parts}
    for col in range(2):
        floor = by_name[f'signal_storage_floor_{col}']
        tray = by_name[f'power_tray_{col}_1']
        b = floor['shape'].BoundBox
        nose = block([b.XMin, b.YMin-14, b.ZMin], [b.XLength, 14, b.ZLength])
        tray['shape'] = tray['shape'].cut(nose).removeSplitter()
        floor['shape'] = floor['shape'].fuse(nose).removeSplitter()



def key_grip(center, end, axis, sign, normal, shaft_width, offset=0, flat_side=-1):
    """細い栓の外側へ、幅10mmの平たいつまみと二指分の予約を作る。"""
    from body_frame_access import FINGER_SIZE, rectangular
    other = next(i for i in range(3) if i not in (axis, normal))
    low, high = list(center), list(center)
    for i in (normal, other):
        low[i], high[i] = center[i]-shaft_width/2-1, center[i]+shaft_width/2+1
    bed = center[other]+flat_side*shaft_width/2
    if flat_side < 0:
        low[other] = bed
    else:
        high[other] = bed
    low[axis], high[axis] = sorted((end, end+sign*TAB_START))
    low[normal] += min(0, offset)
    high[normal] += max(0, offset)
    neck = rectangular(low, high)
    low[normal], high[normal] = center[normal]+offset-shaft_width/2-1, center[normal]+offset+shaft_width/2+1
    low[other], high[other] = sorted((bed, bed-flat_side*TAB_WIDTH))
    low[axis], high[axis] = sorted((end+sign*TAB_START, end+sign*TAB_END))
    tab = rectangular(low, high)
    fingers = []
    for side in (-1, 1):
        fl, fh = list(low), list(high)
        fl[normal], fh[normal] = center[normal]+offset-FINGER_SIZE[0]/2, center[normal]+offset+FINGER_SIZE[0]/2
        fl[axis], fh[axis] = sorted((end+sign*3, end+sign*15))
        edge = low[other] if side < 0 else high[other]
        fl[other], fh[other] = sorted((edge, edge+side*FINGER_SIZE[1]))
        fingers.append(dict(origin=fl, size=[fh[i]-fl[i] for i in range(3)]))
    return neck.fuse(tab).removeSplitter(), dict(
        tab_width_mm=TAB_WIDTH, tab_length_mm=TAB_END-TAB_START,
        tab_thickness_mm=shaft_width+2, stand_off_mm=TAB_START, grip_offset_mm=offset,
        print_build_axis=[-flat_side if i==other else 0 for i in range(3)],
        print_bed_coordinate_mm=bed,
        axis=[sign if i == axis else 0 for i in range(3)],
        finger_boxes=fingers, assumption='各指12×10×12mmの直方体。素手の仮の操作空間で、人体寸法の規格値ではない。')



def rail_shape(recipe, scene, p):
    switch = next(e for e in scene['equipment'] if e['name'] == 'crs812')
    sx, sy, sz = switch['origin']
    sw, sd, _ = switch['size']
    x, y, z = recipe['origin']
    width, depth, height = recipe['size']
    keeper = recipe['switch_keeper']
    wall, clearance = p.switch_stop_thickness, p.switch_fit_clearance
    # 端の低い突起は前後の滑りを止める。側面の突起は筐体の下端だけに当てる。
    end_y = y if keeper['end'] == 'front' else y + depth - wall
    side_x = sx + sw + clearance if keeper['side'] > 0 else sx - clearance - wall
    arm_start = x + width if keeper['side'] > 0 else side_x
    arm_end = side_x + wall if keeper['side'] > 0 else x
    pieces = [block(recipe['origin'], recipe['size']),
              block([x, end_y, sz], [width, wall, p.switch_stop_height]),
              block([arm_start, keeper['keeper_y'], sz - 4], [arm_end - arm_start, 16, 4]),
              block([side_x, keeper['keeper_y'], sz - 4], [wall, 16, p.switch_stop_height + 4])]
    return fuse(pieces)



def band_shapes(scene):
    references = []
    for band in scene['switch_retention']['bands']:
        x0, x1 = band['inner_x']
        z0, z1 = band['inner_z']
        t, y, w = band['thickness'], band['y'], band['width']
        outer = block([x0 - t, y, z0 - t], [x1 - x0 + 2 * t, w, z1 - z0 + 2 * t])
        inner = block([x0, y - 1, z0], [x1 - x0, w + 2, z1 - z0])
        references.append(item(band['name'], band['label'], outer.cut(inner), 'switch_band'))
        references.append(item(band['name'] + '_buckle', '開放できるバックル・参考外形',
                               block(band['buckle_origin'], band['buckle_size']), 'switch_buckle'))
    return references



def create_cable_geometry(scene):
    from body_frame_cable_geometry import tube
    data = scene['cable_management']
    parts, cables, storage = [], [], []
    for recipe in data['mounts']:
        shape = block(recipe['origin'], recipe['size'])
        if recipe.get('tie_plate'):
            x, y, z = recipe['origin']
            for height in (80, 96, 144, 160):
                shape = shape.cut(block([x - 1, y + 4, height], [6, 8, 3]))
        if recipe['slots']:
            x, y, z = recipe['origin']
            for dx in (8, 58):
                for dy in (30, 90, 150):
                    shape = shape.cut(block([x + dx, y + dy, z - 1], [8, 3, 6]))
            shape = shape.cut(block([recipe['feed_x'] - 12, recipe['feed_y'], z - 1], [24, 30, 6]))
        parts.append(item(recipe['name'], recipe['label'], shape.removeSplitter(), 'cable_mount'))
    for route in data['paths']:
        cables.append(item(route['name'], route['label'], tube(route), 'cable_' + route['family'],
                           endpoints=route['endpoints'], detachable_with=route.get('detachable_with')))
    for reservation in data['storage']:
        storage.append(item(reservation['name'], reservation['label'],
                            Part.makeTorus(reservation['radius'], reservation['diameter'] / 2,
                                           App.Vector(*reservation['center']), App.Vector(*reservation['normal'])),
                            'cable_storage', color=COLORS['cable_' + reservation['family']]))
    return parts, cables, storage
