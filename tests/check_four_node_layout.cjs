// 調整画面の配線計算をPythonの生成結果と照合し、主要な操作を確認する。
const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const assert = require('node:assert/strict');
const {chromium} = require('playwright');
let activeBrowser;

(async () => {
  const folder = path.resolve(process.argv[2]);
  const baseline = JSON.parse(fs.readFileSync(path.join(folder, 'layout-report.json'), 'utf8'));
  const browser = await chromium.launch({headless: true});
  activeBrowser = browser;
  const page = await browser.newPage({viewport: {width: 1240, height: 1000}, deviceScaleFactor: 1});
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(pathToFileURL(path.join(folder, 'four-node-layout.html')).href);
  await page.waitForFunction(() => !!window.layoutState);
  for (const mode of ['ring', 'crs812', 'crs804']) {
    await page.locator('#mode').selectOption(mode);
    const actual = await page.evaluate(() => window.layoutState.cables.map(c => c.required_length_mm));
    const expected = (mode === 'ring' ? baseline.ring.ring_cables : baseline[mode].switch_cables).map(c => c.required_length_mm);
    assert.equal(actual.length, 4);
    actual.forEach((v, i) => assert.ok(Math.abs(v - expected[i]) < 1e-8, `${mode}: ${v} != ${expected[i]}`));
    const controllers = await page.evaluate(() => window.layoutState.report.controllers.map(c => ({origin: c.origin, size: c.size})));
    assert.deepEqual(controllers, baseline[mode].controllers.map(c => ({origin: c.origin, size: c.size})));
    for (const view of ['iso', 'front', 'back', 'side', 'top']) {
      await page.locator(`[data-view="${view}"]`).click();
      assert.equal(await page.evaluate(() => window.layoutState.view), view);
      assert.ok(await page.locator('#drawing polygon').count() > 0);
    }
    if (mode === 'ring') {
      await page.locator('[data-view="front"]').click();
      await page.locator('.stage').screenshot({path: path.join(folder, 'layout-ring-front.png')});
    }
  }
  await page.locator('#mode').selectOption('crs812');
  await page.locator('[data-view="iso"]').click();
  await page.screenshot({path: path.join(folder, 'layout-preview.png'), fullPage: true});
  await page.locator('.stage').screenshot({path: path.join(folder, 'layout-overview.png')});
  await page.locator('[data-view="front"]').click();
  await page.locator('.stage').screenshot({path: path.join(folder, 'layout-fans-front.png')});
  assert.equal(await page.evaluate(() => window.layoutState.report.fans.length), 4);
  assert.equal(await page.evaluate(() => window.layoutState.report.controllers.length), 4);
  await page.locator('#include_fans').uncheck();
  assert.equal(await page.evaluate(() => window.layoutState.report.fans.length), 0);
  await page.locator('#include_fans').check();
  const margin400=await page.evaluate(() => window.layoutState.cables[0].margin_mm);
  await page.locator('#cable_length').selectOption('500');
  assert.ok(Math.abs((await page.evaluate(() => window.layoutState.cables[0].margin_mm))-margin400-100)<1e-8);
  await page.locator('#cable_length').selectOption('400');
  await page.locator('#row_pitch').fill('180');
  assert.ok(await page.evaluate(() => window.layoutState.report.errors.some(e => e.includes('保持板範囲')||e.includes('140mm'))));
  await page.locator('#reset').click();
  await page.locator('#straight_lead').fill('50');
  await page.locator('#bend_radius').fill('30');
  assert.ok(await page.evaluate(() => window.layoutState.report.switch_worst_cases.some(c => c.margin_mm < 0)));
  assert.ok(await page.locator('#worst-cases .bad').count() > 0);
  await page.locator('#column_pitch').fill('400');
  assert.ok(await page.evaluate(() => window.layoutState.report.errors.some(e => e.includes('収容範囲'))));
  assert.ok(await page.locator('#notice').getAttribute('class').then(c => c.includes('error')));
  await page.locator('#reset').click();
  assert.equal(await page.locator('#column_pitch').inputValue(), '180');
  await page.locator('summary').click();
  await page.locator('[data-port="0"]').fill('500');
  assert.ok(await page.evaluate(() => window.layoutState.report.errors.some(e => e.includes('端子が筐体の外'))));
  await page.locator('#reset').click();
  await page.locator('summary').click();
  await page.setViewportSize({width: 390, height: 844});
  await page.locator('#mode').selectOption('crs804');
  await page.screenshot({path: path.join(folder, 'layout-mobile-preview.png'), fullPage: true});
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth));
  assert.deepEqual(errors, []);
  await browser.close();
  fs.writeFileSync(path.join(folder, 'browser-validation.json'), JSON.stringify({status: 'passed',
    checked: ['3方式の計算値がPythonと一致', '5方向表示', 'ファン4個とケース範囲', 'ファン表示切替', '段間隔の変更でファン干渉を表示', '曲げ条件変更で超過を表示',
              '収容範囲外を表示', '端子位置の編集', '初期化', '390px表示', '実行時エラーなし']}, null, 2) + '\n');
  const crypto = require('node:crypto');
  const manifestPath = path.join(folder, 'manifest.json');
  const manifest = JSON.parse(fs.readFileSync(manifestPath));
  for (const name of fs.readdirSync(folder)) {
    const file = path.join(folder, name);
    if (name !== 'manifest.json' && fs.statSync(file).isFile()) {
      manifest.outputs_sha256[name] = crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
    }
  }
  fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2) + '\n');
  console.log('調整画面の計算・主要操作・狭い画面の検査: 合格');
})().catch(async error => {console.error(error); if (activeBrowser) await activeBrowser.close(); process.exitCode = 1;});
