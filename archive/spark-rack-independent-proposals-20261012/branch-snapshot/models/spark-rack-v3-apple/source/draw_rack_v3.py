# -*- coding: utf-8 -*-
"""寸法付き2D図(正面・側面・背面・上面・全体等角)と配線図をmatplotlibで描く。"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch, Circle
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib import font_manager
from rack_v3_parameters import *

for f in font_manager.findSystemFonts():
    if 'NotoSansCJK' in f or 'NotoSerifCJK-Regular' in f:
        font_manager.fontManager.addfont(f)
plt.rcParams['font.family'] = ['Noto Sans CJK JP', 'Noto Serif CJK JP', 'DejaVu Sans']

COL = dict(frame='#555b63', plate='#9aa3ad', printed='#2b2b2b', device='#c9a227', fan='#c8b08a',
           psu='#3d7ab8', ctrl='#7a4fb3', shell='#6e6e73', zone='none')
ZCOL = dict(work='#2ca02c', airflow='#d62728', **{'': '#888888'})

def proj(p, view):
    x, y, z, dx, dy, dz = p['box']
    if view == 'front': return x, z, dx, dz, -y
    if view == 'rear':  return OUT_X1+OUT_X0-(x+dx), z, dx, dz, y
    if view == 'side':  return y, z, dy, dz, x + dx   # 右側面から見る(Y右向き)
    if view == 'top':   return x, y, dx, dy, z+dz

def dim(ax, x0, y0, x1, y1, text, off=0, horiz=True):
    if horiz:
        ax.annotate('', (x0, y0+off), (x1, y1+off), arrowprops=dict(arrowstyle='<->', lw=0.8))
        ax.text((x0+x1)/2, y0+off+4, text, ha='center', va='bottom', fontsize=7)
    else:
        ax.annotate('', (x0+off, y0), (x1+off, y1), arrowprops=dict(arrowstyle='<->', lw=0.8))
        ax.text(x0+off-4, (y0+y1)/2, text, ha='right', va='center', fontsize=7, rotation=90)

def draw_view(P, view, title, path, labels=True, hide=('前面ラティスパネル', '背面カバー', '外装シェル_左', '外装シェル_右', '外装シェル_天面')):
    fig, ax = plt.subplots(figsize=(11, 10))
    if view == 'side':
        hide = tuple(hide) + ('シャーシ側壁_左', 'シャーシ側壁_右', '配線チャネル_左', '配線チャネル_右', '背面配線域')
    P = [p for p in P if p['name'] not in hide]
    items = sorted([(proj(p, view), p) for p in P], key=lambda t: t[0][4])
    for (u, v, du, dv, depth), p in items:
        if p['kind'] == 'zone':
            c = ZCOL.get(p['group'], '#888')
            ax.add_patch(Rectangle((u, v), du, dv, fill=False, ec=c, ls='--', lw=0.8, hatch='//', alpha=0.6))
        else:
            ax.add_patch(Rectangle((u, v), du, dv, fc=COL[p['kind']], ec='k', lw=0.4, alpha=0.9 if p['kind'] != 'plate' else 0.5))
    if labels:
        seen = set()
        for (u, v, du, dv, depth), p in items[::-1]:
            if p['kind'] in ('device', 'fan', 'psu', 'ctrl') or ('トンネル_2' in p['name']) or '余長' in p['name']:
                key = (round(u), round(v))
                if key in seen: continue
                seen.add(key)
                if du*dv < 1500 and p['kind'] != 'ctrl': continue
                ax.text(u+du/2, v+dv/2, p['name'].replace('_', '\n'), ha='center', va='center', fontsize=5.5,
                        color='w' if p['kind'] in ('psu', 'ctrl', 'printed') else 'k')
    # 外装の輪郭(大R)を線で重ねる
    import numpy as np
    def shell_outline(u0, u1):
        R = SHELL_R; th = np.linspace(0, np.pi/2, 20)
        xs = [u0, u0] + list(u0+R-R*np.cos(th)) + list(u1-R+R*np.sin(th)) + [u1, u1]
        zs = [10, H-R] + list(H-R+R*np.sin(th)) + list(H-R+R*np.cos(th)) + [H-R, 10]
        return xs, zs
    if view in ('front', 'rear'):
        xs, zs = shell_outline(OUT_X0, OUT_X1); ax.plot(xs, zs, color='#6e6e73', lw=2.5)
        u0, u1 = OUT_X0, OUT_X1
    elif view == 'side':
        ax.plot([OUT_Y0, OUT_Y1, OUT_Y1, OUT_Y0, OUT_Y0], [10, 10, H, H, 10], color='#6e6e73', lw=2.5)
        u0, u1 = OUT_Y0, OUT_Y1
    else:
        ax.plot([OUT_X0, OUT_X1, OUT_X1, OUT_X0, OUT_X0], [OUT_Y0, OUT_Y0, OUT_Y1, OUT_Y1, OUT_Y0], color='#6e6e73', lw=2.5)
        u0, u1 = OUT_X0, OUT_X1
    ax.set_xlim(u0-130, u1+150)
    if view == 'top':
        ax.set_ylim(OUT_Y0-120, OUT_Y1+60)
        dim(ax, OUT_X0, OUT_Y0-60, OUT_X1, OUT_Y0-60, f'外形幅 {OUT_X1-OUT_X0:.0f}')
        dim(ax, OUT_X0-70, OUT_Y0, OUT_X0-70, OUT_Y1, f'外形奥行 {OUT_Y1-OUT_Y0:.0f}', horiz=False)
    else:
        ax.set_ylim(-60, H+90)
        dim(ax, u0, -35, u1, -35, f"{'外形幅' if view != 'side' else '外形奥行'} {u1-u0:.0f}")
        dim(ax, u0-75, 0, u0-75, H, f'高さ {H:.0f}', horiz=False)
        for z, t in ((BASE_Z1, f'底板上 {BASE_Z1:.0f}'), (TIER_BEAM_Z[0]+EXT+TRAY_T, f'1段Spark {TIER_BEAM_Z[0]+EXT+TRAY_T:.0f}'),
                     (TIER_BEAM_Z[1]+EXT+TRAY_T, f'2段Spark {TIER_BEAM_Z[1]+EXT+TRAY_T:.0f}'),
                     (SWITCH_SHELF_Z+EXT+SWITCH_PLATE_T, f'受け板上 {SWITCH_SHELF_Z+EXT+SWITCH_PLATE_T:.0f}')):
            ax.plot([u1, u1+40], [z, z], 'k-', lw=0.5); ax.text(u1+42, z, t, fontsize=7, va='center')
        if view in ('front', 'rear'):
            xs = SPARK_X if view == 'front' else [OUT_X1+OUT_X0-(x+SPARK['w']) for x in SPARK_X[::-1]]
            for x in xs: dim(ax, x, H+20, x+SPARK['w'], H+20, '150')
            dim(ax, xs[0]+SPARK['w'], H+48, xs[1], H+48, f'{xs[1]-xs[0]-SPARK["w"]:.0f}')
            ax.text(u0, H+70, f'外装 天面肩R{SHELL_R:.0f}・2mm陽極酸化アルミ(灰線)。前面ラティス/背面カバーは非表示', fontsize=7)
        if view == 'side':
            dim(ax, OUT_Y0, H+20, FAN_Y0, H+20, f'{FAN_Y0-OUT_Y0:.0f}')
            dim(ax, FAN_Y0, H+20, SPARK_Y0, H+20, f'ファン+ダクト {SPARK_Y0-FAN_Y0:.0f}')
            dim(ax, SPARK_Y0, H+20, SPARK_Y0+150, H+20, 'Spark 150')
            dim(ax, SPARK_Y0+150, H+20, OUT_Y1, H+20, f'背面配線域 {OUT_Y1-SPARK_Y0-150:.0f}')
            dim(ax, SWITCH_Y0, H+50, SWITCH_Y0+SWITCH['d'], H+50, f'CRS812 {SWITCH["d"]:.0f}(要照合)')
            dim(ax, PLINTH['y0'], -12, PLINTH['y1'], -12, f'台座 {PLINTH["y1"]-PLINTH["y0"]:.0f}')
    ax.set_aspect('equal'); ax.set_title(title, fontsize=11)
    ax.text(0.01, 0.01, '凡例: 灰=内部シャーシ(曲げ板/C形梁) 黒=印刷部品 黄=Spark/スイッチ ベージュ=ファン 青=電源類 紫=コントローラー\n'
            '緑破線=作業空間/ケーブル曲げ 赤破線=吸排気確保。単位mm。直方体近似。', transform=ax.transAxes, fontsize=7)
    ax.axis('off'); fig.tight_layout(); fig.savefig(path, dpi=160); plt.close(fig)

def draw_iso(P, path, title):
    fig = plt.figure(figsize=(11, 10)); ax = fig.add_subplot(111, projection='3d')
    for p in P:
        if p['kind'] == 'zone': continue
        x, y, z, dx, dy, dz = p['box']
        v = [(x, y, z), (x+dx, y, z), (x+dx, y+dy, z), (x, y+dy, z), (x, y, z+dz), (x+dx, y, z+dz), (x+dx, y+dy, z+dz), (x, y+dy, z+dz)]
        f = [[v[i] for i in q] for q in ((0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (1, 2, 6, 5), (0, 3, 7, 4))]
        ax.add_collection3d(Poly3DCollection(f, facecolor=COL[p['kind']], edgecolor='k', lw=0.2, alpha=0.35 if p['kind'] in ('plate', 'printed') else 0.85))
    ax.set_xlim(-60, W+60); ax.set_ylim(-60, D+60+90); ax.set_zlim(0, H)
    ax.set_box_aspect((W+120, D+210, H)); ax.view_init(22, -125)
    ax.set_xlabel('X 幅'); ax.set_ylabel('Y 奥行(前0→後)'); ax.set_zlabel('Z')
    ax.set_title(title); fig.tight_layout(); fig.savefig(path, dpi=150); plt.close(fig)

def draw_wiring(P, path):
    """背面から見た配線図: 左=リング運用, 右=スイッチ運用。"""
    fig, axs = plt.subplots(1, 2, figsize=(14, 8))
    sp = {p['name'].split('_')[-1]: p['box'] for p in P if p['name'].startswith('DGX_Spark')}
    def rear_xy(b):  # 背面視: Xは左右反転
        x, y, z, dx, dy, dz = b
        return W-(x+dx/2), z+dz/2
    for k, ax in enumerate(axs):
        ax.add_patch(Rectangle((0, 0), W, H, fill=False, ec='#555', lw=1.5))
        for n, b in sp.items():
            cx, cz = rear_xy(b)
            ax.add_patch(Rectangle((cx-75, cz-25), 150, 50.5, fc='#c9a227', ec='k'))
            ax.text(cx, cz+8, f'Spark {n}', ha='center', fontsize=8)
            ax.plot(cx, cz-8, 's', color='k', ms=6)
            ax.text(cx+8, cz-14, 'QSFP(位置要実測)', fontsize=6)
        tunnel_z = (TUNNEL['z0']+TUNNEL['z1'])/2
        ax.add_patch(Rectangle((20, TUNNEL['z0']), W-40, TUNNEL['z1']-TUNNEL['z0'], fc='#3d7ab8', alpha=0.3, ec='k'))
        ax.text(W/2, tunnel_z, '電源アダプター4個(トンネル) USB-C→各Spark\n左吸気←120mm ×2→右排気', ha='center', fontsize=8)
        pts = {n: rear_xy(b) for n, b in sp.items()}
        if k == 0:
            order = ['1段左', '1段右', '2段右', '2段左', '1段左']
            for a, b in zip(order, order[1:]):
                (x0, z0), (x1, z1) = pts[a], pts[b]
                ax.annotate('', (x1, z1-8), (x0, z0-8), arrowprops=dict(arrowstyle='-', color='#d62728', lw=2.5, connectionstyle='arc3,rad=0.25'))
            ax.set_title('リング運用(途中状態): 40cm QSFP112 DAC×4\n受け板・スイッチ側面保持は取付済み/スイッチ無しでも可', fontsize=10)
        else:
            sx = W/2; sz = SWITCH_SHELF_Z+EXT+SWITCH_PLATE_T+SWITCH_FEET+SWITCH['h']/2
            ax.add_patch(Rectangle((W-(W+SWITCH['w'])/2, sz-22), SWITCH['w'], 44, fc='#c9a227', ec='k'))
            ax.text(sx, sz+5, 'CRS812 DDQ(端子面=背面)', ha='center', fontsize=8)
            for i, grp in enumerate((['1段左', '2段左'], ['1段右', '2段右'])):
                px = W-(W-SWITCH['w'])/2-SWITCH['w']*0.75 + (i*30-15)
                ax.plot(px, sz-8, 'ks', ms=7); ax.text(px, sz-20, f'DD{i+1}', fontsize=7, ha='center')
                split = (px if i == 0 else px, 420)
                ax.plot([px, px], [sz-8, 420], color=['#1f77b4', '#9467bd'][i], lw=4)
                for n in grp:
                    x, z = pts[n]
                    ax.plot([px, x, x], [420, 420-10*i, z-8], color=['#1f77b4', '#9467bd'][i], lw=2)
                ax.add_patch(Circle((px, 420), 8, color='k'))
            ax.text(W/2, 445, '分岐部(位置要確認)・余長は背面上部トレー(R42以上の8の字)', ha='center', fontsize=7)
            ax.set_title('スイッチ運用(完成形): Q2Q56-400G-CU2(2m)×2\nQSFP-DD 2口→各2本のQSFP56枝', fontsize=10)
        ax.text(5, -30, 'AC: タップ9口=Spark電源4+コントローラー電源3+スイッチ2(リング時は7口)', fontsize=7)
        ax.set_xlim(-20, W+20); ax.set_ylim(-50, H+20); ax.set_aspect('equal'); ax.axis('off')
    fig.suptitle('背面から見た配線図(左右反転注意: 背面視)'); fig.tight_layout(); fig.savefig(path, dpi=150); plt.close(fig)

def draw_options(path):
    """3案の概略比較(正面視)。"""
    fig, axs = plt.subplots(1, 3, figsize=(15, 6))
    def r(ax, x, z, w, h, c, t):
        ax.add_patch(Rectangle((x, z), w, h, fc=c, ec='k')); ax.text(x+w/2, z+h/2, t, ha='center', va='center', fontsize=7)
    a = axs[0]; a.set_title('案A(推奨) 490×400×540\nスイッチ最上段・Spark2×2・下段電源', fontsize=9)
    r(a, 0, 0, 490, 165, '#3d7ab8', 'アダプター4/トンネル+制御電源3+タップ'); r(a, 80, 189, 150, 50, '#c9a227', 'Spark'); r(a, 260, 189, 150, 50, '#c9a227', 'Spark')
    r(a, 80, 333, 150, 50, '#c9a227', 'Spark'); r(a, 260, 333, 150, 50, '#c9a227', 'Spark'); r(a, 23, 465, 443, 44, '#e3c35c', 'CRS812'); a.add_patch(Rectangle((0, 0), 490, 540, fill=False, lw=2))
    a = axs[1]; a.set_title('案B 490×400×520\nスイッチ最下段(低重心)・Spark2×2・電源最上段', fontsize=9)
    r(a, 23, 31, 443, 44, '#e3c35c', 'CRS812'); r(a, 80, 110, 150, 50, '#c9a227', 'Spark'); r(a, 260, 110, 150, 50, '#c9a227', 'Spark')
    r(a, 80, 254, 150, 50, '#c9a227', 'Spark'); r(a, 260, 254, 150, 50, '#c9a227', 'Spark'); r(a, 0, 380, 490, 140, '#3d7ab8', 'アダプター+制御電源'); a.add_patch(Rectangle((0, 0), 490, 520, fill=False, lw=2))
    a = axs[2]; a.set_title('案C 690×330×330\nSpark横一列4台×1段・スイッチ上段', fontsize=9)
    for i in range(4): r(a, 20+i*165, 120, 150, 50, '#c9a227', 'Spark')
    r(a, 0, 20, 690, 90, '#3d7ab8', '電源類'); r(a, 120, 260, 443, 44, '#e3c35c', 'CRS812'); a.add_patch(Rectangle((0, 0), 690, 330, fill=False, lw=2))
    for a in axs: a.set_xlim(-20, 710); a.set_ylim(-20, 560); a.set_aspect('equal'); a.axis('off')
    fig.tight_layout(); fig.savefig(path, dpi=140); plt.close(fig)


def draw_render(P, path, title, panel_on=True, color='#6e6e73', elev=16, azim=-115):
    """レンダリング風: 大R外装、ラティス穴の点描、陰影。面単位で奥→手前に描く簡易ペインター法。"""
    import numpy as np
    from matplotlib.colors import to_rgb
    fig = plt.figure(figsize=(12, 11), facecolor='white'); ax = fig.add_subplot(111, projection='3d', computed_zorder=False)
    el, az = np.radians(elev), np.radians(azim)
    cam = np.array([np.cos(el)*np.cos(az), np.cos(el)*np.sin(az), np.sin(el)])   # 視点方向(対象→カメラ)
    L = np.array([-0.4, -0.8, 0.9]); L /= np.linalg.norm(L)
    faces = []
    def quad(v, c, ec='#00000040', lw=0.2, a=1.0):
        v = [tuple(map(float, p)) for p in v]
        n = np.cross(np.subtract(v[1], v[0]), np.subtract(v[2], v[0])); n = n/(np.linalg.norm(n)+1e-9)
        if n @ cam < 0: n = -n
        k = 0.42 + 0.58*max(0.0, float(n @ L)) + 0.12*max(0.0, float(n @ cam))
        rgb = tuple(min(1, x*k) for x in to_rgb(c))
        faces.append((float(np.mean(v, axis=0) @ cam), v, rgb, ec, lw, a))
    def boxp(b, c):
        x, y, z, dx, dy, dz = b
        V = [(x, y, z), (x+dx, y, z), (x+dx, y+dy, z), (x, y+dy, z), (x, y, z+dz), (x+dx, y, z+dz), (x+dx, y+dy, z+dz), (x, y+dy, z+dz)]
        for q in ((0, 1, 5, 4), (1, 2, 6, 5), (4, 5, 6, 7), (0, 4, 7, 3), (3, 7, 6, 2), (0, 1, 2, 3)):
            quad([V[i] for i in q], c)
    R = SHELL_R; th = np.linspace(0, np.pi/2, 10)
    prof = [(OUT_X0, 10.0), (OUT_X0, H-R)] + [(OUT_X0+R-R*np.cos(t), H-R+R*np.sin(t)) for t in th[1:]] + \
           [(OUT_X1-R+R*np.sin(t), H-R+R*np.cos(t)) for t in th] + [(OUT_X1, 10.0)]
    y0, y1 = OUT_Y0+LATTICE['t'], OUT_Y1
    for p in P:
        if p['kind'] in ('zone', 'shell'): continue
        if not panel_on and p['name'].startswith('シャーシ側壁'): pass
        c = {'device': '#d4af37' if 'Spark' in p['name'] else '#c7c7cc', 'fan': '#c8b08a', 'printed': '#2b2b2b', 'psu': '#2f5f8f',
             'ctrl': '#5e4b8b', 'frame': '#8e8e93'}.get(p['kind'], '#999')
        boxp(p['box'], c)
    for a, b in zip(prof, prof[1:]):
        quad([(a[0], y0, a[1]), (b[0], y0, b[1]), (b[0], y1, b[1]), (a[0], y1, a[1])], color, ec='none', lw=0)
    quad([(x, y1, z) for x, z in prof], color, ec='#444', lw=0.6)   # 背面カバー
    faces.sort(key=lambda f: f[0])
    if panel_on:   # 前面パネルは常に最前面
        quad([(x, OUT_Y0, z) for x, z in prof], color, ec='#444', lw=0.6)
    for _, v, rgb, ec, lw, a in faces:
        ax.add_collection3d(Poly3DCollection([v], facecolor=rgb, edgecolor=ec, lw=lw, alpha=a))
    if panel_on:
        xs, zs = [], []
        pitch = 13.0
        for j, z in enumerate(np.arange(25, H-15, pitch*0.866)):
            for x in np.arange(OUT_X0+15+(pitch/2 if j % 2 else 0), OUT_X1-15, pitch):
                if z > H-R and min(x-OUT_X0, OUT_X1-x) < R-np.sqrt(max(0, R**2-(z-(H-R))**2))+10:
                    continue
                xs.append(x); zs.append(z)
        ax.scatter(xs, [OUT_Y0-0.5]*len(xs), zs, s=2.0, c='#1c1c1e', depthshade=False)
        for p in P:
            if p['kind'] == 'ctrl':
                x, y, z, dx, dy, dz = p['box']
                ax.add_collection3d(Poly3DCollection([[(x+6, OUT_Y0-1, z+25), (x+dx-6, OUT_Y0-1, z+25), (x+dx-6, OUT_Y0-1, z+50), (x+6, OUT_Y0-1, z+50)]],
                                                     facecolor='#101820', edgecolor='#bbb', lw=0.6))
                ax.text(x+dx/2, OUT_Y0-2, z+37, '28℃', fontsize=5, color='#30d158', ha='center', zdir='x')
    ax.set_xlim(OUT_X0-40, OUT_X1+40); ax.set_ylim(OUT_Y0-40, OUT_Y1+40); ax.set_zlim(0, H+20)
    ax.set_box_aspect((OUT_X1-OUT_X0+80, OUT_Y1-OUT_Y0+80, H+20)); ax.view_init(elev, azim); ax.axis('off')
    ax.set_title(title, fontsize=13)
    fig.tight_layout(); fig.savefig(path, dpi=150, facecolor='white'); plt.close(fig)
