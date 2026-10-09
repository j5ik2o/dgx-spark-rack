"""収容範囲と配線中心線をFreeCADへ出力する。印刷形状を含まない。"""
import FreeCAD as App
import FreeCADGui as Gui
import Part


def create(report, mode):
    doc = App.newDocument('FourNodeLayout')
    doc.Label = '4台専用ラック・仮配置・' + ('リング' if mode == 'ring' else report['switch_spec']['label'])
    entities = [*report['nodes'].values(), *report['shelves'], *report['fans'],
                *report['fan_holders'], *report['fan_guards'], *report['controllers'], report['envelope']]
    if mode != 'ring':
        entities.append(report['switch'])
    else:
        entities = [e for e in entities if e['name'] != 'switch_shelf']
    colors = {'spark': (0.78, 0.62, 0.26), 'switch': (0.55, 0.60, 0.69),
              'shelf': (0.30, 0.55, 0.70), 'envelope': (0.6, 0.6, 0.6),
              'fan': (0.83, 0.73, 0.53), 'fan_holder': (0.30, 0.39, 0.45),
              'guard': (0.6, 0.6, 0.6), 'controller': (0.31, 0.39, 0.45)}
    for e in entities:
        obj = doc.addObject('Part::Feature', e['name'])
        obj.Label = e['label']
        obj.Shape = Part.makeBox(*e['size'], App.Vector(*e['origin']))
        if e['kind'] in ('fan', 'fan_holder', 'guard'):
            x, y, z = e['origin']
            dx, dy, dz = e['size']
            radius = (e.get('size_mm', dx) - 12) / 2
            opening = Part.makeCylinder(radius, dy + 2, App.Vector(x + dx / 2, y - 1, z + dz / 2), App.Vector(0, 1, 0))
            obj.Shape = obj.Shape.cut(opening)
            if 'mounting_pitch_mm' in e:
                pitch = e['mounting_pitch_mm']
                for sx in (-1, 1):
                    for sz in (-1, 1):
                        hole = Part.makeCylinder(2.25, dy + 2, App.Vector(x + dx / 2 + sx * pitch / 2,
                                               y - 1, z + dz / 2 + sz * pitch / 2), App.Vector(0, 1, 0))
                        obj.Shape = obj.Shape.cut(hole)
        obj.ViewObject.ShapeColor = colors[e['kind']]
        obj.ViewObject.Transparency = 80 if e['kind'] == 'shelf' else 0
        if e['kind'] in ('guard', 'controller'):
            obj.ViewObject.Transparency = 55
        if e['kind'] == 'envelope':
            obj.ViewObject.DisplayMode = 'Wireframe'
        obj.addProperty('App::PropertyString', 'ValidationNote')
        obj.ValidationNote = report['physical_validation']
    cables = report['ring_cables'] if mode == 'ring' else report['switch_cables']
    for i, cable in enumerate(cables):
        if not cable['points']:
            continue
        # 表示中心線は細分化した折線。検査長は解析式の四分円弧長を使う。
        obj = doc.addObject('Part::Feature', 'Cable' + str(i + 1))
        obj.Label = cable['label']
        obj.Shape = Part.makePolygon([App.Vector(*point) for point in cable['points']])
        obj.ViewObject.LineColor = (0.12, 0.55, 0.38)
        obj.ViewObject.LineWidth = 3
        obj.addProperty('App::PropertyLength', 'AssumedRequiredLength')
        obj.AssumedRequiredLength = cable['required_length_mm']
        obj.addProperty('App::PropertyString', 'ValidationNote')
        obj.ValidationNote = '仮定条件での配線検討。実ケーブルの到達は未検証。'
    doc.recompute()
    return doc


def export(report, mode, folder):
    doc = create(report, mode)
    path = folder / ('four-node-layout-' + mode)
    objects = [o for o in doc.Objects if hasattr(o, 'Shape')]
    for obj in objects:
        if obj.Shape.isNull() or not obj.Shape.isValid():
            raise ValueError('無効な参照形状: ' + obj.Label)
    doc.saveAs(str(path.with_suffix('.FCStd')))
    Part.export(objects, str(path.with_suffix('.step')))
    expected = {o.Name: (o.Shape.Volume, o.Shape.Length) for o in objects}
    App.closeDocument(doc.Name)
    reopened = App.openDocument(str(path.with_suffix('.FCStd')))
    for name, (volume, length) in expected.items():
        shape = reopened.getObject(name).Shape
        if not shape.isValid() or abs(shape.Volume - volume) > 1e-6 or abs(shape.Length - length) > 1e-6:
            raise ValueError('保存後の形状が不一致: ' + name)
    App.closeDocument(reopened.Name)
    return {'status': 'passed', 'reference_object_count': len(expected), 'reopened': True,
            'scope': '参照形状の妥当性と保存後の一致。印刷・強度・配線到達を保証しない。'}


if __name__ == '__main__':
    import json
    import os
    from pathlib import Path
    import sys
    import traceback
    try:
        Gui.showMainWindow()
        folder = Path(sys.argv[1])
        reports = json.loads((folder / 'layout-report.json').read_text())
        results = {}
        for key, report in reports.items():
            results[key] = export(report, key, folder)
        (folder / 'cad-validation.json').write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n')
    except Exception:
        traceback.print_exc()
        sys.stderr.flush()
        os._exit(1)
    sys.stdout.flush()
    os._exit(0)
