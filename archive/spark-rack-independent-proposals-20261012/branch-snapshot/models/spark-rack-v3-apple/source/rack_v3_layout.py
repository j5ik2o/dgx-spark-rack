# -*- coding: utf-8 -*-
"""案D(Apple風)の部品配置。直方体近似(外装の大Rと格子穴はFCStd/描画側で表現)。純Python。
kind: frame(内部シャーシ構造) / plate / shell(外装・非構造) / printed / device / fan / psu / ctrl / zone
"""
from rack_v3_parameters import *

def B(name, kind, x, y, z, dx, dy, dz, mass=0.0, note="", group="", material=""):
    return dict(name=name, kind=kind, box=[x, y, z, dx, dy, dz], mass=mass, note=note, group=group, material=material)

AL = 2.68e-6
PETG = 1.27e-6 * 0.45

def sheet(name, kind, x, y, z, dx, dy, dz, t, note="", open_ratio=0.0, material='A5052'):
    area = dx*dy*dz/max(min(dx, dy, dz), 1e-6)
    return B(name, kind, x, y, z, dx, dy, dz, area*t*AL*(1-open_ratio), note, 'frame' if kind != 'shell' else 'shell', material)

def channel(name, x, y, z, dx, dy, dz, note=""):
    L = max(dx, dy, dz)
    return B(name, 'frame', x, y, z, dx, dy, dz, L*80*2*AL, note or "2mm曲げC形チャンネル20x20(内部・非可視)", 'frame', 'A5052')

def printed(name, x, y, z, dx, dy, dz, fill=0.35, note="", group="printed"):
    return B(name, 'printed', x, y, z, dx, dy, dz, dx*dy*dz*PETG*fill, note, group, 'ASA/PC(要選定)')

def parts(state="switch"):
    P = []
    CY = CHASSIS_Y1-CHASSIS_Y0
    # ---- 台座・脚・底板 ----
    p = PLINTH
    P.append(sheet("台座(奥まった基部)", 'frame', p['x0'], p['y0'], p['z0'], p['x1']-p['x0'], p['y1']-p['y0'], p['z1']-p['z0'], 2.0,
                   "2mm曲げ枠。外周より40〜70mm内側に引込み、本体が浮いて見える。AC1本の出口"))
    for nx, x in (("左", p['x0']), ("右", p['x1']-30)):
        for ny, y in (("前", p['y0']), ("後", p['y1']-30)):
            P.append(B(f"脚_{nx}{ny}", 'printed', x, y, 0, 30, 30, FOOT_H, 0.005, "防振ゴム脚φ30(市販)", 'printed', 'ゴム'))
    P.append(B("底板", 'frame', WALL_X[0][0], CHASSIS_Y0, BASE_Z0, WALL_X[1][1]-WALL_X[0][0], CY, BASE_Z1-BASE_Z0,
               (WALL_X[1][1]-WALL_X[0][0])*CY*(BASE_Z1-BASE_Z0)*AL*0.85, "A5052 6mm。側壁を下面から皿ねじで受ける構造の基礎", 'frame', 'A5052'))
    # ---- 内部シャーシ側壁(構造) ----
    for side, (x0, x1) in zip("左右", WALL_X):
        P.append(sheet(f"シャーシ側壁_{side}", 'frame', x0, CHASSIS_Y0, BASE_Z1, x1-x0, CY, 517.0-BASE_Z1, WALL_T,
                       "3mm曲げ板(前後に20mmフランジ)。梁・受け板を内側から支持。配線チャネル側に縦穴"))
    P.append(sheet("シャーシ天板", 'frame', WALL_X[0][0], CHASSIS_Y0, 517.0, WALL_X[1][1]-WALL_X[0][0], CY, 3.0, 3.0, "3mm。側壁上端と箱を閉じ剛性を出す"))
    # ---- 外装(非構造) ----
    sh_y0, sh_y1 = OUT_Y0+LATTICE['t'], OUT_Y1-REAR_LATTICE['t']
    P.append(sheet("外装シェル_左", 'shell', OUT_X0, sh_y0, 10.0, SHELL_T, sh_y1-sh_y0, H-10-SHELL_R, SHELL_T, "陽極酸化A5052 2mm。天面とR40で一体曲げのU字", material='A5052陽極酸化'))
    P.append(sheet("外装シェル_右", 'shell', OUT_X1-SHELL_T, sh_y0, 10.0, SHELL_T, sh_y1-sh_y0, H-10-SHELL_R, SHELL_T, "同上", material='A5052陽極酸化'))
    P.append(sheet("外装シェル_天面", 'shell', OUT_X0+SHELL_R, sh_y0, H-SHELL_T, OUT_X1-OUT_X0-2*SHELL_R, sh_y1-sh_y0, SHELL_T, SHELL_T, "同上(肩R40部は描画で表現)", material='A5052陽極酸化'))
    P.append(sheet("前面ラティスパネル", 'shell', OUT_X0, OUT_Y0, 10.0, OUT_X1-OUT_X0, LATTICE['t'], H-10, 2.0,
                   "千鳥丸穴φ5/P6.5(開口率約54%)。ネオジム磁石8個で着脱。表示窓6か所(透明PC)", open_ratio=0.54, material='A5052陽極酸化'))
    P.append(sheet("背面カバー", 'shell', OUT_X0, OUT_Y1-REAR_LATTICE['t'], 10.0, OUT_X1-OUT_X0, REAR_LATTICE['t'], H-10, REAR_LATTICE['t'],
                   "上部〜中部は穴φ4/P5.5(開口約48%)の排気格子。下部にAC1本のグロメット。つまみねじ4本(工具不要)", open_ratio=0.45, material='A5052陽極酸化'))
    # ---- 梁(内部チャンネル) ----
    for t, zb in enumerate(TIER_BEAM_Z):
        lv = t+1
        P.append(channel(f"{lv}段_受け梁前", INNER_X0, SPARK_Y0, zb, INNER_X1-INNER_X0, EXT, EXT))
        P.append(channel(f"{lv}段_受け梁後", INNER_X0, SPARK_Y0+SPARK['d']-EXT, zb, INNER_X1-INNER_X0, EXT, EXT))
        ztray = zb+EXT; zs = ztray+TRAY_T
        for c, xs in enumerate(SPARK_X):
            n = f"{lv}段{'左右'[c]}"
            P.append(printed(f"Sparkトレー_{n}", xs-5, SPARK_Y0, ztray, SPARK['w']+10, SPARK['d'], TRAY_T, 0.6,
                             "工具不要の引出し: 梁上の案内溝を前へ滑る。前端つまみ+ボールプランジャーで定位置保持"))
            P.append(B(f"DGX_Spark_{n}", 'device', xs, SPARK_Y0, zs, SPARK['w'], SPARK['d'], SPARK['h'], SPARK['mass'], "前面吸気・背面排気(仮定)", 'spark'))
            fz = zs + SPARK['h']/2 - FAN140['s']/2; fx = xs + SPARK['w']/2 - FAN140['s']/2
            P.append(B(f"140ファン_{n}", 'fan', fx, FAN_Y0, fz, FAN140['s'], FAN140['t'], FAN140['s'], FAN140['mass'], "NF-A14x25 G2", 'fan140', 'Noctua'))
            P.append(printed(f"導風ダクト_{n}", xs, DUCT_Y0, fz, SPARK['w'], SPARK_Y0-DUCT_Y0, FAN140['s'], 0.12,
                             "ファンと一体モジュール。梁へ差込み+つまみねじ1本"))
            P.append(B(f"排気確保_{n}", 'zone', xs+10, SPARK_Y0+SPARK['d'], zs+3, SPARK['w']-20, 20, SPARK['h']-6, 0, "背面排気20mm", 'airflow'))
    # ---- 下段: アダプタートンネル(前→後) ----
    T = TUNNEL
    seg = (T['x1']-T['x0'])/2
    for i in range(2):
        P.append(printed(f"アダプタートンネル_{i+1}", T['x0']+i*seg, T['y0'], T['z0'], seg, T['y1']-T['y0'], T['z1']-T['z0'], 0.10,
                         "2分割角筒(135x130x130)。前面は格子、後面に120ファン"))
    for i, x in enumerate((140.0, 251.0)):
        for j, z in enumerate((T['z0']+T['wall']+4, T['z0']+T['wall']+4+ADAPTER['h']+20)):
            P.append(B(f"電源アダプター_{i*2+j+1}", 'psu', x, T['y0']+13, z, ADAPTER['w'], ADAPTER['d'], ADAPTER['h'], ADAPTER['mass'], "AC前・USB-C後", 'in_tunnel'))
    fz = (T['z0']+T['z1'])/2 - FAN120['s']/2
    for i, x in enumerate((125.0, 245.0)):
        P.append(B(f"120ファン_排気{i+1}", 'fan', x, T['y1'], fz, FAN120['s'], FAN120['t'], FAN120['s'], FAN120['mass'], "トンネル後面から背面カバー下部へ排気", 'fan120', 'Noctua'))
    P.append(B("アダプター排気確保", 'zone', 125.0, T['y1']+FAN120['t'], fz, 240, OUT_Y1-REAR_LATTICE['t']-(T['y1']+FAN120['t'])-0.1, FAN120['s'], 0, "背面格子まで物を置かない", 'airflow'))
    # ---- 下段前: コントローラー電源・タップ ----
    for i in range(3):
        P.append(B(f"コントローラー電源_{i+1}", 'psu', 80+i*(CTRL_PSU['l']+20), 75, BASE_Z1, CTRL_PSU['l'], CTRL_PSU['w'], CTRL_PSU['h'], CTRL_PSU['mass'],
                   ["系統1:左列140x2", "系統2:右列140x2", "系統3:120x2"][i]+"(仮範囲)", 'psu'))
    P.append(B("電源タップ", 'psu', 35, 170, BASE_Z1, POWER_STRIP['l'], POWER_STRIP['w'], POWER_STRIP['h'], POWER_STRIP['mass'], "9口使用。外へ出るのはこの1本のACコードのみ", 'psu'))
    P.append(B("プラグ抜き差し空間", 'zone', 35, 160, BASE_Z1+POWER_STRIP['h'], POWER_STRIP['l'], 58, PLUG_KEEPOUT_H, 0, "プラグ+曲げ", 'work'))
    # ---- コントローラー6個: 内側前隅に集約、表示は前面窓越し ----
    cw, ct, cl = CTRL_ENVELOPE['w'], CTRL_ENVELOPE['h'], CTRL_ENVELOPE['l']
    for side, x in (("左", INNER_X0+2), ("右", INNER_X1-2-cw)):
        for lab, z0 in (("電源", 40.0), ("1段", 175.0), ("2段", 300.0)):
            P.append(B(f"コントローラー_{side}{lab}", 'ctrl', x, 24.0, z0, cw, ct, cl, CTRL_ENVELOPE['mass'],
                       "既存ケース+共通ドック(無変更)。印刷ブラケット(前向きL字)で側壁へ。表示とつまみが前向き", 'ctrl'))
            P.append(printed(f"コントローラーブラケット_{side}{lab}", x, 67.0, z0, cw, 4.0, cl, 1.0, "L字ブラケット: 共通ドックM4ピッチ28を受け、側壁へM4"))
            P.append(B(f"表示窓視界_{side}{lab}", 'zone', x, OUT_Y0+LATTICE['t']+0.1, z0, cw, 24.0-(OUT_Y0+LATTICE['t'])-0.2, cl, 0, "前面パネルの表示窓までの視線・つまみ操作空間", 'work'))
    # ---- スイッチ棚 ----
    for side, (x0, x1) in zip("左右", WALL_X):
        xx = x1 if side == "左" else x0-EXT
        P.append(sheet(f"スイッチ受けフランジ_{side}", 'frame', xx, CHASSIS_Y0+14, SWITCH_SHELF_Z+EXT-3, EXT, CY-28, 3.0, 3.0, "側壁の内曲げフランジ(3mm, 幅20)"))
    zp = SWITCH_SHELF_Z+EXT
    P.append(B("スイッチ受け板", 'frame', INNER_X0, CHASSIS_Y0+14, zp, INNER_X1-INNER_X0, CY-28, SWITCH_PLATE_T,
               (INNER_X1-INNER_X0)*(CY-28)*SWITCH_PLATE_T*AL*0.8, "3mm。フランジ上面に載せ下面M5x4", 'frame', 'A5052'))
    for side, x in (("左", INNER_X0+0.1), ("右", INNER_X1-3.5)):
        P.append(printed(f"スイッチ側面保持_{side}", x, SWITCH_Y0+60, zp+SWITCH_PLATE_T, 3.4, 150, 30, 1.0, "後部支持耳の穴位置(M)"))
    if state == "switch":
        sx = (INNER_X0+INNER_X1)/2-SWITCH['w']/2
        P.append(B("CRS812_DDQ", 'device', sx, SWITCH_Y0, zp+SWITCH_PLATE_T+SWITCH_FEET, SWITCH['w'], SWITCH['d'], SWITCH['h'], SWITCH['mass'], "端子面を背面へ", 'switch'))
        P.append(B("スイッチ端子操作空間", 'zone', sx, SWITCH_Y0+SWITCH['d'], zp+SWITCH_PLATE_T+SWITCH_FEET, SWITCH['w'], OUT_Y1-REAR_LATTICE['t']-(SWITCH_Y0+SWITCH['d'])-0.1, SWITCH['h'], 0, "ケーブル曲げ(背面カバー内)", 'work'))
        P.append(B("スイッチ電源・ファン交換空間", 'zone', sx, OUT_Y0+LATTICE['t']+0.1, zp+SWITCH_PLATE_T+SWITCH_FEET, SWITCH['w'], SWITCH_Y0-(OUT_Y0+LATTICE['t'])-0.1, SWITCH['h'], 0, "前面パネルを外して前から", 'work'))
    for c, x in enumerate((30.0, 255.0)):
        P.append(printed(f"余長トレー_{'左右'[c]}", x, 262, 396, 205, 112, 38, 0.25, "分岐ケーブル余長(R42以上の8の字)"))
    P.append(B("背面配線域", 'zone', INNER_X0, SPARK_Y0+SPARK['d']+20, TIER_BEAM_Z[0]+EXT, INNER_X1-INNER_X0, OUT_Y1-REAR_LATTICE['t']-(SPARK_Y0+SPARK['d']+20)-0.1, 210, 0, "リング/分岐ケーブル・USB-C(背面カバー内)", 'work'))
    for side, x in (("左", OUT_X0+SHELL_T+0.1), ("右", WALL_X[1][1]+0.1)):
        P.append(B(f"配線チャネル_{side}", 'zone', x, 30, BASE_Z1, WALL_X[0][0]-OUT_X0-SHELL_T-0.2, 400, 480, 0, "側壁と外装の間25mm: AC/DCの縦配線", 'work'))
    return P
