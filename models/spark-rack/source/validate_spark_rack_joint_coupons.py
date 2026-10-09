"""段差の受け面と、上からの組立経路を接合試験片で確認する。"""
import FreeCAD as App


def contact_area(a, b, height):
    def faces(shape):
        return [face for face in shape.Faces if abs(face.BoundBox.ZMin - height) < 1e-6
                and abs(face.BoundBox.ZMax - height) < 1e-6]
    return sum(left.common(right).Area for left in faces(a) for right in faces(b))


def verify(shapes, corner):
    for name, shape in shapes.items():
        if not shape.isValid() or not shape.isClosed() or len(shape.Solids) != 1:
            raise ValueError('試験片が閉じた単一部品になっていません: ' + name)
    receiver, lower, upper = [shape for _, shape in corner]
    pairs = [('柱と下ほぞ梁', receiver, lower), ('柱と上ほぞ梁', receiver, upper),
             ('隣接梁', lower, upper), ('二股と差し込み', shapes['beam_fork'], shapes['beam_drop_blade'])]
    for label, a, b in pairs:
        if a.common(b).Volume > 1e-5:
            raise ValueError('接合部に干渉があります: ' + label)
    areas = {'lower_shoulder_mm2': contact_area(receiver, lower, 0),
             'upper_shoulder_mm2': contact_area(receiver, upper, 0),
             'straight_bearing_mm2': contact_area(shapes['beam_fork'], shapes['beam_drop_blade'], 4.3)}
    if min(areas.values()) < 150:
        raise ValueError('荷重を受ける面を確認できません')
    samples = 0
    for name, moving, obstacles in [('下ほぞ梁を先に入れる', lower, [receiver]),
                                   ('上ほぞ梁を後から入れる', upper, [receiver, lower]),
                                   ('直線部を上から入れる', shapes['beam_drop_blade'], [shapes['beam_fork']])]:
        for dz in range(60, -1, -2):
            moved = moving.copy(); moved.translate(App.Vector(0, 0, dz))
            samples += 1
            if any(moved.common(fixed).Volume > 1e-5 for fixed in obstacles):
                raise ValueError('上からの組立経路が塞がっています: ' + name)
    reverse_blocked = 0
    for dz in range(60, -1, -2):
        moved = lower.copy(); moved.translate(App.Vector(0, 0, dz))
        if moved.common(upper).Volume > 1e-5:
            reverse_blocked += 1
    if not reverse_blocked:
        raise ValueError('梁の上下ほぞと組立順序の整合を確認できません')
    return {'status': 'passed', 'bearing_contact': areas, 'insertion_direction': '全試験片とも上から',
            'insertion_order': '柱へ下ほぞの梁、次に上ほぞの梁。上側の柱は最後に付ける構想。',
            'checked_insertion_samples': samples, 'tenon_bottom_clearances_mm': [2, 12],
            'reverse_order_blocked_samples': reverse_blocked,
            'hidden_lock_screw': '未設計。止める場合は内側か下面から1本。金具の長さと保持力は試作後に決める。',
            'scope': '接合試験片の形状・受け面・離散的な挿入経路。全体の組立順序と荷重、実物のガタや強度は未検証。'}
