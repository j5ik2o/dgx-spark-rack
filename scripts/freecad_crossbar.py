"""支持棒1種類をFreeCADの寸法表・スケッチ・Pad・Pocketで作る評価モデル。"""

import FreeCAD as App
import Part
import Sketcher


INPUTS = [
    ("ModuleWidth", "210 mm", "ラック幅"),
    ("SideThickness", "12 mm", "側板厚さ"),
    ("TenonLength", "9 mm", "側板の内側から先へ伸びる長さ"),
    ("BeamWidth", "20 mm", "支持棒の幅"),
    ("BeamThickness", "8 mm", "支持棒の厚さ"),
    ("PinDiameter", "4 mm", "固定ピンの直径"),
    ("FitClearance", "0.3 mm", "ピン穴の片側の隙間"),
    ("PinInset", "4 mm", "側板内側から穴中心までの距離"),
]
DERIVED = [
    ("InnerX", "=ModuleWidth / 2 - SideThickness", "左右側板の内側位置"),
    ("BeamLength", "=2 * (InnerX + TenonLength)", "支持棒の全長"),
    ("PinX", "=InnerX + PinInset", "中心からピン穴までの距離"),
    ("HoleDiameter", "=PinDiameter + 2 * FitClearance", "ピン穴の直径"),
]
CELLS = {name: f"B{row}" for row, (name, _, _) in enumerate(INPUTS + DERIVED, 2)}


def dimension(sketch, constraint, name, expression):
    index = sketch.addConstraint(constraint)
    sketch.renameConstraint(index, name)
    sketch.setExpression(f"Constraints.{name}", expression)


def create():
    doc = App.newDocument("DgxCrossbarNativeEvaluation")
    doc.Label = "支持棒_FreeCAD履歴付き評価"
    try:
        sheet = doc.addObject("Spreadsheet::Sheet", "Parameters")
        sheet.Label = "寸法表_青が入力値"
        for cell, text in (("A1", "パラメーター"), ("B1", "値・式"), ("C1", "意味")):
            sheet.set(cell, text)
        for row, (name, value, description) in enumerate(INPUTS + DERIVED, 2):
            sheet.set(f"A{row}", name)
            sheet.set(f"B{row}", value)
            sheet.setAlias(f"B{row}", name)
            sheet.set(f"C{row}", description)
        sheet.setBackground("B2:B9", (0.82, 0.92, 1.0))
        sheet.setBackground("B10:B13", (0.9, 0.9, 0.9))
        sheet.setStyle("A1:C1", "bold", "add")
        sheet.setColumnWidth("A", 180)
        sheet.setColumnWidth("B", 260)
        sheet.setColumnWidth("C", 320)
        doc.recompute()

        body = doc.addObject("PartDesign::Body", "Crossbar")
        body.Label = "支持棒_評価用"
        body.addProperty("App::PropertyString", "EvaluationTag", "Evaluation")
        body.EvaluationTag = "dgx-native-crossbar-v1"
        outline = body.newObject("Sketcher::SketchObject", "Outline")
        outline.Label = "01_輪郭_完全拘束"
        points = [App.Vector(x, y, 0) for x, y in ((-102, -10), (102, -10), (102, 10), (-102, 10))]
        for i in range(4):
            outline.addGeometry(Part.LineSegment(points[i], points[(i + 1) % 4]), False)
            outline.addConstraint(Sketcher.Constraint("Horizontal" if i % 2 == 0 else "Vertical", i))
        for i in range(4):
            outline.addConstraint(Sketcher.Constraint("Coincident", i, 2, (i + 1) % 4, 1))
        dimension(outline, Sketcher.Constraint("DistanceX", 0, 1, -102.0), "Left", "-Parameters.BeamLength / 2")
        dimension(outline, Sketcher.Constraint("DistanceY", 0, 1, -10.0), "Bottom", "-Parameters.BeamWidth / 2")
        dimension(outline, Sketcher.Constraint("Distance", 0, 204.0), "Length", "Parameters.BeamLength")
        dimension(outline, Sketcher.Constraint("Distance", 1, 20.0), "Width", "Parameters.BeamWidth")
        doc.recompute()

        pad = body.newObject("PartDesign::Pad", "Thickness")
        pad.Label = "02_厚さ_押し出し"
        pad.Profile = outline
        pad.setExpression("Length", "Parameters.BeamThickness")
        doc.recompute()
        holes = body.newObject("Sketcher::SketchObject", "PinHoles")
        holes.Label = "03_ピン穴_完全拘束"
        # 面番号への参照を避け、穴スケッチの高さを厚さの式に結び付ける。
        holes.setExpression("Placement.Base.z", "Parameters.BeamThickness")
        for i, x in enumerate((-97, 97)):
            holes.addGeometry(Part.Circle(App.Vector(x, 0, 0), App.Vector(0, 0, 1), 2.3), False)
            holes.addConstraint(Sketcher.Constraint("PointOnObject", i, 3, -1))
            dimension(holes, Sketcher.Constraint("DistanceX", i, 3, float(x)),
                      "LeftHole" if i == 0 else "RightHole", ("-" if i == 0 else "") + "Parameters.PinX")
        holes.addConstraint(Sketcher.Constraint("Equal", 0, 1))
        dimension(holes, Sketcher.Constraint("Diameter", 0, 4.6), "Diameter", "Parameters.HoleDiameter")
        doc.recompute()
        pocket = body.newObject("PartDesign::Pocket", "ThroughHoles")
        pocket.Label = "04_ピン穴_貫通"
        pocket.Profile = holes
        pocket.Type = "ThroughAll"
        doc.recompute()
        body.Tip = pocket
        for obj in (outline, pad, holes):
            obj.Visibility = False
        body.Visibility = True
        pocket.Visibility = True
        return doc
    except Exception:
        # この関数で新規作成した未保存の評価文書だけを閉じる。
        App.closeDocument(doc.Name)
        raise
