"""v2の構成・接合・配線余白を実形状で検査する。熱や強度は保証しない。"""

import math

import FreeCAD as App
import Part

from adapter_rack_parameters import CELLS
from freecad_adapter_rack import PRINT_PARTS, LAYOUTS, show_layout

TOLERANCE = 0.001


def assert_equivalent(a, b):
    """再読込・再生成で生じる浮動小数の差だけを許容する。"""
    if isinstance(a, dict):
        assert a.keys() == b.keys()
        for key in a:
            assert_equivalent(a[key], b[key])
    elif isinstance(a, (list, tuple)):
        assert len(a) == len(b)
        for first, second in zip(a, b):
            assert_equivalent(first, second)
    elif isinstance(a, float):
        assert math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-6), (a, b)
    else:
        assert a == b, (a, b)


def value(doc, name):
    return doc.Parameters.evalExpression(name).Value


def visible_links(doc, group=None):
    group = group or doc.RackAssembly
    result = []
    for obj in group.Group:
        if not obj.Visibility:
            continue
        if obj.TypeId == "App::Link":
            result.append((obj.Name, Part.getShape(obj).copy(True, False)))
        elif obj.TypeId == "App::Part":
            result.extend(visible_links(doc, obj))
    return result


def interference(a, b):
    aa, bb = a.BoundBox, b.BoundBox
    if any(min(getattr(aa, axis+"Max"), getattr(bb, axis+"Max")) -
           max(getattr(aa, axis+"Min"), getattr(bb, axis+"Min")) <= 1e-6 for axis in "XYZ"):
        return 0
    return a.common(b).Volume


def inspect(doc, columns, rows):
    show_layout(doc, columns, rows)
    sketches = [obj for obj in doc.Objects if obj.TypeId == "Sketcher::SketchObject"]
    assert sketches and all(s.FullyConstrained and s.solve() == 0 for s in sketches)
    for name in list(PRINT_PARTS) + ["REFAdapter", "REFFan"]:
        shape = doc.getObject(name).Shape
        assert shape.isValid() and shape.isClosed() and len(shape.Solids) == 1, name
    links = visible_links(doc)
    expected = columns*rows*9 + (columns if rows == 2 else 0)*6 + columns*2 + (2*rows if columns == 2 else 0) + 1
    assert len(links) == expected, (len(links), expected)
    collisions = []
    for index, (name, shape) in enumerate(links):
        for other, candidate in links[index+1:]:
            volume = interference(shape, candidate)
            if volume > TOLERANCE:
                collisions.append((name, other, volume))
    assert not collisions, collisions
    v = lambda name: value(doc, name)
    # 連結穴・固定穴の中心と、部品間に設けた隙間を検査する。
    assert abs(v("JoinSpacing") - (v("ColumnPitch") - 2*v("PostX"))) < 1e-8
    assert v("ModuleHeight") - v("BaseHeight") - v("AdapterHeight") > 10
    assert v("FanPlateBottom") >= 0
    assert v("FanSize") == 120 and v("FanHolePitch") == 105
    assert v("FanMountLow") > v("StackEngagement") + v("BoltHole")/2 + 0.5
    for fan_z in (v("FanMountLow"), v("FanMountHigh")):
        for accessory_z in (v("ModuleHeight")/2-v("AccessoryPitch")/2,
                            v("ModuleHeight")/2+v("AccessoryPitch")/2):
            assert abs(fan_z-accessory_z) > v("BoltHole"), "直交する固定ボルトが干渉します"
    clearances = []
    removal = []
    for col in range(columns):
        for row in range(rows):
            x, z = col*v("ColumnPitch"), row*v("ModuleHeight")
            for end, start_x in (("AC", x-v("AdapterLength")/2-v("CableAllowance")),
                                 ("USB-C", x+v("AdapterLength")/2)):
                zone = Part.makeBox(v("CableAllowance"), 20, 20,
                                    App.Vector(start_x, -10, z+v("BaseHeight")+v("AdapterHeight")/2-10))
                for name, shape in links:
                    volume = interference(zone, shape)
                    if volume > TOLERANCE:
                        clearances.append((col, row, end, name, volume))
            # ケーブルを外した電源を後方へ水平に引き出す経路。
            sweep = Part.makeBox(v("AdapterLength"), v("AdapterWidth")+150, v("AdapterHeight"),
                                 App.Vector(x-v("AdapterLength")/2, -v("AdapterWidth")/2, z+v("BaseHeight")))
            for name, shape in links:
                if name == f"Adapter{col}{row}":
                    continue
                volume = interference(sweep, shape)
                if volume > TOLERANCE:
                    removal.append((col, row, name, volume))
    assert not clearances, clearances
    assert not removal, removal
    # 上下位置決めピンに荷重を預けず、柱の上下面が接触する。
    contact_area = None
    if rows == 2:
        lower = dict(links)["SideL00"]
        upper = dict(links)["SideL01"]
        joint_z = v("ModuleHeight")
        lower_faces = [face for face in lower.Faces
                       if face.BoundBox.ZLength < 1e-6 and abs(face.CenterOfMass.z-joint_z) < 1e-6]
        upper_faces = [face for face in upper.Faces
                       if face.BoundBox.ZLength < 1e-6 and abs(face.CenterOfMass.z-joint_z) < 1e-6]
        contact_area = sum(a.common(b).Area for a in lower_faces for b in upper_faces)
        assert contact_area > 0, "上下の側枠に接触面がありません"
    whole = Part.makeCompound([shape for _, shape in links])
    box = whole.BoundBox
    return {
        "layout": [columns, rows], "assembly_solids": len(whole.Solids),
        "dimensions_mm": [box.XLength, box.YLength, box.ZLength],
        "fully_constrained_sketches": len(sketches),
        "interference_threshold_mm3": TOLERANCE,
        "collisions": collisions, "cable_clearance_collisions": clearances,
        "cable_allowance_mm": v("CableAllowance"), "rear_removal_collisions": removal,
        "stack_contact_area_mm2_per_side": contact_area,
        "part_volumes_mm3": {name: doc.getObject(name).Shape.Volume for name in PRINT_PARTS},
        "fan_count": columns,
    }


def validate(doc):
    report = {name: inspect(doc, *layout) for name, layout in LAYOUTS.items()}
    changes = {"AdapterWidth": "105 mm", "AdapterLength": "105 mm", "AdapterHeight": "38 mm"}
    originals = {name: doc.Parameters.getContents(CELLS[name]) for name in changes}
    try:
        for name, content in changes.items():
            doc.Parameters.set(CELLS[name], content)
        doc.recompute()
        report["alternate_adapter"] = inspect(doc, 2, 2)
    finally:
        for name, content in originals.items():
            doc.Parameters.set(CELLS[name], content)
        doc.recompute()
    restored = inspect(doc, 1, 2)
    for name, volume in restored["part_volumes_mm3"].items():
        assert abs(volume-report["two_vertical"]["part_volumes_mm3"][name]) < 1e-6
    original_clearance = doc.Parameters.getContents(CELLS["FitClearance"])
    report["clearance_variants"] = {}
    try:
        for clearance in ("0.2 mm", "0.4 mm"):
            doc.Parameters.set(CELLS["FitClearance"], clearance)
            doc.recompute()
            report["clearance_variants"][clearance] = inspect(doc, 2, 2)
    finally:
        doc.Parameters.set(CELLS["FitClearance"], original_clearance)
        doc.recompute()
    assert_equivalent(inspect(doc, 1, 2), report["two_vertical"])
    return report
