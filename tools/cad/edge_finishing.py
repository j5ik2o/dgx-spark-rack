"""外周の凸稜線を選んで面取りする。穴の円周・既存曲面・凹稜線は選ばない。"""
import FreeCAD as App
import Part

TOUCH_CHAMFER = 0.3
SMALL_CHAMFER = 0.2


def convex_plane_edges(shape, planes, minimum_length=1.0, allow_openings=False):
    """指定面と外接面が交わる外周を選択。通風窓の入口は明示した場合のみ含める。"""
    envelope=shape.optimalBoundingBox(False)
    adjacent = {}
    for face in shape.Faces:
        for edge in face.Edges:
            adjacent.setdefault(edge.hashCode(), []).append(face)
    selected = []
    for index, edge in enumerate(shape.Edges, 1):
        if type(edge.Curve).__name__ != 'Line' or edge.Length < minimum_length:
            continue
        bounds = edge.BoundBox
        matching_axes=[axis for axis,value in planes
                       if abs(getattr(bounds,axis+'Min')-value)<1e-6
                       and abs(getattr(bounds,axis+'Max')-value)<1e-6]
        if not matching_axes:
            continue
        # 切抜きの入口も立体としては凸稜線になり得る。外周との区別を別に行う。
        if not allow_openings and not any(
                other != axis and abs(getattr(bounds,other+'Min')-getattr(envelope,other+end))<1e-6
                and abs(getattr(bounds,other+'Max')-getattr(envelope,other+end))<1e-6
                for axis in matching_axes for other in 'XYZ' for end in ('Min','Max')):
            continue
        faces = adjacent.get(edge.hashCode(), [])
        if len(faces) != 2 or any(type(face.Surface).__name__ != 'Plane' for face in faces):
            continue
        point = edge.valueAt((edge.FirstParameter+edge.LastParameter)/2)
        normals = [face.normalAt(*face.Surface.parameter(point)) for face in faces]
        if abs(normals[0].dot(normals[1])) > 0.01:
            continue
        inward = normals[0]+normals[1]
        inward.normalize()
        if shape.isInside(point-inward*0.05,1e-7,False):
            selected.append((index,edge))
    return selected


def chamfer(shape, planes, size=TOUCH_CHAMFER, allow_openings=False):
    selected = convex_plane_edges(shape, planes, allow_openings=allow_openings)
    if not selected:
        raise ValueError('指定された面に面取り対象の凸稜線がありません')
    result = shape.makeChamfer(size,[edge for _,edge in selected])
    if not result.isValid() or len(result.Solids)!=1 or result.Volume<=0:
        raise ValueError('外周面取りの生成に失敗しました')
    return result.removeSplitter()


def extrema(shape, axes='XYZ'):
    bounds=shape.optimalBoundingBox(False)
    return [(axis,getattr(bounds,axis+end)) for axis in axes for end in ('Min','Max')]


def round_opening(shape, axis, coordinate, radius, size=0.3):
    edges=[e for e in shape.Edges if type(e.Curve).__name__=='Circle'
           and abs(e.Curve.Radius-radius)<1e-6
           and abs(getattr(e.BoundBox,axis+'Min')-coordinate)<1e-6
           and abs(getattr(e.BoundBox,axis+'Max')-coordinate)<1e-6]
    if not edges:raise ValueError('送風開口の縁を特定できません')
    result=shape.makeFillet(size,edges)
    if not result.isValid() or len(result.Solids)!=1:raise ValueError('送風開口のフィレットに失敗しました')
    return result.removeSplitter()


def chamfer_feature(doc, body, planes=(), size=TOUCH_CHAMFER, pin=False):
    """稜線番号を保持せず、寸法表変更後に幾何条件から再選択する。"""
    base=body.Tip
    selected=pin_edges(base.Shape) if pin else convex_plane_edges(base.Shape,planes)
    if not selected:raise ValueError(f'{body.Name}: 面取り対象がありません')
    bounds=base.Shape.optimalBoundingBox(False)
    selectors=[]
    for axis,value in planes:
        end='Min' if abs(getattr(bounds,axis+'Min')-value)<1e-6 else 'Max'
        if abs(getattr(bounds,axis+end)-value)>1e-6:
            raise ValueError('面取り基準は部品の外接面で指定してください')
        selectors.append(axis+end)
    feature=body.newObject('PartDesign::FeaturePython',body.Name+'TouchChamfer')
    feature.Label=f'外周 C{size:g}（接合穴の円周は保持）'
    feature.addProperty('App::PropertyLink','Source','Manufacturing')
    feature.Source=base
    feature.addProperty('App::PropertyStringList','Planes','Manufacturing')
    feature.Planes=selectors
    feature.addProperty('App::PropertyBool','PinEnds','Manufacturing')
    feature.PinEnds=pin
    feature.addProperty('App::PropertyLength','Size','Manufacturing')
    feature.Size=size
    feature.addProperty('App::PropertyLength','OpeningRadius','Manufacturing')
    feature.OpeningRadius=0
    feature.addProperty('App::PropertyInteger','FinishedEdges','Manufacturing')
    feature.Proxy=EdgeFinishProxy()
    doc.recompute()
    if feature.Shape.isNull() or not feature.Shape.isValid() or len(feature.Shape.Solids)!=1:
        raise ValueError(f'{body.Name}: 履歴付き面取りに失敗しました')
    base.Visibility=False
    body.Tip=feature
    return feature


class EdgeFinishProxy:
    def execute(self, obj):
        # 失敗時に古い有効形状が残って検査をすり抜けないよう、まず消去する。
        obj.Shape=Part.Shape()
        source=obj.Source.Shape
        bounds=source.optimalBoundingBox(False)
        planes=[(key[0],getattr(bounds,key)) for key in obj.Planes]
        obj.FinishedEdges=len(pin_edges(source) if obj.PinEnds else convex_plane_edges(source,planes))
        result=round_pin_ends(source,obj.Size.Value) if obj.PinEnds else chamfer(source,planes,obj.Size.Value)
        if obj.OpeningRadius.Value>0:
            result=round_opening(result,'Y',bounds.YMin,obj.OpeningRadius.Value)
        obj.Shape=result

    def dumps(self):
        return None

    def loads(self, state):
        pass


def pin_edges(shape):
    bounds=shape.optimalBoundingBox(False)
    edges=[(i,e) for i,e in enumerate(shape.Edges,1) if type(e.Curve).__name__=='Circle'
           and e.BoundBox.ZLength<1e-6
           and (abs(e.CenterOfMass.z-bounds.ZMin)<1e-6 or abs(e.CenterOfMass.z-bounds.ZMax)<1e-6)]
    if len(edges)!=2:raise ValueError('ピンの両端を特定できません')
    return edges


def round_pin_ends(shape, size=SMALL_CHAMFER):
    result=shape.makeChamfer(size,[e for _,e in pin_edges(shape)])
    if not result.isValid() or len(result.Solids)!=1:raise ValueError('ピン端面の面取りに失敗しました')
    return result.removeSplitter()
