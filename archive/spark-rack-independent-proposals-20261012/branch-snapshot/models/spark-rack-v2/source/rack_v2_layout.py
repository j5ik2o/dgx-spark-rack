# -*- coding: utf-8 -*-
"""案Aの部品配置(直方体近似)。FreeCADに依存しない純Python。build/描画/検査で共有。

kind: frame/plate/printed/device/fan/psu/ctrl/zone
zone は実体ではなく、作業空間・ケーブル曲げ・吸排気・余長の確保範囲(干渉検査の相手)。
"""
from rack_v2_parameters import *

def B(name, kind, x, y, z, dx, dy, dz, mass=0.0, note="", group="", material=""):
    return dict(name=name, kind=kind, box=[x, y, z, dx, dy, dz], mass=mass,
                note=note, group=group, material=material)

EXT_KG_PER_MM = 0.00050   # 2020押出材 約0.5kg/m (P: 一般値)
AL_DENS = 2.68e-6         # kg/mm3 A5052
PETG_DENS = 1.27e-6 * 0.45  # 充填率45%相当の見かけ密度(A)

def ext(name, x, y, z, dx, dy, dz, note=""):
    L = max(dx, dy, dz)
    return B(name, 'frame', x, y, z, dx, dy, dz, L * EXT_KG_PER_MM, note, 'frame', '2020アルミ押出材')

def printed(name, x, y, z, dx, dy, dz, fill=0.35, note="", group="printed"):
    return B(name, 'printed', x, y, z, dx, dy, dz, dx*dy*dz*PETG_DENS*fill, note, group, 'PETG/ASA(要選定)')

def parts(state="switch"):
    """state: 'switch'(完成形) または 'ring'(途中状態: スイッチと分岐ケーブル無し)"""
    P = []
    # --- 柱4本(足の上 Z=8〜540) ---
    for ix, x in enumerate((0, W-EXT)):
        for iy, y in enumerate((0, D-EXT)):
            P.append(ext(f"柱_{'左右'[ix]}{'前後'[iy]}", x, y, FOOT_H, EXT, EXT, H-FOOT_H, "端面タップM5, 梁は内側ブラインドジョイント"))
            P.append(printed(f"脚_{'左右'[ix]}{'前後'[iy]}", x-2, y-2, 0, EXT+4, EXT+4, FOOT_H, 1.0, "防振TPU脚(柱下面M5で固定)", 'printed'))
    # --- 水平梁: 下枠・Spark段・スイッチ棚・天枠 ---
    def ring_level(tag, z, front_back=True, sides=True):
        out = []
        if front_back:
            out.append(ext(f"{tag}_前梁", EXT, 0, z, W-2*EXT, EXT, EXT))
            out.append(ext(f"{tag}_後梁", EXT, D-EXT, z, W-2*EXT, EXT, EXT))
        if sides:
            out.append(ext(f"{tag}_左側梁", 0, EXT, z, EXT, D-2*EXT, EXT))
            out.append(ext(f"{tag}_右側梁", W-EXT, EXT, z, EXT, D-2*EXT, EXT))
        return out
    P += ring_level("下枠", FOOT_H)
    P += ring_level("天枠", H-EXT)
    P += ring_level("スイッチ棚", SWITCH_SHELF_Z)
    P.append(B("底板", 'plate', EXT, EXT, FOOT_H+EXT, W-2*EXT, D-2*EXT, 3, (W-2*EXT)*(D-2*EXT)*3*AL_DENS*0.85,
               "A5052 3mm, 通風穴(質量15%減で計上)", 'frame', 'A5052'))
    for t, zb in enumerate(TIER_BEAM_Z):
        lv = t+1
        P.append(ext(f"{lv}段_左側梁", 0, EXT, zb, EXT, D-2*EXT, EXT))
        P.append(ext(f"{lv}段_右側梁", W-EXT, EXT, zb, EXT, D-2*EXT, EXT))
        P.append(ext(f"{lv}段_受け梁前", EXT, SPARK_Y0, zb, W-2*EXT, EXT, EXT, "トレー前端の段差受け"))
        P.append(ext(f"{lv}段_受け梁後", EXT, SPARK_Y0+SPARK['d']-EXT, zb, W-2*EXT, EXT, EXT, "トレー後端の段差受け"))
        ztray = zb+EXT
        zs = ztray+TRAY_T
        for c, xs in enumerate(SPARK_X):
            n = f"{lv}段{'左右'[c]}"
            P.append(printed(f"Sparkトレー_{n}", xs-5, SPARK_Y0, ztray, SPARK['w']+10, SPARK['d'], TRAY_T, 0.6,
                             "梁上面の段差で荷重受け、下面からM5で梁スロットへ抜け止め"))
            P.append(B(f"DGX_Spark_{n}", 'device', xs, SPARK_Y0, zs, SPARK['w'], SPARK['d'], SPARK['h'], SPARK['mass'],
                       "前面吸気・背面排気/端子(公開参考, 要実物確認)", 'spark'))
            fz = zs + SPARK['h']/2 - FAN140['s']/2
            fx = xs + SPARK['w']/2 - FAN140['s']/2
            P.append(B(f"140ファン_{n}", 'fan', fx, FAN_Y0, fz, FAN140['s'], FAN140['t'], FAN140['s'], FAN140['mass'],
                       "NF-A14x25 G2 PWM。Spark前面へ押込み", 'fan140', 'Noctua'))
            P.append(printed(f"導風ダクト_{n}", xs, DUCT_Y0, fz, SPARK['w'], SPARK_Y0-DUCT_Y0, FAN140['s'], 0.12,
                             "140角→Spark前面吸気口(150x約46)へ絞る。ファンとM4×4で一体の着脱モジュール"))
            # 吸気/排気確保ゾーン
            P.append(B(f"排気確保_{n}", 'zone', xs+10, SPARK_Y0+SPARK['d'], zs+3, SPARK['w']-20, 20, SPARK['h']-6, 0,
                       "Spark背面排気: 20mmはケーブル/コネクター禁止(端子部を除く仮範囲)", 'airflow'))
    # --- 下段: アダプタートンネル(後) ---
    T = TUNNEL
    tw = T['wall']
    seglen = (W-2*EXT)/3
    for i in range(3):
        P.append(printed(f"アダプタートンネル_{i+1}", EXT+i*seglen, T['y0'], T['z0'], seglen, T['y1']-T['y0'], T['z1']-T['z0'], 0.10,
                         "3分割の角筒(150x130x130)。内部に棚板、端部は段差はめ合い"))
    # トンネル内部を空洞として扱うため、内部機器は'device'でもトンネルとの干渉を除外する(グループ指定)
    ax = [EXT+FAN120['t']+60, EXT+FAN120['t']+60+ADAPTER['w']+20]
    ax = [140.0, 251.0]
    for i, x in enumerate(ax):
        for j, z in enumerate((T['z0']+tw+4, T['z0']+tw+4+ADAPTER['h']+20)):
            P.append(B(f"電源アダプター_{i*2+j+1}", 'psu', x, T['y0']+13, z, ADAPTER['w'], ADAPTER['d'], ADAPTER['h'], ADAPTER['mass'],
                       "240W純正。AC(C6)を前(-Y)、USB-Cを後(+Y)", 'in_tunnel'))
    fz = (T['z0']+T['z1'])/2 - FAN120['s']/2
    fy = (T['y0']+T['y1'])/2 - FAN120['s']/2
    P.append(B("120ファン_吸気左", 'fan', EXT, fy, fz, FAN120['t'], FAN120['s'], FAN120['s'], FAN120['mass'], "NF-A12x25 G2。左側面から吸気", 'in_tunnel', 'Noctua'))
    P.append(B("120ファン_排気右", 'fan', W-EXT-FAN120['t'], fy, fz, FAN120['t'], FAN120['s'], FAN120['s'], FAN120['mass'], "右側面へ排気(Spark前面吸気から遠い後方側)", 'in_tunnel', 'Noctua'))
    P.append(B("右排気確保", 'zone', W+SIDE_PANEL_T+0.1, fy, fz, 60, FAN120['s'], FAN120['s'], 0, "右側面外60mmに物を置かない", 'airflow'))
    P.append(B("左吸気確保", 'zone', -SIDE_PANEL_T-60.1, fy, fz, 60, FAN120['s'], FAN120['s'], 0, "左側面外60mmに物を置かない", 'airflow'))
    # --- 下段前: コントローラー電源3個・電源タップ ---
    z0 = BAY_Z0
    for i in range(3):
        P.append(B(f"コントローラー電源_{i+1}", 'psu', 40+i*(CTRL_PSU['l']+30), 60, z0, CTRL_PSU['l'], CTRL_PSU['w'], CTRL_PSU['h'], CTRL_PSU['mass'],
                   ["系統1:140ファン左列2個", "系統2:140ファン右列2個", "系統3:120ファン2個"][i]+"。12V3A据置型の仮範囲(M)。面ファスナー+印刷クリップで底板固定", 'psu'))
    P.append(B("電源タップ", 'psu', 35, 170, z0, POWER_STRIP['l'], POWER_STRIP['w'], POWER_STRIP['h'], POWER_STRIP['mass'],
               "10口以上・上向き口(仮)。9口使用", 'psu'))
    P.append(B("プラグ抜き差し空間", 'zone', 35, 160, z0+POWER_STRIP['h'], POWER_STRIP['l'], 58, PLUG_KEEPOUT_H, 0, "プラグ+コード曲げ+指", 'work'))
    # --- 側板(2mm A5052, 柱外面) とコントローラー6個 ---
    for side, x in (("左", -SIDE_PANEL_T), ("右", W)):
        P.append(B(f"側板_{side}", 'plate', x, EXT, BAY_Z0, SIDE_PANEL_T, D-2*EXT, SWITCH_SHELF_Z-BAY_Z0, (D-2*EXT)*(SWITCH_SHELF_Z-BAY_Z0)*2*AL_DENS*0.75,
                   "2mm A5052。柱スロットへ内側からT形ナット固定。120ファン開口・通風穴", 'frame', 'A5052'))
        xo = x-CTRL_ENVELOPE['h'] if side == "左" else x+SIDE_PANEL_T
        for k, (zc, lab) in enumerate(((TIER_BEAM_Z[0]+EXT+TRAY_T+25, "1段"), (TIER_BEAM_Z[1]+EXT+TRAY_T+25, "2段"), (90.0, "電源"))):
            P.append(B(f"コントローラー_{side}{lab}", 'ctrl', xo, 30, zc-CTRL_ENVELOPE['l']/2, CTRL_ENVELOPE['h'], CTRL_ENVELOPE['w'], CTRL_ENVELOPE['l'], CTRL_ENVELOPE['mass'],
                       "既存ケース+共通ドック(M4ピッチ28)をそのまま使用。ケース長手=縦", 'ctrl'))
            P.append(B(f"コントローラー操作空間_{side}{lab}", 'zone', xo + (-30 if side=="左" else CTRL_ENVELOPE['h']), 30, zc-CTRL_ENVELOPE['l']/2, 30, CTRL_ENVELOPE['w'], CTRL_ENVELOPE['l'], 0, "表示・つまみ・端子操作", 'work'))
    # --- スイッチ棚 ---
    zp = SWITCH_SHELF_Z+EXT
    P.append(B("スイッチ受け板", 'plate', EXT, EXT, zp, W-2*EXT, D-2*EXT, SWITCH_PLATE_T, (W-2*EXT)*(D-2*EXT)*SWITCH_PLATE_T*AL_DENS*0.8,
               "A5052 3mm。左右側梁上面に載せ、下面からM5×4で抜け止め。下段への熱を遮る", 'frame', 'A5052'))
    for side, x in (("左", EXT), ("右", W-EXT-3.5)):
        P.append(printed(f"スイッチ側面保持_{side}", x, SWITCH_Y0+60, zp+SWITCH_PLATE_T, 3.5, 150, 30, 1.0,
                         "後部支持耳の穴位置(M)で筐体側面を保持。受け板へ下面ねじ"))
    if state == "switch":
        P.append(B("CRS812_DDQ", 'device', (W-SWITCH['w'])/2, SWITCH_Y0, zp+SWITCH_PLATE_T+SWITCH_FEET, SWITCH['w'], SWITCH['d'], SWITCH['h'], SWITCH['mass'],
                   "端子面を背面(+Y)へ。前面取付耳は外す。電源2/ファンは前側から交換", 'switch'))
        P.append(B("スイッチ端子操作空間", 'zone', (W-SWITCH['w'])/2, SWITCH_Y0+SWITCH['d'], zp+SWITCH_PLATE_T+SWITCH_FEET, SWITCH['w'], 90, SWITCH['h'], 0,
                   "QSFP-DD/QSFP56のラッチ・曲げ(柱外へ出る範囲を含む)", 'work'))
        P.append(B("スイッチ電源・ファン交換空間", 'zone', (W-SWITCH['w'])/2, -60, zp+SWITCH_PLATE_T+SWITCH_FEET, SWITCH['w'], SWITCH_Y0+60, SWITCH['h'], 0,
                   "AC入力2本・ホットスワップ電源/ファン引出し", 'work'))
    # --- 余長トレー(背面上部) ---
    for c, x in enumerate((30.0, 255.0)):
        P.append(printed(f"余長トレー_{'左右'[c]}", x, 262, 396, 205, 112, 38, 0.25,
                         "分岐ケーブル枝の余長をR42以上の8の字で収納。排気の上・吸気の反対側"))
    # --- ケーブル経路・作業空間 ---
    P.append(B("背面配線域", 'zone', EXT, SPARK_Y0+SPARK['d']+20, TIER_BEAM_Z[0]+EXT, W-2*EXT, D-EXT-(SPARK_Y0+SPARK['d']+20), 210, 0,
               "リング/分岐ケーブルのコネクター・曲げ(R42)・ラッチ操作", 'work'))
    return P
