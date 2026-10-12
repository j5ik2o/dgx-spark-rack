# -*- coding: utf-8 -*-
"""案Aの幾何・質量・配線長の検査。純Python(直方体近似)。
CAD上の検査であり、耐荷重・冷却性能・実物適合を保証しない。"""
import math, itertools
from rack_v3_parameters import *

def overlap(a, b, tol=0.01):
    ax, ay, az, adx, ady, adz = a; bx, by, bz, bdx, bdy, bdz = b
    o = [min(ax+adx, bx+bdx)-max(ax, bx), min(ay+ady, by+bdy)-max(ay, by), min(az+adz, bz+bdz)-max(az, bz)]
    return o if all(v > tol for v in o) else None

SOLID = ('frame', 'plate', 'shell', 'printed', 'device', 'fan', 'psu', 'ctrl')

def excluded(p, q):
    g = {p['group'], q['group']}
    names = p['name'] + q['name']
    if 'in_tunnel' in g and ('アダプタートンネル' in p['name'] or 'アダプタートンネル' in q['name']):
        return True   # トンネルは中空。内部機器は内側として扱う
    if '導風ダクト' in names and '140ファン' in names:
        return False
    return False

def interference(P):
    res = []
    for p, q in itertools.combinations(P, 2):
        if p['kind'] == 'zone' and q['kind'] == 'zone':
            continue
        if excluded(p, q):
            continue
        o = overlap(p['box'], q['box'])
        if o:
            res.append(dict(a=p['name'], b=q['name'], overlap_mm=[round(v, 2) for v in o]))
    return res

def print_fit(P):
    out = []
    for p in P:
        if p['kind'] != 'printed':
            continue
        dims = sorted(p['box'][3:])
        ok = dims[1] <= PRINT_LIMIT and dims[2] <= PRINT_LIMIT
        out.append(dict(name=p['name'], dims=[round(d, 1) for d in p['box'][3:]], fits_246=ok))
    return out

def sweep(P, name, axis, dist, ignore=()):
    """部品をaxis方向にdist動かす経路の干渉。"""
    tgt = next(p for p in P if p['name'] == name)
    x, y, z, dx, dy, dz = tgt['box']
    b = [x, y, z, dx, dy, dz]
    i = 'xyz'.index(axis.lstrip('-'))
    if axis.startswith('-'):
        b[i] -= dist; b[i+3] += dist
    else:
        b[i+3] += dist
    hits = []
    for p in P:
        if p is tgt or p['kind'] not in SOLID or any(s in p['name'] for s in ignore):
            continue
        if overlap(b, p['box']):
            hits.append(p['name'])
    return dict(part=name, direction=axis, distance=dist, removed_first=list(ignore), hits=hits, clear=not hits)

def mass_cg(P):
    m = sum(p['mass'] for p in P)
    cg = [sum(p['mass']*(p['box'][k]+p['box'][k+3]/2) for p in P)/m for k in range(3)]
    # 支持多角形=脚の外周(柱外面 X0..W, Y0..D)
    x, y, z = cg
    p = PLINTH
    d = dict(left=x-p['x0'], right=p['x1']-x, front=y-p['y0'], back=p['y1']-y)
    tip = {k: round(math.degrees(math.atan2(v, z)), 1) for k, v in d.items()}
    # 天面で水平に押したときに転倒する力(N): F*H = m*g*d
    push = {k: round(m*9.81*v/H, 1) for k, v in d.items()}
    return dict(total_kg=round(m, 2), cg_mm=[round(v, 1) for v in cg], tip_angle_deg=tip, top_push_to_tip_N=push)

def bend_path_len(dx, dz, r, straight):
    """背面端子から真後ろへstraight出し、R曲げでUターン/横移動する最短の目安長さ。"""
    # 出→R90→横/縦移動→R90→戻り(直線)。曲げ2つ分の弧を含む
    return 2*straight + max(0.0, math.hypot(dx, dz) - 2*r) + math.pi*r

def ring_cables(P):
    sp = {p['name'].split('_')[-1]: p for p in P if p['name'].startswith('DGX_Spark')}
    c = {k: (v['box'][0]+v['box'][3]/2, v['box'][2]+v['box'][5]/2) for k, v in sp.items()}
    links = [("1段左", "1段右"), ("1段右", "2段右"), ("2段右", "2段左"), ("2段左", "1段左")]
    out = []
    for a, b in links:
        dx = c[b][0]-c[a][0]; dz = c[b][1]-c[a][1]
        need = bend_path_len(dx, dz, RING_BEND_R, QSFP_STRAIGHT)
        out.append(dict(link=f"{a}→{b}", center_dx=round(dx), center_dz=round(dz), est_required_mm=round(need),
                        available_mm=RING_CABLE_LEN, margin_mm=round(RING_CABLE_LEN-need),
                        ok=need <= RING_CABLE_LEN))
    return out

def breakout(P):
    sw = next((p for p in P if p['name'] == 'CRS812_DDQ'), None)
    if not sw:
        return []
    sx, sy, sz, sdx, sdy, sdz = sw['box']
    port = (sx+sdx*0.75, sy+sdy, sz+sdz/2)   # 仮: QSFP-DD 2口は右寄り(M)
    out = []
    for p in P:
        if not p['name'].startswith('DGX_Spark'):
            continue
        x, y, z, dx, dy, dz = p['box']
        tgt = (x+dx/2, y+dy, z+dz/2)
        # 経路: スイッチ端子→後方へ直線→下降(背面配線域)→Spark端子(直線)。曲げ3回
        route = QSFP_STRAIGHT*2 + abs(port[2]-tgt[2]) + abs(port[0]-tgt[0]) + abs(port[1]-tgt[1]) + 150  # +150: 束ね・回り込み余裕(A)
        out.append(dict(spark=p['name'], route_mm=round(route), nominal_branch_budget_mm=2000,
                        slack_mm=round(2000-route), note="分岐位置・枝長は未確定。幹+枝=公称2mとして余長を見積もる"))
    return out

def run(P_switch, P_ring):
    res = {}
    for key, P in (("switch", P_switch), ("ring", P_ring)):
        res[key] = dict(interference=interference(P), mass=mass_cg(P))
    res['print_fit'] = print_fit(P_switch)
    res['sweeps'] = [
        sweep(P_switch, 'CRS812_DDQ', 'y', 420, ignore=('スイッチ側面保持', '背面カバー')),
        sweep(P_switch, 'コントローラー_左1段', '-y', 60, ignore=('前面ラティスパネル',)),
        sweep(P_switch, '外装シェル_天面', 'z', 600, ignore=()),
        sweep(P_switch, 'DGX_Spark_1段左', '-y', 200, ignore=('導風ダクト_1段左', '140ファン_1段左', '前面ラティスパネル')),
        sweep(P_switch, 'DGX_Spark_2段右', '-y', 200, ignore=('導風ダクト_2段右', '140ファン_2段右', '前面ラティスパネル')),
        sweep(P_switch, '140ファン_1段左', '-y', 120, ignore=('前面ラティスパネル',)),
        sweep(P_switch, '電源アダプター_1', 'y', 140, ignore=('アダプタートンネル', '120ファン', '背面カバー')),
        sweep(P_switch, 'コントローラー電源_2', '-y', 60, ignore=('前面ラティスパネル',)),
    ]
    res['ring_cables'] = ring_cables(P_ring)
    res['cooling'] = cooling()
    res['breakout_estimate'] = breakout(P_switch)
    return res


def perforated_dp(phi, v_face, t, d, rho=1.2):
    """穴あき板の圧損(Idelchik 薄板式＋厚さ補正の概算)。v_face: 前面風速 m/s"""
    zeta = (0.707*math.sqrt(1-phi)+1-phi)**2/phi**2
    if t/d > 0.5:
        zeta *= 0.85   # 厚板は縮流が回復し僅かに下がる(概算)
    return zeta, zeta*rho*v_face**2/2

def cooling():
    out = {}
    phi_f = (math.pi/4*LATTICE['hole_d']**2)/(LATTICE['pitch']**2*math.sqrt(3)/2)
    phi_r = (math.pi/4*REAR_LATTICE['hole_d']**2)/(REAR_LATTICE['pitch']**2*math.sqrt(3)/2)
    out['front_open_ratio'] = round(phi_f, 3); out['rear_open_ratio'] = round(phi_r, 3)
    cases = []
    for q in (60.0, 100.0):   # 140ファン1台あたりの実流量仮定 m3/h
        Q = q/3600
        v_face = Q/(0.140*0.140)
        zf, dpf = perforated_dp(phi_f, v_face, LATTICE['t'], LATTICE['hole_d'])
        # ダクト縮小(142角→150x44): 急縮小 ζ≈0.5*(1-A2/A1) を出口速度基準
        a1, a2 = 0.142**2, 0.150*0.044
        v2 = Q/a2; dpd = 0.5*(1-a2/a1)*1.2*v2**2/2 + 1.0*1.2*v2**2/2*0   # 本体内部損失は含めない
        # 背面: Spark4台分を排気格子の有効面積(2段Spark背面範囲 450x200)で受ける
        vr = 4*Q/(0.450*0.200)
        zr, dpr = perforated_dp(phi_r, vr, REAR_LATTICE['t'], REAR_LATTICE['hole_d'])
        cases.append(dict(fan_flow_m3h=q, front_face_v_ms=round(v_face, 2), front_dp_Pa=round(dpf, 1),
                          duct_contraction_dp_Pa=round(dpd, 1), duct_outlet_v_ms=round(v2, 2),
                          rear_dp_Pa=round(dpr, 1), total_added_dp_Pa=round(dpf+dpd+dpr, 1)))
    out['cases'] = cases
    out['note'] = ('外装で追加される圧損の概算(Spark内部抵抗を除く)。NF-A14x25 G2の最大静圧はNoctua公表値で数mmH2O(約20〜40Pa、要確認)。'
                   '総追加圧損がこれに対して小さいことを比較の目安とし、冷却性能の保証ではない。')
    return out
