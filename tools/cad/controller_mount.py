"""両ラックとケースで共有する取付インターフェース。単位mm。"""
import math
import FreeCAD as App
import Part
from edge_finishing import chamfer

LENGTH = 100.0
WIDTH = 43.4  # ケース幅39.4mmに対して左右2mmずつの見付け
THICKNESS = 8.0
STANDOFF = 3.0
RACK_PITCH = 28.0
RACK_U = -42.0  # Sparkのドック上下端をZ=52/152、アダプター前端をY=-75へ揃える
CASE_PITCH = 92.0
EAR_THICKNESS = 4.0
CASE_COUNTERSINK_DEPTH = 1.5
CASE_COUNTERSINK_RADIUS = 3.2
OUTER_RADIUS = 4.0
WINDOW_RADIUS = 4.0
EAR_RADIUS = 3.0
EDGE_RADIUS = 0.4


def box(x,y,z,dx,dy,dz):
    return Part.makeBox(dx,dy,dz,App.Vector(x,y,z))


def hole(x,y,z,radius,height):
    return Part.makeCylinder(radius,height,App.Vector(x,y,z))


def vertical_edges(shape, height):
    return [e for e in shape.Edges if e.BoundBox.XLength < 1e-7
            and e.BoundBox.YLength < 1e-7 and abs(e.BoundBox.ZLength-height)<1e-7]


def rounded_plate(x,y,z,length,width,height,radius):
    shape=box(x,y,z,length,width,height)
    return shape.makeFillet(radius,vertical_edges(shape,height))


def dock():
    """U=ケース長手、V=幅、W=ラック面からケース側。M4頭は表面より沈む。"""
    s=rounded_plate(-LENGTH/2,-WIDTH/2,0,LENGTH,WIDTH,THICKNESS,OUTER_RADIUS)
    # 触れる外周だけを小さく丸め、締結面と穴の寸法は維持する。
    rims=[e for e in s.Edges if e.BoundBox.ZLength<1e-7]
    s=s.makeFillet(EDGE_RADIUS,rims)
    opening=rounded_plate(-22,-WIDTH/2+6,-1,60,WIDTH-12,THICKNESS+2,WINDOW_RADIUS)
    s=s.cut(opening)
    for v in (-RACK_PITCH/2,RACK_PITCH/2):
        s=s.fuse(hole(RACK_U,v,-STANDOFF,6,STANDOFF))
        s=s.cut(hole(RACK_U,v,-STANDOFF-1,2.25,THICKNESS+STANDOFF+2))
        s=s.cut(hole(RACK_U,v,3.5,4.2,THICKNESS))
    for u in (-CASE_PITCH/2,CASE_PITCH/2):
        s=s.cut(hole(u,0,-1,1.7,THICKNESS+2))
        r=5.8/math.sqrt(3)
        pts=[App.Vector(u+r*math.cos(i*math.pi/3),r*math.sin(i*math.pi/3),0) for i in range(7)]
        s=s.cut(Part.Face(Part.makePolygon(pts)).extrude(App.Vector(0,0,2.8)))
    # ここは非接合の通風窓だけが直線の入口稜線として該当する。
    return chamfer(s.removeSplitter(),[('Z',THICKNESS)],allow_openings=True)


def case_ears(shape, xmin, xmax, cy, bottom):
    """ケース底の外側の耳。基板下へねじ頭やナットを突出させない。"""
    cx=(xmin+xmax)/2
    for sign in (-1,1):
        lo,hi=(cx-LENGTH/2,xmin+2) if sign<0 else (xmax-2,cx+LENGTH/2)
        if hi<=lo: raise ValueError('ケースが共通ドックの外形を超えています')
        ear=box(lo,cy-6,bottom,hi-lo,12,EAR_THICKNESS)
        tip=lo if sign<0 else hi
        edges=[e for e in vertical_edges(ear,EAR_THICKNESS)
               if abs(e.CenterOfMass.x-tip)<1e-7]
        ear=ear.makeFillet(EAR_RADIUS,edges)
        top_edges=[e for e in ear.Edges if e.BoundBox.ZLength<1e-7
                   and abs(e.BoundBox.ZMin-bottom-EAR_THICKNESS)<1e-7]
        ear=ear.makeFillet(0.3,top_edges)
        shape=shape.fuse(ear)
        shape=shape.cut(hole(cx+sign*CASE_PITCH/2,cy,bottom-1,1.7,EAR_THICKNESS+2))
        shape=shape.cut(Part.makeCone(1.7,CASE_COUNTERSINK_RADIUS,CASE_COUNTERSINK_DEPTH,
                          App.Vector(cx+sign*CASE_PITCH/2,cy,bottom+EAR_THICKNESS-CASE_COUNTERSINK_DEPTH)))
    return shape.removeSplitter()


def case_mount_bolt(u):
    """M3×12、90度皿頭の参照形状。長さ12mmは頭を含み、頭頂は0.2mm沈む。"""
    top=THICKNESS+EAR_THICKNESS-0.2
    head_height=1.5
    shaft=hole(u,0,top-12,1.5,12-head_height)
    head=Part.makeCone(1.5,3.0,head_height,App.Vector(u,0,top-head_height))
    return shaft.fuse(head).removeSplitter()


def place(shape, origin, u, v, w):
    """右手系のドック座標をラック座標に変換する。"""
    if (App.Vector(*u).cross(App.Vector(*v))-App.Vector(*w)).Length > 1e-8:
        raise ValueError('ドック配置は右手系の直交座標で指定してください')
    m=App.Matrix()
    m.A11,m.A21,m.A31=u
    m.A12,m.A22,m.A32=v
    m.A13,m.A23,m.A33=w
    m.A14,m.A24,m.A34=origin
    result=shape.copy()
    result.Placement=App.Placement(m).multiply(result.Placement)
    return result


def hardware_bom():
    return {'dock_per_controller':1,'M4x25_socket_screws':2,'M4_nuts':2,
            'M3x12_90deg_countersunk_screws':2,'M3_nuts':2,
            'case_screw_head_max_diameter_mm':6.0,'case_screw_length_includes_head':True,
            'rack_screw_head_max_diameter_mm':8.0,'rack_screw_head_max_height_mm':4.0}
