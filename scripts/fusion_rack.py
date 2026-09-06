"""FusionのF3D正本を検査し、STEP・STL・プレビューを書き出す。単位式はmm。"""


import datetime


import json


import math


from pathlib import Path


import adsk.core as core


import adsk.fusion as fusion


ROOT = Path(__file__).resolve().parents[1]


OUT = ROOT / "exports" / "fusion"


OUT.mkdir(parents=True, exist_ok=True)


TAG = "dgx_spark_rack_fusion_v1"


APP = core.Application.get()


DESIGN = None


def expr(value):
    return f"{value} mm" if isinstance(value, (int, float)) else value


def ev(value):
    return DESIGN.unitsManager.evaluateExpression(expr(value), "mm")


def oc(items):
    result = core.ObjectCollection.create()
    for item in items:
        result.add(item)
    return result


def progress(stage, **extra):
    record = {"stage": stage, "at": datetime.datetime.now().astimezone().isoformat(), **extra}
    (OUT / "progress.json").write_text(json.dumps(record, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps(record, ensure_ascii=False), flush=True)


def active():
    global DESIGN
    DESIGN = fusion.Design.cast(APP.activeProduct)
    if not DESIGN or not DESIGN.rootComponent.attributes.itemByName(TAG, "owned"):
        raise RuntimeError("生成中のラック文書をアクティブにしてください。別の文書は変更しません。")
    return DESIGN.rootComponent


def group(role):
    root=active()
    return next(o.component for o in root.occurrences
                if o.component.attributes.itemByName(TAG,"role")
                and o.component.attributes.itemByName(TAG,"role").value==role)


def parts():
    library=group("library")
    return {o.component.attributes.itemByName(TAG,"part").value:o.component for o in library.occurrences
            if o.component.attributes.itemByName(TAG,"part")}


def assembly_bodies(include_visual=True):
    root=active()
    assembly_occ=next(o for o in root.occurrences if o.component.attributes.itemByName(TAG,"role")
                      and o.component.attributes.itemByName(TAG,"role").value=="assembly")
    prefix=assembly_occ.fullPathName+"+"
    result=[]
    for occurrence in root.allOccurrences:
        if not occurrence.fullPathName.startswith(prefix):
            continue
        attr=occurrence.component.attributes.itemByName(TAG,"part")
        if not attr or (not include_visual and attr.value in {"REF_FAN","REF_GUARD"}):
            continue
        for body in occurrence.component.bRepBodies:
            result.append((occurrence.fullPathName,body.createForAssemblyContext(occurrence)))
    return result


def extents_mm(bodies):
    boxes=[b.preciseBoundingBox for _,b in bodies]
    low=[min(getattr(b.minPoint,c) for b in boxes)*10 for c in "xyz"]
    high=[max(getattr(b.maxPoint,c) for b in boxes)*10 for c in "xyz"]
    return {"minimum_mm":low,"maximum_mm":high,"dimensions_mm":[b-a for a,b in zip(low,high)]}


def feature_health():
    bad=[]
    for item in DESIGN.timeline:
        entity=item.entity
        if hasattr(entity,"healthState") and int(entity.healthState)!=0:
            bad.append({"index":item.index,"name":entity.name,"message":entity.errorOrWarningMessage})
    return bad


def validate():
    active()
    DESIGN.computeAll()
    progress("validation_started")
    (OUT/"validation.json").write_text('{"status":"running"}\n')
    p=parts()
    report={"fusion_version":APP.version,"parameters":DESIGN.userParameters.count,
            "timeline_features":DESIGN.timeline.count,"parts":{},"existing_documents_modified":False}
    for name,comp in p.items():
        if name.startswith("REF_"):
            continue
        assert comp.bRepBodies.count==1,name
        body=comp.bRepBodies.item(0)
        box3=body.preciseBoundingBox
        dims=[(getattr(box3.maxPoint,c)-getattr(box3.minPoint,c))*10 for c in "xyz"]
        report["parts"][name]={"solid":body.isSolid,"volume_mm3":body.volume*1000,
            "native_dimensions_mm":dims,"sketches":comp.sketches.count,
            "fully_constrained_sketches":sum(s.isFullyConstrained for s in comp.sketches)}
        assert body.isSolid and max(dims)<=230.001,name
        assert all(s.isFullyConstrained for s in comp.sketches),name
    report["health_issues"]=feature_health()
    assert not report["health_issues"],report["health_issues"]
    report["assembly"]=extents_mm(assembly_bodies())
    w=DESIGN.userParameters.itemByName("ModuleWidth")
    original=w.expression
    before_crossbar=p["crossbar"].bRepBodies.item(0).preciseBoundingBox
    before_width=(before_crossbar.maxPoint.x-before_crossbar.minPoint.x)*10
    w.expression=f"({original})+4 mm"
    DESIGN.computeAll()
    after_crossbar=p["crossbar"].bRepBodies.item(0).preciseBoundingBox
    after_width=(after_crossbar.maxPoint.x-after_crossbar.minPoint.x)*10
    changed=extents_mm(assembly_bodies())
    changed_health=feature_health()
    w.expression=original
    DESIGN.computeAll()
    report["parameter_change_test"]={"parameter":"ModuleWidth","delta_mm":4,
        "crossbar_before_mm":before_width,"crossbar_after_mm":after_width,
        "assembly_before_mm":report["assembly"]["dimensions_mm"],
        "assembly_after_mm":changed["dimensions_mm"],"restored":w.expression==original,
        "health_issues":changed_health}
    assert abs(after_width-before_width-4)<0.001
    assert abs(changed["dimensions_mm"][0]-report["assembly"]["dimensions_mm"][0]-8)<0.001,report["parameter_change_test"]
    assert not changed_health,changed_health
    bodies=assembly_bodies(False)
    inp=DESIGN.createInterferenceInput(oc([body for _,body in bodies]))
    inp.areCoincidentFacesIncluded=False
    results=DESIGN.analyzeInterference(inp)
    overlaps=[]
    for result in results:
        volume=result.interferenceBody.volume*1000
        if volume>0.001:
            def entity_name(entity):
                context=entity.assemblyContext
                return (context.fullPathName+"/" if context else "")+entity.name
            overlaps.append({"one":entity_name(result.entityOne),"two":entity_name(result.entityTwo),"volume_mm3":volume})
    report["interference"]={"tested_bodies":len(bodies),"threshold_mm3":0.001,"overlaps":overlaps,
        "excluded":"ファン内部とガードの簡略参照形状"}
    report["physical_validation"]="実機の足・通風口・コネクター、強度、冷却性能は未検証"
    report["status"]="passed" if not overlaps else "failed"
    report["signature"]=geometry_signature()
    (OUT/"validation.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    assert not overlaps,overlaps
    progress("validation_complete",parts=len(report["parts"]),tested_bodies=len(bodies),overlaps=len(overlaps),
             assembly_mm=report["assembly"]["dimensions_mm"])


def write_stls():
    import struct
    active()
    directory=OUT/"stl"
    directory.mkdir(exist_ok=True)
    rotations={"side_L":("Y",math.pi/2),"side_R":("Y",-math.pi/2),
        "locking_pin":("X",math.pi),"bridge_clip":("X",math.pi/2),"fan_cassette":("X",math.pi/2),
        "fit_coupon_020":("Y",math.pi/2),"fit_coupon_030":("Y",math.pi/2),"fit_coupon_040":("Y",math.pi/2)}
    records={}
    for name,comp in parts().items():
        if name.startswith("REF_"):
            continue
        calculator=comp.bRepBodies.item(0).meshManager.createMeshCalculator()
        calculator.surfaceTolerance=0.002
        mesh=calculator.calculate()
        transform=core.Matrix3D.create()
        if name in rotations:
            axis,angle=rotations[name]
            vector={"X":core.Vector3D.create(1,0,0),"Y":core.Vector3D.create(0,1,0)}[axis]
            transform.setToRotation(angle,vector,core.Point3D.create(0,0,0))
        coords=[]
        for point in mesh.nodeCoordinates:
            point.transformBy(transform)
            coords.append([v*10 for v in point.asArray()])
        minimum=[min(p[i] for p in coords) for i in range(3)]
        coords=[[p[i]-minimum[i] for i in range(3)] for p in coords]
        indices=mesh.nodeIndices
        path=directory/(name+".stl")
        with path.open("wb") as file:
            file.write(b"DGX Spark rack - native Fusion BRep tessellation - mm".ljust(80,b" "))
            file.write(struct.pack("<I",mesh.triangleCount))
            for i in range(0,len(indices),3):
                a,b,c=[coords[index] for index in indices[i:i+3]]
                u=[b[j]-a[j] for j in range(3)];v=[c[j]-a[j] for j in range(3)]
                n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
                length=math.sqrt(sum(t*t for t in n))
                n=[t/length for t in n] if length else [0,0,0]
                file.write(struct.pack("<12fH",*n,*a,*b,*c,0))
        records[name]={"dimensions_mm":[max(p[i] for p in coords) for i in range(3)],
            "triangles":mesh.triangleCount,"bytes":path.stat().st_size}
    (OUT/"stl_manifest.json").write_text(json.dumps(records,ensure_ascii=False,indent=2)+"\n")
    progress("stl_complete",parts=len(records))


def hide_annotations():
    active()
    for comp in DESIGN.allComponents:
        comp.isJointsFolderLightBulbOn=False
        comp.isJointOriginsFolderLightBulbOn=False
        comp.isOriginFolderLightBulbOn=False
        comp.isConstructionFolderLightBulbOn=False
        comp.isSketchFolderLightBulbOn=False
        for joint in comp.joints:
            joint.isLightBulbOn=False
        for origin in comp.jointOrigins:
            origin.isLightBulbOn=False
        for sketch in comp.sketches:
            sketch.isVisible=False


def geometry_signature():
    return {"parameters":{p.name:p.expression for p in DESIGN.userParameters},
            "timeline":DESIGN.timeline.count,
            "part_volumes":{name:[round(b.volume*1000,3) for b in comp.bRepBodies] for name,comp in parts().items()},
            "assembly_mm":[round(n,4) for n in extents_mm(assembly_bodies())["dimensions_mm"]]}


def style():
    active()
    p=parts()
    source=p["side_L"].bRepBodies.item(0).appearance
    styles={"frame":(130,138,148),"pin":(140,174,113),"dgx":(205,164,87),"fan":(80,86,95),"metal":(210,215,224)}
    appearances={}
    for name,rgb in styles.items():
        label="DGX_外観のみ_"+name
        app=DESIGN.appearances.itemByName(label)
        if not app:
            app=DESIGN.appearances.addByCopy(source,label)
        for identifier in ("metal_f0","surface_albedo"):
            prop=core.ColorProperty.cast(app.appearanceProperties.itemById(identifier))
            if prop:
                prop.value=core.Color.create(*(rgb if identifier=="metal_f0" else (255,255,255)),255)
        rough=core.FloatProperty.cast(app.appearanceProperties.itemById("surface_roughness"))
        if rough:
            rough.value=0.5 if name in {"frame","pin","fan"} else 0.3
        appearances[name]=app
    for name,comp in p.items():
        key="frame"
        if name in {"locking_pin","stack_locator","bridge_clip"}:key="pin"
        elif name=="REF_DGX":key="dgx"
        elif name=="REF_FAN":key="fan"
        elif name in {"REF_GUARD","REF_SCREW","REF_NUT"}:key="metal"
        for body in comp.bRepBodies:
            body.appearance=appearances[key]
    hide_annotations()
    APP.activeViewport.fit()
    progress("style_complete",note="外観色のみ。物性による強度・熱解析は未実施。")


def export():
    active()
    report=json.loads((OUT/"validation.json").read_text())
    assert report["status"]=="passed"
    assert report["signature"]==geometry_signature(),"形状が検査時から変わっています。再検査してください。"
    hide_annotations()
    write_stls()
    manager=DESIGN.exportManager
    f3d=ROOT/"DGX-SPARK-RACK-FUSION-v1.f3d"
    step=OUT/"DGX-SPARK-RACK-FUSION-v1.step"
    assert manager.execute(manager.createFusionArchiveExportOptions(str(f3d)))
    assert manager.execute(manager.createSTEPExportOptions(str(step),group("assembly")))
    APP.activeViewport.fit()
    APP.activeViewport.saveAsImageFile(str(OUT/"four_units.png"),1600,1200)
    progress("export_complete",f3d=str(f3d),step=str(step),f3d_bytes=f3d.stat().st_size,step_bytes=step.stat().st_size)


def layout(name):
    active()
    choices={"single":(1,1),"vertical":(1,2),"horizontal":(2,1),"four":(2,2)}
    cols,rows=choices[name]
    root=DESIGN.rootComponent
    assembly_occ=next(o for o in root.occurrences if o.component.attributes.itemByName(TAG,"role")
                      and o.component.attributes.itemByName(TAG,"role").value=="assembly")
    prefix=assembly_occ.fullPathName+"+"
    visible_units=0
    for occurrence in root.allOccurrences:
        if not occurrence.fullPathName.startswith(prefix):
            continue
        native=occurrence.nativeObject or occurrence
        marker=native.attributes.itemByName(TAG,"layout")
        if marker:
            row,col=[int(n) for n in marker.value.split(",")]
            occurrence.isLightBulbOn=row<rows and col<cols
            visible_units+=int(row<rows and col<cols)
        part=occurrence.component.attributes.itemByName(TAG,"part")
        if part and part.value=="stack_locator":
            occurrence.isLightBulbOn=rows==2 and (cols==2 or occurrence.transform2.translation.x<0)
        elif part and part.value=="bridge_clip":
            occurrence.isLightBulbOn=cols==2 and (rows==2 or occurrence.transform2.translation.z<ev("FrameHeight"))
    assert visible_units==cols*rows,(name,visible_units)
    APP.activeViewport.refresh()
    APP.activeViewport.fit()


def previews():
    for name,file in (("single","single.png"),("vertical","two_vertical.png"),
                      ("horizontal","two_horizontal.png"),("four","four_units.png")):
        layout(name)
        APP.activeViewport.saveAsImageFile(str(OUT/file),1600,1200)
    progress("previews_complete")


def roundtrip():
    import hashlib
    active()
    expected=geometry_signature()
    source=ROOT/"DGX-SPARK-RACK-FUSION-v1.f3d"
    options=APP.importManager.createFusionArchiveImportOptions(str(source))
    document=APP.importManager.importToNewDocument(options)
    assert document
    active()
    actual=geometry_signature()
    assert actual==expected,{"expected":expected,"actual":actual}
    assert not feature_health(),feature_health()
    report={"status":"passed","file_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
            "parameters":len(actual["parameters"]),"timeline_features":actual["timeline"],
            "geometry_signature_retained":True,"cloud_save_performed":False}
    (OUT/"roundtrip.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    hide_annotations()
    APP.activeViewport.fit()
    progress("roundtrip_complete",**report)
