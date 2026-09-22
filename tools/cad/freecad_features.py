"""FreeCADのスケッチと加工フィーチャーを作る共通処理。"""

import math
import re

import FreeCAD as App
import Part
import Sketcher


class Features:
    def __init__(self, doc, body, aliases):
        self.doc = doc
        self.body = body
        self.aliases = set(aliases)

    def value(self, expression):
        return self.doc.Parameters.evalExpression(expression).Value

    def link(self, expression):
        return re.sub(r"\b[A-Za-z_][A-Za-z_0-9]*\b",
                      lambda m: "Parameters." + m[0] if m[0] in self.aliases else m[0], expression)

    def dimension(self, sketch, constraint, name, expression):
        index = sketch.addConstraint(constraint)
        sketch.renameConstraint(index, name)
        sketch.setExpression("Constraints." + name, self.link(expression))

    def sketch(self, name, plane, offset):
        sketch = self.body.newObject("Sketcher::SketchObject", name)
        if plane == "YZ":
            sketch.Placement.Rotation = App.Rotation(App.Vector(1, 1, 1), 120)
            axis = "x"
        elif plane == "XZ":
            sketch.Placement.Rotation = App.Rotation(App.Vector(1, 0, 0), 90)
            axis = "y"
        else:
            assert plane == "XY"
            axis = "z"
        sketch.setExpression("Placement.Base." + axis, self.link(offset))
        return sketch

    def rectangle(self, sketch, left, bottom, width, height, prefix):
        x, y, w, h = [self.value(e) for e in (left, bottom, width, height)]
        assert w > 0 and h > 0
        start = sketch.GeometryCount
        points = [App.Vector(a, b, 0) for a, b in ((x, y), (x + w, y), (x + w, y + h), (x, y + h))]
        for i in range(4):
            sketch.addGeometry(Part.LineSegment(points[i], points[(i + 1) % 4]), False)
            sketch.addConstraint(Sketcher.Constraint("Horizontal" if i % 2 == 0 else "Vertical", start + i))
        for i in range(4):
            sketch.addConstraint(Sketcher.Constraint("Coincident", start + i, 2, start + (i + 1) % 4, 1))
        self.coordinate(sketch, start, 1, "X", left, prefix + "X")
        self.coordinate(sketch, start, 1, "Y", bottom, prefix + "Y")
        self.dimension(sketch, Sketcher.Constraint("Distance", start, w), prefix + "Width", width)
        self.dimension(sketch, Sketcher.Constraint("Distance", start + 1, h), prefix + "Height", height)

    def coordinate(self, sketch, geometry, point, axis, expression, name):
        value = self.value(expression)
        if expression == "0 mm":
            sketch.addConstraint(Sketcher.Constraint("PointOnObject", geometry, point, -2 if axis == "X" else -1))
        else:
            self.dimension(sketch, Sketcher.Constraint("Distance" + axis, geometry, point, value), name, expression)

    def circle(self, sketch, x, y, diameter, prefix):
        index = sketch.addGeometry(Part.Circle(App.Vector(self.value(x), self.value(y), 0),
                                               App.Vector(0, 0, 1), self.value(diameter) / 2), False)
        self.coordinate(sketch, index, 3, "X", x, prefix + "X")
        self.coordinate(sketch, index, 3, "Y", y, prefix + "Y")
        self.dimension(sketch, Sketcher.Constraint("Diameter", index, self.value(diameter)), prefix + "Diameter", diameter)

    def hexagon(self, sketch, x, y, radius):
        cx, cy, r = [self.value(e) for e in (x, y, radius)]
        points = [App.Vector(cx + r * math.cos(i * math.pi / 3), cy + r * math.sin(i * math.pi / 3), 0)
                  for i in range(6)]
        for i in range(6):
            sketch.addGeometry(Part.LineSegment(points[i], points[(i + 1) % 6]), False)
        circle = sketch.addGeometry(Part.Circle(App.Vector(cx, cy, 0), App.Vector(0, 0, 1), r), True)
        for i in range(6):
            sketch.addConstraint(Sketcher.Constraint("Coincident", i, 2, (i + 1) % 6, 1))
            sketch.addConstraint(Sketcher.Constraint("PointOnObject", i, 1, circle))
            if i:
                sketch.addConstraint(Sketcher.Constraint("Equal", 0, i))
        sketch.addConstraint(Sketcher.Constraint("Horizontal", 1))
        self.coordinate(sketch, circle, 3, "X", x, "CenterX")
        self.coordinate(sketch, circle, 3, "Y", y, "CenterY")
        self.dimension(sketch, Sketcher.Constraint("Radius", circle, r), "Radius", radius)

    def extrude(self, name, label, sketch, length, cut=True, reverse=False, through=False):
        self.doc.recompute()
        assert sketch.FullyConstrained and sketch.solve() == 0, sketch.Name
        feature = self.body.newObject("PartDesign::Pocket" if cut else "PartDesign::Pad", name)
        feature.Label = label
        feature.Profile = sketch
        if through:
            feature.Type = "ThroughAll"
        else:
            feature.setExpression("Length", self.link(length))
        feature.Reversed = reverse
        self.doc.recompute()
        assert not feature.Shape.isNull() and feature.Shape.isValid(), (name, list(feature.State))
        self.show_tip(feature)
        return feature

    def show_tip(self, feature):
        for obj in self.body.Group:
            if hasattr(obj, "ViewObject"):
                obj.Visibility = obj == feature
        self.body.Visibility = True
        feature.Visibility = True
