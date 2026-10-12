# -*- coding: utf-8 -*-
"""案D 印刷部品のSTL・プレート別3MF・板金外注用STEP/DXFを生成し検査する(試作=prototype)。
出力: build/spark-rack-v3-apple/print-<実行ID>/ と print-projects/spark-rack-v3-apple/prototype/generated/<実行ID>/
本番(production)条件は未設定のため生成しない。"""
import os, sys, json, hashlib, datetime, zipfile, platform, math
HERE = os.environ.get('RACK_V3_SRC') or os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import importlib
import FreeCAD as App, Part, Mesh, MeshPart
import rack_v3_parameters, rack_v3_layout, printed_parts_v3, printed_tiles_v3
for m in (rack_v3_parameters, rack_v3_layout, printed_parts_v3, printed_tiles_v3): importlib.reload(m)
from rack_v3_parameters import *
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib import font_manager
for f in font_manager.findSystemFonts():
    if 'NotoSansCJK' in f or 'NotoSerifCJK-Regular' in f: font_manager.fontManager.addfont(f)
plt.rcParams['font.family'] = ['Noto Sans CJK JP', 'Noto Serif CJK JP', 'DejaVu Sans']

ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
RUN = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
OUT = os.path.join(ROOT, 'build', 'spark-rack-v3-apple', f'print-{RUN}')
PP = os.path.join(ROOT, 'print-projects', 'spark-rack-v3-apple', 'prototype', 'generated', RUN)
for d in ('stl', 'stl-options-tiles', 'sheetmetal', 'preview'): os.makedirs(os.path.join(OUT, d), exist_ok=True)
os.makedirs(PP, exist_ok=True)

DENS = 1.20   # PAHT-CF g/cm3 (Bambu公表値付近, 要確認)
LIMIT = PRINT_LIMIT

def est(shape):
    vol = shape.Volume/1000.0; area = shape.Area/100.0
    shell_frac = min(1.0, area*0.17/vol) if vol > 0 else 1   # 外周4壁+上下5層 ≈ 1.7mm
    f = shell_frac + (1-shell_frac)*0.40                    # インフィル40%
    g = vol*DENS*f
    return round(g, 1), round(g/14.0+0.25, 1)               # 時間: 約14g/h (0.4mm硬化ノズル, PAHT-CF標準速度の仮定)

def export(shape, path):
    shape = shape.copy(); bb = shape.BoundBox
    shape.translate(App.Vector(-bb.XMin, -bb.YMin, -bb.ZMin))
    m = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.05, AngularDeflection=0.35, Relative=False)
    m.write(path)
    mm = Mesh.Mesh(path)
    b = mm.BoundBox
    chk = dict(points=mm.CountPoints, facets=mm.CountFacets, is_solid=mm.isSolid(), non_manifold=mm.hasNonManifolds(),
               components=mm.countComponents(), mesh_volume_cm3=round(mm.Volume/1000, 2), cad_volume_cm3=round(shape.Volume/1000, 2),
               bbox_mm=[round(b.XLength, 2), round(b.YLength, 2), round(b.ZLength, 2)],
               cad_bbox_mm=[round(shape.BoundBox.XLength, 2), round(shape.BoundBox.YLength, 2), round(shape.BoundBox.ZLength, 2)])
    chk['bbox_match'] = all(abs(a-c) < 0.1 for a, c in zip(chk['bbox_mm'], chk['cad_bbox_mm']))
    chk['volume_match'] = abs(chk['mesh_volume_cm3']-chk['cad_volume_cm3']) <= max(0.02, 0.01*chk['cad_volume_cm3'])
    chk['fits_246'] = max(chk['bbox_mm'][:2]) <= LIMIT and chk['bbox_mm'][2] <= LIMIT
    chk['watertight'] = chk['is_solid'] and not chk['non_manifold'] and chk['components'] == 1
    chk['passed'] = chk['watertight'] and chk['bbox_match'] and chk['volume_match'] and chk['fits_246']
    return mm, chk

results, meshes = [], {}
for name, fn, qty, orient, support, critical in printed_parts_v3.PARTS:
    s = fn()
    assert s.isValid(), name
    p = os.path.join(OUT, 'stl', f'{name}.stl'); mm, chk = export(s, p)
    g, h = est(s)
    results.append(dict(name=name, qty=qty, orientation=orient, support=support, fit_test_first=critical,
                        est_weight_g=g, est_time_h=h, file=os.path.relpath(p, ROOT), check=chk))
    meshes[name] = (mm, qty)
tiles = []
for name, fn, qty, orient in printed_tiles_v3.tiles():
    s = fn(); assert s.isValid(), name
    p = os.path.join(OUT, 'stl-options-tiles', f'{name}.stl'); mm, chk = export(s, p)
    g, h = est(s)
    tiles.append(dict(name=name, qty=qty, orientation=orient, est_weight_g=g, est_time_h=h, file=os.path.relpath(p, ROOT), check=chk))

# ---- プレート詰め(棚詰め, 246角, 間隔6mm) ----
def pack(items, limit=LIMIT, gap=6.0):
    inst = []
    for nm, (mm, q) in items.items():
        b = mm.BoundBox
        for i in range(q): inst.append((nm, i+1, b.XLength, b.YLength))
    inst.sort(key=lambda t: -t[3])
    plates = []
    for nm, i, w, d in inst:
        placed = False
        for pl in plates:
            for sh in pl['shelves']:
                if sh['x']+w <= limit and d <= sh['h']:
                    pl['items'].append((nm, i, sh['x'], sh['y'], w, d)); sh['x'] += w+gap; placed = True; break
            if placed: break
            if pl['top']+d <= limit:
                pl['shelves'].append(dict(y=pl['top'], h=d, x=w+gap)); pl['items'].append((nm, i, 0, pl['top'], w, d)); pl['top'] += d+gap; placed = True; break
        if not placed:
            plates.append(dict(shelves=[dict(y=0, h=d, x=w+gap)], items=[(nm, i, 0, 0, w, d)], top=d+gap))
    return plates

def write_3mf(path, plate, meshes, off=5.0):
    """汎用3MF(Bambu Studioで読込可)。単位mm。プレート256角の中央寄せ。"""
    vs, objs, build = [], [], []
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<model unit="millimeter" xml:lang="ja-JP" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">',
           '<metadata name="Title">spark-rack-v3-apple prototype (PAHT-CF)</metadata><resources>']
    for k, (nm, i, x, y, w, d) in enumerate(plate['items']):
        mm = meshes[nm][0]
        pts = mm.Topology[0]; fac = mm.Topology[1]
        xml.append(f'<object id="{k+1}" name="{nm}_{i}" type="model"><mesh><vertices>')
        xml.append(''.join(f'<vertex x="{p.x:.4f}" y="{p.y:.4f}" z="{p.z:.4f}"/>' for p in pts))
        xml.append('</vertices><triangles>')
        xml.append(''.join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in fac))
        xml.append('</triangles></mesh></object>')
        build.append(f'<item objectid="{k+1}" transform="1 0 0 0 1 0 0 0 1 {x+off:.3f} {y+off:.3f} 0"/>')
    xml.append('</resources><build>' + ''.join(build) + '</build></model>')
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
        z.writestr('_rels/.rels', '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
        z.writestr('3D/3dmodel.model', '\n'.join(xml))

def preview(path, plate, meshes, title):
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.add_patch(plt.Rectangle((0, 0), 256, 256, fill=False, ec='k', lw=1.5))
    ax.add_patch(plt.Rectangle((5, 5), LIMIT, LIMIT, fill=False, ec='r', ls='--', lw=0.8))
    for nm, i, x, y, w, d in plate['items']:
        mm = meshes[nm][0]
        pts = mm.Topology[0]; tris = mm.Topology[1]
        step = max(1, len(tris)//6000)
        polys = [[(pts[a].x+x+5, pts[a].y+y+5), (pts[b].x+x+5, pts[b].y+y+5), (pts[c].x+x+5, pts[c].y+y+5)] for a, b, c in tris[::step]]
        ax.add_collection(PolyCollection(polys, facecolor='#3a3a3c', edgecolor='none', alpha=0.6))
        ax.text(x+5+w/2, y+5+d/2, f'{nm}\n#{i}', ha='center', va='center', fontsize=6, color='#ff9f0a')
    ax.set_xlim(-5, 261); ax.set_ylim(-5, 261); ax.set_aspect('equal'); ax.set_title(title, fontsize=9)
    ax.text(0, -4, '黒枠=X1Cプレート256mm, 赤破線=246mm目安', fontsize=7, va='top')
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)

plates = pack(meshes)
plate_info = []
for k, pl in enumerate(plates):
    f3 = os.path.join(PP, f'spark-rack-v3-apple-pahtcf-plate{k+1:02d}.3mf'); write_3mf(f3, pl, meshes)
    pv = os.path.join(OUT, 'preview', f'plate{k+1:02d}.png'); preview(pv, pl, meshes, f'プレート{k+1}: ' + ', '.join(sorted({i[0] for i in pl['items']})))
    plate_info.append(dict(plate=k+1, file_3mf=os.path.relpath(f3, ROOT), preview=os.path.relpath(pv, ROOT),
                           items=[f'{i[0]}#{i[1]}' for i in pl['items']],
                           within_246=all(i[2]+i[4] <= LIMIT+1e-6 and i[3]+i[5] <= LIMIT+1e-6 for i in pl['items'])))
# 3MFの再読込検査(ZIP構造とオブジェクト数)
for pi, pl in zip(plate_info, plates):
    with zipfile.ZipFile(os.path.join(ROOT, pi['file_3mf'])) as z:
        txt = z.read('3D/3dmodel.model').decode()
    pi['reopen_objects'] = txt.count('<object '); pi['reopen_ok'] = pi['reopen_objects'] == len(pl['items'])

# ---- 板金(外注見積用の概形): STEP + DXF(平板の外形) ----
sheet = []
def dxf_rect(path, w, h, note):
    L = ['0', 'SECTION', '2', 'ENTITIES']
    for (x1, y1), (x2, y2) in (((0, 0), (w, 0)), ((w, 0), (w, h)), ((w, h), (0, h)), ((0, h), (0, 0))):
        L += ['0', 'LINE', '8', 'OUTLINE', '10', f'{x1}', '20', f'{y1}', '30', '0', '11', f'{x2}', '21', f'{y2}', '31', '0']
    L += ['0', 'TEXT', '8', 'NOTE', '10', '5', '20', f'{h+8}', '30', '0', '40', '5', '1', note]
    L += ['0', 'ENDSEC', '0', 'EOF']
    open(path, 'w').write('\n'.join(L))
for p in rack_v3_layout.parts('switch'):
    if p['kind'] not in ('frame', 'shell') or 'ゴム' in p['material']: continue
    x, y, z, dx, dy, dz = p['box']
    if p['name'] in ('外装シェル_左', '外装シェル_右'): continue
    safe = p['name'].replace('/', '_').replace('(', '_').replace(')', '')
    if p['name'] == '外装シェル_天面':
        R, t = SHELL_R, SHELL_T
        def rnd(x0, x1, z1, r, yy, ddy, zz0):
            b = Part.makeBox(x1-x0, ddy, z1-zz0, App.Vector(x0, yy, zz0))
            return b.makeFillet(r, [e for e in b.Edges if e.BoundBox.YLength > ddy-1e-6 and abs(e.BoundBox.ZMin-z1) < 1e-6])
        s = rnd(OUT_X0, OUT_X1, H, R, y, dy, 10).cut(rnd(OUT_X0+t, OUT_X1-t, H-t, R-t, y-1, dy+2, 9))
        flat = (H-10-R)*2 + (OUT_X1-OUT_X0-2*R) + math.pi/2*(R-t/2)*2
        blank = (round(flat, 1), round(dy, 1)); safe = '外装シェルU字_R40'
        tname = '外装シェルU字(天面+左右, R40)'
    else:
        s = Part.makeBox(dx, dy, dz, App.Vector(x, y, z)); tname = p['name']
        dims = sorted((dx, dy, dz)); blank = (round(dims[2], 1), round(dims[1], 1))
        if 'シャーシ側壁' in p['name']: blank = (round(dy+40, 1), round(dz, 1))      # 前後20mmフランジ込み
        if '台座' in p['name']: blank = (round(2*(dx+dy), 1), round(dz+15, 1))       # 枠を1本曲げ(概算)
    sp = os.path.join(OUT, 'sheetmetal', f'{safe}.step'); s.exportStep(sp)
    dp = os.path.join(OUT, 'sheetmetal', f'{safe}_blank.dxf')
    thick = round(min(dx, dy, dz), 1) if tname != '外装シェルU字(天面+左右, R40)' else SHELL_T
    dxf_rect(dp, blank[0], blank[1], f'{safe} t={thick} A5052 BLANK(approx, holes/bends not detailed)')
    sheet.append(dict(name=tname, material=p['material'], thickness_mm=thick, blank_mm=blank, step=os.path.relpath(sp, ROOT), dxf=os.path.relpath(dp, ROOT), note=p['note']))

summary = dict(parts_types=len(results), parts_total=sum(r['qty'] for r in results), plates=len(plates),
               all_parts_passed=all(r['check']['passed'] for r in results), all_tiles_passed=all(t['check']['passed'] for t in tiles),
               tiles_total=sum(t['qty'] for t in tiles), plates_within_246=all(p['within_246'] for p in plate_info),
               plates_reopen_ok=all(p['reopen_ok'] for p in plate_info),
               total_weight_g=round(sum(r['est_weight_g']*r['qty'] for r in results)), total_time_h=round(sum(r['est_time_h']*r['qty'] for r in results), 1),
               tiles_weight_g=round(sum(t['est_weight_g']*t['qty'] for t in tiles)), tiles_time_h=round(sum(t['est_time_h']*t['qty'] for t in tiles), 1))
summary['passed'] = summary['all_parts_passed'] and summary['all_tiles_passed'] and summary['plates_within_246'] and summary['plates_reopen_ok']
val = dict(scope='メッシュの閉じた形状(watertight)・非多様体・連結成分・CADとの外形/体積一致・246mm以内・3MF再読込。強度・寸法精度・実物適合は未検証。寸法は実測前の仮値。',
           summary=summary, parts=results, plates=plate_info, tiles_option=tiles, sheetmetal=sheet)
json.dump(val, open(os.path.join(OUT, 'validation.json'), 'w'), ensure_ascii=False, indent=1)
json.dump(dict(plates=plate_info, source_run=f'print-{RUN}'), open(os.path.join(PP, 'plates.json'), 'w'), ensure_ascii=False, indent=1)

def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
inputs = [os.path.join(HERE, f) for f in ('rack_v3_parameters.py', 'rack_v3_layout.py', 'printed_parts_v3.py', 'printed_tiles_v3.py', 'build_print_v3.py')]
outs = []
for base in (OUT, PP):
    for dp_, _, fs in os.walk(base):
        outs += [os.path.join(dp_, f) for f in fs if f != 'manifest.json']
man = dict(run_id=RUN, model='spark-rack-v3-apple 印刷部品(試作/prototype, PAHT-CF)', status='success' if summary['passed'] else 'checks_failed',
           freecad_version=App.Version()[:4], python=platform.python_version(),
           inputs={os.path.relpath(p, ROOT): sha(p) for p in inputs}, outputs={os.path.relpath(p, ROOT): sha(p) for p in sorted(outs)},
           summary=summary, note='3MFは形状の正本ではなく配置の記録。スライス設定(PAHT-CF)はBambu Studioで印刷指示書に従い設定する。本番(production)は条件未設定のため生成しない。')
json.dump(man, open(os.path.join(OUT, 'manifest.json'), 'w'), ensure_ascii=False, indent=1)
json.dump(man, open(os.path.join(PP, 'manifest.json'), 'w'), ensure_ascii=False, indent=1)
print('PRINT_OUT', OUT, PP, json.dumps(summary, ensure_ascii=False))
