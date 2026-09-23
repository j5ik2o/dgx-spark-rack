"""生成FCStdを正投影し、A3の三面図PDF・SVGを作る。形状は変更しない。"""
import argparse
import hashlib
import json
from pathlib import Path
import runpy


def project(cad_file, output):
    import FreeCAD as App
    import Part
    import TechDraw

    source = Path(__file__).with_name('freecad_fan_controller.py')
    manifest = json.loads(cad_file.with_name('manifest.json').read_text())
    source_key = 'models/fan-controller/source/freecad_fan_controller.py'
    if hashlib.sha256(source.read_bytes()).hexdigest() != manifest['sources_sha256'][source_key]:
        raise ValueError('CADと現在の寸法定義が異なります。先にCADを再生成してください。')
    model = runpy.run_path(str(source))
    ports = {key: list(model[key]) for key in ('USB_PORT', 'FAN_PORT', 'NTC_PORT')}
    allowance = model['OPENING_EXTRA']
    App.closeDocument(model['doc'].Name)
    output.mkdir(parents=True, exist_ok=False)
    doc = App.openDocument(str(cad_file))
    result = {'cad_file': str(cad_file), 'cad_sha256': hashlib.sha256(cad_file.read_bytes()).hexdigest(),
              'units': 'mm', 'projection': 'third-angle', 'curve_deflection_mm': 0.01,
              'ports': ports, 'opening_extra': allowance, 'parts': {}}
    try:
        for name in ('CaseBody', 'CaseLid'):
            shape = doc.getObject(name).Shape
            views = {}
            for view in ('top', 'front', 'right', 'left'):
                rotated = shape.copy()
                if view == 'front':
                    rotated.rotate(App.Vector(), App.Vector(1, 0, 0), -90)
                elif view in ('right', 'left'):
                    # 投影平面の横軸=±Y、縦軸=Z、視線方向=±X。
                    sign = 1 if view == 'right' else -1
                    matrix = App.Matrix()
                    matrix.A11, matrix.A12, matrix.A13 = 0, sign, 0
                    matrix.A21, matrix.A22, matrix.A23 = 0, 0, 1
                    matrix.A31, matrix.A32, matrix.A33 = sign, 0, 0
                    rotated = rotated.transformGeometry(matrix)
                groups = TechDraw.project(rotated, App.Vector(0, 0, 1))
                bounds = Part.makeCompound([g for g in groups if not g.isNull()]).optimalBoundingBox(False)
                lines = {'visible': [], 'hidden': []}
                for index, group in enumerate(groups):
                    for edge in group.Edges:
                        points = edge.discretize(Deflection=0.01)
                        lines['visible' if index < 2 else 'hidden'].append(
                            [[p.x - bounds.XMin, bounds.YMax - p.y] for p in points])
                views[view] = {'width': bounds.XLength, 'height': bounds.YLength, **lines}
            result['parts'][name] = views
    finally:
        App.closeDocument(doc.Name)
    (output / 'projection.json').write_text(json.dumps(result, ensure_ascii=False))


def render(output):
    from html import escape
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.units import mm

    data = json.loads((output / 'projection.json').read_text())
    pdfmetrics.registerFont(TTFont('DrawingJP', '/System/Library/Fonts/Supplemental/Arial Unicode.ttf'))
    pdf = canvas.Canvas(str(output / 'fan-controller-three-views.pdf'), pagesize=(420 * mm, 297 * mm))
    pdf.setTitle('ファンコンケース 三面図・端子面詳細')
    pdf.setAuthor('IDEO PLUS LLC')
    svg = []

    def text(x, y, value, size=3.2, color='#172b42'):
        pdf.setFillColor(color)
        pdf.setFont('DrawingJP', size * mm)
        pdf.drawString(x * mm, (297 - y) * mm, value)
        svg.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}">{escape(value)}</text>')

    def line(x1, y1, x2, y2, color='#243549', width=0.18, dashed=False):
        pdf.setStrokeColor(color)
        pdf.setLineWidth(width * mm)
        pdf.setDash([1.5 * mm, 1 * mm] if dashed else [])
        pdf.line(x1 * mm, (297-y1) * mm, x2 * mm, (297-y2) * mm)
        dash = ' stroke-dasharray="1.5 1"' if dashed else ''
        svg.append(f'<path d="M{x1},{y1} L{x2},{y2}" fill="none" stroke="{color}" stroke-width="{width}"{dash}/>')

    def view(part, direction, x, y, scale):
        v = data['parts'][part][direction]
        for kind in ('hidden', 'visible'):
            hidden = kind == 'hidden'
            for points in v[kind]:
                if len(points) < 2:
                    continue
                path = pdf.beginPath()
                path.moveTo((x+scale*points[0][0])*mm, (297-y-scale*points[0][1])*mm)
                for a,b in points[1:]:
                    path.lineTo((x+scale*a)*mm, (297-y-scale*b)*mm)
                color, width = ('#a6adb5', 0.12) if hidden else ('#172b42', 0.22)
                pdf.setStrokeColor(color)
                pdf.setLineWidth(width * mm)
                pdf.setDash([1.3*mm, 0.9*mm] if hidden else [])
                pdf.drawPath(path)
                coords = ' '.join(f'{x+scale*a:.4f},{y+scale*b:.4f}' for a,b in points)
                dash = ' stroke-dasharray="1.3 0.9"' if hidden else ''
                svg.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="{width}"{dash}/>')
        return v['width'] * scale, v['height'] * scale

    def horizontal(x, y, width, value):
        line(x,y-5,x,y+2); line(x+width,y-5,x+width,y+2); line(x,y,x+width,y)
        for xx, sign in ((x,1),(x+width,-1)):
            line(xx,y,xx+sign*2,y-0.8); line(xx,y,xx+sign*2,y+0.8)
        text(x+width/2-6,y-2,f'{value:.2f}')

    def vertical(x, y, height, value):
        line(x-2,y,x+5,y); line(x-2,y+height,x+5,y+height); line(x,y,x,y+height)
        for yy, sign in ((y,1),(y+height,-1)):
            line(x,yy,x-0.8,yy+sign*2); line(x,yy,x+0.8,yy+sign*2)
        text(x-13,y+height/2,f'{value:.2f}')

    def start(title, page, scale):
        svg.clear()
        text(15,18,title,6)
        text(15,26,'第三角法 / 単位 mm / 実線：見える稜線　破線：隠れた稜線',3.2)
        text(320,20,f'A3横 / 縮尺 {scale}:1 / {page} / 3',3.2)
        line(15,31,405,31)

    def finish(name):
        line(15,265,405,265)
        text(15,273,'USB-C位置は実測反映済み。端子台の逃げ・ファン／温度センサー開口は要修正。',3.1,'#b34426')
        text(15,280,'現在の設計確認用。実物適合の確認前に、この図面だけで本番製作しないでください。',3.1)
        text(15,287,'CAD: '+Path(data['cad_file']).parent.name+' / 曲線近似偏差 0.01mm',2.7)
        text(330,287,'Copyright 2026 IDEO PLUS LLC',2.6)
        (output / (name+'.svg')).write_text('<svg xmlns="http://www.w3.org/2000/svg" width="420mm" height="297mm" viewBox="0 0 420 297"><rect width="420" height="297" fill="white"/><g font-family="sans-serif">'+''.join(svg)+'</g></svg>')
        pdf.showPage()

    for page,(part,label) in enumerate((('CaseBody','ケース本体'),('CaseLid','蓋')),1):
        start(label+' — CAD三面図',page,2)
        text(40,41,'上面図（+Zから）')
        w,h = view(part,'top',40,47,2)
        horizontal(40,47+h+10,w,w/2)
        vertical(28,47,h,h/2)
        text(40,164,'正面図（長辺側・−Yから）')
        w,h = view(part,'front',40,171,2)
        horizontal(40,171+h+10,w,w/2)
        vertical(28,171,h,h/2)
        text(265,164,'右側面図（ファン端子側・+Xから）')
        w,h = view(part,'right',265,171,2)
        horizontal(265,171+h+10,w,w/2)
        text(260,52,'向きの対応',3.5)
        text(260,61,'左短辺：端子台・USB-C')
        text(260,69,'右短辺：ファン・温度センサー端子')
        text(260,77,'上面：表示器とつまみの側')
        text(260,93,'寸法値はCADの外形から取得。')
        if part == 'CaseLid':
            text(260,103,'蓋は組立時の姿勢で表示。')
            text(260,111,'基板押さえは本体側の別部品4個。')
        finish(part+'-three-views')

    start('ケース本体 — 両端の開口確認',3,4)
    text(38,49,'左側面：端子台・USB-C（−Xから）',4)
    text(235,49,'右側面：ファン・温度センサー（+Xから）',4)
    view('CaseBody','left',38,60,4)
    view('CaseBody','right',235,60,4)
    text(38,180,'USB-C開口の設計値（余裕を含む）',4)
    _, cy, cz, width, height = data['ports']['USB_PORT']
    width += data['opening_extra']
    height += data['opening_extra']
    for i, row in enumerate((f'幅 {width:.2f} × 高さ {height:.2f} mm',
                              f'基板の近い長辺から中心：{cy:.3f} mm',
                              f'基板下面から中心：{cz:.3f} mm',
                              f'基板下面から開口下端 {cz-height/2:.2f} / 上端 {cz+height/2:.2f} mm')):
        text(38,190+i*9,row)
    text(235,180,'未確定の開口（現状を表示）',4)
    for y, key, label in ((191,'FAN_PORT','ファン'),(200,'NTC_PORT','温度センサー')):
        port = data['ports'][key]
        text(235,y,f'{label}：幅 {port[3]+data["opening_extra"]:.2f} × 高さ {port[4]+data["opening_extra"]:.2f} mm')
    text(235,213,'位置・幅は仮値。プラグ外形の採寸が必要。',3.2,'#b34426')
    finish('connector-faces')
    pdf.save()
    write = {'status':'passed','source':data['cad_file'],'source_sha256':data['cad_sha256'],
             'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             'projection':'third-angle','units':'mm','pages':3,
             'outputs_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.suffix in ('.svg','.pdf','.json') and p.name != 'manifest.json'}}
    (output/'manifest.json').write_text(json.dumps(write,ensure_ascii=False,indent=2)+'\n')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=('project','render'))
    parser.add_argument('output',type=Path)
    parser.add_argument('--cad',type=Path)
    args=parser.parse_args()
    if args.mode=='project':
        if not args.cad: parser.error('--cad is required')
        project(args.cad.resolve(),args.output.resolve())
    else:
        render(args.output.resolve())
