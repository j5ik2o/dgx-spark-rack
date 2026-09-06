import sys,json,hashlib
from pathlib import Path

def run(_context):
 root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'scripts'))
 import fusion_rack as rack
 rack.active()
 signature=rack.geometry_signature()
 validation=json.loads((root/'exports/fusion/validation.json').read_text())
 assert signature==validation['signature'],'Active Fusion document differs from saved baseline'
 out=root/'exports/freecad/source-parts';out.mkdir(parents=True,exist_ok=True)
 manager=rack.DESIGN.exportManager
 manifest={}
 for name,component in rack.parts().items():
  if name.startswith('REF_'):continue
  path=out/(name+'.step');assert not path.exists(),str(path)
  assert manager.execute(manager.createSTEPExportOptions(str(path),component))
  manifest[name]={'step':'source-parts/'+path.name,'volume_mm3':component.bRepBodies.item(0).volume*1000,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
 data={'fusion_version':rack.APP.version,'f3d_sha256':hashlib.sha256((root/'DGX-SPARK-RACK-FUSION-v1.f3d').read_bytes()).hexdigest(),'assembly_step':'exports/fusion/DGX-SPARK-RACK-FUSION-v1.step','parameters':signature['parameters'],'print_parts':manifest}
 (out.parent/'source_manifest.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'print_parts':len(manifest),'source_preserved':True}))
