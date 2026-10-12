# -*- coding: utf-8 -*-
"""寸法付き2D図(正面・側面・背面・上面・全体等角)と配線図をmatplotlibで描く。"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch, Circle
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib import font_manager
from rack_v2_parameters import *

for f in font_manager.findSystemFonts():
    if 'NotoSansCJK' in f or 'NotoSerifCJK-Regular' in f:
        font_manager.fontManager.addfont(f)
plt.rcParams['font.family'] = ['Noto Sans CJK JP', 'Noto Serif CJK JP', 'DejaVu Sans']

COL = dict(frame='#555b63', plate='#9aa3ad', printed='#2b2b2b', device='#c9a227', fan='#c8b08a',
           psu='#3d7ab8', ctrl='#7a4fb3', zone='none')
ZCOL = dict(work='#2ca02c', airflow='#d62728', **{'': '#888888'})

def proj(p, view):
    x, y, z, dx, dy, dz = p['box']
    if view == 'front': return x, z, dx, dz, -y
    if view == 'rear':  return W-(x+dx), z, dx, dz, y
    if view == 'side':  return y, z, dy, dz, x + dx   # 右側面から見る(Y右向き)
    if view == 'top':   return x, y, dx, dy, z+dz

def dim(ax, x0, y0, x1, y1, text, off=0, horiz=True):
    if horiz:
        ax.annotate('', (x0, y0+off), (x1, y1+off), arrowprops=dict(arrowstyle='<->', lw=0.8))
        ax.text((x0+x1)/2, y0+off+4, text, ha='center', va='bottom', fontsize=7)
    else:
        ax.annotate('', (x0+off, y0), (x1+off, y1), arrowprops=dict(arrowstyle='<->', lw=0.8))
        ax.text(x0+off-4, (y0+y1)/2, text, ha='right', va='center', fontsize=7, rotation=90)

def draw_view(P, view, title, path, labels=True):
    fig, ax = plt.subplots(figsize=(11, 10))
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
    ext_w = {'front': W, 'rear': W, 'side': D, 'top': W}[view]
    ax.set_xlim(-130, ext_w+130)
    if view == 'top':
        ax.set_ylim(-120, D+140)
        dim(ax, 0, -60, W, -60, f'外形幅 {W:.0f}(側板込み{W+2*SIDE_PANEL_T:.0f})')
        dim(ax, -70, 0, -70, D, f'奥行 {D:.0f}', horiz=False)
    else:
        ax.set_ylim(-60, H+80)
        dim(ax, 0, -35, ext_w, -35, f"{'幅' if view != 'side' else '奥行'} {ext_w:.0f}")
        dim(ax, -75, 0, -75, H, f'高さ {H:.0f}', horiz=False)
        for z, t in ((FOOT_H+EXT+3, '底板上 31'), (TIER_BEAM_Z[0]+EXT+TRAY_T, f'1段Spark {TIER_BEAM_Z[0]+EXT+TRAY_T:.0f}'),
                     (TIER_BEAM_Z[1]+EXT+TRAY_T, f'2段Spark {TIER_BEAM_Z[1]+EXT+TRAY_T:.0f}'),
                     (SWITCH_SHELF_Z+EXT+SWITCH_PLATE_T, f'受け板上 {SWITCH_SHELF_Z+EXT+SWITCH_PLATE_T:.0f}')):
            ax.plot([ext_w, ext_w+40], [z, z], 'k-', lw=0.5)
            ax.text(ext_w+42, z, t, fontsize=7, va='center')
        if view in ('front', 'rear'):
            xs = SPARK_X if view == 'front' else [W-(x+SPARK['w']) for x in SPARK_X[::-1]]
            for x in xs:
                dim(ax, x, H+20, x+SPARK['w'], H+20, '150')
            dim(ax, xs[0]+SPARK['w'], H+45, xs[1], H+45, f'{xs[1]-xs[0]-SPARK["w"]:.0f}')
        if view == 'side':
            dim(ax, FAN_Y0, H+20, SPARK_Y0, H+20, f'ファン+ダクト {SPARK_Y0-FAN_Y0:.0f}')
            dim(ax, SPARK_Y0, H+20, SPARK_Y0+150, H+20, 'Spark 150')
            dim(ax, SPARK_Y0+150, H+20, D, H+20, f'背面配線域 {D-SPARK_Y0-150:.0f}')
            dim(ax, SWITCH_Y0, H+50, SWITCH_Y0+SWITCH['d'], H+50, f'CRS812 {SWITCH["d"]:.0f}(要照合)')
    ax.set_aspect('equal'); ax.set_title(title, fontsize=11)
    ax.text(0.01, 0.01, '凡例: 灰=2020枠/板 黒=印刷部品 黄=Spark/スイッチ ベージュ=ファン 青=電源類 紫=コントローラー\n'
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
