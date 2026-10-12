// 接続切替、交換予約、取付面の開閉表示をブラウザーで確認する。
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const {pathToFileURL} = require('node:url');
const {chromium} = require('playwright');
let browser;
(async () => {
  const folder = path.resolve(process.argv[2]);
  const validation = JSON.parse(fs.readFileSync(path.join(folder, 'validation.json')));
  assert.equal(validation.status, 'passed');
  assert.equal(validation.physical_validation, false);
  assert.equal(validation.whole_assembly_path_validated, false);
  assert.equal(validation.exchange_envelopes.status, 'passed');
  assert.equal(validation.support_contacts.status, 'passed');
  assert.equal(validation.controller_face_validation.status, 'passed');
  assert.equal(validation.candidate_part_instances, 72);
  browser = await chromium.launch({headless: true});
  const page = await browser.newPage({viewport: {width: 1320, height: 1050}});
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto(pathToFileURL(path.join(folder, 'fixed-rack.html')).href);
  await page.waitForFunction(() => !!window.fixedRackState);
  const z = await page.evaluate(() => fixedRackState.layout.nodes.map(n => n.origin[2]).sort());
  for (const mode of ['ring', 'crs812']) {
    await page.locator('#mode').selectOption(mode);
    const actual = await page.evaluate(() => fixedRackState);
    assert.deepEqual(actual.layout.nodes.map(n => n.origin[2]).sort(), z);
    assert.equal(actual.visibleNames.includes('switch'), mode !== 'ring');
    for (const view of ['iso', 'front', 'back', 'side', 'top']) {
      await page.locator(`[data-view="${view}"]`).click();
      assert.equal(await page.evaluate(() => fixedRackState.view), view);
      assert.ok(await page.evaluate(() => fixedRackState.renderedTriangles > 1000));
    }
  }
  await page.locator('[data-view="iso"]').click();
  await page.locator('#outer_walls').uncheck();
  assert.ok(await page.evaluate(() => !fixedRackState.visibleNames.some(n => n.startsWith('side_'))));
  await page.locator('#drawing').screenshot({path: path.join(folder, 'fixed-rack-supports.png')});
  await page.locator('#outer_walls').check();
  for (const view of ['front', 'back', 'side']) {
    await page.locator(`[data-view="${view}"]`).click();
    await page.locator('#drawing').screenshot({path: path.join(folder, `fixed-rack-${view}.png`)});
  }
  await page.locator('[data-view="iso"]').click();
  const closed = await page.locator('#drawing').screenshot();
  await page.locator('#door').fill('90');
  assert.equal(await page.evaluate(() => fixedRackState.doorAngle), 90);
  const opened = await page.locator('#drawing').screenshot();
  assert.notEqual(closed.toString('base64'), opened.toString('base64'));
  await page.locator('#drawing').screenshot({path: path.join(folder, 'control-door-open.png')});
  await page.locator('#door').fill('0');
  for (const id of ['air', 'service', 'storage']) await page.locator('#' + id).check();
  await page.locator('#drawing').screenshot({path: path.join(folder, 'reserved-spaces.png')});
  for (const id of ['air', 'service', 'storage']) await page.locator('#' + id).uncheck();
  await page.locator('#equipment').uncheck();
  assert.ok(await page.evaluate(() => !fixedRackState.visibleNames.some(n => n === 'upper_left' || n.startsWith('case_'))));
  await page.locator('#equipment').check();
  const drawing = await page.locator('#drawing').boundingBox();
  await page.mouse.move(drawing.x + drawing.width / 2, drawing.y + drawing.height / 2);
  await page.mouse.down();
  await page.mouse.move(drawing.x + drawing.width / 2 + 50, drawing.y + drawing.height / 2 + 20, {steps: 3});
  await page.mouse.up();
  await page.locator('[data-view="iso"]').click();
  await page.screenshot({path: path.join(folder, 'fixed-rack-desktop.png'), fullPage: true});
  await page.locator('#drawing').screenshot({path: path.join(folder, 'fixed-rack-iso.png')});
  await page.setViewportSize({width: 390, height: 844});
  await page.screenshot({path: path.join(folder, 'fixed-rack-mobile.png'), fullPage: true});
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  assert.deepEqual(errors, []);
  await browser.close();
  const result = {status: 'passed', scope: '2接続方式で段位置を維持、5方向、構造面の切替、90度の取付面表示、予約空間、機器表示、ドラッグ、390px表示、実行時エラー'};
  fs.writeFileSync(path.join(folder, 'browser-validation.json'), JSON.stringify(result, null, 2) + '\n');
  const manifestPath = path.join(folder, 'manifest.json');
  const manifest = JSON.parse(fs.readFileSync(manifestPath));
  for (const name of fs.readdirSync(folder).filter(n => n !== 'manifest.json')) {
    manifest.outputs_sha256[name] = crypto.createHash('sha256').update(fs.readFileSync(path.join(folder, name))).digest('hex');
  }
  fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2) + '\n');
  console.log('固定段ラックの表示・主要操作の確認: 合格');
})().catch(async e => {console.error(e);if (browser) await browser.close();process.exitCode = 1;});
