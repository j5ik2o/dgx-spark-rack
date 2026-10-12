"""支持段の接合、受け面、固定ねじを実形状で確認する。造形用には出力しない。"""
import math
import FreeCAD as App
import Part

from switch_support_parameters import SUPPORT


def box(x, y, z, a, b, c):
    return Part.makeBox(a, b, c, App.Vector(x, y, z))


def bore(center, radius, length, axis, sign=1):
    direction = [0, 0, 0]; direction[axis] = sign
    return Part.makeCylinder(radius, length, App.Vector(*center), App.Vector(*direction))


def hex_nut(center, axis, sign=1):
    # 仮外形：二面幅7mm、厚さ3.2mm。購入品の実寸は未確認。
    u, v = [i for i in range(3) if i != axis]
    vertices = []
    for i in range(6):
        point = list(center); t = math.pi*i/3
        point[u] += 7/math.sqrt(3)*math.cos(t)
        point[v] += 7/math.sqrt(3)*math.sin(t)
        vertices.append(App.Vector(*point))
    direction = [0, 0, 0]; direction[axis] = sign*3.2
    solid = Part.Face(Part.makePolygon(vertices+vertices[:1])).extrude(App.Vector(*direction))
    return solid.cut(bore(center, 2.05, 3.2, axis, sign))


def build_shapes(p=SUPPORT):
    p.validate(); c=p.clearance; top=p.rail_top; bottom=top-28
    shapes = {}; fixtures = []; receiver_info = []

    def hardware(name, start, axis, length, nut_start, sign=1, washer=False):
        head_start = list(start); head_start[axis] -= sign*4
        shapes[name+'_screw'] = bore(start, 2, length, axis, sign).fuse(bore(head_start, 4, 4, axis, sign))
        shapes[name+'_nut'] = hex_nut(nut_start, axis, sign)
        fixtures.append({'name': name, 'axis': axis, 'start': start, 'length': length,
                         'nut_start': nut_start, 'nut_thickness': 3.2, 'sign': sign})
        if washer:
            wstart=list(start); wstart[axis]+=sign*0
            shapes[name+'_washer']=bore(wstart,4.5,1,axis,sign).cut(bore(wstart,2.25,1,axis,sign))

    # 下側の柱は上へ開いた受け穴。上側は梁の後から載せ、12×6mmの突起で位置決め。
    for side, x in (('left', -256), ('right', 228)):
        for end, y in (('front', -428), ('rear', 64)):
            name=f'column_{side}_{end}'
            lower=box(x,y,0,28,28,top)
            cap=box(x,y,top,28,28,420-top)
            peg_y=y+1 if end=='front' else y+21
            peg=box(x+8,peg_y,top,12,6,24)
            lower=lower.fuse(peg)
            cap=cap.cut(box(x+8-c,peg_y-c,top-1,12+2*c,6+2*c,25.3))
            root_y=y+20 if end=='front' else y
            tenon_y=y+8 if end=='front' else y+8
            lower=lower.cut(box(x-c,root_y-c,bottom,28+2*c,8+2*c,29))
            lower=lower.cut(box(x+8-c,tenon_y-c,bottom+8,12+2*c,12+2*c,21))
            # 柱と奥行梁を固定するねじ。頭は枠の内側、ナットは柱の中。
            sign=-1 if side=='left' else 1; inside=x+28 if side=='left' else x
            lock_y=tenon_y+6; lock_z=bottom+14
            start=[inside,lock_y,lock_z]; hole=[inside-sign,lock_y,lock_z]
            lower=lower.cut(bore(hole,2.25,30,0,sign))
            nut_x=inside+sign*20
            access_y=y-1 if end=='front' else y+9.7
            lower=lower.cut(box(min(nut_x,nut_x+sign*3.2)-c,access_y,lock_z-4.1,
                                 3.2+2*c,20,8.2))
            hardware(name+'_rail_lock',start,0,25,[nut_x,lock_y,lock_z],sign)
            # 上側の柱の抜け止めも内側から1本。受け板が通る高さを避ける。
            lock_y=peg_y+3; lock_z=top+18
            for label,shape in [('lower',lower),('upper',cap)]:
                shape=shape.cut(bore([inside-sign,lock_y,lock_z],2.25,30,0,sign))
                if label=='upper':
                    shape=shape.cut(box(min(nut_x,nut_x+sign*3.2)-c,access_y,lock_z-4.1,3.2+2*c,20,8.2))
                shapes[name+'_'+label]=shape.removeSplitter()
            hardware(name+'_cap_lock',[inside,lock_y,lock_z],0,25,[nut_x,lock_y,lock_z],sign)
            receiver_info.append((side,end,name))

    for side,x in (('left',-256),('right',228)):
        segments=[]; y=-400
        for i,length in enumerate((180,142,142)):
            s=box(x,y,bottom,28,length,28)
            if i<2:
                s=s.cut(box(x+8-c,y+length-24-c,bottom+4.3,12+2*c,25+c,29))
            if i>0:
                s=s.fuse(box(x+8,y-24,bottom+4.3,12,24,28-4.3-c))
            if i==0:
                s=s.fuse(box(x,-408,bottom,28,8,28-c)).fuse(box(x+8,-420,bottom+10,12,12,8))
            if i==2:
                s=s.fuse(box(x,64,bottom,28,8,28-c)).fuse(box(x+8,72,bottom+10,12,12,8))
            for yc in p.cross_centers_y:
                if side=='left':
                    s=s.cut(box(-236-c,yc-14-c,top-10,9+c,28+2*c,11))
                    s=s.cut(box(-248-c,yc-6-c,top-8,12+2*c,12+2*c,9))
                else:
                    s=s.cut(box(228-c,yc-14-c,top-10,8+2*c,28+2*c,11))
                    s=s.cut(box(236-c,yc-6-c,top-8,12+2*c,12+2*c,9))
            sign=-1 if side=='left' else 1; inside=x+28 if side=='left' else x
            for lock_y in (-414,78):
                s=s.cut(bore([inside-sign,lock_y,bottom+14],2.25,30,0,sign))
            segments.append(s.removeSplitter()); y+=length
        for i,s in enumerate(segments): shapes[f'rail_{side}_{i}']=s
        for i,junction in enumerate((-220,-78)):
            cx=x+14; cy=junction-12; start=[cx,cy,bottom-1]
            for index in (i,i+1):
                key=f'rail_{side}_{index}'
                shapes[key]=shapes[key].cut(bore([cx,cy,bottom-2],2.25,32,2))
                shapes[key]=shapes[key].cut(box(cx-4.1 if side=='left' else x-1,cy-4.1,bottom+12.7,19.1,8.2,3.8)).removeSplitter()
            hardware(f'rail_{side}_{i}_splice_lock',start,2,20,[cx,cy,bottom+13],washer=True)

    for i,yc in enumerate(p.cross_centers_y):
        z=top-p.cross_height; floor=z+4.3
        left=box(-220,yc-14,z,220,28,p.cross_height)
        right=box(0,yc-14,z,220,28,p.cross_height)
        left=left.fuse(box(-236,yc-14,top-10,16,28,10-c)).fuse(box(-248,yc-6,top-6,12,12,4))
        right=right.fuse(box(220,yc-14,top-10,16,28,10-c)).fuse(box(236,yc-6,top-6,12,12,4))
        left=left.cut(box(-24-c,yc-6-c,floor,25+c,12+2*c,p.cross_height))
        right=right.fuse(box(-24,yc-6,floor,24,12,p.cross_height-4.3-c))
        center_start=[0,yc,z-1]; center_nut=[0,yc,z+13]
        for side,s in [('left',left),('right',right)]:
            s=s.cut(bore([0,yc,z-2],2.25,p.cross_height+4,2))
            if side=='right':
                s=s.cut(box(-4.1,yc-15,z+12.7,8.2,19.1,3.8))
            if i==1:
                for fx in (-205,205):
                    s=s.cut(bore([fx,yc,z-1],2.25,p.cross_height+5,2))
                    s=s.cut(box(fx-4.1,yc-4.1,z+3.7,8.2,19.1,3.8))
            shapes[f'cross_{i}_{side}']=s.removeSplitter()
        hardware(f'cross_{i}_lock',center_start,2,20,center_nut,washer=True)
    for i,yc in enumerate(p.cross_centers_y):
        index=0 if yc<-220 else 2
        for side,cx in (('left',-234),('right',234)):
            rail_key=f'rail_{side}_{index}'; cross_key=f'cross_{i}_{side}'
            for key in (rail_key,cross_key):
                shapes[key]=shapes[key].cut(bore([cx,yc,bottom-1],2.25,31,2))
            access_x=-239 if side=='left' else 219
            shapes[cross_key]=shapes[cross_key].cut(box(access_x,yc-4.1,top-7.3,20,8.2,3.8)).removeSplitter()
            hardware(f'cross_{i}_{side}_end_lock',[cx,yc,bottom],2,25,[cx,yc,top-7])
    tray=box(-p.tray_width/2,p.tray_front_y,top,p.tray_width,p.tray_depth,p.tray_thickness)
    for x in (-205,205):
        y=p.cross_centers_y[1]
        tray=tray.cut(bore([x,y,top-1],2.25,p.tray_thickness+2,2))
        hardware('tray_lock_'+str(x),[x,y,top+p.tray_thickness],2,20,[x,y,top-p.cross_height+7.2],-1)
    shapes['tray']=tray.removeSplitter()
    return shapes,fixtures
