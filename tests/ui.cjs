const {JSDOM,VirtualConsole}=require('jsdom');
const fs=require('node:fs');
const assert=require('node:assert/strict');
let checks=0;
const check=(value,message)=>{assert.ok(value,message);checks++};
const tick=()=>new Promise(resolve=>setTimeout(resolve,30));
function make(preview,ready=false){
 const errors=[],calls=[];const vc=new VirtualConsole();vc.on('jsdomError',e=>{if(!e.message.includes('navigation'))errors.push(e.message)});
 const dom=new JSDOM(fs.readFileSync('web/index.html','utf8'),{url:'https://niyam.example/',runScripts:'outside-only',virtualConsole:vc});
 const w=dom.window;w.NIYAM_PUBLIC_PREVIEW=preview;w.HTMLElement.prototype.scrollIntoView=()=>{};w.confirm=()=>true;
 w.sessionStorage.setItem('niyam.backend','https://untrusted.example');w.sessionStorage.setItem('niyam.token','obsolete-token');
 const runtime={research_ready:ready,interpretation_ready:ready,ready,message:ready?'Ready':'Preparing'};
 const catalog={ready,symbols:ready?[{symbol:'TEST',rows:300,start:'2020-01-01',end:'2021-02-23'}]:[],rows:ready?300:0,benchmark_rows:ready?300:0,benchmark_start:'2020-01-01',benchmark_end:'2021-02-23',version:'1'};
 let signedIn=false;
 w.fetch=async(url,options={})=>{calls.push([url,options]);let status=200,value;
 if(url==='/api/health')value={app:'niyam'};
 else if(url==='/api/runtime')value=runtime;
 else if(url==='/api/data')value=catalog;
 else if(url==='/api/auth/me'){status=signedIn?200:401;value=signedIn?{id:'u1',name:'Researcher',email:'user@example.com'}:{detail:'Sign in'};}
 else if(url==='/api/auth/signup'){signedIn=true;value={user:{id:'u1',name:'Researcher',email:'user@example.com'},token:'never-store-this',recovery_code:'test-only-recovery-code-12345678'};}
 else if(url==='/api/strategies'||url==='/api/jobs')value=[];
 else if(url==='/api/signals')value={watches:[],alerts:[]};
 else if(url==='/api/interpret')value={status:'connection_required',summary:'Temporarily unavailable',strategy:null,questions:[]};
 else value={};
 return {ok:status===200,status,json:async()=>value};};
 w.URL.createObjectURL=()=> 'blob:test';w.URL.revokeObjectURL=()=>{};
 w.eval(fs.readFileSync('web/templates.js','utf8'));
 w.eval(fs.readFileSync('web/app.js','utf8')+'\nwindow.__audit={state,api,render,openAuth,runInterpret,csv,clearPrivate,actions,refreshWorkspace,getTemplate};');
 return {dom,w,doc:w.document,calls,errors,a:w.__audit,runtime,catalog};
}
(async()=>{
 for(const preview of [true,false]){
 const p=make(preview);await tick();
 check(p.doc.querySelector('h1').textContent.includes('Every strategy'),'studio renders');
 check(p.doc.querySelector('.language-badge').textContent.includes('\u0939\u093f\u0902\u0926\u0940'),'Hindi label renders as Unicode');
 check(p.doc.querySelector('#authButton').textContent.includes('↗'),'navigation arrow has no encoding corruption');
 check(!p.doc.querySelector('[href="#data"]'),'no operator setup navigation');
 check(!p.doc.querySelector('.setup-strip,#backendUrl,#connectionForm'),'no backend setup controls');
 check(p.w.sessionStorage.getItem('niyam.backend')===null,'legacy foreign backend cleared');
 check(p.w.sessionStorage.getItem('niyam.token')===null,'legacy session token cleared');
 for(const view of ['library','backtests','optimise','signals','guide','studio']){p.w.location.hash=view;await tick();check(p.doc.querySelector('#main').textContent.length>100,view+' page renders');}
 for(const kind of ['trend','rsi','breakout']){p.a.state.spec=null;p.a.render();p.doc.querySelector(`[data-kind="${kind}"]`).click();check(p.a.state.spec.entry.op,kind+' loads');check(p.doc.querySelector('#jsonEditor'),kind+' editable JSON');check(!p.doc.querySelector('[data-spec="price_basis_confirmed"]'),'no user data attestation');}
 p.a.state.spec.name='<img src=x onerror=alert(1)>';p.a.render();check(!p.doc.querySelector('#main img[src=x]'),'strategy names escaped');
 for(const el of p.doc.querySelectorAll('[data-action]'))check(typeof p.a.actions[el.dataset.action]==='function','visible control has handler: '+el.dataset.action);
 if(preview){p.a.openAuth();check(!p.doc.querySelector('input[type=password]'),'preview never collects passwords');check(!p.doc.querySelector('a[href*="127.0.0.1"]'),'preview never sends mobile users to localhost');check(!p.calls.length,'no preview API traffic');}
 check(!p.errors.length,'no DOM errors');p.dom.window.close();
 }
 const l=make(false);await tick();check(l.a.state.online,'same-origin service auto-connects on remote HTTPS hostname');l.a.openAuth('signup');
 const form=l.doc.querySelector('#authForm');form.elements.name.value='Researcher';form.elements.email.value='user@example.com';form.elements.password.value='unique-test-password-123';
 form.dispatchEvent(new l.w.Event('submit',{bubbles:true,cancelable:true}));await tick();
 check(l.a.state.user?.name==='Researcher','signup stores user');check(l.doc.querySelector('.recovery-code'),'recovery code displayed');
 check(!l.w.sessionStorage.getItem('niyam.token'),'browser never persists session bearer token');
 check(l.calls.every(([url,o])=>url.startsWith('/api/')&&o.credentials==='same-origin'&&!o.headers.Authorization),'all calls use same-origin cookie credentials');
 l.a.actions['close-modal']();l.a.state.prompt='20 SMA above 50 SMA';
 await l.a.runInterpret();check(l.a.state.interpretation.status==='connection_required','provider unavailable remains truthful');
 check(!l.doc.querySelector('[data-action="connections"]'),'provider failure offers no setup action');
 l.a.state.interpretation={status:'clarify',summary:'Which MA?',questions:[{question:'SMA or EMA?',options:['SMA','EMA']}]};l.a.render();
 await assert.rejects(()=>l.a.runInterpret(true),/answer/);checks++;check(l.a.state.answers.length===0,'blank clarification rejected');
 l.doc.querySelector('[data-answer]').value='SMA';await l.a.runInterpret(true);check(l.a.state.answers.length===1,'clarification retry succeeds');
 check(l.a.csv([{symbol:'=HYPERLINK("bad")',pnl:-12}]).includes("'=HYPERLINK"),'CSV neutralises spreadsheet formula');
 Object.assign(l.runtime,{research_ready:true,interpretation_ready:true,ready:true});Object.assign(l.catalog,{ready:true,symbols:[{symbol:'TEST',start:'2020-01-01',end:'2021-02-23'}],version:'2'});
 await l.a.refreshWorkspace();check(l.a.state.runtime.ready&&l.a.state.data.symbols.length===1,'new backend inputs become available without user setup or reload');
 check(!l.doc.querySelector('.setup-strip'),'ready workspace still has no setup tasks');
 const t=l.a.getTemplate('trend');check(t.symbols[0]==='TEST'&&t.start==='2020-01-01'&&t.end==='2021-02-23','template uses managed stock and coverage');
 l.a.state.result={private:true};l.a.state.saved=[{private:true}];l.a.state.signalData={watches:[{}],alerts:[{}]};
 l.w.fetch=async()=>({ok:false,status:401,json:async()=>({detail:'Session expired'})});
 await assert.rejects(()=>l.a.api('/api/jobs'),/expired/);checks++;
 check(!l.a.state.user&&!l.a.state.result&&!l.a.state.saved.length&&!l.a.state.signalData.alerts.length,'expired session clears private UI');
 check(!l.errors.length,'no signed-in DOM errors');l.dom.window.close();
 console.log(`${checks} DOM checks passed.`);
})().catch(e=>{console.error(e);process.exitCode=1});
