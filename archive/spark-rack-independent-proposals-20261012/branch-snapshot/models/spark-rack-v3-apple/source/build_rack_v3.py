# -*- coding: utf-8 -*-
"""案Dを生成: FCStd(完成形/リング) + STEP + 2D図 + 3D HTML + 検査 + manifest。
実行: freecadcmd -c "exec(open('<this>').read())"  または  python(FreeCAD同梱) でFREECAD_LIBを通す。
出力: build/spark-rack-v3-apple/<実行ID>/
"""
import os, sys, json, hashlib, datetime, platform
HERE = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.environ['RACK_V3_SRC']
sys.path.insert(0, HERE)
import FreeCAD as App, Part
import importlib, rack_v3_parameters, rack_v3_layout, rack_v3_checks, draw_rack_v3
for m in (rack_v3_parameters, rack_v3_layout, rack_v3_checks, draw_rack_v3):
    importlib.reload(m)
from rack_v3_parameters import *
L, C, Dr = rack_v3_layout, rack_v3_checks, draw_rack_v3

ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
RUN = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
OUT = os.path.join(ROOT, 'build', 'spark-rack-v3-apple', RUN)
os.makedirs(OUT, exist_ok=True)

RGB = dict(frame=(0.33, 0.36, 0.39), plate=(0.6, 0.64, 0.68), printed=(0.15, 0.15, 0.15), device=(0.79, 0.64, 0.15),
           fan=(0.78, 0.69, 0.54), psu=(0.24, 0.48, 0.72), ctrl=(0.48, 0.31, 0.70), shell=(0.43, 0.43, 0.45))

def solid(p):
    x, y, z, dx, dy, dz = p['box']
    s = Part.makeBox(dx, dy, dz, App.Vector(x, y, z))
    if p['kind'] == 'fan':   # 羽根部の円形開口を表現
        r = (min(dx, dy, dz) if False else sorted((dx, dy, dz))[1]) / 2 - 4
        if dx < dy:
            c = Part.makeCylinder(r, dx+2, App.Vector(x-1, y+dy/2, z+dz/2), App.Vector(1, 0, 0))
        else:
            c = Part.makeCylinder(r, dy+2, App.Vector(x+dx/2, y-1, z+dz/2), App.Vector(0, 1, 0))
        s = s.cut(c)
    if '導風ダクト' in p['name']:   # 140角→Spark前面(150×46)へ絞るロフト殻
        def rect(y0, cx, cz, w, h):
            return Part.makePolygon([App.Vector(cx-w/2, y0, cz-h/2), App.Vector(cx+w/2, y0, cz-h/2),
                                     App.Vector(cx+w/2, y0, cz+h/2), App.Vector(cx-w/2, y0, cz+h/2), App.Vector(cx-w/2, y0, cz-h/2)])
        cx, cz = x+dx/2, z+dz/2
        outer = Part.makeLoft([rect(y, cx, cz, 142, 142), rect(y+dy, cx, cz, 150, 52)], True)
        inner = Part.makeLoft([rect(y-1, cx, cz, 136, 136), rect(y+dy+1, cx, cz, 144, 44)], True)
        s = outer.cut(inner)
    if 'アダプタートンネル' in p['name']:
        w = TUNNEL['wall']
        s = s.cut(Part.makeBox(dx+2, dy+2, dz-2*w, App.Vector(x-1, y-1, z+w)))   # 前後に開口(前=格子は省略)
    if p['name'] == '外装シェル_天面':   # 大R U字外装を一体で生成(左右部品は表示用に空形状)
        R, t = SHELL_R, SHELL_T
        def rounded(x0, x1, z1, r):
            bx = Part.makeBox(x1-x0, dy, z1-10, App.Vector(x0, y, 10))
            ed = [e for e in bx.Edges if e.BoundBox.YLength > dy-1e-6 and abs(e.BoundBox.ZMin-z1) < 1e-6]
            return bx.makeFillet(r, ed)
        outer = rounded(OUT_X0, OUT_X1, H, R)
        inner = Part.makeBox(OUT_X1-OUT_X0-2*t, dy+2, H-t-10+1, App.Vector(OUT_X0+t, y-1, 9))
        ed = [e for e in inner.Edges if e.BoundBox.YLength > dy and abs(e.BoundBox.ZMin-(H-t)) < 1e-6]
        inner = inner.makeFillet(R-t, ed)
        s = outer.cut(inner)
    if p['name'] in ('外装シェル_左', '外装シェル_右'):
        s = Part.Shape()
    return s

def build_doc(P, name):
    doc = App.newDocument(name)
    for i, p in enumerate(P):
        if p['kind'] == 'zone':
            continue
        if p['name'] in ('外装シェル_左', '外装シェル_右'):
            continue   # 天面オブジェクトのU字一体形状に含める
        o = doc.addObject('Part::Feature', f'P{i:03d}')
        o.Label = p['name']; o.Shape = solid(p)
        for k, v in (('Kind', p['kind']), ('Note', p['note']), ('Material', p['material'])):
            o.addProperty('App::PropertyString', k, 'RackV2'); setattr(o, k, v)
        o.addProperty('App::PropertyFloat', 'MassKg', 'RackV2'); o.MassKg = p['mass']
        try:
            o.ViewObject.ShapeColor = RGB[p['kind']]
        except Exception:
            pass
    zg = doc.addObject('App::DocumentObjectGroup', 'Zones'); zg.Label = '確保範囲(作業空間・吸排気・曲げ)'
    for i, p in enumerate(P):
        if p['kind'] != 'zone':
            continue
        x, y, z, dx, dy, dz = p['box']
        o = doc.addObject('Part::Feature', f'Z{i:03d}'); o.Label = 'ZONE_' + p['name']
        o.Shape = Part.makeBox(dx, dy, dz, App.Vector(x, y, z)); zg.addObject(o)
    doc.recompute()
    path = os.path.join(OUT, f'{name}.FCStd'); doc.saveAs(path)
    return doc, path

P_sw, P_ring = L.parts('switch'), L.parts('ring')
doc_sw, f_sw = build_doc(P_sw, 'rack_v3_D_switch')
doc_ring, f_ring = build_doc(P_ring, 'rack_v3_D_ring')
solids = [o for o in doc_sw.Objects if o.Name.startswith('P')]
step = os.path.join(OUT, 'rack_v3_D_switch.step')
Part.export(solids, step)

# --- FreeCAD実形状での検査(直方体検査の補完): 主要実体同士の共通体積 ---
brep = []
sol = [(o.Label, o.Shape) for o in solids]
for i in range(len(sol)):
    for j in range(i+1, len(sol)):
        a, b = sol[i], sol[j]
        if not a[1].BoundBox.intersect(b[1].BoundBox):
            continue
        if ('アダプタートンネル' in a[0] and b[0].startswith(('電源アダプター', '120ファン'))) or \
           ('アダプタートンネル' in b[0] and a[0].startswith(('電源アダプター', '120ファン'))):
            pass  # 中空化後なので実形状で検査する
        if 'U字' in a[0] or 'U字' in b[0]:
            pass
        v = a[1].common(b[1]).Volume
        if v > 1.0 and not ({a[0], b[0]} & {'外装シェル_天面'} and v < 0):
            brep.append(dict(a=a[0], b=b[0], volume_mm3=round(v, 1)))
# 再読込
App.closeDocument(doc_sw.Name)
d2 = App.openDocument(f_sw); reload_ok = len([o for o in d2.Objects if o.Name.startswith('P')]) == len(solids)
App.closeDocument(d2.Name); App.closeDocument(doc_ring.Name)

checks = C.run(P_sw, P_ring)
checks['brep_interference_switch'] = brep
checks['reload_ok'] = reload_ok
checks['scope'] = ('CAD上の直方体近似と実形状(ロフト・中空)の干渉、印刷寸法、取り出し経路、配線長の目安、質量・重心・転倒角の概算。'
                   '材料強度・たわみ・クリープ・振動・冷却性能・実物の適合は検査していない。')
summary = dict(
    interference_box_switch=len(checks['switch']['interference']), interference_box_ring=len(checks['ring']['interference']),
    interference_brep_switch=len(brep), print_parts_all_fit=all(p['fits_246'] for p in checks['print_fit']),
    sweeps_all_clear=all(s['clear'] for s in checks['sweeps']), ring_all_ok=all(r['ok'] for r in checks['ring_cables']),
    reload_ok=reload_ok)
checks['summary'] = summary
summary['passed'] = all(v for k, v in summary.items() if k.endswith(('fit', 'clear', 'ok'))) and \
    summary['interference_box_switch'] == 0 and summary['interference_box_ring'] == 0 and summary['interference_brep_switch'] == 0
json.dump(checks, open(os.path.join(OUT, 'validation.json'), 'w'), ensure_ascii=False, indent=1)
json.dump(dict(switch=P_sw, ring=P_ring), open(os.path.join(OUT, 'parts.json'), 'w'), ensure_ascii=False, indent=1)

# --- 図 ---
imgs = {}
for v, t in (('front', '案D 正面図(スイッチ運用・完成形)'), ('side', '案D 右側面図'), ('rear', '案D 背面図'), ('top', '案D 上面図')):
    imgs[v] = os.path.join(OUT, f'view_{v}.png'); Dr.draw_view(P_sw, v, t, imgs[v])
    Dr.draw_view(P_sw, v, t, os.path.join(OUT, f'view_{v}.svg'))
imgs['iso'] = os.path.join(OUT, 'view_overall_iso.png'); Dr.draw_iso(P_sw, imgs['iso'], '案D 全体図(等角, 確保範囲は非表示)')
Dr.draw_iso(P_ring, os.path.join(OUT, 'view_overall_iso_ring.png'), '案D リング運用時(スイッチ未設置)')
imgs['wiring'] = os.path.join(OUT, 'wiring_ring_vs_switch.png'); Dr.draw_wiring(P_sw, imgs['wiring'])
imgs['render'] = os.path.join(OUT, 'render_overall.png'); Dr.draw_render(P_sw, imgs['render'], '案D Apple風 全体(スペースグレイ・前面ラティス)', True)
Dr.draw_render(P_sw, os.path.join(OUT, 'render_overall_gold.png'), '案D 全体(シャンパンゴールド案)', True, color='#c9b27c')
imgs['render_open'] = os.path.join(OUT, 'render_panel_removed.png'); Dr.draw_render(P_sw, imgs['render_open'], '案D 前面パネルを外した状態', False)

# --- 3D HTMLビューア ---
html = open(os.path.join(HERE, 'viewer_template.html'), encoding='utf-8').read()
html = html.replace('__PARTS__', json.dumps(dict(switch=P_sw, ring=P_ring), ensure_ascii=False))
open(os.path.join(OUT, 'rack_v3_viewer.html'), 'w', encoding='utf-8').write(html)

# --- manifest ---
def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
inputs = sorted(os.path.join(HERE, f) for f in os.listdir(HERE) if f.endswith(('.py', '.html', '.FCMacro')))
outputs = sorted(os.path.join(OUT, f) for f in os.listdir(OUT) if f != 'manifest.json')
man = dict(run_id=RUN, model='spark-rack-v3-apple (案D)', status='success' if summary['passed'] else 'checks_failed',
           freecad_version=App.Version()[:4], python=platform.python_version(),
           inputs={os.path.relpath(p, ROOT): sha(p) for p in inputs},
           outputs={os.path.relpath(p, ROOT): sha(p) for p in outputs}, summary=summary,
           note='造形用STL/3MFは出力しない(実測前の比較用モデル)。')
json.dump(man, open(os.path.join(OUT, 'manifest.json'), 'w'), ensure_ascii=False, indent=1)
print('RACK_V3_OUT', OUT, json.dumps(summary, ensure_ascii=False))
