const {JSDOM,VirtualConsole}=require('jsdom');
const fs=require('node:fs');
const assert=require('node:assert/strict');
let checks=0;
const check=(value,message)=>{assert.ok(value,message);checks++};
const tick=()=>new Promise(resolve=>setTimeout(resolve,20));
function make(preview){
 const errors=[],calls=[];const vc=new VirtualConsole();vc.on('jsdomError',e=>{if(!e.message.includes('navigation'))errors.push(e.message)});
 const dom=new JSDOM(fs.readFileSync('web/index.html','utf8'),{url:preview?'https://whood-yop.github.io/niyam/':'http://127.0.0.1:8000/',runScripts:'outside-only',virtualConsole:vc});
 const w=dom.window;w.NIYAM_PUBLIC_PREVIEW=preview;w.HTMLElement.prototype.scrollIntoView=()=>{};w.confirm=()=>true;
 const catalog={ready:false,symbols:[],rows:0,benchmark_rows:0,errors:[]};
 w.fetch=async(url,options={})=>{calls.push([url,options]);let value=url.endsWith('/api/health')?{app:'niyam',connections:{ai:false,search:false}}:url.endsWith('/api/data')?catalog:url.endsWith('/api/auth/signup')?{user:{id:'u1',name:'Researcher',email:'user@example.com'},token:'test-session',recovery_code:'test-only-recovery-code-12345678'}:url.endsWith('/api/strategies')?[]:url.endsWith('/api/jobs')?[]:url.endsWith('/api/signals')?{watches:[],alerts:[]}:url.endsWith('/api/interpret')?{status:'connection_required',summary:'Connect AI',strategy:null,questions:[]}:{};return {ok:true,status:200,json:async()=>value}};
 w.URL.createObjectURL=()=> 'blob:test';w.URL.revokeObjectURL=()=>{};
 w.eval(fs.readFileSync('web/templates.js','utf8'));
 w.eval(fs.readFileSync('web/app.js','utf8')+'\nwindow.__audit={state,api,render,openAuth,runInterpret,csv,clearPrivate,actions};');
 return {dom,w,doc:w.document,calls,errors,a:w.__audit};
}
(async()=>{
 const p=make(true);await tick();
 check(p.doc.querySelector('h1').textContent.includes('Every strategy'),'studio initial render');
 for(const view of ['library','backtests','optimise','signals','data','guide','studio']){p.w.location.hash=view;await tick();check(p.doc.querySelector('#main').textContent.length>100,view+' page renders');}
 for(const kind of ['trend','rsi','breakout']){p.a.state.spec=null;p.a.render();p.doc.querySelector(`[data-kind="${kind}"]`).click();check(p.a.state.spec.entry.op,kind+' loads');check(p.doc.querySelector('#jsonEditor'),kind+' editable JSON');}
 p.a.openAuth();check(!p.doc.querySelector('input[type=password]'),'public preview does not collect passwords');
 check([...p.doc.querySelectorAll('.modal a')].some(a=>a.href==='http://127.0.0.1:8000/'),'public preview links to local workspace');
 await assert.rejects(()=>p.a.api('/api/auth/login',{method:'POST',body:{}}),/workspace/);checks++;
 check(!p.calls.some(([url])=>url.includes('/api/auth/')),'no public auth traffic');
 p.a.state.spec.name='<img src=x onerror=alert(1)>';p.a.render();check(!p.doc.querySelector('#main img[src=x]'),'strategy names escaped');
 for(const el of p.doc.querySelectorAll('[data-action]'))check(typeof p.a.actions[el.dataset.action]==='function','visible control has handler: '+el.dataset.action);
 check(!p.errors.length,'no public DOM errors');p.dom.window.close();
 const l=make(false);await tick();check(l.a.state.online,'local health connection');l.a.openAuth('signup');
 const form=l.doc.querySelector('#authForm');form.elements.name.value='Researcher';form.elements.email.value='user@example.com';form.elements.password.value='unique-test-password-123';
 form.dispatchEvent(new l.w.Event('submit',{bubbles:true,cancelable:true}));await tick();
 check(l.a.state.user?.name==='Researcher','signup stores user');check(l.doc.querySelector('.recovery-code'),'recovery code displayed');
 l.a.actions['close-modal']();l.a.state.prompt='20 SMA above 50 SMA';
 await l.a.runInterpret();check(l.a.state.interpretation.status==='connection_required','missing AI remains explicit');
 l.a.state.interpretation={status:'clarify',summary:'Which MA?',questions:[{question:'SMA or EMA?',options:['SMA','EMA']}]};l.a.render();
 await assert.rejects(()=>l.a.runInterpret(true),/answer/);checks++;check(l.a.state.answers.length===0,'blank answer does not poison history');
 l.doc.querySelector('[data-answer]').value='SMA';await l.a.runInterpret(true);check(l.a.state.answers.length===1,'clarification retry succeeds');
 check(l.a.csv([{symbol:'=HYPERLINK("bad")',pnl:-12}]).includes("'=HYPERLINK"),'CSV neutralises spreadsheet formula');
 l.a.state.result={private:true};l.a.state.saved=[{private:true}];l.a.state.signalData={watches:[{}],alerts:[{}]};
 l.w.fetch=async()=>({ok:false,status:401,json:async()=>({detail:'Session expired'})});
 await assert.rejects(()=>l.a.api('/api/jobs'),/expired/);checks++;
 check(!l.a.state.user&&!l.a.state.result&&!l.a.state.saved.length&&!l.a.state.signalData.alerts.length,'expired session clears private UI');
 check(!l.errors.length,'no local DOM errors');l.dom.window.close();
 console.log(`${checks} DOM checks passed (jsdom; no visual browser audit).`);
})().catch(e=>{console.error(e);process.exitCode=1});
