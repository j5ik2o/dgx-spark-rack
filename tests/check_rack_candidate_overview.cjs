// 自作の構想図の表示と操作を確認し、閲覧用の画像を保存する。
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const {pathToFileURL} = require('node:url');
const {chromium} = require('playwright');
let browser;
(async () => {
  const folder = path.resolve(process.argv[2]);
  browser = await chromium.launch({headless: true});
  const page = await browser.newPage({viewport: {width: 1360, height: 1000}});
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(pathToFileURL(path.join(folder, 'rack-candidate-overview.html')).href);
  await page.waitForFunction(() => !!window.overviewState);
  for (const mode of ['ring', 'crs812', 'crs804']) {
    await page.locator('#mode').selectOption(mode);
    const actual = await page.evaluate(() => window.overviewState.scene);
    assert.equal(actual.members.length, 52);
    assert.equal(actual.equipment.filter(i => i.kind === 'spark').length, 4);
    assert.equal(actual.equipment.filter(i => i.kind === 'fan' && i.size_mm === 140).length, 4);
    assert.equal(actual.equipment.filter(i => i.kind === 'fan' && i.size_mm === 120).length, 2);
    assert.equal(actual.equipment.filter(i => i.kind === 'adapter').length, 4);
    assert.equal(actual.equipment.filter(i => i.kind === 'controller').length, 6);
    assert.equal(actual.equipment.filter(i => i.kind === 'switch').length, mode === 'ring' ? 0 : 1);
    assert.equal(actual.mount_holes_committed, false);
    assert.equal(actual.switch_support_generated, false);
    for (const view of ['iso', 'front', 'back', 'side', 'top']) {
      await page.locator(`[data-view="${view}"]`).click();
      assert.equal(await page.evaluate(() => window.overviewState.view), view);
      assert.ok(await page.locator('#drawing polygon').count() > 50);
      if (['iso', 'front', 'back'].includes(view)) {
        await page.locator('#stage').screenshot({path: path.join(folder, `${mode}-${view}.png`)});
      }
    }
  }
  await page.locator('#mode').selectOption('ring');
  await page.locator('[data-view="iso"]').click();
  await page.locator('#revision').selectOption('previous');
  assert.equal(await page.evaluate(() => window.overviewState.scene.controller_width_mm), 618);
  await page.locator('#stage').screenshot({path: path.join(folder, 'previous-ring-iso.png')});
  await page.locator('#revision').selectOption('current');
  assert.equal(await page.evaluate(() => window.overviewState.scene.controller_width_mm), 512);
  await page.locator('#adapters').uncheck();
  assert.equal(await page.evaluate(() => window.overviewState.shownPower), false);
  await page.locator('#stage').screenshot({path: path.join(folder, 'ring-without-power.png')});
  await page.locator('#adapters').check();
  await page.locator('#equipment').uncheck();
  assert.equal(await page.evaluate(() => window.overviewState.shownEquipment), false);
  await page.locator('#stage').screenshot({path: path.join(folder, 'ring-frame-only.png')});
  await page.locator('#equipment').check();
  const polygons = await page.locator('#drawing').innerHTML();
  const drawing = await page.locator('#drawing').boundingBox();
  await page.mouse.move(drawing.x + drawing.width / 2, drawing.y + drawing.height / 2);
  await page.mouse.down();
  await page.mouse.move(drawing.x + drawing.width / 2 + 65, drawing.y + drawing.height / 2 + 25, {steps: 3});
  await page.mouse.up();
  assert.notEqual(await page.locator('#drawing').innerHTML(), polygons);
  await page.locator('[data-view="iso"]').click();
  await page.screenshot({path: path.join(folder, 'overview-desktop.png'), fullPage: true});
  await page.setViewportSize({width: 390, height: 844});
  await page.screenshot({path: path.join(folder, 'overview-mobile.png'), fullPage: true});
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth));
  assert.deepEqual(errors, []);
  assert.ok(await page.locator('img').evaluateAll(images => images.every(i => i.complete && i.naturalWidth > 0)));
  await browser.close();
  // 閲覧画像も同じ実行の照合対象へ追加する。
  const crypto = require('node:crypto');
  const manifestPath = path.join(folder, 'manifest.json');
  const manifest = JSON.parse(fs.readFileSync(manifestPath));
  const validation = {status: 'passed', scope: '3配置・5方向・新旧比較・電源表示切替・機器表示切替・ドラッグ回転・390px表示・参照画像・実行時エラー'};
  fs.writeFileSync(path.join(folder, 'browser-validation.json'), JSON.stringify(validation, null, 2) + '\n');
  for (const name of fs.readdirSync(folder).filter(n => n !== 'manifest.json')) {
    manifest.outputs_sha256[name] = crypto.createHash('sha256').update(fs.readFileSync(path.join(folder, name))).digest('hex');
  }
  fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2) + '\n');
  console.log('全体構想図の表示・主要操作の確認: 合格');
})().catch(async error => {console.error(error); if (browser) await browser.close(); process.exitCode = 1;});
