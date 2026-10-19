// 元のHTMLを直接開く経路を、描画環境から独立して検査する。
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const {pathToFileURL,fileURLToPath}=require('node:url');
const source=path.resolve('models/spark-rack/source/body_frame_view.html');
const html=fs.readFileSync(source,'utf8'),script=html.match(/<script>([\s\S]*)<\/script>/)[1];
for(const hash of ['', '#support']){
  const href=pathToFileURL(source).href+hash;let target=null;const main={innerHTML:''};
  const context={URL,location:{href,hash,replace:url=>target=String(url)},document:{querySelector:selector=>{assert.equal(selector,'main');return main;}}};
  vm.runInNewContext(script,context,{filename:source,timeout:1000});
  assert.ok(target,'データ未埋め込みのHTMLからモデルのページへ移動しません');
  const url=new URL(target);
  assert.equal(url.hash,hash);
  assert.ok(url.pathname.endsWith('/build/spark-rack/body-frame/latest/body-frame.html'));
  assert.ok(main.innerHTML.includes('モデル'));
  assert.ok(fs.existsSync(fileURLToPath(url)),'最新モデルへのリンク先が存在しません');
  assert.ok(!fs.readFileSync(fileURLToPath(url),'utf8').includes('__BODY_FRAME_DATA__'),'最新ページも未生成のテンプレートです');
}
console.log('元のHTMLから最新モデルへの案内と表示モードの保持: 合格');
