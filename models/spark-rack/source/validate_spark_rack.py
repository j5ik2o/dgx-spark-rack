"""本体ラックの生成形状・配置・パラメーター変更を検証する。"""
from dataclasses import replace

import Part

from freecad_spark_rack import PRINT_PARTS, LAYOUTS, shapes, assembly_shapes


def dimensions(shape):
    b=shape.BoundBox
    return [b.XLength,b.YLength,b.ZLength]


def bounds(shape):
    b=shape.BoundBox
    return [getattr(b,axis+end) for axis in "XYZ" for end in ("Min","Max")]


def inspect_parts(parts):
    assert set(parts)==set(PRINT_PARTS)
    report={}
    for name,shape in parts.items():
        assert shape.isValid() and shape.isClosed() and len(shape.Solids)==1,name
        assert shape.Volume>0,name
        report[name]={"volume_mm3":shape.Volume,"dimensions_mm":dimensions(shape)}
    return report


def inspect_assembly(p,parts,columns,rows):
    items=assembly_shapes(p,parts,columns,rows,include_visual=False)
    overlaps=[]
    for i,(name,a) in enumerate(items):
        aa=a.BoundBox
        for other,b in items[i+1:]:
            bb=b.BoundBox
            if any(min(getattr(aa,axis+"Max"),getattr(bb,axis+"Max"))-
                   max(getattr(aa,axis+"Min"),getattr(bb,axis+"Min"))<=1e-6 for axis in "XYZ"):
                continue
            v=a.common(b).Volume
            if v>0.001:overlaps.append((name,other,v))
    assert not overlaps,overlaps
    whole=Part.makeCompound([s for _,s in assembly_shapes(p,parts,columns,rows)])
    assert len(whole.Solids)==29*columns*rows+4*columns*(rows-1)+2*(columns-1)*rows
    return {"solids":len(whole.Solids),"volume_mm3":whole.Volume,"dimensions_mm":dimensions(whole),
            "bounds_mm":bounds(whole),"overlaps":overlaps,
            "excluded_from_interference":"ファン内部とガードの簡略参照形状"}


def validate(p):
    parts=shapes(p)
    report={"parts":inspect_parts(parts),"layouts":{n:inspect_assembly(p,parts,*layout) for n,layout in LAYOUTS.items()}}
    changed=replace(p,module_width=p.module_width+4)
    new_parts=shapes(changed)
    assert abs(dimensions(new_parts['crossbar'])[0]-dimensions(parts['crossbar'])[0]-4)<1e-6
    enlarged=inspect_assembly(changed,new_parts,2,2)
    assert abs(enlarged['dimensions_mm'][0]-report['layouts']['four_units']['dimensions_mm'][0]-8)<1e-6
    report['width_change']=enlarged
    report['clearance_variants']={}
    for c in (0.2,0.4):
        variant=replace(p,fit_clearance=c)
        report['clearance_variants'][str(c)]=inspect_assembly(variant,shapes(variant),2,2)
    return report
