import adsk.core,adsk.fusion,json,time
from pathlib import Path

def run(_context):
 app=adsk.core.Application.get();previous=app.activeDocument
 root=Path(__file__).resolve().parents[1]
 results=[]
 try:
  for i in range(3):
   options=app.importManager.createSTEPImportOptions(str(root/'exports/fusion/DGX-SPARK-RACK-FUSION-v1.step'))
   t=time.perf_counter();doc=app.importManager.importToNewDocument(options);elapsed=time.perf_counter()-t
   assert doc
   design=adsk.fusion.Design.cast(app.activeProduct)
   results.append({'seconds':elapsed,'bodies':sum(o.component.bRepBodies.count for o in design.rootComponent.allOccurrences)+design.rootComponent.bRepBodies.count})
   doc.close(False)
 finally:
  previous.activate()
 payload={'fusion_version':app.version,'operation':'importManager.importToNewDocument(STEP)','runs':results,'scope':'同じSTEPの新規文書への読み込み。起動・MCP通信・明示的描画更新は除外。キャッシュ未制御。'}
 (root/'comparison/freecad/fusion_step_timing.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(payload))
