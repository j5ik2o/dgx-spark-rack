"""接触部を造形範囲内で一体化する共通処理。"""


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
