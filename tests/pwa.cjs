const fs=require('node:fs');const vm=require('node:vm');const assert=require('node:assert/strict');
const {JSDOM}=require('jsdom');
const manifest=JSON.parse(fs.readFileSync('web/manifest.webmanifest','utf8'));
assert.equal(manifest.display,'standalone');assert.equal(manifest.scope,'./');assert.equal(manifest.start_url,'./#studio');
for(const icon of manifest.icons)assert.ok(fs.existsSync('web/'+icon.src.replace('./','')));
let online=true;const events={};const buckets=new Map();let claimed=false,skipped=false;
const key=x=>typeof x==='string'?x:x.url||x.href;
const fetchAsset=async request=>{
 if(!online)throw Error('Offline');
 const url=new URL(key(request)),path=url.pathname.replace('/niyam/','');
 assert.ok(!path.startsWith('api/'),'API requests must not enter the offline handler');
 return new Response(fs.readFileSync('web/'+(path||'index.html')));
};
const caches={keys:async()=>[...buckets.keys()],delete:async n=>buckets.delete(n),open:async name=>{
 if(!buckets.has(name))buckets.set(name,new Map());const bucket=buckets.get(name);
 return {addAll:async requests=>{const responses=await Promise.all(requests.map(fetchAsset));requests.forEach((request,i)=>bucket.set(key(request),responses[i]));},
         match:async request=>bucket.get(key(request))?.clone()};
}};
vm.runInNewContext(fs.readFileSync('web/sw.js','utf8'),{self:{location:{href:'https://example.com/niyam/sw.js'},addEventListener:(n,fn)=>events[n]=fn,clients:{claim:async()=>claimed=true},skipWaiting:()=>skipped=true},caches,fetch:fetchAsset,URL,Request,Set,Promise,Error});
const life=name=>new Promise((resolve,reject)=>events[name]({waitUntil:p=>p.then(resolve,reject)}));
function request(path,mode='cors',method='GET'){
 let handled=false,promise;
 events.fetch({request:{url:'https://example.com'+path,mode,method},respondWith:p=>{handled=true;promise=p;}});
 return {handled,promise};
}
(async()=>{
 await life('install');assert.ok(skipped,'new app versions activate after caching');skipped=false;
 buckets.set('niyam-review-app:/niyam/:old',new Map());buckets.set('niyam-review-app:/another-app/:old',new Map());buckets.set('private-account-cache',new Map());
 await life('activate');assert.ok(claimed);assert.ok(!buckets.has('niyam-review-app:/niyam/:old'));assert.ok(buckets.has('niyam-review-app:/another-app/:old'));assert.ok(buckets.has('private-account-cache'));
 online=false;
 const shell=await request('/niyam/','navigate').promise;assert.ok((await shell.text()).includes('manifest.webmanifest'));
 for(const file of ['app.js?v=design-20261113','review.js?v=review-20261113','pwa.js?v=autoupdate-20261113','icons/apple-touch-icon.png'])assert.ok((await request('/niyam/'+file).promise).ok,'offline asset '+file);
 assert.equal(request('/niyam/api/paper').handled,false);
 assert.equal(request('/niyam/private.json').handled,false);
 assert.equal(request('/outside/','navigate').handled,false);
 assert.equal(request('/niyam/','navigate','POST').handled,false);
 events.message({data:{type:'ACTIVATE_UPDATE'}});assert.ok(skipped);
 const dom=new JSDOM(fs.readFileSync('web/index.html','utf8'),{url:'https://example.com/niyam/',runScripts:'outside-only'}),w=dom.window;
 w.NIYAM_PUBLIC_PREVIEW=true;w.NIYAM_REVIEW_MODE=true;w.matchMedia=()=>({matches:false});
 Object.defineProperty(w.navigator,'userAgent',{value:'iPhone Safari'});
 w.eval(fs.readFileSync('web/pwa.js','utf8'));
 w.document.querySelector('#installNiyam').click();
 assert.equal(w.document.querySelector('#installHelp').hidden,false);
 assert.ok(w.document.querySelector('#installHelp').textContent.includes('Safari'));
 assert.ok(w.document.querySelector('#installHelp').textContent.includes('Add to Home Screen'));
 assert.equal(w.document.querySelector('#mobileAppNav').hidden,false);
 w.close();
 const updateDom=new JSDOM(fs.readFileSync('web/index.html','utf8'),{url:'https://example.com/niyam/',runScripts:'outside-only'}),uw=updateDom.window;
 uw.NIYAM_PUBLIC_PREVIEW=true;uw.NIYAM_REVIEW_MODE=true;uw.matchMedia=()=>({matches:false});Object.defineProperty(uw,'isSecureContext',{value:true});
 let activationMessage,updateChecks=0;const registration={waiting:{postMessage:message=>activationMessage=message},addEventListener(){},update(){updateChecks++;return Promise.resolve();}};
 Object.defineProperty(uw.navigator,'serviceWorker',{value:{controller:{},register:async()=>registration,ready:Promise.resolve(registration),addEventListener(){}}});
 uw.eval(fs.readFileSync('web/pwa.js','utf8'));await new Promise(resolve=>setTimeout(resolve,0));
 assert.equal(activationMessage.type,'ACTIVATE_UPDATE','waiting update activates without a button');
 uw.dispatchEvent(new uw.Event('online'));assert.equal(updateChecks,1,'returning online checks for updates');uw.close();
 const local=new JSDOM(fs.readFileSync('web/index.html','utf8'),{runScripts:'outside-only'});local.window.eval(fs.readFileSync('web/pwa.js','utf8'));assert.equal(local.window.document.querySelector('#appInstall').hidden,true);local.window.close();
 console.log('App checks passed: manifest, offline shell/assets, private-data exclusions, scoped cache updates, iPhone install instructions and local-backend isolation.');
})().catch(e=>{console.error(e);process.exitCode=1});
