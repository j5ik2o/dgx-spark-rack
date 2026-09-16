"""ACアダプター用の開放スタンド。寸法は公開実測を参考にした仮置き。"""

from pathlib import Path
import sys

import FreeCAD as App

sys.path.insert(0, str(Path(__file__).resolve().parent))
from freecad_features import Features


INPUTS = [
    ("AdapterWidth", "100 mm", "アダプター幅：仮寸法"),
    ("AdapterLength", "100 mm", "アダプター長さ：仮寸法"),
    ("AdapterHeight", "36 mm", "アダプター厚さ：仮寸法"),
    ("LiftHeight", "30 mm", "アダプター底面の高さ"),
    ("SideGap", "1 mm", "左右の余裕、片側"),
    ("ModuleGap", "8 mm", "隣のスタンドとの隙間"),
    ("FitClearance", "0.3 mm", "印刷部品どうしの片側の隙間"),
    ("PostWidth", "12 mm", "支持台の柱幅"),
    ("BeamHeight", "8 mm", "支持梁の高さ"),
    ("BeamDepth", "12 mm", "支持台の前後厚さ"),
    ("LipHeight", "6 mm", "左右のずれ止め高さ"),
    ("RailWidth", "14 mm", "底レールの幅"),
    ("RailBase", "3 mm", "底レールの底板厚さ"),
    ("StemWidth", "6 mm", "底レールの差込幅"),
    ("StemHeight", "5 mm", "底レールの差込高さ"),
    ("PinDiameter", "3 mm", "印刷する固定ピン径"),
    ("PinHeadDiameter", "7 mm", "固定ピンの頭径"),
    ("PinHeadHeight", "2 mm", "固定ピンの頭厚さ"),
    ("DockPitch", "28 mm", "後付けブラケットのM4穴ピッチ"),
    ("DockHole", "4.5 mm", "後付けブラケットのM4通し穴"),
    ("DockNutAF", "7.5 mm", "M4ナット座の対辺"),
    ("DockNutDepth", "3.5 mm", "M4ナット座の深さ"),
    ("JoinPegDiameter", "4 mm", "横連結クリップの差込ピン径"),
    ("JoinPegLength", "4 mm", "横連結クリップの差込長さ"),
    ("JoinThickness", "4 mm", "横連結クリップの厚さ"),
]
DERIVED = [
    ("InsideWidth", "=AdapterWidth + 2 * SideGap", "アダプターを受ける内幅"),
    ("PostCenter", "=InsideWidth / 2 + PostWidth / 2", "左右の柱とレールの中心"),
    ("SaddleWidth", "=InsideWidth + 2 * PostWidth", "支持台の幅"),
    ("SaddleLift", "=LiftHeight - RailBase", "支持台単体の受け面高さ"),
    ("SaddleHeight", "=SaddleLift + LipHeight", "支持台単体の全高"),
    ("SupportPitch", "=AdapterLength * 0.65", "前後の支持台の中心間隔"),
    ("RailLength", "=AdapterLength + 40 mm", "底レールの長さ"),
    ("RailHeight", "=RailBase + StemHeight", "底レールの全高"),
    ("ModuleWidth", "=2 * PostCenter + RailWidth", "1台分の幅"),
    ("ModulePitch", "=ModuleWidth + ModuleGap", "横に増設する中心間隔"),
    ("PinLength", "=LiftHeight + LipHeight - 1 mm", "固定ピンの軸長さ"),
    ("JoinSpacing", "=ModulePitch - 2 * PostCenter", "横連結の差込ピン間隔"),
    ("JoinLength", "=JoinSpacing + 14 mm", "横連結クリップの長さ"),
]
CELLS = {name: f"B{row}" for row, (name, _, _) in enumerate(INPUTS + DERIVED, 2)}


def new_body(doc, name, label):
    body = doc.addObject("PartDesign::Body", name)
    body.Label = label
    doc.PartLibrary.addObject(body)
    return body, Features(doc, body, CELLS)


def make_saddle(doc):
    body, f = new_body(doc, "Saddle", "支持台_前後共通")
    s = f.sketch("SaddleOutline", "XZ", "-BeamDepth / 2")
    f.rectangle(s, "-SaddleWidth / 2", "0 mm", "SaddleWidth", "SaddleHeight", "Outer")
    f.extrude("SaddleBlank", "支持台の素形", s, "BeamDepth", cut=False, reverse=True)
    s = f.sketch("SaddleOpenings", "XZ", "-BeamDepth / 2")
    f.rectangle(s, "-InsideWidth / 2", "-1 mm", "InsideWidth", "SaddleLift - BeamHeight + 1 mm", "Bottom")
    f.rectangle(s, "-InsideWidth / 2", "SaddleLift", "InsideWidth", "LipHeight + 1 mm", "Top")
    f.extrude("SaddleOpenCut", "上下を開放する", s, None, through=True)
    s = f.sketch("RailNotches", "XZ", "-BeamDepth / 2")
    for prefix, x in (("Left", "-PostCenter"), ("Right", "PostCenter")):
        f.rectangle(s, x + " - StemWidth / 2 - FitClearance", "-1 mm", "StemWidth + 2 * FitClearance",
                    "StemHeight + FitClearance + 1 mm", prefix)
    f.extrude("RailNotchCut", "底レールの差込部", s, None, through=True)
    s = f.sketch("SaddlePinHoles", "XY", "SaddleHeight")
    for prefix, x in (("Left", "-PostCenter"), ("Right", "PostCenter")):
        f.circle(s, x, "0 mm", "PinDiameter + 2 * FitClearance", prefix)
    f.extrude("SaddlePinsCut", "固定ピンの穴", s, None, through=True)
    return body


def make_rail(doc):
    body, f = new_body(doc, "Rail", "底レール_左右共通_ファン用M4穴付き")
    s = f.sketch("RailBaseProfile", "XY", "0 mm")
    f.rectangle(s, "-RailWidth / 2", "-RailLength / 2", "RailWidth", "RailLength", "Base")
    f.extrude("RailBasePad", "床に接する底板", s, "RailBase", cut=False)
    s = f.sketch("RailStemProfile", "XY", "RailBase")
    f.rectangle(s, "-StemWidth / 2", "-RailLength / 2", "StemWidth", "RailLength", "Stem")
    f.extrude("RailStemPad", "支持台を位置決めする桟", s, "StemHeight", cut=False)
    s = f.sketch("DockBossProfiles", "XY", "RailBase")
    for prefix, y in (("Front", "-DockPitch / 2"), ("Rear", "DockPitch / 2")):
        f.rectangle(s, "-RailWidth / 2", y + " - 7 mm", "RailWidth", "14 mm", prefix)
    f.extrude("DockBossPad", "後付けブラケットの取付座", s, "StemHeight", cut=False)
    s = f.sketch("RailPinHoles", "XY", "RailHeight")
    for prefix, y in (("Front", "-SupportPitch / 2"), ("Rear", "SupportPitch / 2")):
        f.circle(s, "0 mm", y, "PinDiameter + 2 * FitClearance", prefix)
    f.extrude("RailPinsCut", "支持台を留めるピン穴", s, None, through=True)
    s = f.sketch("DockHoleProfiles", "XY", "RailHeight")
    for prefix, y in (("Front", "-DockPitch / 2"), ("Rear", "DockPitch / 2")):
        f.circle(s, "0 mm", y, "DockHole", prefix)
    f.extrude("DockHolesCut", "後付けブラケットのM4穴", s, None, through=True)
    s = f.sketch("CableTieProfiles", "XY", "RailHeight")
    for prefix, y in (("Front", "-AdapterLength / 2 - 12 mm"), ("Rear", "AdapterLength / 2 + 12 mm")):
        f.rectangle(s, "-2 mm", y + " - 6 mm", "4 mm", "12 mm", prefix)
    f.extrude("CableTieCut", "ケーブル固定用のバンド穴", s, None, through=True)
    for prefix, y in (("Front", "-DockPitch / 2"), ("Rear", "DockPitch / 2")):
        s = f.sketch(prefix + "DockNut", "XY", "0 mm")
        f.hexagon(s, "0 mm", y, "DockNutAF / sqrt(3)")
        f.extrude(prefix + "DockNutCut", "M4ナット座_" + prefix, s, "DockNutDepth", reverse=True)
    return body


def make_pin(doc):
    body, f = new_body(doc, "LockPin", "印刷する固定ピン")
    s = f.sketch("PinHead", "XY", "0 mm")
    f.circle(s, "0 mm", "0 mm", "PinHeadDiameter", "Head")
    f.extrude("PinHeadPad", "ピンの頭", s, "PinHeadHeight", cut=False)
    s = f.sketch("PinShaft", "XY", "PinHeadHeight")
    f.circle(s, "0 mm", "0 mm", "PinDiameter", "Shaft")
    f.extrude("PinShaftPad", "ピンの軸", s, "PinLength", cut=False)
    return body


def make_join(doc):
    body, f = new_body(doc, "JoinClip", "横連結クリップ")
    s = f.sketch("JoinBase", "XY", "0 mm")
    f.rectangle(s, "-JoinLength / 2", "-6 mm", "JoinLength", "12 mm", "Base")
    f.extrude("JoinBasePad", "横連結の橋", s, "JoinThickness", cut=False)
    s = f.sketch("JoinPegs", "XY", "JoinThickness")
    for prefix, x in (("Left", "-JoinSpacing / 2"), ("Right", "JoinSpacing / 2")):
        f.circle(s, x, "0 mm", "JoinPegDiameter", prefix)
    f.extrude("JoinPegsPad", "M4穴へ差し込む突起", s, "JoinPegLength", cut=False)
    return body


def make_reference(doc):
    body, f = new_body(doc, "REFAdapter", "参考_ACアダプター_実寸未確認")
    s = f.sketch("AdapterEnvelope", "XY", "LiftHeight")
    f.rectangle(s, "-AdapterWidth / 2", "-AdapterLength / 2", "AdapterWidth", "AdapterLength", "Adapter")
    f.extrude("AdapterEnvelopePad", "アダプターの仮外形", s, "AdapterHeight", cut=False)
    return body


def link(doc, group, source, name, label, x="0 mm", y="0 mm", z="0 mm", inverted=False):
    obj = doc.addObject("App::Link", name)
    obj.setLink(source)
    group.addObject(obj)
    obj.Label = label
    if inverted:
        obj.Placement.Rotation = App.Rotation(App.Vector(1, 0, 0), 180)
    for axis, expression in zip("xyz", (x, y, z)):
        obj.setExpression("Placement.Base." + axis, expression)
    obj.Visibility = True
    return obj


def show_units(doc, count):
    assert count in (2, 4)
    for i in range(4):
        doc.getObject(f"Unit{i + 1}").Visibility = i < count
    for i in range(3):
        doc.getObject(f"JoinPair{i + 1}").Visibility = i < count - 1
    doc.recompute()


def create():
    doc = App.newDocument("DGXSparkAdapterStand")
    doc.Label = "ACアダプタースタンド_仮寸法"
    try:
        sheet = doc.addObject("Spreadsheet::Sheet", "Parameters")
        sheet.Label = "寸法表_電源外寸は未確認"
        for cell, value in (("A1", "パラメーター"), ("B1", "値・式"), ("C1", "意味")):
            sheet.set(cell, value)
        for row, (name, value, description) in enumerate(INPUTS + DERIVED, 2):
            sheet.set(f"A{row}", name)
            sheet.set(f"B{row}", value)
            sheet.setAlias(f"B{row}", name)
            sheet.set(f"C{row}", description)
        sheet.setBackground("B2:B8", (0.82, 0.92, 1.0))
        sheet.setBackground(f"B{len(INPUTS) + 2}:B{len(INPUTS + DERIVED) + 1}", (0.9, 0.9, 0.9))
        for column, width in (("A", 200), ("B", 360), ("C", 360)):
            sheet.setColumnWidth(column, width)
        doc.addObject("App::Part", "PartLibrary").Label = "部品原型_通常は非表示"
        doc.recompute()
        parts = {"Saddle": make_saddle(doc), "Rail": make_rail(doc), "LockPin": make_pin(doc),
                 "JoinClip": make_join(doc), "REFAdapter": make_reference(doc)}
        colors = {"Saddle": (0.38, 0.55, 0.68), "Rail": (0.45, 0.5, 0.56), "LockPin": (0.6, 0.7, 0.43),
                  "JoinClip": (0.6, 0.7, 0.43), "REFAdapter": (0.19, 0.2, 0.21)}
        for name, body in parts.items():
            body.ViewObject.ShapeColor = colors[name]
            body.Tip.ViewObject.ShapeColor = colors[name]
        assembly = doc.addObject("App::Part", "StandAssembly")
        assembly.Label = "開放スタンド_初期2台_横に4台まで"
        assembly.addProperty("App::PropertyString", "DesignStatus", "Design")
        assembly.DesignStatus = "Provisional dimensions; adapter model and cable exits await confirmation."
        for i in range(4):
            unit = doc.addObject("App::Part", f"Unit{i + 1}")
            unit.Label = f"アダプター{i + 1}"
            assembly.addObject(unit)
            unit.setExpression("Placement.Base.x", f"{i} * Parameters.ModulePitch")
            for side, x in (("L", "-Parameters.PostCenter"), ("R", "Parameters.PostCenter")):
                link(doc, unit, parts["Rail"], f"Rail{side}{i}", "底レール_" + side, x=x)
            for end, y in (("Front", "-Parameters.SupportPitch / 2"), ("Rear", "Parameters.SupportPitch / 2")):
                link(doc, unit, parts["Saddle"], f"Saddle{end}{i}", "支持台_" + end, y=y, z="Parameters.RailBase")
                for side, x in (("L", "-Parameters.PostCenter"), ("R", "Parameters.PostCenter")):
                    link(doc, unit, parts["LockPin"], f"Pin{end}{side}{i}", "固定ピン", x=x, y=y,
                         z="Parameters.LiftHeight + Parameters.LipHeight + Parameters.PinHeadHeight", inverted=True)
            link(doc, unit, parts["REFAdapter"], f"Adapter{i}", "参考_電源外形_実寸未確認")
        for i in range(3):
            group = doc.addObject("App::Part", f"JoinPair{i + 1}")
            group.Label = f"横連結_{i + 1}と{i + 2}"
            assembly.addObject(group)
            for end, y in (("Front", "-Parameters.DockPitch / 2"), ("Rear", "Parameters.DockPitch / 2")):
                link(doc, group, parts["JoinClip"], f"Join{end}{i}", "横連結クリップ",
                     x=f"({i} + 0.5) * Parameters.ModulePitch", y=y,
                     z="Parameters.RailHeight + Parameters.JoinThickness", inverted=True)
        doc.PartLibrary.Visibility = False
        show_units(doc, 2)
        return doc
    except Exception:
        App.closeDocument(doc.Name)
        raise
