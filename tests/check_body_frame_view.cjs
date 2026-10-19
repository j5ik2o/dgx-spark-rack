// 正本から生成した本体連結案の表示と、固定取付の見え方を確認する。
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const crypto=require('node:crypto');
const {pathToFileURL}=require('node:url');
const {chromium}=require('playwright');
let browser;
(async()=>{
  const folder=path.resolve(process.argv[2]);
  const report=JSON.parse(fs.readFileSync(path.join(folder,'validation.json')));
  assert.equal(report.status,'passed');
  assert.equal(report.physical_validation,false);
  assert.equal(report.manufacturing_geometry,false);
  assert.equal(report.reopened,true);
  assert.equal(report.fan_straight_removal.length,6);
  assert.equal(report.switch_retention.bands,2);
  assert.equal(report.switch_retention.seismic_rating_verified,false);
  assert.equal(report.screwless_assembly.assembly_screws,0);
  assert.equal(report.screwless_assembly.assembly_nuts,0);
  assert.equal(report.assembly_order.status,'passed');
  assert.equal(report.assembly_order.finger_access.status,'passed');
  assert.equal(report.assembly_order.finger_access.key_grips,20);
  assert.equal(report.assembly_order.finger_access.release_reservations.length,16);
  const printPlan=JSON.parse(fs.readFileSync(path.join(folder,'print-plan.json')));
  assert.equal(printPlan.printed_part_count,81);
  assert.equal(printPlan.minimum_key_width_mm,1.8);
  assert.equal(printPlan.slicer_validated,false);
  const supportPlan=JSON.parse(fs.readFileSync(path.join(folder,'support-plan.json')));
  assert.equal(supportPlan.printed_parts,81);
  assert.ok(supportPlan.region_count>0);
  assert.equal(supportPlan.removal_steps,supportPlan.region_count);
  assert.equal(supportPlan.slicer_validated,false);
  browser=await chromium.launch({headless:true});
  const page=await browser.newPage({viewport:{width:1300,height:1000}});
  const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(pathToFileURL(path.join(folder,'body-frame.html')).href);
  await page.waitForFunction(()=>!!window.bodyFrameState);
  assert.ok((await page.locator('#size').textContent()).includes(String(report.overall_size_mm[0])));
  assert.equal(await page.locator('#inventory tr').count(),8);
  for(const view of ['iso','front','back','side','top']){
    await page.locator('[data-view="'+view+'"]').click();
    assert.equal(await page.evaluate(()=>bodyFrameState.view),view);
    assert.ok(await page.evaluate(()=>bodyFrameState.triangles>500));
    await page.locator('#drawing').screenshot({path:path.join(folder,'body-frame-'+view+'.png')});
  }
  await page.locator('#core-only').check();
  assert.ok(await page.evaluate(()=>bodyFrameState.visibleNames.every(n=>n.startsWith('core_')||/^spark_\d_\d$/.test(n))));
  assert.equal(await page.evaluate(()=>bodyFrameState.visibleKinds.filter(k=>k==='spark').length),4);
  await page.locator('[data-view="iso"]').click();
  await page.locator('#drawing').screenshot({path:path.join(folder,'body-frame-core.png')});
  await page.locator('#core-only').uncheck();
  await page.locator('#fans').uncheck();
  assert.ok(await page.evaluate(()=>bodyFrameState.visibleKinds.every(n=>!['fan','fan_holder','fan_pin'].includes(n))));
  await page.locator('#drawing').screenshot({path:path.join(folder,'body-frame-without-fans.png')});
  await page.locator('#fans').check();
  await page.locator('#cables').uncheck();
  assert.ok(await page.evaluate(()=>bodyFrameState.visibleKinds.every(k=>!k.startsWith('cable_')||['cable_mount','cable_storage'].includes(k))));
  await page.locator('#cables').check();
  await page.locator('#storage').uncheck();
  assert.ok(await page.evaluate(()=>!bodyFrameState.visibleKinds.includes('cable_storage')));
  await page.locator('#storage').check();
  await page.locator('#external').uncheck();
  assert.ok(await page.evaluate(()=>!bodyFrameState.visibleKinds.includes('external_reservation')));
  await page.locator('#external').check();
  await page.locator('#routing-only').check();
  assert.ok(await page.evaluate(()=>bodyFrameState.visibleKinds.every(k=>k.startsWith('cable_')||['body_connector','external_reservation'].includes(k))));
  await page.locator('#drawing').screenshot({path:path.join(folder,'body-frame-routing.png')});
  await page.locator('#routing-only').uncheck();
  await page.locator('#switch-only').check();
  assert.equal(await page.evaluate(()=>bodyFrameState.switchOnly),true);
  assert.equal(await page.evaluate(()=>bodyFrameState.visibleKinds.filter(k=>k==='switch_band').length),2);
  assert.ok(await page.evaluate(()=>bodyFrameState.visibleNames.includes('crs812')));
  await page.locator('#drawing').screenshot({path:path.join(folder,'body-frame-switch-retention.png')});
  await page.locator('#switch-only').uncheck();
  await page.locator('#joint-only').check();
  assert.equal(await page.evaluate(()=>bodyFrameState.jointOnly),true);
  assert.equal(await page.evaluate(()=>bodyFrameState.visibleNames.length),3);
  assert.ok((await page.locator('#screwless-summary').textContent()).includes('ビス0本・ナット0個'));
  await page.locator('#drawing').screenshot({path:path.join(folder,'body-frame-joinery.png')});
  await page.locator('#joint-only').uncheck();
  await page.locator('#assembly-only').check();
  assert.equal(await page.evaluate(()=>bodyFrameState.assemblyOnly),true);
  assert.equal(await page.locator('#assembly-step option').count(),report.assembly_order.bench_join_operations+report.assembly_order.mounting_operations);
  await page.locator('#assembly-progress').evaluate(e=>{e.value=0;e.dispatchEvent(new Event('input',{bubbles:true}));});
  const assemblyStart=await page.locator('#drawing').screenshot();
  await page.locator('#assembly-progress').evaluate(e=>{e.value=100;e.dispatchEvent(new Event('input',{bubbles:true}));});
  assert.notEqual(assemblyStart.toString('base64'),(await page.locator('#drawing').screenshot()).toString('base64'));
  await page.locator('#drawing').screenshot({path:path.join(folder,'body-frame-assembly-bench.png')});
  await page.locator('#assembly-next').click();assert.equal(await page.evaluate(()=>bodyFrameState.assemblyIndex),1);
  await page.locator('#assembly-prev').click();assert.equal(await page.evaluate(()=>bodyFrameState.assemblyIndex),0);
  await page.locator('#access-only').check();
  assert.equal(await page.evaluate(()=>bodyFrameState.accessOnly),true);
  assert.equal(await page.evaluate(()=>bodyFrameState.visibleKinds.filter(k=>k==='operation_space').length),2);
  for(let index=0;index<report.assembly_order.bench_join_operations;index++){
    await page.locator('#assembly-step').selectOption(String(index));
    assert.equal(await page.evaluate(()=>bodyFrameState.visibleKinds.filter(k=>k==='operation_space').length),2);
  }
  await page.locator('#assembly-step').selectOption('8');
  await page.locator('#drawing').screenshot({path:path.join(folder,'body-frame-finger-access.png')});
  await page.locator('#assembly-progress').evaluate(e=>{e.value=85;e.dispatchEvent(new Event('input',{bubbles:true}));});
  assert.ok(await page.evaluate(()=>{
    const poses=bodyFrameState.assemblyOffsets;
    return Object.entries(poses).filter(([n])=>n.includes('_finger_')).every(([n,p])=>p.every((v,i)=>v===poses[n.replace(/_finger_\d+$/,'')][i]));
  }));
  await page.locator('#access-only').uncheck();
  await page.locator('#assembly-step').selectOption(String(report.assembly_order.bench_join_operations));
  await page.locator('#drawing').screenshot({path:path.join(folder,'body-frame-assembly-base.png')});
  await page.locator('#assembly-step').selectOption(String(await page.locator('#assembly-step option').count()-1));
  assert.equal(await page.evaluate(()=>bodyFrameState.visibleNames.length),report.assembly_order.rigid_objects);
  await page.locator('#drawing').screenshot({path:path.join(folder,'body-frame-assembly-final.png')});
  await page.locator('#assembly-complete').click();assert.equal(await page.evaluate(()=>bodyFrameState.assemblyOnly),false);
  await page.locator('#release-space').check();
  assert.equal(await page.evaluate(()=>bodyFrameState.visibleKinds.filter(k=>k==='operation_space').length),16);
  await page.locator('#drawing').screenshot({path:path.join(folder,'body-frame-release-reservations.png')});
  await page.locator('#release-space').uncheck();
  await page.locator('#print-only').check();
  assert.equal(await page.locator('#print-part option').count(),81);
  assert.equal(await page.locator('#assembly-only').isDisabled(),true);
  for(const [index,part]of printPlan.parts.entries()){
    await page.locator('#print-part').selectOption(String(index));
    const state=await page.evaluate(()=>bodyFrameState);
    assert.equal(state.printOnly,true);
    assert.deepEqual(state.visibleNames,[part.name,'print_bed']);
    assert.deepEqual(state.printSize,part.size_mm);
  }
  for(const name of ['joint_key_10','spark_fan_0_front_pin_0','spark_fan_0_rear_holder','controller_-1_0_lid']){
    await page.locator('#print-part').selectOption(String(printPlan.parts.findIndex(p=>p.name===name)));
    await page.locator('#drawing').screenshot({path:path.join(folder,'body-frame-print-'+name+'.png')});
  }
  await page.locator('#print-part').selectOption(String(printPlan.parts.findIndex(p=>p.name==='spark_fan_0_rear_holder')));
  await page.locator('#support-view').check();
  assert.equal(await page.evaluate(()=>bodyFrameState.supportMode),true);
  const supportCount=await page.evaluate(()=>bodyFrameState.supportRegionCount);
  assert.ok(supportCount>0);
  assert.equal(await page.evaluate(()=>bodyFrameState.visibleKinds.filter(k=>k==='print_support').length),supportCount);
  await page.locator('#drawing').screenshot({path:path.join(folder,'body-frame-support-all.png')});
  await page.locator('#support-step').selectOption('0');
  const supportStart=await page.locator('#drawing').screenshot();
  await page.locator('#support-progress').evaluate(e=>{e.value=100;e.dispatchEvent(new Event('input',{bubbles:true}));});
  assert.notEqual(supportStart.toString('base64'),(await page.locator('#drawing').screenshot()).toString('base64'));
  assert.equal(await page.evaluate(()=>bodyFrameState.supportProgress),1);
  assert.ok(await page.evaluate(()=>Object.values(bodyFrameState.supportOffsets).every(p=>p.some(n=>n!==0))));
  await page.locator('#drawing').screenshot({path:path.join(folder,'body-frame-support-removal.png')});
  for(const [index,part]of printPlan.parts.entries()){
    await page.locator('#print-part').selectOption(String(index));
    assert.equal(await page.evaluate(()=>bodyFrameState.visibleKinds.filter(k=>k==='print_support').length),supportPlan.parts.find(p=>p.name===part.name).region_count);
  }
  await page.locator('#support-view').uncheck();
  await page.locator('#print-only').uncheck();
  const before=await page.locator('#drawing').screenshot();
  const b=await page.locator('#drawing').boundingBox();
  await page.mouse.move(b.x+b.width/2,b.y+b.height/2);
  await page.mouse.down();await page.mouse.move(b.x+b.width/2+60,b.y+b.height/2+20,{steps:3});await page.mouse.up();
  assert.notEqual(before.toString('base64'),(await page.locator('#drawing').screenshot()).toString('base64'));
  for(const width of [390,320]){
    await page.setViewportSize({width,height:900});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.locator('#assembly-only').check();
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.locator('#assembly-only').uncheck();
    await page.locator('#print-only').check();
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.locator('#print-only').uncheck();
  }
  const assemblyPage=await browser.newPage();
  await assemblyPage.goto(pathToFileURL(path.join(folder,'body-frame.html')).href+'#assembly');
  await assemblyPage.waitForFunction(()=>window.bodyFrameState?.assemblyOnly);
  await assemblyPage.close();
  const accessPage=await browser.newPage();
  await accessPage.goto(pathToFileURL(path.join(folder,'body-frame.html')).href+'#access');
  await accessPage.waitForFunction(()=>window.bodyFrameState?.accessOnly);
  await accessPage.close();
  const printPage=await browser.newPage();
  await printPage.goto(pathToFileURL(path.join(folder,'body-frame.html')).href+'#print');
  await printPage.waitForFunction(()=>window.bodyFrameState?.printOnly);
  await printPage.close();
  const supportPage=await browser.newPage();
  await supportPage.goto(pathToFileURL(path.join(folder,'body-frame.html')).href+'#support');
  await supportPage.waitForFunction(()=>window.bodyFrameState?.supportMode);
  assert.equal(await supportPage.evaluate(()=>bodyFrameState.printPart),'spark_fan_0_rear_holder');
  await supportPage.close();
  assert.deepEqual(errors,[]);
  await page.screenshot({path:path.join(folder,'body-frame-mobile.png'),fullPage:true});
  await browser.close();
  fs.writeFileSync(path.join(folder,'browser-validation.json'),JSON.stringify({
    status:'passed',scope:'5方向、表示切替、接合と指の拡大、組立順と差込位置、解除部16箇所、造形姿勢81個と支持材領域・除去操作、全剛体対象、各専用リンク、ドラッグ、390pxと320px、実行時エラー'
  },null,2)+'\n');
  const manifest=JSON.parse(fs.readFileSync(path.join(folder,'manifest.json')));
  for(const name of fs.readdirSync(folder).filter(n=>n!=='manifest.json')){
    manifest.outputs_sha256[name]=crypto.createHash('sha256').update(fs.readFileSync(path.join(folder,name))).digest('hex');
  }
  fs.writeFileSync(path.join(folder,'manifest.json'),JSON.stringify(manifest,null,2)+'\n');
  console.log('本体連結案の表示と主要操作: 合格');
})().catch(async e=>{console.error(e);if(browser)await browser.close();process.exitCode=1;});
