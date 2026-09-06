"""左側板をFreeCADの履歴付きモデルとして作る。Fusionの正本は変更しない。"""

import FreeCAD as App
from freecad_sideplate_features import Features


INPUTS = [
    ("ModuleWidth", "210 mm", "ラック幅"),
    ("ModuleDepth", "230 mm", "ラック奥行"),
    ("FrameHeight", "170 mm", "側板高さ"),
    ("SideThickness", "12 mm", "側板厚さ"),
    ("FitClearance", "0.3 mm", "接合部の片側の隙間"),
    ("SupportTop", "60 mm", "本体を支える棒の上面高さ"),
    ("DgxFront", "60 mm", "本体前面の位置"),
    ("DgxDepth", "150 mm", "本体奥行"),
    ("FanDepth", "27 mm", "ファン厚さ"),
    ("PinDiameter", "4 mm", "支持棒用ピン径"),
    ("LocatorDiameter", "6 mm", "上下連結ピン径"),
    ("WindowRadius", "3 mm", "窓の隅の丸み"),
    ("NutAF", "7 mm", "M4ナットの対辺"),
]
DERIVED = [
    ("InnerX", "=ModuleWidth / 2 - SideThickness", "側板内面の位置"),
    ("PinX", "=InnerX + 4 mm", "支持棒用ピン中心"),
    ("PostX", "=ModuleWidth / 2 - SideThickness / 2", "側板厚さ方向の中心"),
    ("FrontY", "=FanDepth + 11 mm", "側板前端"),
    ("SupportFrontY", "=DgxFront + 22 mm", "前の支持棒中心"),
    ("SupportRearY", "=DgxFront + DgxDepth - 12 mm", "後ろの支持棒中心"),
    ("UpperBarY", "=ModuleDepth - 50 mm", "上の支持棒中心"),
    ("CassetteUpperZ", "=FrameHeight - 25 mm", "ファン保持部の上側ねじ高さ"),
]
CELLS = {name: f"B{row}" for row, (name, _, _) in enumerate(INPUTS + DERIVED, 2)}


def create():
    doc = App.newDocument("DgxSideplateNativeEvaluation")
    doc.Label = "左側板_FreeCAD履歴付き評価"
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
        sheet.setBackground("B2:B14", (0.82, 0.92, 1.0))
        sheet.setBackground("B15:B22", (0.9, 0.9, 0.9))
        sheet.setStyle("A1:C1", "bold", "add")
        for column, width in (("A", 180), ("B", 300), ("C", 320)):
            sheet.setColumnWidth(column, width)
        body = doc.addObject("PartDesign::Body", "Sideplate")
        body.Label = "左側板_評価用"
        body.addProperty("App::PropertyString", "EvaluationTag", "Evaluation")
        body.EvaluationTag = "dgx-native-sideplate-v1"
        doc.recompute()
        f = Features(doc, CELLS)

        outline = f.sketch("PlateOutline", "YZ", "-ModuleWidth / 2")
        f.rectangle(outline, "FrontY", "0 mm", "ModuleDepth - FrontY", "FrameHeight", "Plate")
        f.extrude("PlatePad", "01_素板", outline, "SideThickness", cut=False)
        windows = f.sketch("WindowProfiles", "YZ", "-ModuleWidth / 2")
        f.rectangle(windows, "FrontY + 20 mm", "18 mm", "ModuleDepth - FrontY - 40 mm", "SupportTop - 30 mm", "Lower")
        f.rectangle(windows, "FrontY + 20 mm", "SupportTop + 12 mm", "ModuleDepth - FrontY - 40 mm",
                    "FrameHeight - SupportTop - 30 mm", "Upper")
        cut = f.extrude("WindowCut", "02_上下の窓", windows, None, reverse=True, through=True)
        f.round_windows(cut)

        sockets = f.sketch("SocketProfiles", "YZ", "-InnerX")
        for prefix, y, z in (("Front", "SupportFrontY", "SupportTop - 8 mm"),
                             ("Rear", "SupportRearY", "SupportTop - 8 mm"),
                             ("Upper", "UpperBarY", "FrameHeight - 10 mm")):
            f.rectangle(sockets, y + " - 10 mm - FitClearance", z + " - FitClearance",
                        "20 mm + 2 * FitClearance", "8 mm + 2 * FitClearance", prefix)
        f.extrude("SocketCut", "04_支持棒の差込口3か所", sockets, "SideThickness - 3 mm + FitClearance")
        pins = f.sketch("LowerPinProfiles", "XY", "SupportTop - 20 mm")
        for prefix, y in (("Front", "SupportFrontY"), ("Rear", "SupportRearY")):
            f.circle(pins, "-PinX", y, "PinDiameter + 2 * FitClearance", prefix)
        f.extrude("LowerPinCut", "05_下の支持棒用ピン穴", pins, "44 mm", reverse=True)
        pins = f.sketch("UpperPinProfile", "XY", "FrameHeight - 22 mm")
        f.circle(pins, "-PinX", "UpperBarY", "PinDiameter + 2 * FitClearance", "Upper")
        f.extrude("UpperPinCut", "06_上の支持棒用ピン穴", pins, "44 mm", reverse=True)

        for prefix, plane_z, reverse, label in (("Bottom", "0 mm", True, "07_底の上下連結穴"),
                                                 ("Top", "FrameHeight", False, "08_上の上下連結穴")):
            holes = f.sketch(prefix + "LocatorProfiles", "XY", plane_z)
            for name, y in (("Front", "FrontY + 8 mm"), ("Rear", "ModuleDepth - 8 mm")):
                f.circle(holes, "-PostX", y, "LocatorDiameter + 2 * FitClearance", name)
            f.extrude(prefix + "LocatorCut", label, holes, "8.3 mm", reverse=reverse)
        socket = f.sketch("CassetteSocketProfile", "XZ", "FrontY")
        f.rectangle(socket, "-PostX - 4 mm - FitClearance", "20 mm - FitClearance",
                    "8 mm + 2 * FitClearance", "8 mm + 2 * FitClearance", "Cassette")
        f.extrude("CassetteSocketCut", "09_ファン保持部の下側差込口", socket, "8 mm + FitClearance")
        screw = f.sketch("ScrewProfile", "XZ", "FrontY")
        f.circle(screw, "-PostX", "CassetteUpperZ", "4.5 mm", "Screw")
        f.extrude("ScrewCut", "10_M4通し穴", screw, "18 mm")
        nut = f.sketch("NutProfile", "XZ", "FrontY + 12.4 mm")
        f.hexagon(nut, "-PostX", "CassetteUpperZ", "(NutAF + 0.5 mm) / sqrt(3)")
        final = f.extrude("NutCut", "11_M4ナット差込口", nut, "8.1 mm")
        body.Tip = final
        doc.recompute()
        return doc
    except Exception:
        App.closeDocument(doc.Name)
        raise
