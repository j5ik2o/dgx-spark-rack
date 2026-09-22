"""1台単位で縦横に連結するアダプターラック。ファンは1列につき1基。"""

import FreeCAD as App

from adapter_rack_parameters import CELLS, INPUTS, DERIVED
from freecad_features import Features

PRINT_PARTS = {
    "SideL": "side_L", "SideR": "side_R", "SupportBeam": "support_beam",
    "LockPin": "locking_pin", "StackPin": "stack_pin", "StackStrap": "stack_strap",
    "JoinBridge": "join_bridge", "FanPlate": "fan_plate", "AccessoryPlate": "accessory_plate",
    "FitCoupon020": "fit_coupon_020", "FitCoupon030": "fit_coupon_030",
    "FitCoupon040": "fit_coupon_040", "BeamCoupon": "beam_coupon",
}
LAYOUTS = {"single": (1, 1), "two_horizontal": (2, 1), "two_vertical": (1, 2), "four_units": (2, 2)}


def body(doc, name, label):
    obj = doc.addObject("PartDesign::Body", name)
    obj.Label = label
    doc.PartLibrary.addObject(obj)
    return obj, Features(doc, obj, CELLS)


def side(doc, name, left):
    obj, f = body(doc, name, "側枠_左" if left else "側枠_右")
    s = f.sketch(name + "Outline", "YZ", "0 mm")
    f.rectangle(s, "-FrameDepth / 2", "0 mm", "FrameDepth", "ModuleHeight", "Outer")
    f.extrude(name + "Pad", "側枠の素形", s, "FrameThickness", cut=False)
    s = f.sketch(name + "Window", "YZ", "FrameThickness")
    f.rectangle(s, "-FrameDepth / 2 + PostDepth", "BaseHeight", "FrameDepth - 2 * PostDepth",
                "ModuleHeight - BaseHeight - TopBeam", "Window")
    f.extrude(name + "Open", "配線と取り出し用の開口", s, None, through=True)
    s = f.sketch(name + "Sockets", "YZ", "FrameThickness" if left else "0 mm")
    for tag, y in (("Front", "-BeamPitch / 2"), ("Rear", "BeamPitch / 2")):
        f.rectangle(s, y + " - BeamWidth / 2 - FitClearance", "BeamZ - FitClearance",
                    "BeamWidth + 2 * FitClearance", "BeamHeight + 2 * FitClearance", tag)
    f.extrude(name + "SocketCut", "支持棒の差込口", s, "TenonLength + FitClearance", reverse=not left)
    s = f.sketch(name + "PinHoles", "XY", "BaseHeight")
    px = "FrameThickness - TenonLength / 2" if left else "TenonLength / 2"
    for tag, y in (("Front", "-BeamPitch / 2"), ("Rear", "BeamPitch / 2")):
        f.circle(s, px, y, "PinDiameter + 2 * FitClearance", tag)
    f.extrude(name + "PinCut", "支持棒固定ピン穴", s, None, through=True)
    for tag, z, reverse in (("Top", "ModuleHeight", False), ("Bottom", "0 mm", True)):
        s = f.sketch(name + tag + "Locators", "XY", z)
        for end, y in (("Front", "-PostY"), ("Rear", "PostY")):
            f.circle(s, "FrameThickness / 2", y, "StackDiameter + 2 * FitClearance", end)
        f.extrude(name + tag + "LocatorCut", "上下位置決め穴", s,
                  "StackEngagement + 0.5 mm", reverse=reverse)
    s = f.sketch(name + "HorizontalJoin", "XY", "BaseHeight")
    for tag, y in (("Front", "-JoinY"), ("Rear", "JoinY")):
        f.circle(s, "FrameThickness / 2", y, "JoinPegDiameter + 2 * FitClearance", tag)
    f.extrude(name + "JoinCut", "横連結の差込穴", s, "JoinEngagement + 0.5 mm")
    s = f.sketch(name + "FrontFixings", "XZ", "-FrameDepth / 2")
    for tag, z in (("Low", "FanMountLow"), ("High", "FanMountHigh")):
        f.circle(s, "FrameThickness / 2", z, "BoltHole", tag)
    f.extrude(name + "FanCut", "ファン保持板用M4穴", s, "PostDepth")
    s = f.sketch(name + "SideFixings", "YZ", "FrameThickness")
    for tag, z in (("Lower", "StrapPitch / 2"), ("Upper", "ModuleHeight - StrapPitch / 2")):
        f.circle(s, "0 mm", z, "BoltHole", tag)
    for tag, z in (("AccessoryLow", "ModuleHeight / 2 - AccessoryPitch / 2"),
                   ("AccessoryHigh", "ModuleHeight / 2 + AccessoryPitch / 2")):
        f.circle(s, "-PostY", z, "BoltHole", tag)
    f.extrude(name + "SideCut", "上下保持板とアクセサリー用M4穴", s, None, through=True)
    return obj


def beam(doc):
    obj, f = body(doc, "SupportBeam", "支持棒_前後共通")
    s = f.sketch("BeamOutline", "XY", "0 mm")
    f.rectangle(s, "-BeamLength / 2", "-BeamWidth / 2", "BeamLength", "BeamWidth", "Beam")
    f.extrude("BeamPad", "電源を支える棒", s, "BeamHeight", cut=False)
    s = f.sketch("BeamLips", "XY", "BeamHeight")
    for tag, x in (("L", "-AdapterLength / 2 - SideGap - LipWidth"), ("R", "AdapterLength / 2 + SideGap")):
        f.rectangle(s, x, "-BeamWidth / 2", "LipWidth", "BeamWidth", tag)
    f.extrude("BeamLipPad", "横ずれ止め", s, "LipHeight", cut=False)
    s = f.sketch("BeamPins", "XY", "BeamHeight")
    for tag, x in (("L", "-PinX"), ("R", "PinX")):
        f.circle(s, x, "0 mm", "PinDiameter + 2 * FitClearance", tag)
    f.extrude("BeamPinCut", "固定ピン穴", s, None, through=True)
    s = f.sketch("BeamBandSlots", "XY", "BeamHeight")
    for tag, x in (("L", "-AdapterLength / 2 - SideGap - LipWidth - 6 mm"),
                   ("R", "AdapterLength / 2 + SideGap + LipWidth + 2 mm")):
        f.rectangle(s, x, "-3 mm", "4 mm", "6 mm", tag)
    f.extrude("BeamBandCut", "電源保持バンド用の長穴", s, None, through=True)
    return obj


def round_pin(doc, name, diameter, length, head=False):
    obj, f = body(doc, name, "支持棒固定ピン" if head else "上下位置決めピン")
    s = f.sketch(name + "Profile", "XY", "0 mm")
    f.circle(s, "0 mm", "0 mm", "PinHeadDiameter" if head else diameter, "Circle")
    f.extrude(name + "Pad", "ピンの素形", s, "PinHeadHeight" if head else length, cut=False)
    if head:
        s = f.sketch(name + "Shaft", "XY", "PinHeadHeight")
        f.circle(s, "0 mm", "0 mm", diameter, "Shaft")
        f.extrude(name + "ShaftPad", "ピンの軸", s, length, cut=False)
    return obj


def strap(doc):
    obj, f = body(doc, "StackStrap", "上下の浮き上がりを留める保持板")
    s = f.sketch("StrapOutline", "YZ", "0 mm")
    f.rectangle(s, "-8 mm", "-14 mm", "16 mm", "28 mm", "Strap")
    f.extrude("StrapPad", "上下保持板", s, "StrapThickness", cut=False)
    s = f.sketch("StrapHoles", "YZ", "StrapThickness")
    for tag, z in (("Lower", "-StrapPitch / 2"), ("Upper", "StrapPitch / 2")):
        f.circle(s, "0 mm", z, "BoltHole", tag)
    f.extrude("StrapCut", "上下保持板のM4穴", s, None, through=True)
    return obj


def bridge(doc):
    obj, f = body(doc, "JoinBridge", "横連結クリップ")
    s = f.sketch("BridgeOutline", "XY", "0 mm")
    f.rectangle(s, "-JoinWidth / 2", "-8 mm", "JoinWidth", "16 mm", "Bridge")
    f.extrude("BridgePad", "横連結の橋", s, "JoinThickness", cut=False)
    s = f.sketch("BridgePins", "XY", "JoinThickness")
    for tag, x in (("L", "-JoinSpacing / 2"), ("R", "JoinSpacing / 2")):
        f.circle(s, x, "0 mm", "JoinPegDiameter", tag)
    f.extrude("BridgePinsPad", "横連結の突起", s, "JoinEngagement", cut=False)
    return obj


def fan_plate(doc):
    obj, f = body(doc, "FanPlate", "120mmファン保持板_縦2段共用")
    s = f.sketch("FanPlateOutline", "XZ", "0 mm")
    f.rectangle(s, "-ModuleWidth / 2", "FanPlateBottom", "ModuleWidth", "FanPlateHeight", "Plate")
    f.circle(s, "0 mm", "FanCenterZ", "FanOpening", "Air")
    f.extrude("FanPlatePad", "ファン保持板", s, "FanPlateThickness", cut=False, reverse=True)
    s = f.sketch("FanPlateHoles", "XZ", "0 mm")
    for side_tag, x in (("L", "-FanHolePitch / 2"), ("R", "FanHolePitch / 2")):
        for end_tag, z in (("Low", "FanCenterZ - FanHolePitch / 2"), ("High", "FanCenterZ + FanHolePitch / 2")):
            f.circle(s, x, z, "BoltHole", side_tag + end_tag)
    for side_tag, x in (("L", "-PostX"), ("R", "PostX")):
        for end_tag, z in (("Low", "FanMountLow"), ("High", "FanMountHigh")):
            f.circle(s, x, z, "BoltHole", "Rack" + side_tag + end_tag)
    f.extrude("FanPlateCut", "ファンとラックを固定するM4穴", s, None, through=True)
    return obj


def accessory(doc):
    obj, f = body(doc, "AccessoryPlate", "ファンコンケース用取り付け面_ケース未確定")
    s = f.sketch("AccessoryOutline", "YZ", "0 mm")
    f.rectangle(s, "-PostY - 22 mm", "ModuleHeight / 2 - 24 mm", "44 mm", "48 mm", "Plate")
    f.extrude("AccessoryPad", "着脱式取り付け面", s, "AccessoryThickness", cut=False)
    s = f.sketch("AccessoryFixings", "YZ", "AccessoryThickness")
    for tag, z in (("Low", "ModuleHeight / 2 - AccessoryPitch / 2"),
                   ("High", "ModuleHeight / 2 + AccessoryPitch / 2")):
        f.circle(s, "-PostY", z, "BoltHole", tag)
    for tag, y in (("Front", "-PostY - 17 mm"), ("Rear", "-PostY + 13 mm")):
        f.rectangle(s, y, "ModuleHeight / 2 - 9 mm", "4 mm", "18 mm", tag)
    f.extrude("AccessoryCut", "M4穴とケース保持バンド用長穴", s, None, through=True)
    return obj


def references(doc):
    obj, f = body(doc, "REFAdapter", "参考_純正電源_配線は左右")
    s = f.sketch("AdapterOutline", "XY", "BaseHeight")
    f.rectangle(s, "-AdapterLength / 2", "-AdapterWidth / 2", "AdapterLength", "AdapterWidth", "Adapter")
    f.extrude("AdapterPad", "電源外形の参考", s, "AdapterHeight", cut=False)
    fan, f = body(doc, "REFFan", "参考_NF-A12x25 G2_羽根は省略")
    s = f.sketch("FanOutline", "XZ", "0 mm")
    f.rectangle(s, "-FanSize / 2", "FanCenterZ - FanSize / 2", "FanSize", "FanSize", "Fan")
    f.circle(s, "0 mm", "FanCenterZ", "FanOpening", "Air")
    f.extrude("FanEnvelopePad", "ファン枠の参考", s, "FanThickness", cut=False, reverse=True)
    s = f.sketch("FanReferenceHoles", "XZ", "0 mm")
    for tag, x in (("L", "-FanHolePitch / 2"), ("R", "FanHolePitch / 2")):
        for end, z in (("Low", "FanCenterZ - FanHolePitch / 2"), ("High", "FanCenterZ + FanHolePitch / 2")):
            f.circle(s, x, z, "BoltHole", tag + end)
    f.extrude("FanReferenceCut", "参考ファンの取付穴", s, None, through=True)
    return obj, fan


def coupons(doc):
    for suffix, clearance in (("020", "0.2 mm"), ("030", "0.3 mm"), ("040", "0.4 mm")):
        name = "FitCoupon" + suffix
        obj, f = body(doc, name, "接合試験片_片側" + clearance)
        s = f.sketch(name+"Outline", "YZ", "0 mm")
        f.rectangle(s, "-12 mm", "0 mm", "24 mm", "BaseHeight", "Block")
        f.extrude(name+"Pad", "側枠下梁と同じ断面", s, "FrameThickness", cut=False)
        s = f.sketch(name+"Socket", "YZ", "FrameThickness")
        f.rectangle(s, "-BeamWidth / 2 - "+clearance, "BeamZ - "+clearance,
                    "BeamWidth + 2 * "+clearance, "BeamHeight + 2 * "+clearance, "Slot")
        f.extrude(name+"SlotCut", "支持棒の試験用差込口", s, "TenonLength + "+clearance)
        s = f.sketch(name+"Pin", "XY", "BaseHeight")
        f.circle(s, "FrameThickness - TenonLength / 2", "0 mm", "PinDiameter + 2 * "+clearance, "Pin")
        f.extrude(name+"PinCut", "試験用ピン穴", s, None, through=True)
    obj, f = body(doc, "BeamCoupon", "短い支持棒_接合試験用")
    s = f.sketch("BeamCouponOutline", "XY", "0 mm")
    f.rectangle(s, "0 mm", "-BeamWidth / 2", "24 mm", "BeamWidth", "Beam")
    f.extrude("BeamCouponPad", "短い支持棒", s, "BeamHeight", cut=False)
    s = f.sketch("BeamCouponHole", "XY", "BeamHeight")
    f.circle(s, "TenonLength / 2", "0 mm", "PinDiameter + 2 * FitClearance", "Pin")
    f.extrude("BeamCouponCut", "固定ピン穴", s, None, through=True)


def link(doc, group, source, name, x="0 mm", y="0 mm", z="0 mm", inverted=False):
    obj = doc.addObject("App::Link", name)
    obj.setLink(source)
    obj.Label = source.Label
    group.addObject(obj)
    if inverted:
        obj.Placement.Rotation = App.Rotation(App.Vector(1, 0, 0), 180)
    for axis, expression in zip("xyz", (x, y, z)):
        obj.setExpression("Placement.Base." + axis, Features(doc, None, CELLS).link(expression))
    return obj


def show_layout(doc, columns=1, rows=2):
    if (columns, rows) not in LAYOUTS.values():
        raise ValueError("表示できる構成は1台・横2台・縦2台・2段2列です")
    for col in range(2):
        for row in range(2):
            doc.getObject(f"Unit{col}{row}").Visibility = col < columns and row < rows
        doc.getObject(f"Stack{col}").Visibility = col < columns and rows == 2
        doc.getObject(f"Cooling{col}").Visibility = col < columns
    for row in range(2):
        doc.getObject(f"Horizontal{row}").Visibility = columns == 2 and row < rows
    doc.recompute()


def create():
    doc = App.newDocument("DGXSparkAdapterRack")
    doc.Label = "ACアダプターラック_v2_縦横連結"
    try:
        sheet = doc.addObject("Spreadsheet::Sheet", "Parameters")
        sheet.Label = "寸法表_正本はPython"
        for row, (name, value, description) in enumerate(INPUTS + DERIVED, 2):
            for col, text in (("A", name), ("B", value), ("C", description)):
                sheet.set(f"{col}{row}", text)
            sheet.setAlias(f"B{row}", name)
        sheet.setBackground(f"B2:B{len(INPUTS)+1}", (0.82, 0.92, 1.0))
        for col, width in (("A", 180), ("B", 320), ("C", 360)):
            sheet.setColumnWidth(col, width)
        doc.addObject("App::Part", "PartLibrary").Label = "部品原型_印刷用"
        doc.recompute()
        side(doc, "SideL", True)
        side(doc, "SideR", False)
        beam(doc)
        round_pin(doc, "LockPin", "PinDiameter", "BaseHeight", head=True)
        round_pin(doc, "StackPin", "StackDiameter", "2 * StackEngagement")
        strap(doc)
        bridge(doc)
        fan_plate(doc)
        accessory(doc)
        references(doc)
        coupons(doc)
        assembly = doc.addObject("App::Part", "RackAssembly")
        assembly.Label = "アダプターラック_初期は縦2台"
        assembly.addProperty("App::PropertyString", "DesignStatus")
        assembly.DesignStatus = "設計試作。実物の適合・耐荷重・冷却は未検証。"
        for col in range(2):
            xbase = f"{col} * ColumnPitch"
            for row in range(2):
                group = doc.addObject("App::Part", f"Unit{col}{row}")
                group.Label = f"収納部_{col+1}列_{row+1}段"
                assembly.addObject(group)
                zbase = f"{row} * ModuleHeight"
                for tag, name, x in (("L", "SideL", "-ModuleWidth / 2"), ("R", "SideR", "InnerWidth / 2")):
                    link(doc, group, doc.getObject(name), f"Side{tag}{col}{row}", x=xbase+" + "+x, z=zbase)
                for end, y in (("Front", "-BeamPitch / 2"), ("Rear", "BeamPitch / 2")):
                    link(doc, group, doc.SupportBeam, f"Beam{end}{col}{row}", x=xbase, y=y, z=zbase+" + BeamZ")
                    for tag, x in (("L", "-PinX"), ("R", "PinX")):
                        link(doc, group, doc.LockPin, f"Pin{tag}{end}{col}{row}", x=xbase+" + "+x, y=y,
                             z=zbase+" + BaseHeight + PinHeadHeight", inverted=True)
                link(doc, group, doc.REFAdapter, f"Adapter{col}{row}", x=xbase, z=zbase)
            group = doc.addObject("App::Part", f"Stack{col}")
            group.Label = f"上下連結_{col+1}列"
            assembly.addObject(group)
            for tag, x in (("L", "-PostX"), ("R", "PostX")):
                for end, y in (("Front", "-PostY"), ("Rear", "PostY")):
                    link(doc, group, doc.StackPin, f"Locator{tag}{end}{col}", x=xbase+" + "+x, y=y,
                         z="ModuleHeight - StackEngagement")
            for tag, x in (("L", "-ModuleWidth / 2 - StrapThickness"), ("R", "ModuleWidth / 2")):
                link(doc, group, doc.StackStrap, f"Strap{tag}{col}", x=xbase+" + "+x, z="ModuleHeight")
            group = doc.addObject("App::Part", f"Cooling{col}")
            group.Label = f"120mm送風部_{col+1}列_上下共用"
            assembly.addObject(group)
            link(doc, group, doc.FanPlate, f"FanMount{col}", x=xbase, y="-FrameDepth / 2 - FanPlateThickness")
            link(doc, group, doc.REFFan, f"Fan{col}", x=xbase,
                 y="-FrameDepth / 2 - FanPlateThickness - FanThickness")
        for row in range(2):
            group = doc.addObject("App::Part", f"Horizontal{row}")
            group.Label = f"横連結_{row+1}段"
            assembly.addObject(group)
            for end, y in (("Front", "-JoinY"), ("Rear", "JoinY")):
                link(doc, group, doc.JoinBridge, f"Bridge{end}{row}", x="ColumnPitch / 2", y=y,
                     z=f"{row} * ModuleHeight + BaseHeight + JoinThickness", inverted=True)
        accessory_group = doc.addObject("App::Part", "AccessoryAssembly")
        accessory_group.Label = "ファンコン用取り付け面_左前"
        assembly.addObject(accessory_group)
        link(doc, accessory_group, doc.AccessoryPlate, "ControllerDock", x="-ModuleWidth / 2 - AccessoryThickness")
        for obj in doc.PartLibrary.Group:
            color = (0.22, 0.24, 0.26)
            if obj.Name == "REFAdapter":
                color = (0.52, 0.53, 0.55)
            elif obj.Name == "REFFan":
                color = (0.76, 0.66, 0.49)
            elif obj.Name in ("LockPin", "StackPin", "JoinBridge"):
                color = (0.48, 0.61, 0.40)
            obj.ViewObject.ShapeColor = color
            obj.Tip.ViewObject.ShapeColor = color
        doc.PartLibrary.Visibility = False
        show_layout(doc)
        return doc
    except Exception:
        App.closeDocument(doc.Name)
        raise
