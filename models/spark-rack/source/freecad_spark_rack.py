"""寸法と幾何演算から本体ラックを作る。FCStd・STEP・STLを入力にしない。"""
import math

import FreeCAD as App
import Part

from spark_rack_parameters import Parameters

PRINT_PARTS = ("side_L", "side_R", "crossbar", "locking_pin", "stack_locator", "bridge_clip",
               "fan_cassette", "fit_coupon_020", "fit_coupon_030", "fit_coupon_040", "bar_coupon", "hardware_coupon")
LAYOUTS = {"single": (1, 1), "two_horizontal": (2, 1), "two_vertical": (1, 2), "four_units": (2, 2)}


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
              "stack_locator":locator,"bridge_clip":clip,"fan_cassette":cassette(p)}
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
        library.Label="印刷部品_12種類"
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
