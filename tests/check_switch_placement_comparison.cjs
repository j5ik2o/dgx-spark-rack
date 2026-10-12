// 比較案の切替と未検証表示、図と寸法の整合を確認する。
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const {pathToFileURL} = require('node:url');
const {chromium} = require('playwright');
let browser;
(async () => {
  const out = path.resolve(process.argv[2]);
  const report = JSON.parse(fs.readFileSync(path.join(out, 'comparison.json')));
  assert.equal(report.manufacturing_geometry, false);
  assert.equal(report.network.routing_validated, false);
  browser = await chromium.launch({headless: true});
  const page = await browser.newPage({viewport: {width: 1320, height: 1000}});
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto(pathToFileURL(path.join(out, 'switch-placement.html')).href);
  await page.waitForFunction(() => !!window.switchPlacementState);
  assert.equal(await page.evaluate(() => switchPlacementState.selected), 'upper');
  for (const c of report.cases) {
    await page.locator('#case').selectOption(c.key);
    const state = await page.evaluate(() => switchPlacementState);
    assert.deepEqual(state.metrics, c.metrics);
    assert.equal(state.checks.status, c.checks.status);
    await page.locator('[data-view="side"]').click();
    for (const id of ['air', 'service', 'storage']) await page.locator('#' + id).check();
    await page.locator('#drawing').screenshot({path: path.join(out, c.key + '-side.png')});
    for (const id of ['air', 'service', 'storage']) await page.locator('#' + id).uncheck();
  }
  await page.locator('[data-case="upper"]').click();
  await page.locator('[data-view="front"]').click();
  assert.equal(await page.locator('#levels').textContent(), '208／428mm');
  await page.screenshot({path: path.join(out, 'switch-placement-desktop.png'), fullPage: true});
  await page.locator('#drawing').screenshot({path: path.join(out, 'upper-front.png')});
  await page.setViewportSize({width: 390, height: 844});
  await page.screenshot({path: path.join(out, 'switch-placement-mobile.png'), fullPage: true});
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  assert.deepEqual(errors, []);
  await browser.close();
  fs.writeFileSync(path.join(out, 'browser-validation.json'), JSON.stringify({status:'passed',scope:'4配置、2方向、予約の切替、寸法の一致、未検証の記録、390px表示、実行時エラー'},null,2)+'\n');
  const manifest = JSON.parse(fs.readFileSync(path.join(out, 'manifest.json')));
  for (const name of fs.readdirSync(out).filter(n => n !== 'manifest.json')) {
    manifest.outputs_sha256[name] = crypto.createHash('sha256').update(fs.readFileSync(path.join(out, name))).digest('hex');
  }
  fs.writeFileSync(path.join(out, 'manifest.json'), JSON.stringify(manifest,null,2)+'\n');
  console.log('スイッチ配置比較の表示確認: 合格');
})().catch(async e => {console.error(e);if(browser)await browser.close();process.exitCode=1});
