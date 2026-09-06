"""側板の検査用形状。最終モデルの履歴とは独立して寸法からソリッドを組み立てる。"""

import math

import FreeCAD as App
import Part


def rounded_window(x, depth, y0, y1, z0, z1, radius):
    width, height = y1 - y0, z1 - z0
    assert width > 2 * radius and height > 2 * radius and radius > 0
    core = Part.makeBox(depth, width - 2 * radius, height, App.Vector(x, y0 + radius, z0))
    shapes = [Part.makeBox(depth, width, height - 2 * radius, App.Vector(x, y0, z0 + radius))]
    for y in (y0 + radius, y1 - radius):
        for z in (z0 + radius, z1 - radius):
            shapes.append(Part.makeCylinder(radius, depth, App.Vector(x, y, z), App.Vector(1, 0, 0)))
    return core.multiFuse(shapes)


def build(p):
    w, d, h, thickness, gap = [p[k] for k in ("ModuleWidth", "ModuleDepth", "FrameHeight", "SideThickness", "FitClearance")]
    support_top, dgx_front, dgx_depth = [p[k] for k in ("SupportTop", "DgxFront", "DgxDepth")]
    x0, inner = -w / 2, w / 2 - thickness
    pin_x, post_x, front = -(inner + 4), -(w / 2 - thickness / 2), p["FanDepth"] + 11
    shape = Part.makeBox(thickness, d - front, h, App.Vector(x0, front, 0))
    for z0, z1 in ((18, support_top - 12), (support_top + 12, h - 18)):
        shape = shape.cut(rounded_window(x0 - 1, thickness + 2, front + 20, d - 20, z0, z1, p["WindowRadius"]))
    for y, z in ((dgx_front + 22, support_top - 8), (dgx_front + dgx_depth - 12, support_top - 8), (d - 50, h - 10)):
        socket_x = x0 + 3 - gap
        shape = shape.cut(Part.makeBox(-inner + 0.5 - socket_x, 20 + 2 * gap, 8 + 2 * gap,
                                       App.Vector(socket_x, y - 10 - gap, z - gap)))
        shape = shape.cut(Part.makeCylinder((p["PinDiameter"] + 2 * gap) / 2, 44,
                                            App.Vector(pin_x, y, z - 12)))
    for y in (front + 8, d - 8):
        for z in (-0.3, h - 8.3):
            shape = shape.cut(Part.makeCylinder((p["LocatorDiameter"] + 2 * gap) / 2, 8.6, App.Vector(post_x, y, z)))
    shape = shape.cut(Part.makeBox(8 + 2 * gap, 9 + gap, 8 + 2 * gap, App.Vector(post_x - 4 - gap, front - 1, 20 - gap)))
    shape = shape.cut(Part.makeCylinder(2.25, 20, App.Vector(post_x, front - 2, h - 25), App.Vector(0, 1, 0)))
    radius = (p["NutAF"] + 0.5) / math.sqrt(3)
    vertices = [App.Vector(post_x + radius * math.cos(i * math.pi / 3), front + 12.4,
                           h - 25 + radius * math.sin(i * math.pi / 3)) for i in range(6)]
    wire = Part.makePolygon(vertices + [vertices[0]])
    nut = Part.Face(wire).extrude(App.Vector(0, 8.1, 0))
    return shape.cut(nut)
