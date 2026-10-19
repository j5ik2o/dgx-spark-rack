"""ねじ不要の保持部。木造の段差・ほぞと、樹脂の差し込み栓を使う設計候補。"""
import FreeCAD as App
import Part


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
    from body_frame_geometry import block, item
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


def integrate_small_parts(parts, p, protected):
    """同じ部品として造形できる接触部を一体化し、不要な接合と栓を減らす。"""
    from validate_body_frame import near, shared_area
    result = [dict(e, integrated_members=e.get('integrated_members', [e['name']])) for e in parts]
    changed = True
    while changed:
        changed = False
        for i, first in enumerate(result):
            if first['name'] in protected:
                continue
            for j in range(i+1, len(result)):
                second = result[j]
                if second['name'] in protected or not near(first['shape'], second['shape']):
                    continue
                b = first['shape'].BoundBox.united(second['shape'].BoundBox)
                if max(b.XLength, b.YLength, b.ZLength) > p.usable_print_size:
                    continue
                if shared_area(first['shape'], second['shape']) < 2:
                    continue
                fused = first['shape'].fuse(second['shape']).removeSplitter()
                if len(fused.Solids) != 1 or not fused.isValid():
                    continue
                # 本体を直接受ける接続部の種別を保つ。
                root, other = (second, first) if second['kind'] == 'body_connector' else (first, second)
                merged = dict(root, shape=fused, integrated_members=first['integrated_members']+second['integrated_members'])
                result[i] = merged
                result.pop(j)
                changed = True
                break
            if changed:
                break
    return result


def lap_storage_floors(parts):
    """薄い受け同士の端面だけでつながず、下へ重ねて段差で受ける。"""
    from body_frame_geometry import block
    by_name = {e['name']: e for e in parts}
    for col in range(2):
        floor = by_name[f'signal_storage_floor_{col}']
        tray = by_name[f'power_tray_{col}_1']
        b = floor['shape'].BoundBox
        nose = block([b.XMin, b.YMin-14, b.ZMin], [b.XLength, 14, b.ZLength])
        tray['shape'] = tray['shape'].cut(nose).removeSplitter()
        floor['shape'] = floor['shape'].fuse(nose).removeSplitter()
