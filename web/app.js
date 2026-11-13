/* Niyam browser client. All untrusted strings pass through esc(); no generated code runs. */
'use strict';
const PUBLIC_PREVIEW=window.NIYAM_PUBLIC_PREVIEW===true;
const REVIEW_MODE=PUBLIC_PREVIEW&&window.NIYAM_REVIEW_MODE===true;
const $=(s,root=document)=>root.querySelector(s);
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const clone=x=>JSON.parse(JSON.stringify(x));
const storage={get(k){try{return sessionStorage.getItem('niyam.'+k)}catch{return null}},set(k,v){try{sessionStorage.setItem('niyam.'+k,v)}catch{}},remove(k){try{sessionStorage.removeItem('niyam.'+k)}catch{}}};
const paths={studio:'M12 3v18M3 12h18M5 5l14 14M19 5 5 19',backtests:'M4 19V5m0 14h16M8 15l4-5 4 2 4-7',optimise:'M4 7h16M4 17h16M8 4v6m8 4v6',signals:'M6 16v-5a6 6 0 0 1 12 0v5l2 2H4l2-2Zm4 5h4',data:'M4 5c0-4 16-4 16 0s-16 4-16 0v14c0 4 16 4 16 0V5M4 12c0 4 16 4 16 0',library:'M4 4h6v16H4zM14 4l6 1-2 15-6-1z',guide:'M4 4h7c2 0 2 2 2 2s0-2 2-2h5v15h-5c-2 0-2 2-2 2s0-2-2-2H4V4Zm9 2v15',arrow:'M5 12h14m-5-5 5 5-5 5',attach:'m8 12 6-6a3 3 0 0 1 4 4l-9 9a5 5 0 0 1-7-7l10-10',shield:'M12 2 3 6v6c0 5 9 10 9 10s9-5 9-10V6l-9-4Zm-4 10 3 3 5-6',check:'m5 12 4 4L19 6',download:'M12 3v12m-5-5 5 5 5-5M4 17v4h16v-4',close:'m6 6 12 12M18 6 6 18',copy:'M8 8h12v12H8zM4 16V4h12',trash:'M3 6h18M8 6V3h8v3M5 6l1 15h12l1-15M10 10v7m4-7v7',user:'M8 7a4 4 0 1 0 8 0 4 4 0 0 0-8 0M4 21v-3a8 8 0 0 1 16 0v3',trend:'m3 17 6-6 4 3 7-10M14 4h6v6',rsi:'M3 14c3-15 6 15 9 0s6 15 9-4M3 5h18M3 20h18',breakout:'M3 16h18M3 8h12M4 13l4-4 4 3 8-10',refresh:'M20 7V3l-3 3A8 8 0 1 0 3 14M20 3h-5',play:'m8 4 12 8-12 8V4Z',clock:'M12 8v5l3 2M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20',logout:'M9 3H4v18h5M10 12h11m-4-4 4 4-4 4'};
const icon=(name,cls='')=>`<svg class="${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${paths[name]||paths.studio}"/></svg>`;
const fmt=(v,d=2)=>v===null||v===undefined||!Number.isFinite(Number(v))?'—':Number(v).toLocaleString('en-IN',{maximumFractionDigits:d,minimumFractionDigits:d});
const pct=v=>v===null||v===undefined?'—':fmt(v)+'%';
const rupees=v=>'₹'+fmt(v,0);
const today=()=>new Date().toLocaleDateString('en-CA',{timeZone:'Asia/Kolkata'});
const baseDefault=location.origin;
storage.remove('backend');storage.remove('token');
const state={base:baseDefault,token:'',runtime:null,user:null,health:null,online:false,
 data:null,spec:null,prompt:REVIEW_MODE?'':storage.get('prompt')||'',attachments:[],answers:[],interpretation:null,view:'studio',tab:'overview',result:null,
 jobs:[],saved:[],signalData:{watches:[],alerts:[]},busy:false,authMode:'login',space:{},trainPct:70,maxTrials:40,minTrades:3,objective:'calmar',poll:null};
if(REVIEW_MODE)Object.assign(state,window.NIYAM_REVIEW.initial());
let toastTimer;
function toast(message){$('#toast').textContent=message;$('#toast').classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('#toast').classList.remove('show'),5000)}
function navigation(){const nav=[['studio','Strategy studio'],['library','Saved strategies'],['backtests','Backtests'],['optimise','Optimisation'],['signals','Daily signals'],['paper','Paper trading'],['guide','How it works']];$('#nav').innerHTML=nav.map(([id,title],i)=>`${i===5?'<div class="nav-divider"></div>':''}<a class="nav-link ${state.view===id?'active':''}" href="#${id}" ${state.view===id?'aria-current="page"':''}>${icon(id)}<span>${title}</span></a>`).join('');$('#breadcrumb').textContent=nav.find(x=>x[0]===state.view)?.[1]||'Backtest report';$('#connectionBadge').innerHTML=`<span class="dot ${state.online?'good':''}"></span>${REVIEW_MODE?'Frontend review':PUBLIC_PREVIEW?'Product preview':state.online?'Workspace online':'Reconnecting'}`;$('#authButton').innerHTML=state.user?`${icon('user')}${esc(state.user.name.split(' ')[0])}`:'Sign in <span>↗</span>';}
function clearPrivate(){state.token='';state.user=null;state.spec=null;state.result=null;state.saved=[];state.jobs=[];state.attachments=[];state.answers=[];state.interpretation=null;state.signalData={watches:[],alerts:[]};state.paper=[];state.data=null;state.coverage=null;clearTimeout(state.poll);storage.remove('token')}
async function api(path,{method='GET',body,auth=true,timeout=20000}={}){
 if(REVIEW_MODE)return window.NIYAM_REVIEW.api(path,{method,body});
 if(PUBLIC_PREVIEW)throw Error('This is a product preview. The research workspace will be available when the hosted service launches.');
 const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),timeout);
 try{const headers={};if(body&&!(body instanceof FormData))headers['Content-Type']='application/json';
 const response=await fetch(path,{method,credentials:'same-origin',headers,body:body instanceof FormData?body:body?JSON.stringify(body):undefined,signal:controller.signal});
 let out;try{out=await response.json()}catch{throw Error('The service is temporarily unavailable. Please try again shortly.')}
 if(!response.ok){if(response.status===401&&auth){clearPrivate();render()}const extra=out.fields?.map(x=>`${x.field}: ${x.message}`).join('; ');const error=Error((out.detail||'The request could not be completed.')+(extra?' '+extra:''));error.coverage=out.coverage;throw error}return out
 }catch(e){if(e.name==='AbortError')throw Error('The request timed out. Your draft is still here. Please retry.');if(e instanceof TypeError)throw Error('The service is temporarily unreachable. Please try again shortly.');throw e}finally{clearTimeout(timer)}
}
async function refreshWorkspace(initial=false){
 if(PUBLIC_PREVIEW)return;
 try{const health=await api('/api/health',{auth:false});if(health.app!=='niyam')throw Error('Service unavailable');
 const runtime=await api('/api/runtime',{auth:false});const changed=!state.online||JSON.stringify(runtime)!==JSON.stringify(state.runtime);state.online=true;state.health=health;state.runtime=runtime;
 if(initial){try{state.user=await api('/api/auth/me',{auth:false})}catch{clearPrivate()}}
 if(state.user){const data=await api('/api/data');const dataChanged=data.version!==state.data?.version;state.data=data;if(changed||dataChanged||initial){await route();return}}
 if(changed||initial)render();
 }catch{state.online=false;if(initial)render()}
}
function serviceNotice(){return !PUBLIC_PREVIEW&&state.runtime&&!state.runtime.ready?'<div class="notice" role="status">The research service is being prepared. Your saved work is safe. Please try again shortly.</div>':''}
function requireUser(){if(PUBLIC_PREVIEW&&!REVIEW_MODE){openAuth();return false}if(!state.online){toast('The service is reconnecting. Please try again shortly.');return false}if(!state.user){openAuth();return false}return true}

function go(view){location.hash=view;if(state.view===view)route()}
async function route(){const allowed=['studio','library','backtests','optimise','signals','paper','guide','report'];const view=location.hash.slice(1).split('?')[0]||'studio';const nextView=allowed.includes(view)?view:'studio';if(nextView!==state.view){document.documentElement.scrollTop=0;document.body.scrollTop=0;}state.view=nextView;$('#sidebar').classList.remove('open');clearTimeout(state.poll);render();if(state.user&&state.online){try{if(state.view==='library')state.saved=await api('/api/strategies');if(state.view==='backtests')state.jobs=await api('/api/jobs');if(state.view==='signals')state.signalData=await api('/api/signals');if(state.view==='paper')state.paper=await api('/api/paper');render();if(state.view==='report'&&state.result&&['queued','running'].includes(state.result.state))pollJob(state.result.id)}catch(e){toast(e.message)}}}
const head=(title,subtitle,action='')=>`<div class="hero"><div><div class="eyebrow">YOUR RESEARCH WORKSPACE</div><h1>${title}</h1><p>${subtitle}</p></div>${action}</div>`;
const empty=(name,title,body,button='')=>`<div class="card"><div class="empty"><div class="empty-icon">${icon(name)}</div><h2>${title}</h2><p>${body}</p>${button}</div></div>`;
function getTemplate(kind){const spec=clone(window.NIYAM_TEMPLATES[kind]);if(REVIEW_MODE){spec.taxes={enabled:true,stt_bps:10,stamp_buy_bps:1.5,gst_pct:18,short_term_pct:20,long_term_pct:12.5,annual_long_term_exemption:125000,cess_pct:4};spec.price_basis_confirmed=true;}spec.end=today();const first=state.data?.symbols?.[0];if(first){spec.symbols=[first.symbol];spec.start=[first.start,state.data.benchmark_start].filter(Boolean).sort().at(-1)||spec.start;spec.end=[first.end,state.data.benchmark_end,today()].filter(Boolean).sort()[0]}return spec}
function expr(x){if(!x)return 'Not defined';if(x.op==='benchmark_close')return 'Benchmark close';if(['open','high','low','close','volume'].includes(x.op))return x.op[0].toUpperCase()+x.op.slice(1);if(x.op==='constant')return String(x.value);if(['parameter','fundamental'].includes(x.op))return x.name.toUpperCase();const parts=(x.args||[]).map(expr);if(x.window!==null&&x.window!==undefined)return x.op.toUpperCase()+'('+[...parts,x.window].join(', ')+')';if(x.op==='not')return 'NOT '+parts[0];const op={gt:'>',gte:'≥',lt:'<',lte:'≤',eq:'=',cross_above:'crosses above',cross_below:'crosses below',all:'AND',any:'OR',add:'+',sub:'−',mul:'×',div:'÷'};return '('+parts.join(' '+op[x.op]+' ')+')'}
function templateCards(){return `<div class="section-heading"><h2>Start with a familiar idea</h2><span>Editable strategy templates</span></div><div class="template-grid">${[['trend','Moving average crossover','Follow a trend with a 20 / 50 SMA crossover.','TREND FOLLOWING'],['rsi','RSI mean reversion','Buy below RSI 30. Exit above RSI 60.','MEAN REVERSION'],['breakout','Donchian breakout','Enter a 55-day high. Exit a 20-day low.','MOMENTUM']].map(([kind,title,desc,tag])=>`<button class="template-card" data-action="template" data-kind="${kind}"><div class="template-top"><div class="template-icon">${icon(kind)}</div><span class="template-tag">${tag}</span></div><h3>${title}</h3><p>${desc}</p><span class="template-arrow">↗</span></button>`).join('')}</div>`}
function studio(){return `${head('Every strategy starts<br>with <em>a thought.</em>','Describe your idea in Hindi, English or a little of both.<br>Turn it into clear trading rules, then let the evidence speak.','<button class="button" data-action="guide">A quick walkthrough '+icon('arrow')+'</button>')}
${serviceNotice()}
<div class="studio-grid"><section class="card prompt-card"><div class="card-head"><span class="prompt-label">${icon('studio')} What would you like to test?</span><span class="language-badge">ENGLISH · हिंदी · HINGLISH</span></div><div class="prompt-wrap"><label class="hidden" for="strategyPrompt">Describe your strategy</label><textarea id="strategyPrompt" maxlength="12000" aria-autocomplete="list" aria-controls="mentionMenu" aria-expanded="false" placeholder="For example: Buy when the 20-day SMA crosses above the 50-day SMA. Exit on the reverse crossover, with a 5% trailing stop.">${esc(state.prompt)}</textarea><div id="mentionMenu" class="mention-menu" role="listbox" aria-label="Strategy reference suggestions" hidden></div><div class="prompt-hint">Describe your entry, exit and risk rules. Type <strong>@</strong> to choose data, indicators, stocks or a universe.</div><div id="promptReferences" class="prompt-references" aria-live="polite"></div><div class="attachments">${state.attachments.map(x=>`<span class="chip">${icon('attach')}${esc(x.name)}<button data-action="remove-attachment" data-id="${esc(x.id)}" aria-label="Remove ${esc(x.name)}">×</button></span>`).join('')}</div></div><div class="prompt-footer"><button class="attachment-button" data-action="attach">${icon('attach')} Attach rules <span class="tiny muted">PDF / DOCX / TXT</span></button><input id="documentFile" type="file" accept=".pdf,.docx,.txt,.md" class="hidden"><button class="button primary" data-action="interpret">Understand strategy ${icon('arrow')}</button></div></section><aside class="card research-card"><div class="kicker">ONE CLEAR FRAME OF REFERENCE</div><h3>Your idea.<br>The market.<br>The evidence.</h3><div class="research-row"><span>Market</span><strong>Indian equities</strong></div><div class="research-row"><span>Timeframe</span><strong>Daily candles</strong></div><div class="research-row"><span>Benchmark</span><strong>Nifty 50</strong></div><div class="research-note">Every result includes the assumptions behind it. Every comparison uses the same dates.</div></aside></div>
${dataInventory()}${interpretationView()}${state.spec?editor():templateCards()}<div class="workspace-note"><div>${icon('shield')} Your strategy stays in your account</div><div>${icon('clock')} Next-open execution · no future data</div><button class="text-button tiny" data-action="guide">Understand the methodology ↗</button></div>`}
function interpretationView(){const out=state.interpretation;if(!out)return '';return `<div class="${out.status==='ready'?'notice':'question-card'}"><strong>${out.status==='ready'?'Here is how I understood your strategy':out.status==='connection_required'?'Strategy understanding is temporarily unavailable':out.status==='unavailable'?'This backtest is currently not feasible':'Let’s make this rule precise'}</strong><p>${esc(out.summary)}</p>${(out.questions||[]).map((q,i)=>`<div><label class="field">${esc(q.question)}<input data-answer="${i}" placeholder="Your answer"></label><div class="question-options">${q.options.map(option=>`<button class="button small" data-action="answer-option" data-question="${i}" data-value="${esc(option)}">${esc(option)}</button>`).join('')}</div></div>`).join('')}${out.questions?.length?'<button class="button primary small" data-action="clarify">Continue with these answers →</button>':''}${out.sources?.length?'<div class="sources">References consulted:'+out.sources.map(x=>`<a href="${safeUrl(x.url)}" target="_blank" rel="noopener noreferrer">${esc(x.title)} ↗</a>`).join('')+'</div>':''}</div>`}
function safeUrl(url){try{const u=new URL(url);return ['https:','http:'].includes(u.protocol)?esc(u.href):'#'}catch{return '#'}}
function field(label,key,value,type='number',extra='',span=''){return `<label class="field ${span}">${label}<input type="${type}" data-spec="${esc(key)}" value="${esc(value)}" ${extra}></label>`}
function universeLabel(spec){
 if(spec.universe?.kind==='market_cap')return 'Historical top '+spec.universe.top_n+' by market cap';
 if(spec.universe?.kind==='index')return spec.universe.index_id;
 return spec.symbols.join(', ')||'Choose a universe';
}

function toolboxItems(){
 return state.data?.catalogue||[];
}
function toolboxItem(id){
 return toolboxItems().find(item=>item.id===id);
}
function filteredToolbox(){
 const query=(state.toolboxQuery||'').trim().toLowerCase();
 const category=state.toolboxCategory||'all';
 return toolboxItems().filter(item=>
   (category==='all'||item.category===category||(category==='fundamentals'&&item.category==='fields'&&!['open','high','low','close','volume','benchmark_close'].includes(item.id)))&&
   (state.toolboxPending||item.available||item.category==='fields')&&
   (!query||[item.label,item.tag,item.description].some(value=>value.toLowerCase().includes(query)))
 ).sort((a,b)=>Number(b.available)-Number(a.available));
}
function toolboxRows(){
 const items=filteredToolbox();
 const pages=Math.max(1,Math.ceil(items.length/8));
 state.toolboxPage=Math.max(0,Math.min(state.toolboxPage||0,pages-1));
 const first=state.toolboxPage*8;
 const rows=items.slice(first,first+8);
 return `<div class="toolbox-table-wrap"><table class="toolbox-table">
 <caption class="hidden">Strategy data and indicators with availability and historical dates</caption>
 <thead><tr><th scope="col">Data or rule</th><th scope="col">Availability</th><th scope="col" class="toolbox-dates">Source dates</th><th scope="col"><span class="hidden">Action</span></th></tr></thead>
 <tbody>${rows.length?rows.map(item=>`<tr>
 <td><strong>${esc(item.label)}</strong><code>@${esc(item.tag)}</code><small>${esc(item.description)}</small>${item.start&&item.end?`<small class="toolbox-mobile-dates">${esc(item.start)} to ${esc(item.end)}</small>`:''}</td>
 <td><span class="toolbox-status ${item.available?'ready':'pending'}">${item.available?'Ready':'Pending'}</span></td>
 <td class="toolbox-dates">${item.start&&item.end?`<span>${esc(item.start)}</span><span>to ${esc(item.end)}</span>`:item.available?'Check selected dates':'Awaiting requirements'}</td>
 <td><button class="button small ${item.available?'':'ghost'}" data-action="${item.available?'insert-reference':'reference-detail'}" data-reference="${esc(item.id)}" aria-label="${item.available?'Add @'+esc(item.tag)+' to strategy':'Why '+esc(item.label)+' is pending'}">${item.available?'+ Add':'Details'}</button></td>
 </tr>`).join(''):'<tr><td colspan="4" class="toolbox-empty">No matching items. Try another search or include pending items.</td></tr>'}</tbody></table></div>
 <div class="toolbox-footer"><span>${items.length?first+1:0}–${Math.min(first+8,items.length)} of ${items.length.toLocaleString()} items</span>
 <div><button class="button small" data-action="toolbox-page" data-step="-1" ${state.toolboxPage===0?'disabled':''}>Previous</button>
 <button class="button small" data-action="toolbox-page" data-step="1" ${state.toolboxPage===pages-1?'disabled':''}>Next</button></div></div>`;
}
function toolboxDetail(){
 const item=toolboxItem(state.toolboxDetail);
 if(!item)return '';
 return `<aside class="toolbox-detail" role="status"><div><strong>${esc(item.label)}</strong><p>${esc(item.reason||item.description)}</p>
 ${item.start?`<small>Source coverage ${esc(item.start)} to ${esc(item.end)}. Your exact stock list and dates are checked before a run.</small>`:''}</div>
 <button class="icon-button" data-action="close-reference-detail" aria-label="Close item details">×</button></aside>`;
}
function dataInventory(){
 const data=state.data;
 if(!data?.catalogue)return '';
 const categories=[['all','All items'],['fields','All fields'],['fundamentals','Fundamentals'],['indicators','Indicators'],['stocks','Stocks'],['universes','Universes'],['portfolio','Portfolio rules']];
 const pending=toolboxItems().filter(item=>!item.available).length;
 return `<section class="card strategy-toolbox" id="dataToolbox">
 <div class="card-head"><div><h2>Strategy toolbox</h2><p>Click + Add or type <kbd>@</kbd> in your strategy to reference an item.</p></div>
 <span class="toolbox-count">${data.symbols.length.toLocaleString()} stocks</span></div>
 <div class="toolbox-controls"><label class="toolbox-search">${icon('data')}<span class="hidden">Search strategy toolbox</span><input id="toolboxSearch" type="search" value="${esc(state.toolboxQuery||'')}" placeholder="Search ROE, EPS, prices, RSI, stocks…" autocomplete="off"></label>
 <label class="toolbox-pending"><input id="toolboxPending" type="checkbox" ${state.toolboxPending?'checked':''}> Include ${pending} pending items</label></div>
 <div class="toolbox-tabs" role="group" aria-label="Toolbox categories">${categories.map(([id,label])=>`<button data-action="toolbox-category" data-category="${id}" aria-pressed="${(state.toolboxCategory||'all')===id}">${label}</button>`).join('')}</div>
 <p class="toolbox-financial-note">Fundamental fields are listed even while pending. Imported values need verified publication dates before historical strategy use.</p><div id="toolboxResults">${toolboxRows()}</div><div id="toolboxDetail">${toolboxDetail()}</div>
 <details class="toolbox-about"><summary>About coverage and imported financial data</summary>
 <p>Source dates show the outer data window. Individual histories can contain gaps. Niyam checks every required stock and session before a backtest.</p>
 <p>Nifty 50 price benchmark · ${esc(data.benchmark_start)} to ${esc(data.benchmark_end)}.</p>
 ${data.source_archive?`<p>${data.source_archive.financial_observations.toLocaleString()} financial values are imported. ${data.source_archive.dated_financial_observations.toLocaleString()} have verified publication dates. Pending fields become usable when their requirements are met.</p>`:''}
 </details></section>`;
}
function renderToolbox(){
 const container=$('#dataToolbox');
 if(container)container.outerHTML=dataInventory();
}
function promptReferenceNames(){
 return [...new Set([...state.prompt.matchAll(/(?:^|[^\w@])@([A-Za-z][A-Za-z0-9_&-]*(?:\.[A-Za-z0-9_&-]+)*)/g)].map(match=>match[1]))];
}
function renderPromptReferences(){
 const container=$('#promptReferences');
 if(!container)return;
 container.innerHTML=promptReferenceNames().map(name=>{
   const item=toolboxItems().find(row=>row.tag.toLowerCase()===name.toLowerCase())||toolboxItems().find(row=>row.category==='stocks'&&row.tag.toLowerCase()===name.toLowerCase()+'.ns');
   return `<span class="reference-chip ${item?.available?'':'pending'}">${esc('@'+(item?.tag||name))}${item&&!item.available?' · pending':''}</span>`;
 }).join('');
}
function hideMentions(){
 state.mention=null;
 const menu=$('#mentionMenu');
 if(menu){menu.hidden=true;menu.innerHTML=''}
 $('#strategyPrompt')?.setAttribute('aria-expanded','false');
}
function showMentionMenu(){
 const input=$('#strategyPrompt'),menu=$('#mentionMenu');
 if(!input||!menu)return;
 const prefix=input.value.slice(0,input.selectionStart);
 const match=prefix.match(/(?:^|[\s(,])@([A-Za-z0-9_&.-]*)$/);
 if(!match){hideMentions();return}
 const query=match[1].toLowerCase();
 const rows=toolboxItems().filter(item=>
   !query||[item.tag,item.label].some(value=>value.toLowerCase().includes(query))
 ).sort((a,b)=>Number(b.available)-Number(a.available)).slice(0,7);
 if(!rows.length){hideMentions();return}
 const previous=state.mention;
 const selected=previous?.query===query?Math.min(previous.selected,rows.length-1):0;
 state.mention={start:prefix.lastIndexOf('@'),end:input.selectionStart,query,rows,selected};
 menu.hidden=false;
 menu.innerHTML=rows.map((item,index)=>`<button type="button" role="option" id="mention-${index}" aria-selected="${index===selected}" data-action="mention-reference" data-reference="${esc(item.id)}">
 <span><strong>${esc(item.label)}</strong><small>@${esc(item.tag)} · ${esc(item.category)}</small></span>
 <span class="toolbox-status ${item.available?'ready':'pending'}">${item.available?'Add':'Pending'}</span></button>`).join('');
 input.setAttribute('aria-expanded','true');
 input.setAttribute('aria-activedescendant','mention-'+selected);
}
function insertReference(id,replaceMention=false){
 const item=toolboxItem(id),input=$('#strategyPrompt');
 if(!item||!input)return;
 if(!item.available){
   state.toolboxDetail=id;
   renderToolbox();$('#toolboxDetail')?.scrollIntoView({behavior:'smooth',block:'center'});
   hideMentions();return;
 }
 const selection=replaceMention?state.mention:null;
 const start=selection?.start??input.selectionStart;
 const end=selection?.end??input.selectionEnd;
 const before=input.value.slice(0,start);
 const separator=before&&!/[\s(,]$/.test(before)?' ':'';
 const inserted=separator+item.insert+' ';
 const value=before+inserted+input.value.slice(end);
 if(value.length>12000){toast('Keep the strategy under 12,000 characters.');return}
 state.prompt=value;if(!REVIEW_MODE)storage.set('prompt',value);input.value=value;
 input.focus();input.setSelectionRange(start+inserted.length,start+inserted.length);
 hideMentions();renderPromptReferences();
}

function universeEditor(spec){
 const kind=spec.universe?.kind||'fixed', u=state.data?.universes;
 const hasIndices=!!u?.indices.some(i=>i.available);
 const types=[['fixed','Fixed ticker list',true],['market_cap','Historical top N by market cap',u?.market_cap.available],['index','Historical Nifty constituents',hasIndices]];
 const selector=`<label class="field span3">Stock universe<select id="universeKind">${types.map(([key,label,available])=>`<option value="${key}" ${key===kind?'selected':''} ${!available&&key!==kind?'disabled':''}>${label}${!available&&key!=='fixed'?' · history unavailable':''}</option>`).join('')}</select></label>`;
 if(kind==='market_cap')return selector+field('Number of stocks ranked by prior-month cap','universe.top_n',spec.universe.top_n,'number','min="1" max="750" step="1"','span3');
 if(kind==='index')return selector+`<label class="field span3">Index<select data-spec="universe.index_id">${(u?.indices||[]).map(i=>`<option value="${esc(i.id)}" ${i.id===spec.universe.index_id?'selected':''} ${!i.available?'disabled':''}>${esc(i.id)}</option>`).join('')}</select></label>`;
 return selector+field('Stocks · comma-separated tickers','symbols',spec.symbols.join(', '),'text','placeholder="Choose available tickers" list="tickerList"','span3')+`<datalist id="tickerList">${(state.data?.symbols||[]).map(x=>`<option value="${esc(x.symbol)}"></option>`).join('')}</datalist>`;
}
function formulaEditor(){
 return `<details><summary>Enter your own formulas</summary>
 <p class="subtext">Use the installed fields and functions listed above. Leave a formula blank to keep its current rule.</p>
 <label class="field">Buy formula<textarea id="entryFormula" maxlength="1500" placeholder="cross_above(sma(close, 20), sma(close, 50)) and rsi(close, 14) &lt; 70">${esc(state.formulaEntry||'')}</textarea></label>
 <label class="field">Sell formula<textarea id="exitFormula" maxlength="1500" placeholder="cross_below(sma(close, 20), sma(close, 50))">${esc(state.formulaExit||'')}</textarea></label>
 <button class="button small" data-action="apply-formulas">Check and apply formulas</button></details>`;
}
function taxEditor(spec){
 const defaults={enabled:false,stt_bps:10,stamp_buy_bps:1.5,gst_pct:18,short_term_pct:20,long_term_pct:12.5,annual_long_term_exemption:125000,cess_pct:4};
 spec.taxes={...defaults,...spec.taxes};
 const t=spec.taxes;
 return `<details><summary>With tax or without tax</summary><p class="subtext">Both views retain the same trades, position sizes, base fees and slippage. Enter base fees excluding the taxes listed here to avoid double-counting. The with-tax view estimates trade levies and capital-gains tax using the fixed rates below across the whole test.</p>
 <label class="field"><span><input type="checkbox" data-spec="taxes.enabled" ${t.enabled?'checked':''}> Include the with-tax comparison</span></label>
 <div class="form-grid">
 ${field('STT per side · basis points','taxes.stt_bps',t.stt_bps,'number','min="0" max="100" step="0.1"')}
 ${field('Stamp duty on buys · basis points','taxes.stamp_buy_bps',t.stamp_buy_bps,'number','min="0" max="100" step="0.1"')}
 ${field('GST on base fees · %','taxes.gst_pct',t.gst_pct,'number','min="0" max="100" step="0.1"')}
 ${field('Short-term capital gains · %','taxes.short_term_pct',t.short_term_pct,'number','min="0" max="100" step="0.1"')}
 ${field('Long-term capital gains · %','taxes.long_term_pct',t.long_term_pct,'number','min="0" max="100" step="0.1"')}
 ${field('Annual long-term exemption · ₹','taxes.annual_long_term_exemption',t.annual_long_term_exemption,'number','min="0"')}
 ${field('Cess on capital-gains tax · %','taxes.cess_pct',t.cess_pct,'number','min="0" max="100" step="0.1"')}
 </div><p class="subtext">This editable delivery-equity scenario applies the same rates to every trade, including same-day exits. Historical rate changes, intraday business-tax treatment, surcharge, external income, loss carry-forwards and grandfathering need individual treatment. The exemption is assumed fully available to this strategy.</p>
 <p class="subtext">Preset references · <a href="https://www.nseindia.com/static/invest/first-time-investor-sebi-turnover-fees-stt-other-levies" target="_blank" rel="noopener noreferrer">NSE trade levies</a> · <a href="https://www.pib.gov.in/newsite/erelcontentt.aspx?_d=2036604&amp;lang=2&amp;reg=48" target="_blank" rel="noopener noreferrer">CBDT capital-gains rates</a></p></details>`;
}
function taxComparison(result){
 const comparison=result.tax_comparison;
 if(!comparison)return '';
 const s=comparison.summary;
 return `<section class="card"><div class="card-head"><h3>Tax comparison on the same trades</h3></div><div class="card-body">
 <div class="action-row"><button class="button" data-action="tax-view" data-view="without_tax" aria-pressed="${state.taxView==='without_tax'}">Without tax</button><button class="button" data-action="tax-view" data-view="with_tax" aria-pressed="${state.taxView!=='without_tax'}">With tax estimate</button></div>
 <p><strong>${state.taxView==='without_tax'?'Showing without tax':'Showing with tax estimate'}</strong> · Total modelled taxes ${rupees(s.total_tax)}</p>
 <p class="subtext">STT ${rupees(s.stt)} · Stamp duty ${rupees(s.stamp_duty)} · GST on fees ${rupees(s.gst_on_fees)} · Capital gains and cess ${rupees(s.capital_gains_tax)}</p>
 <p class="subtext">Fixed selected rates apply across the test. Tax payments reduce reported wealth while the executed trades stay fixed. The benchmark remains before tax.</p>
 <p class="subtext">Ending value without tax ${rupees(result.metrics.ending_value)} · With tax estimate ${rupees(comparison.with_tax.metrics.ending_value)}</p>
 </div></section>`;
}
function coverageKey(){
 if(!state.spec)return '';
 return JSON.stringify({symbols:state.spec.symbols,universe:state.spec.universe||null,start:state.spec.start,end:state.spec.end,version:state.data?.version});
}
function coveragePanel(){
 if(!state.coverage||state.coverageKey!==coverageKey())return '';
 const c=state.coverage;
 return `<section class="card" id="coveragePanel" aria-live="polite">
 <div class="card-head"><h2>${c.ready?'Data coverage checked':'Choose a covered test period'}</h2></div>
 <div class="card-body"><p>${esc(c.summary)}</p>
 ${c.actual_start?`<p class="subtext">Available benchmark period within your dates · ${esc(c.actual_start)} to ${esc(c.actual_end)} · ${c.sessions} sessions</p>`:''}
 ${c.missing_bars?`<p>${c.missing_bars.toLocaleString()} required price bars are missing across ${c.affected_stocks} stocks.</p>`:''}
 ${!c.ready&&c.ranges.length?`<p>Complete price coverage for this stock selection</p><div class="action-row">${c.ranges.map((r,i)=>`<button class="button small" data-action="use-covered-range" data-index="${i}">${esc(r.start)} to ${esc(r.end)} · ${r.sessions} sessions</button>`).join('')}</div>`:''}
 ${!c.ready&&!c.ranges.length?'<p class="subtext">Market-data preparation is required for this selection. You can revise the stocks or check another period.</p>':''}
 ${c.issues.length?`<details><summary>Coverage details for ${c.issues.length} findings</summary><ul class="detail-list">${c.issues.map(i=>`<li>${esc(i.symbol)} · ${i.count} ${i.kind==='missing_prices'?'missing bars':'unmatched sessions'} · ${esc(i.first_date)} to ${esc(i.last_date)}</li>`).join('')}</ul></details>`:''}
 </div></section>`;
}
async function checkCoverage(){
 if(!requireUser()||!state.spec)return null;
 const key=coverageKey(),spec=clone(state.spec);
 const coverage=await api('/api/coverage',{method:'POST',body:spec,timeout:120000});
 if(key!==coverageKey()){toast('Your selection changed. Check coverage again.');return null}
 state.coverage=coverage;state.coverageKey=key;
 if(!coverage.ready&&state.view!=='studio')go('studio');
 render();document.querySelector('#coveragePanel')?.scrollIntoView({behavior:'smooth',block:'center'});
 return coverage;
}
function editor(){const s=state.spec;return `<section class="card editor"><div class="card-head"><h2>Your strategy, in plain sight</h2><span class="pill">Review before running</span></div><div class="card-body"><div class="field"><label for="strategyName">Strategy name</label><input id="strategyName" data-spec="name" value="${esc(s.name)}" maxlength="100"></div><div class="rule-row"><span class="rule-label">BUY WHEN</span><span>${esc(expr(s.entry))}</span></div><div class="rule-row"><span class="rule-label">SELL WHEN</span><span>${esc(expr(s.exit))}</span></div><div class="param-grid">${Object.entries(s.parameters).map(([k,v])=>field(esc(k),'parameters.'+k,v,'number','step="any"')).join('')}</div><div class="form-grid">${universeEditor(s)}${field('Starting capital · ₹','capital',s.capital,'number','min="1000" step="1000"')}${field('Start date','start',s.start,'date')}${field('End date','end',s.end,'date',`max="${today()}"`)}<label class="field">Stop-loss method<select data-spec="stop.kind">${[['none','No stop loss'],['percent','Fixed percentage'],['trailing_percent','Trailing percentage'],['atr','Fixed ATR multiple'],['trailing_atr','Trailing ATR multiple']].map(([k,label])=>`<option value="${k}" ${s.stop.kind===k?'selected':''}>${label}</option>`).join('')}</select></label>${field('Stop distance · % or ATR multiple','stop.value',s.stop.value,'number','min="0.01" max="100" step="0.1"')}${field('ATR period · daily bars','stop.atr_period',s.stop.atr_period,'number','min="2" max="500"')}${field('Take profit · % (blank = none)','take_profit_pct',s.take_profit_pct??'','number','min="0.1" step="0.1"')}${field(s.universe?'Portfolio allocation target · %':'Capital allocated per stock sleeve · %','allocation_pct',s.allocation_pct,'number','min="1" max="100"')}${field('Trading fees per side · basis points','costs.fee_bps',s.costs.fee_bps,'number','min="0" step="0.1"')}${field('Slippage per side · basis points','costs.slippage_bps',s.costs.slippage_bps,'number','min="0" step="0.1"')}</div><p class="subtext tiny" style="margin-top:12px">1 basis point = 0.01%. Fee assumptions are editable and do not automatically reproduce historical STT, GST, stamp duty or brokerage schedules.</p><p class="subtext tiny">Market data is managed by Niyam. Results use the Nifty 50 price index and exclude dividends.</p>${coveragePanel()}${taxEditor(s)}${formulaEditor()}<details><summary>Edit exact rules as JSON</summary><p class="subtext tiny">For advanced conditions. This is a validated rule format, never executable code.</p><textarea class="code-editor" id="jsonEditor" aria-label="Strategy JSON">${esc(JSON.stringify(s,null,2))}</textarea><button class="button small" data-action="apply-json">Apply rule edits</button></details><div class="action-row"><button class="button" data-action="save-strategy">${icon('library')} Save strategy</button><button class="button" data-action="validate">Check rules</button><button class="button" data-action="check-coverage">Check data coverage</button>${s.universe?'':'<button class="button ghost push" data-action="optimise">Optimise parameters</button>'}<button class="button primary" data-action="run">Run backtest ${icon('arrow')}</button></div></div></section>`}
function libraryView(){return head('A place for your <em>ideas.</em>','Save a clear set of rules, revisit an experiment, or start with a different hypothesis.','<button class="button primary" data-action="studio">New strategy +</button>')+(!state.user?empty('library','Your personal strategy library','Sign in to keep your strategies separate from everyone else’s.','<button class="button primary" data-action="auth">Sign in</button>'):!state.saved.length?empty('library','Your first idea belongs here','Build or load a strategy in the studio, then select Save strategy.','<button class="button primary" data-action="studio">Open the studio →</button>'):state.saved.map(x=>`<article class="list-card"><div><h3>${esc(x.name)}</h3><p>${esc(universeLabel(x.spec))} · ${esc(x.spec.start)} to ${esc(x.spec.end)}</p><p>${esc(expr(x.spec.entry))}</p></div><div class="list-actions"><button class="button small" data-action="load-strategy" data-id="${x.id}">Open strategy ↗</button><button class="icon-button" data-action="delete-strategy" data-id="${x.id}" aria-label="Delete ${esc(x.name)}">${icon('trash')}</button></div></article>`).join(''))}
function backtestsView(){return head('A record of the <em>evidence.</em>','Every test keeps its rules, costs, dates and dataset fingerprint. Revisit completed research and inspect its assumptions.','<button class="button" data-action="refresh-jobs">'+icon('refresh')+' Refresh</button>')+(!state.jobs.length?empty('backtests','Nothing tested. Nothing assumed.','Your completed and queued backtests will appear here. Choose a strategy and run your first test.','<button class="button primary" data-action="studio">Build a strategy →</button>'):state.jobs.map(x=>`<article class="list-card"><div><h3>${esc(x.request.strategy.name)} <span class="pill ${x.state==='failed'?'error':''}">${esc(x.state)}</span></h3><p>${esc(x.request.mode==='optimise'?'Parameter optimisation':'Backtest')} · ${esc(x.request.strategy.universe?universeLabel(x.request.strategy):x.request.strategy.symbols.length+' stocks')} · ${esc(x.request.strategy.start)} — ${esc(x.request.strategy.end)}</p>${x.error?`<p class="negative">${esc(x.error)}</p>`:''}${['queued','running'].includes(x.state)?`<div class="bar"><div class="bar-fill" style="width:${x.progress*100}%"></div></div>`:''}</div><div class="list-actions"><button class="button small" data-action="open-result" data-id="${x.id}">View ${x.state==='completed'?'report':'progress'} ↗</button></div></article>`).join(''))}
function optimisationView(){if(!state.spec||state.spec.universe)return head('Look for <em>robustness.</em>','Find parameters on one period. Test the winner on a later period it has never seen.')+empty('optimise','Start with a strategy','Choose or create your strategy before exploring different parameter values.','<button class="button primary" data-action="studio">Open strategy studio →</button>');return head('Better questions.<br><em>Stronger evidence.</em>','Explore a bounded parameter range. Niyam selects a winner using training data, then evaluates it once on the later validation period.')+`<div class="settings-grid"><section class="card"><div class="card-head"><h2>${esc(state.spec.name)}</h2><span class="pill">Training data only</span></div><div class="card-body"><p class="subtext">Enter candidate values separated by commas. Leave a parameter blank to keep its current value.</p><div class="form-grid">${Object.entries(state.spec.parameters).map(([k,v])=>`<label class="field span3">${esc(k)} <span class="muted">Current: ${esc(v)}</span><input data-range="${esc(k)}" value="${esc(state.space[k]||'')}" placeholder="Example: 10, 20, 30"><small>At most 20 values. Windows must be whole numbers from 1 to 1000.</small></label>`).join('')}</div><div class="form-grid"><label class="field">Selection objective<select id="objective"><option value="calmar" ${state.objective==='calmar'?'selected':''}>Growth / largest fall</option><option value="sharpe" ${state.objective==='sharpe'?'selected':''}>Sharpe ratio</option><option value="return" ${state.objective==='return'?'selected':''}>Total return</option></select></label><label class="field">Training share<input id="trainPct" type="number" min="50" max="85" value="${state.trainPct}"><small>The later ${100-state.trainPct}% is held out.</small></label><label class="field">Maximum trials<input id="maxTrials" type="number" min="1" max="100" value="${state.maxTrials}"></label><label class="field">Minimum training trades<input id="minTrades" type="number" min="0" value="${state.minTrades}"></label></div><div class="action-row"><button class="button" data-action="studio">Edit strategy</button><button class="button primary" data-action="run-optimise">Start optimisation ${icon('arrow')}</button></div></div></section><aside class="card"><div class="card-head"><h2>What makes the comparison honest?</h2></div><div class="card-body"><ul class="detail-list"><li>Candidate parameters see only the earlier training period.</li><li>The chosen parameters are frozen before testing the later period.</li><li>Validation starts in cash. Indicators may use earlier history to warm up.</li><li>Identical costs, price assumptions and benchmark alignment.</li><li>A fixed search seed makes the sampled combinations reproducible.</li></ul><div class="notice amber">A strong historical score is not proof of a durable edge. Repeated experiments against the same validation period make it less independent.</div></div></aside></div>`}
function chart(data,drawdown=false){if(!data?.length)return '';const W=1000,H=280,pad={l:65,r:25,t:25,b:35};const values=drawdown?data.map(x=>x.drawdown):data.flatMap(x=>[x.strategy,x.benchmark]);let min=Math.min(...values),max=Math.max(...values);const spread=max-min||1;min-=spread*.06;max+=spread*.08;const px=i=>pad.l+i/(data.length-1||1)*(W-pad.l-pad.r);const py=v=>pad.t+(max-v)/(max-min)*(H-pad.t-pad.b);const line=key=>data.map((d,i)=>`${px(i).toFixed(2)},${py(d[key]).toFixed(2)}`).join(' ');const ticks=Array.from({length:5},(_,i)=>min+(max-min)*i/4);const key=drawdown?'drawdown':'strategy';const area=`${pad.l},${H-pad.b} ${line(key)} ${W-pad.r},${H-pad.b}`;const labels=[0,Math.floor(data.length/2),data.length-1];return `<div class="chart-wrap"><svg class="chart" data-chart="${drawdown?'drawdown':'equity'}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${drawdown?'Strategy drawdown over time':'Strategy equity compared with Nifty 50'}"><defs><linearGradient id="${drawdown?'dd':'eq'}Fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="${drawdown?'#bc8d6b':'#709956'}" stop-opacity=".18"/><stop offset="100%" stop-color="#709956" stop-opacity="0"/></linearGradient></defs>${ticks.map(v=>`<line x1="${pad.l}" x2="${W-pad.r}" y1="${py(v)}" y2="${py(v)}" stroke="#edf1e7"/><text x="${pad.l-12}" y="${py(v)+3}" text-anchor="end">${drawdown?fmt(v,1)+'%':v>=100000?fmt(v/100000,1)+'L':fmt(v/1000,0)+'k'}</text>`).join('')}<polygon points="${area}" fill="url(#${drawdown?'dd':'eq'}Fill)"/>${!drawdown?`<polyline points="${line('benchmark')}" stroke="#b5bda0" stroke-width="2" fill="none" stroke-dasharray="5 4"/>`:''}<polyline points="${line(key)}" fill="none" stroke="${drawdown?'#b17f59':'#527e42'}" stroke-width="2.4"/>${labels.map(i=>`<text x="${px(i)}" y="${H-9}" text-anchor="${i===0?'start':i===data.length-1?'end':'middle'}">${esc(data[i].date)}</text>`).join('')}</svg><div class="chart-tooltip"></div></div>`}
function metric(label,value,foot,cls=''){return `<article class="metric"><div class="metric-label">${label}</div><div class="metric-value ${cls}">${value}</div><div class="metric-foot">${foot}</div></article>`}
function getShownResult(){
 const result=state.result?.result;
 if(!result)return null;
 if(result.mode==='optimise')return result.validation;
 if(result.tax_comparison&&state.taxView!=='without_tax'){
   return {...result,...result.tax_comparison.with_tax,assumptions:[...result.assumptions,...result.tax_comparison.assumptions]};
 }
 return result;
}
function reportView(){const job=state.result;if(!job)return head('Your backtest report','Open a completed run to inspect its evidence.')+empty('backtests','Choose a run','Your reports are listed in Backtests.','<button class="button primary" data-action="backtests">View backtests</button>');const title=esc(job.request.strategy.name);if(job.state!=='completed')return head(title,'Your job is processed by the research engine.')+`<div class="card"><div class="empty"><div class="empty-icon">${icon(job.state==='failed'?'shield':'clock')}</div><h2>${esc({queued:'Waiting in the research queue',running:'Testing your rules',failed:'This test needs attention',cancelled:'Test cancelled',interrupted:'Backend restarted'}[job.state]||job.state)}</h2><p>${esc(job.error||'You can leave this page. Your job will continue while the backend is running.')}</p>${['queued','running'].includes(job.state)?`<div class="bar"><div class="bar-fill" style="width:${job.progress*100}%"></div></div><p>${Math.round(job.progress*100)}% complete</p><button class="button" data-action="cancel-job" data-id="${job.id}">Cancel job</button>`:'<button class="button primary" data-action="studio">Review strategy</button><button class="button" data-action="check-coverage">Check available dates</button>'}</div></div>`;const result=job.result;const r=getShownResult();const m=r.metrics;const isOpt=result.mode==='optimise';return `${head(title,`${esc(r.start)} — ${esc(r.end)} · ${r.sessions} daily sessions · ${isOpt?'Unseen validation period':fmt(r.elapsed_ms,0)+' ms engine time'}`,'<button class="button" data-action="export-json">'+icon('download')+' Export report</button>')}${isOpt?`<div class="notice"><strong>These are validation results.</strong> Parameters were chosen on data ending ${esc(result.training_end)}. The chart below begins ${esc(result.validation_start)}. ${result.trials} candidates were tested.${result.note?' '+esc(result.note):''}<div class="action-row"><button class="button small" data-action="adopt-best">Use selected parameters →</button></div></div>`:''}${taxComparison(result)}<div class="metric-grid">${metric('Total return',pct(m.return_pct),`${m.excess_return_pp>=0?'+':''}${fmt(m.excess_return_pp)} percentage points vs Nifty 50`,m.return_pct>=0?'positive':'negative')}${metric('Annualised growth',pct(m.cagr_pct),'Growth rate over this exact period')}${metric('Largest fall',pct(m.max_drawdown_pct),'Maximum decline from a previous peak','negative')}${metric('Winning trades',pct(m.win_rate_pct),`${m.trades} closed trades · ${rupees(m.total_fees)} in fees`)}</div><div class="result-tabs" role="tablist">${[['overview','Overview'],['trades','Trade ledger'],['assumptions','Assumptions & audit'],...(isOpt?[['search','Parameter search']]:[])].map(([key,label])=>`<button class="result-tab ${state.tab===key?'active':''}" role="tab" aria-selected="${state.tab===key}" data-action="result-tab" data-tab="${key}">${label}</button>`).join('')}</div>${state.tab==='overview'?reportOverview(r):state.tab==='trades'?tradesView(r):state.tab==='search'&&isOpt?searchView(result):assumptionsView(r,result)}<div class="action-row"><button class="button" data-action="studio">Edit strategy</button><button class="button" data-action="signals">View daily signals</button>${r.universe?'':`<button class="button" data-action="paper-result">Start paper portfolio</button><button class="button primary push" data-action="watch-result">Watch this strategy ${icon('signals')}</button>`}</div>`}
function reportOverview(r){return `<section class="card"><div class="card-head"><h2>Growth of ${rupees(state.result.request.strategy.capital)}</h2><div class="chart-legend"><span><i class="legend-dot"></i>Your strategy</span><span><i class="legend-dot benchmark"></i>Nifty 50</span></div></div>${chart(r.curve)}</section><div class="two-col"><section class="card"><div class="card-head"><h3>How much did it fall along the way?</h3></div>${chart(r.curve,true)}</section><section class="card"><div class="card-head"><h3>A like-for-like comparison</h3></div><div class="table-wrap"><table><thead><tr><th>Metric</th><th>Strategy</th><th>Nifty 50</th></tr></thead><tbody>${[['Total return','return_pct'],['Annual growth','cagr_pct'],['Largest fall','max_drawdown_pct'],['Volatility','volatility_pct'],['Sharpe ratio','sharpe']].map(([label,key])=>`<tr><td>${label}</td><td>${key==='sharpe'?fmt(r.metrics[key]):pct(r.metrics[key])}</td><td>${key==='sharpe'?fmt(r.benchmark_metrics[key]):pct(r.benchmark_metrics[key])}</td></tr>`).join('')}</tbody></table></div></section></div><section class="card"><div class="card-head"><h3>Month by month</h3><span class="tiny muted">Returns include trading costs</span></div><div class="table-wrap"><table><thead><tr><th>Month</th><th>Strategy</th><th>Nifty 50</th><th>Difference</th></tr></thead><tbody>${r.monthly.map(x=>`<tr><td>${esc(x.month)}</td><td class="${x.strategy>=0?'heat-positive':'heat-negative'}">${pct(x.strategy)}</td><td>${pct(x.benchmark)}</td><td>${fmt(x.strategy-x.benchmark)} pp</td></tr>`).join('')}</tbody></table></div></section>`}
function tradesView(r){return `<section class="card"><div class="card-head"><h3>${r.trades.length} closed trades</h3><button class="button small" data-action="export-csv">${icon('download')} Download CSV</button></div>${r.trades.length?`<div class="table-wrap"><table><thead><tr><th>Stock</th><th>Entry date</th><th>Exit date</th><th>Shares</th><th>Entry</th><th>Exit</th><th>Net P&L</th><th>Fees</th><th>Exit reason</th></tr></thead><tbody>${r.trades.map(t=>`<tr><td>${esc(t.symbol)}</td><td>${esc(t.entry_date)}</td><td>${esc(t.exit_date)}</td><td>${t.quantity}</td><td>${fmt(t.entry_price)}</td><td>${fmt(t.exit_price)}</td><td class="${t.pnl>=0?'positive':'negative'}">${rupees(t.pnl)}</td><td>${fmt(t.fees)}</td><td>${esc(t.reason)}</td></tr>`).join('')}</tbody></table></div>`:'<div class="empty"><p>No completed trades occurred. This is a valid result; win rate and profit factor are undefined.</p></div>'}</section>`}
function assumptionsView(r,result){return `<div class="settings-grid"><section class="card"><div class="card-head"><h3>Execution and measurement</h3></div><div class="card-body"><ul class="detail-list">${r.assumptions.map(x=>`<li>${esc(x)}</li>`).join('')}</ul></div></section><section class="card"><div class="card-head"><h3>Checks and reproducibility</h3></div><div class="card-body">${r.warnings.map(x=>`<div class="notice amber">${esc(x)}</div>`).join('')||'<div class="notice">No additional execution warnings were produced for this run. This does not verify the source data against the exchange.</div>'}${r.universe?`<p><strong>${esc(universeLabel(result.strategy))}</strong> · ${esc(r.universe.source)} · ${r.universe.changes.length} membership snapshots. The report export includes each dated stock list.</p>`:''}<p class="subtext">Dataset fingerprint</p><pre>${esc(result.data_version)}</pre><p class="subtext">Engine ${esc(result.engine_version)} · Export the report to retain exact rules and costs.</p><details><summary>Exact strategy snapshot</summary><pre>${esc(JSON.stringify(result.selected_strategy||result.strategy,null,2))}</pre></details></div></section></div>`}
function searchView(result){return `<section class="card"><div class="card-head"><h3>Training leaderboard</h3><span class="tiny muted">${result.trials} evaluated · seed ${result.seed}</span></div><div class="table-wrap"><table><thead><tr><th>Parameters</th><th>Training score</th><th>Return</th><th>Largest fall</th><th>Trades</th><th>Eligible</th></tr></thead><tbody>${result.leaderboard.map(x=>`<tr><td>${esc(Object.entries(x.parameters).map(([k,v])=>k+': '+v).join(' · '))}</td><td>${fmt(x.score,3)}</td><td>${pct(x.metrics.return_pct)}</td><td>${pct(x.metrics.max_drawdown_pct)}</td><td>${x.metrics.trades}</td><td>${x.eligible?'Yes':'No'}</td></tr>`).join('')}</tbody></table></div></section>`}
function signalsView(){const {watches,alerts}=state.signalData;return head('Stay close to <em>your rules.</em>','End-of-day paper signals, evaluated when new completed daily candles arrive. Signals update as new daily data becomes available.','<button class="button" data-action="refresh-signals">'+icon('refresh')+' Check new bars</button>')+`<div class="notice amber">Daily candles support end-of-day checks, not instant intraday alerts. Watches use simulated model positions, not your actual broker holdings. No orders are placed.</div><div class="section-heading"><h2>Your active ideas <span class="badge-count">${watches.length}</span></h2>${state.spec?'<button class="button small" data-action="watch-draft">Watch current strategy +</button>':''}</div>${!watches.length?empty('signals','Let a tested idea run alongside you','After a backtest, choose Watch this strategy. Each watch waits for a newly completed daily bar and avoids duplicate alerts.','<button class="button" data-action="backtests">Choose a backtest →</button>'):watches.map(w=>`<article class="list-card"><div><h3>${esc(w.spec.name)} <span class="pill ${w.active?'':'warning'}">${w.active?'Watching':'Paused'}</span></h3><p>${esc(w.spec.symbols.join(', '))} · Last processed: ${esc(w.last_date||'Waiting')}</p>${w.error?`<p class="negative">${esc(w.error)}</p>`:''}</div><div class="list-actions"><button class="button small" data-action="toggle-watch" data-id="${w.id}" data-active="${w.active?'0':'1'}">${w.active?'Pause':'Resume'}</button><button class="icon-button" data-action="delete-watch" data-id="${w.id}" aria-label="Remove watch">${icon('trash')}</button></div></article>`).join('')}<div class="section-heading"><h2>Latest signals</h2><span>Completed bars only · Asia/Kolkata</span></div>${alerts.length?alerts.map(a=>`<article class="list-card"><div><h3>${esc(a.symbol)} <span class="pill">${esc(a.action.replaceAll('_',' '))}</span></h3><p>${esc(a.bar_date)} · ${esc(a.body.name)} · ${esc(a.body.timing)}</p><p>${esc(a.body.basis)}</p></div></article>`).join(''):'<div class="notice">No signals yet. An empty feed means no new qualifying event has been recorded.</div>'}`}
function guideView(){return head('From a thought<br>to a <em>testable idea.</em>','Describe a strategy, review its rules and explore the evidence.')+`<div class="flow-grid">${[['Describe your idea','Write in Hindi, English or Hinglish, attach your rules, or use a template.'],['Review the rules','Check entry and exit conditions, stops, stocks, dates and costs. Clarify anything that changes behaviour.'],['Run a historical test','Niyam uses managed daily market data. Close-based signals execute at the following open.'],['Compare the evidence','Inspect individual trades, return and drawdown alongside the Nifty 50 price index.'],['Try parameters carefully','Select on earlier training data and evaluate the frozen choice on a later holdout.'],['Follow daily signals','Watch completed daily candles using simulated positions. No broker orders are placed.']].map(([title,body])=>`<article class="flow-step"><h3>${title}</h3><p>${body}</p></article>`).join('')}</div><div class="notice">Daily long-only Indian cash equities, up to 100 selected stocks, whole shares and equal initial capital sleeves. Intraday trading, shorting, derivatives, leverage and portfolio rebalancing are outside this model. Historical simulations do not promise future returns.</div><div class="action-row"><button class="button primary" data-action="studio">Start an idea ${icon('arrow')}</button></div>`}

function render(){navigation();const pages={studio,library:libraryView,backtests:backtestsView,optimise:optimisationView,report:reportView,signals:signalsView,paper:paperView,guide:guideView};$('#main').innerHTML=(REVIEW_MODE?'<aside class="review-banner"><strong>Frontend review · sample data</strong><span>Explore every screen. No AI, backtest, Yahoo or broker connection. Results are illustrative and do not evaluate your rules. Changes reset when you reload.</span></aside>':'')+(pages[state.view]||studio)();if(REVIEW_MODE){const labels={run:'Preview sample report',interpret:'Preview rule review','run-optimise':'Preview optimisation','refresh-paper':'Refresh sample view','refresh-signals':'Refresh sample signals','save-strategy':'Save for this review'};for(const [action,label] of Object.entries(labels))document.querySelectorAll('[data-action="'+action+'"]').forEach(button=>button.textContent=label);}renderPromptReferences();}
function openAuth(mode='login'){if(PUBLIC_PREVIEW){$('#modal-root').innerHTML=`<div class="modal-overlay"><section class="modal" role="dialog" aria-modal="true" aria-labelledby="authTitle"><button class="close icon-button" data-action="close-modal" aria-label="Close">${icon('close')}</button><h2 id="authTitle">Explore Niyam</h2><p>This page previews the product. Sign-in and research will be available on the hosted workspace when it launches.</p><button class="button" data-action="close-modal">Continue exploring</button></section></div>`;return}state.authMode=mode;if(state.user){$('#modal-root').innerHTML=`<div class="modal-overlay"><section class="modal" role="dialog" aria-modal="true" aria-labelledby="authTitle"><button class="close icon-button" data-action="close-modal" aria-label="Close">${icon('close')}</button><div class="eyebrow">YOUR ACCOUNT</div><h2 id="authTitle">${esc(state.user.name)}</h2><p>${esc(state.user.email)}</p><p>Your strategies and results are private to this account in your workspace.</p><button class="button full" data-action="logout">${icon('logout')} Sign out</button></section></div>`;return}const signup=mode==='signup',recovery=mode==='recover';$('#modal-root').innerHTML=`<div class="modal-overlay"><section class="modal" role="dialog" aria-modal="true" aria-labelledby="authTitle"><button class="close icon-button" data-action="close-modal" aria-label="Close">${icon('close')}</button><div class="eyebrow">NIYAM WORKSPACE</div><h2 id="authTitle">${signup?'A space for your ideas.':recovery?'Recover your account.':'Welcome back.'}</h2><p>${signup?'Create your Niyam account. Save your recovery code when it appears.':recovery?'Use the recovery code you saved when creating your account.':'Sign in to save strategies, run tests and follow daily signals.'}</p>${!state.online?'<div class="notice">The service is reconnecting. Please try again shortly.</div>':''}<form id="authForm">${signup?'<label class="field">Your name<input name="name" autocomplete="name" maxlength="60" required></label>':''}<label class="field">Email<input type="email" name="email" autocomplete="username" maxlength="254" required></label>${recovery?'<label class="field">Recovery code<input name="recovery_code" autocomplete="off" required></label>':''}<label class="field">${recovery?'New password':'Password'}<input type="password" name="password" minlength="${signup||recovery?'12':'1'}" maxlength="256" autocomplete="${signup||recovery?'new-password':'current-password'}" required>${signup?'<small>At least 12 characters. Use a unique password.</small>':''}</label><div id="authError" class="auth-error" role="alert"></div><button type="submit" class="button primary full" ${state.online?'':'disabled'}>${signup?'Create account':recovery?'Reset password':'Sign in'} ${icon('arrow')}</button></form><div class="auth-switch">${signup?'Already have an account?':'New here?'} <button class="text-button" data-action="auth-switch" data-mode="${signup?'login':'signup'}">${signup?'Sign in':'Create account'}</button></div>${!signup&&!recovery?'<div class="auth-switch"><button class="text-button" data-action="auth-switch" data-mode="recover">Forgot password? Use recovery code</button></div>':''}<p class="tiny muted">Email is an account identifier. Mailbox verification and email-based recovery are not enabled. Save your recovery code.</p></section></div>`;setTimeout(()=>$('#authForm input')?.focus(),20)}
function showRecovery(code,reset=false){$('#modal-root').innerHTML=`<div class="modal-overlay"><section class="modal" role="dialog" aria-modal="true" aria-labelledby="recoveryTitle"><div class="eyebrow">KEEP THIS SOMEWHERE SAFE</div><h2 id="recoveryTitle">Your recovery code.</h2><p>This code can reset your password. It is shown only now. Save it in your password manager; do not share it.</p><div class="recovery-code">${esc(code)}</div><div class="action-row"><button class="button" data-action="copy" data-value="${esc(code)}">${icon('copy')} Copy code</button><button class="button primary" data-action="${reset?'recovery-done':'close-modal'}">I have saved it →</button></div></section></div>`}
function download(name,content,type='text/plain'){const blob=new Blob([content],{type});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
function csv(rows){if(!rows.length)return 'symbol,entry_date,exit_date,quantity,entry_price,exit_price,pnl,fees,reason\n';const keys=Object.keys(rows[0]);const cell=value=>{let s=String(value??'');if(typeof value==='string'&&/^[=+@\-\t\r]/.test(s))s="'"+s;return '"'+s.replaceAll('"','""')+'"'};return [keys.map(cell).join(','),...rows.map(row=>keys.map(k=>cell(row[k])).join(','))].join('\r\n')}
async function pollJob(id){clearTimeout(state.poll);try{const out=await api('/api/jobs/'+id);state.result=out;if(state.view==='report'){render();if(['queued','running'].includes(out.state))state.poll=setTimeout(()=>pollJob(id),1500)}}catch(e){toast(e.message)}}
async function run(mode){
 if(!requireUser()||state.busy)return;
 if(!state.spec)throw Error('Load a template or build a strategy first.');
 state.busy=true;
 try{
   const coverage=await checkCoverage();
   if(!coverage||!coverage.ready)return;
   const body={strategy:clone(state.spec),mode};
   if(mode==='optimise'){
     body.search_space={};
     for(const [key,value] of Object.entries(state.space)){
       if(!value.trim())continue;
       const values=[...new Set(value.split(',').map(x=>Number(x.trim())))];
       if(values.some(x=>!Number.isFinite(x)))throw Error('Parameter ranges must contain numbers separated by commas.');
       body.search_space[key]=values;
     }
     Object.assign(body,{objective:state.objective,train_pct:Number(state.trainPct),max_trials:Number(state.maxTrials),min_trades:Number(state.minTrades)});
   }
   let out;
   try{
     out=await api('/api/jobs',{method:'POST',body,timeout:120000});
   }catch(error){
     if(error.coverage){
       state.coverage=error.coverage;
       state.coverageKey=coverageKey();
       go('studio');render();return;
     }
     throw error;
   }
   state.result={id:out.id,state:'queued',progress:0,request:body};
   state.tab='overview';state.taxView='with_tax';go('report');
 }finally{
   state.busy=false;
 }
}
async function runInterpret(clarify=false){if(!requireUser())return;if(state.prompt.trim().length<3)throw Error('Describe the strategy you want to test.');if(clarify){const pending=(state.interpretation.questions||[]).map((q,i)=>({question:q.question,answer:document.querySelector(`[data-answer="${i}"]`)?.value||''}));if(pending.some(x=>!x.answer.trim()))throw Error('Please answer the specific question before continuing.');state.answers.push(...pending)}else state.answers=[];const defaults=state.spec||getTemplate('trend');const out=await api('/api/interpret',{method:'POST',body:{text:state.prompt,attachment_ids:state.attachments.map(x=>x.id),defaults,answers:state.answers,references:promptReferenceNames()},timeout:280000});state.interpretation=out;if(out.status==='unavailable'&&!out.strategy){state.spec=null;state.coverage=null;state.space={}}if(out.status==='ready'||out.strategy&&out.coverage){state.spec=out.strategy;state.space=Object.fromEntries(Object.entries(out.search_space||{}).map(([k,v])=>[k,v.join(', ')]))}if(out.coverage&&out.strategy){state.coverage=out.coverage;state.coverageKey=coverageKey()}render();document.querySelector('.question-card,.notice')?.scrollIntoView({behavior:'smooth',block:'center'});}
async function watch(spec){if(!requireUser())return;const out=await api('/api/signals',{method:'POST',body:spec});toast(out.message);go('signals')}
const actions={
 'toolbox-category'(el){state.toolboxCategory=el.dataset.category;state.toolboxPage=0;renderToolbox()},
 'toolbox-page'(el){state.toolboxPage=(state.toolboxPage||0)+Number(el.dataset.step);$('#toolboxResults').innerHTML=toolboxRows()},
 'insert-reference'(el){insertReference(el.dataset.reference)},
 'mention-reference'(el){insertReference(el.dataset.reference,true)},
 'reference-detail'(el){state.toolboxDetail=el.dataset.reference;$('#toolboxDetail').innerHTML=toolboxDetail()},
 'close-reference-detail'(){state.toolboxDetail=null;$('#toolboxDetail').innerHTML=''},

 menu:()=>$('#sidebar').classList.toggle('open'),
 paper:()=>go('paper'),
 'paper-draft'(){return startPaper(state.spec)},
 'paper-result'(){const spec=clone(state.result.request.strategy);if(state.result.result.mode==='optimise')spec.parameters=clone(state.result.result.best_parameters);return startPaper(spec)},
 async 'refresh-paper'(){if(!requireUser())return;state.paper=await api('/api/paper/refresh',{method:'POST',timeout:280000});render();toast('Yahoo refresh checked. See each portfolio’s data date.')},
 async 'toggle-paper'(el){await api('/api/paper/'+el.dataset.id,{method:'PUT',body:{active:el.dataset.active==='1'}});await route()},
 async 'delete-paper'(el){if(!confirm('Remove this paper portfolio and its simulated ledger?'))return;await api('/api/paper/'+el.dataset.id,{method:'DELETE'});await route()},
 studio:()=>go('studio'),guide:()=>go('guide'),backtests:()=>go('backtests'),optimise:()=>go('optimise'),signals:()=>go('signals'),
 auth:()=>openAuth(),'auth-switch':el=>openAuth(el.dataset.mode),'close-modal':()=>{$('#modal-root').innerHTML='';$('#authButton').focus()},'recovery-done':()=>openAuth('login'),
 async logout(){await api('/api/auth/logout',{method:'POST'});state.token='';state.user=null;state.spec=null;state.prompt='';state.interpretation=null;state.result=null;state.saved=[];state.jobs=[];state.paper=[];state.attachments=[];state.signalData={watches:[],alerts:[]};storage.remove('token');storage.remove('prompt');$('#modal-root').innerHTML='';render();toast('Signed out.')},
 template(el){state.coverage=null;state.formulaEntry='';state.formulaExit='';state.spec=getTemplate(el.dataset.kind);state.interpretation=null;state.space={};state.answers=[];state.prompt={trend:'Buy when the 20-day SMA crosses above the 50-day SMA. Sell on the reverse crossover. Use a fixed 5% stop loss.',rsi:'Buy when 14-day Wilder RSI is below 30. Sell when it is above 60. Use a fixed 5% stop loss.',breakout:'Buy when the daily close is above the previous 55-day high. Exit below the previous 20-day low. Use a fixed 5% stop loss.'}[el.dataset.kind];render();toast('Template loaded. Review the rules, stocks and costs.');$('.editor')?.scrollIntoView({behavior:'smooth',block:'start'})},
 attach(){if(requireUser())$('#documentFile').click()},
 async 'remove-attachment'(el){await api('/api/attachments/'+el.dataset.id,{method:'DELETE'});state.attachments=state.attachments.filter(x=>x.id!==el.dataset.id);render()},
 interpret:()=>runInterpret(false),clarify:()=>runInterpret(true),
 'answer-option'(el){const input=document.querySelector(`[data-answer="${el.dataset.question}"]`);if(input)input.value=el.dataset.value},
 async 'apply-formulas'(){
   if(!requireUser())return;
   state.spec=await api('/api/formulas',{method:'POST',body:{strategy:state.spec,entry:state.formulaEntry||'',exit:state.formulaExit||''}});
   state.formulaEntry='';state.formulaExit='';state.interpretation=null;render();toast('Validated formulas applied.');
 },
 async 'apply-json'(){if(!requireUser())return;let spec;try{spec=JSON.parse($('#jsonEditor').value)}catch{throw Error('The JSON has a syntax issue. Check commas, quotes and brackets.')}await api('/api/validate',{method:'POST',body:spec});state.spec=spec;render();toast('Validated rule edits applied.')},
 async validate(){if(!requireUser())return;await api('/api/validate',{method:'POST',body:state.spec});await checkCoverage()},
 'check-coverage'(){if(state.view==='report'&&state.result){state.spec=clone(state.result.request.strategy);go('studio')}return checkCoverage()},
 'use-covered-range'(el){if(state.coverageKey!==coverageKey())throw Error('Check coverage for the current selection first.');const range=state.coverage.ranges[Number(el.dataset.index)];if(!range)return;state.spec.start=range.start;state.spec.end=range.end;state.coverage=null;render();toast('Dates updated. Review them, then run your backtest.')},
 async 'save-strategy'(){if(!requireUser())return;await api('/api/strategies',{method:'POST',body:state.spec});toast('Strategy saved to your account.')},
 'load-strategy'(el){const row=state.saved.find(x=>x.id===el.dataset.id);if(row){state.spec=clone(row.spec);state.interpretation=null;state.space={};go('studio')}},
 async 'delete-strategy'(el){if(!confirm('Delete this saved strategy? Existing backtest reports will stay available.'))return;await api('/api/strategies/'+el.dataset.id,{method:'DELETE'});await route()},
 run:()=>run('backtest'),'run-optimise':()=>run('optimise'),'refresh-jobs':()=>route(),
 async 'open-result'(el){state.taxView='with_tax';state.result=await api('/api/jobs/'+el.dataset.id);state.tab='overview';state.spec=clone(state.result.request.strategy);go('report')},
 async 'cancel-job'(el){await api('/api/jobs/'+el.dataset.id+'/cancel',{method:'POST'});toast('Cancellation requested. The engine will stop at the next safe checkpoint.')},
 'tax-view'(el){state.taxView=el.dataset.view;render()},
 'result-tab'(el){state.tab=el.dataset.tab;render()},
 'export-json'(){download('niyam-backtest-report.json',JSON.stringify(state.result.result,null,2),'application/json')},
 'export-csv'(){download('niyam-trades.csv',csv(getShownResult().trades),'text/csv;charset=utf-8')},
 'adopt-best'(){state.spec=clone(state.result.request.strategy);state.spec.parameters=clone(state.result.result.best_parameters);state.interpretation=null;go('studio');toast('Selected parameters copied into the strategy editor.')},
 'watch-result'(){const spec=clone(state.result.request.strategy);if(state.result.result.mode==='optimise')spec.parameters=clone(state.result.result.best_parameters);return watch(spec)},
 'watch-draft'(){return watch(state.spec)},
 async 'refresh-signals'(){if(!requireUser())return;state.signalData=await api('/api/signals/refresh',{method:'POST',timeout:120000});render();toast('New completed bars checked.')},
 async 'toggle-watch'(el){await api('/api/signals/'+el.dataset.id,{method:'PUT',body:{active:el.dataset.active==='1'}});await route()},
 async 'delete-watch'(el){if(!confirm('Remove this watch and its recorded alerts? Backtest reports will stay available.'))return;await api('/api/signals/'+el.dataset.id,{method:'DELETE'});await route()},
 async 'delete-report'(el){if(!confirm('Delete this saved report?'))return;await api('/api/jobs/'+el.dataset.id,{method:'DELETE'});await route()},
 async copy(el){try{await navigator.clipboard.writeText(el.dataset.value);toast('Copied.')}catch{toast('Copy unavailable. Select and copy the displayed text.')}}
};
document.addEventListener('click',async event=>{const el=event.target.closest('[data-action]');if(!el||el.disabled)return;const action=actions[el.dataset.action];if(!action)return;event.preventDefault();const before=el.innerHTML;try{const result=action(el);if(result&&typeof result.then==='function'){el.disabled=true;el.innerHTML='<span class="spinner"></span> Working…';await result}}catch(e){toast(e.message||'Please check the connection and try again.')}finally{if(el.isConnected){el.disabled=false;el.innerHTML=before}}});
document.addEventListener('input',event=>{const el=event.target;if(el.id==='entryFormula')state.formulaEntry=el.value;if(el.id==='exitFormula')state.formulaExit=el.value;if(el.id==='strategyPrompt'){state.prompt=el.value;if(!REVIEW_MODE)storage.set('prompt',el.value);renderPromptReferences();showMentionMenu()}if(el.id==='toolboxSearch'){state.toolboxQuery=el.value;state.toolboxPage=0;$('#toolboxResults').innerHTML=toolboxRows()}if(el.dataset.spec&&state.spec){let value=el.type==='checkbox'?el.checked:el.type==='number'?(el.value===''?null:Number(el.value)):el.value;const path=el.dataset.spec.split('.');if(path.some(k=>['__proto__','prototype','constructor'].includes(k)))return;if(path[0]==='symbols')value=el.value.split(',').map(s=>s.trim().toUpperCase()).filter(Boolean);let target=state.spec;for(const part of path.slice(0,-1))target=target[part];target[path.at(-1)]=value;if($('#jsonEditor')&&el.id!=='jsonEditor')$('#jsonEditor').value=JSON.stringify(state.spec,null,2)}if(el.dataset.range)state.space[el.dataset.range]=el.value;if(['objective','trainPct','maxTrials','minTrades'].includes(el.id))state[el.id]=el.value});
document.addEventListener('change',async event=>{if(event.target.id==='toolboxPending'){state.toolboxPending=event.target.checked;state.toolboxPage=0;renderToolbox();return}if(event.target.id==='universeKind'&&state.spec){
 const kind=event.target.value;
 if(kind==='fixed'){state.spec.universe=null;}
 else{
   state.spec.symbols=[];
   state.spec.universe=kind==='market_cap'?{kind,top_n:50}:{kind,index_id:state.data.universes.indices.find(i=>i.available).id};
 }
 render();return;
}if(event.target.id!=='documentFile')return;const file=event.target.files[0];if(!file)return;try{if(state.attachments.length>=3)throw Error('Attach up to three documents.');if(file.size>8*1024*1024)throw Error('Choose a document smaller than 8 MB.');const data=new FormData();data.append('file',file);toast('Reading the document…');const out=await api('/api/attachments',{method:'POST',body:data,timeout:60000});state.attachments.push(out);render();toast(`${out.name}: ${out.characters.toLocaleString()} characters extracted.`)}catch(e){toast(e.message)}finally{event.target.value=''}});
document.addEventListener('submit',async event=>{if(event.target.id!=='authForm')return;event.preventDefault();const form=event.target;const button=form.querySelector('[type=submit]');const before=button.innerHTML;button.disabled=true;button.innerHTML='<span class="spinner"></span> Connecting…';try{const body=Object.fromEntries(new FormData(form).entries());const mode=state.authMode;const out=await api('/api/auth/'+(mode==='recover'?'recover':mode),{method:'POST',body,auth:false});if(mode==='recover'){showRecovery(out.recovery_code,true);return}state.user=out.user;state.data=await api('/api/data');$('#modal-root').innerHTML='';render();if(out.recovery_code)showRecovery(out.recovery_code);else{toast('Welcome back.');await route()}}catch(e){const error=$('#authError');if(form.id==='authForm'&&error)error.textContent=e.message;else toast(e.message)}finally{if(button.isConnected){button.disabled=false;button.innerHTML=before}}});
document.addEventListener('keydown',event=>{const modal=$('.modal');if(!modal)return;if(event.key==='Escape'&&!$('.recovery-code')){$('#modal-root').innerHTML='';$('#authButton').focus()}if(event.key==='Tab'){const elements=[...modal.querySelectorAll('button:not([disabled]),input,a[href],textarea')];if(!elements.length)return;const first=elements[0],last=elements.at(-1);if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus()}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus()}}});
document.addEventListener('pointermove',event=>{const svg=event.target.closest('[data-chart]');if(!svg)return;const r=getShownResult();if(!r?.curve.length)return;const rect=svg.getBoundingClientRect();const x=(event.clientX-rect.left)/rect.width*1000;const index=Math.max(0,Math.min(r.curve.length-1,Math.round((x-65)/910*(r.curve.length-1))));const row=r.curve[index];const tip=svg.parentElement.querySelector('.chart-tooltip');tip.style.display='block';tip.style.left=Math.min(Math.max(0,event.clientX-rect.left),Math.max(0,rect.width-200))+'px';tip.style.top='18px';tip.innerHTML=`<strong>${esc(row.date)}</strong><br>${svg.dataset.chart==='drawdown'?'Drawdown: '+pct(row.drawdown):'Strategy: '+rupees(row.strategy)+'<br>Nifty 50: '+rupees(row.benchmark)}`});
document.addEventListener('pointerout',event=>{const svg=event.target.closest('[data-chart]');if(svg&&!svg.contains(event.relatedTarget))svg.parentElement.querySelector('.chart-tooltip').style.display='none'});
window.addEventListener('hashchange',route);
route();
refreshWorkspace(true);
setInterval(()=>refreshWorkspace(),30000);

document.addEventListener('keydown',event=>{
 if(event.target.id!=='strategyPrompt'||!state.mention)return;
 const mention=state.mention;
 if(event.key==='Escape'){event.preventDefault();hideMentions();return}
 if(event.key==='ArrowDown'||event.key==='ArrowUp'){
   event.preventDefault();
   mention.selected=(mention.selected+(event.key==='ArrowDown'?1:-1)+mention.rows.length)%mention.rows.length;
   showMentionMenu();return;
 }
 if(event.key==='Enter'){
   event.preventDefault();insertReference(mention.rows[mention.selected].id,true);
 }
});
document.addEventListener('click',event=>{
 if(!event.target.closest('#mentionMenu')&&event.target.id!=='strategyPrompt')hideMentions();
});
document.addEventListener('keyup',event=>{
 if(event.target.id==='strategyPrompt'&&['ArrowLeft','ArrowRight','Home','End'].includes(event.key))showMentionMenu();
});

async function startPaper(spec){if(!requireUser())return;if(!spec)throw Error('Choose and review a strategy in the studio first.');const out=await api('/api/paper',{method:'POST',body:spec});toast(out.message);go('paper')}
function paperView(){
 const portfolios=state.user?(state.paper||[]):[];
 return head('Test forward with <em>paper money.</em>','Yahoo daily prices · starts in cash · simulated trades only')+'<div class="action-row"><button class="button" data-action="refresh-paper">'+icon('refresh')+' Refresh Yahoo prices</button></div>'+
 `<div class="notice">Automatic checks run every 15 minutes while this local server is running. Only completed candles are used, after 4 pm India time. Each portfolio begins with the next session’s close; a qualifying signal can fill at the following open. Yahoo availability and delays can vary.</div>
 <div class="section-heading"><h2>Your paper portfolios</h2>${state.spec?'<button class="button primary small" data-action="paper-draft">Start current strategy +</button>':'<button class="button" data-action="studio">Choose a strategy →</button>'}</div>
 <p>Fixed lists of up to 20 stocks · equal initial capital per stock · fees and slippage included. Historical top-N membership, fundamental rules, tax estimates and the VM optimiser are not supported in paper mode yet.</p>
 ${portfolios.length?portfolios.map(p=>{const r=p.result;return `<article class="card paper-card"><div class="card-head"><div><h2>${esc(p.spec.name)}</h2><p>${esc(p.spec.symbols.join(', '))}</p></div><span class="pill">${p.active?'Tracking':'Paused'}</span></div><div class="paper-body"><p>Tracking from ${esc(p.start)} · Data through ${esc(r?.end||'Waiting for first completed session')} · ${rupees(p.spec.capital)} starting cash</p>${p.error?`<div class="notice amber">${esc(p.error)} ${r?'Last saved results remain below.':''}</div>`:''}
 ${r?`<div class="metric-grid">${metric('Portfolio value',rupees(r.metrics.ending_value),'Marked to completed close')}${metric('Return',pct(r.metrics.return_pct),'Since paper start')}${metric('Cash',rupees(r.cash),'Across fixed sleeves')}${metric('Closed trades',r.metrics.trades,'Simulated fills')}</div>
 <details open><summary>Holdings & next-session signals</summary><div class="toolbox-table-wrap"><table class="toolbox-table"><thead><tr><th>Stock</th><th>Shares</th><th>Last price</th><th>Next action</th></tr></thead><tbody>${r.positions.map(x=>`<tr><td>${esc(x.symbol)}</td><td>${x.model_quantity}</td><td>${rupees(x.last_price)}</td><td>${esc(x.next_action)}</td></tr>`).join('')}</tbody></table></div></details>
 <details><summary>Performance history · ${r.sessions} sessions</summary><div class="toolbox-table-wrap"><table class="toolbox-table"><thead><tr><th>Date</th><th>Portfolio</th><th>Nifty 50</th></tr></thead><tbody>${r.curve.slice(-90).reverse().map(x=>`<tr><td>${esc(x.date)}</td><td>${rupees(x.strategy)}</td><td>${rupees(x.benchmark)}</td></tr>`).join('')}</tbody></table></div><p>Latest 90 sessions shown.</p></details>
 <details><summary>Closed-trade ledger · ${r.trades.length} trades</summary>${r.trades.length?tradesView(r):'<p>No closed trades yet. Open holdings appear above.</p>'}</details><p class="tiny muted">${esc(r.basis)}</p>`:'<div class="notice">Your portfolio is in cash. Performance and signals will appear after its first completed session. Prices used for indicator warm-up do not create past trades.</div>'}
 <div class="action-row"><button class="button small" data-action="toggle-paper" data-id="${esc(p.id)}" data-active="${p.active?'0':'1'}">${p.active?'Pause checks':'Resume & catch up'}</button><button class="button small" data-action="delete-paper" data-id="${esc(p.id)}">Remove</button></div></div></article>`}).join(''):'<div class="notice">No paper portfolios yet. Review a fixed-stock strategy in the studio, then choose Start current strategy here, or Start paper portfolio from a backtest report.</div>'}`;
}
