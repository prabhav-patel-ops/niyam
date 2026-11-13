/* Frontend review fixtures. Entirely synthetic; never calls a backend or provider. */
'use strict';
if(window.NIYAM_REVIEW_MODE){
 window.NIYAM_REVIEW=(()=>{
  const copy=x=>JSON.parse(JSON.stringify(x));
  const dates=Array.from({length:90},(_,i)=>{const d=new Date(Date.UTC(2025,0,1+i));return d.toISOString().slice(0,10)}).filter(d=>![0,6].includes(new Date(d+'T12:00:00Z').getUTCDay()));
  const start=dates[0],end=dates.at(-1);
  const symbols=['RELIANCE.NS','TCS.NS','INFY.NS','HDFCBANK.NS','ICICIBANK.NS','ITC.NS'];
  const tax={enabled:true,stt_bps:10,stamp_buy_bps:1.5,gst_pct:18,short_term_pct:20,long_term_pct:12.5,annual_long_term_exemption:125000,cess_pct:4};
  const makeSpec=(kind='trend')=>({...copy(window.NIYAM_TEMPLATES[kind]),symbols:symbols.slice(0,3),start,end,universe:null,taxes:copy(tax),notes:['FRONTEND REVIEW: sample rules. No interpretation or calculations performed.'],price_basis_confirmed:true});
  const catalogue=copy(window.NIYAM_REVIEW_CATALOGUE||[]);
  const catalog={ready:true,version:'frontend-sample-v1',symbols:symbols.map(symbol=>({symbol,start,end,rows:dates.length})),rows:dates.length*symbols.length,benchmark_rows:dates.length,benchmark_start:start,benchmark_end:end,
   catalogue,formulas:{price_fields:['open','high','low','close','volume','benchmark_close'],fundamental_fields:[],unavailable_fundamentals:['roe','roce','eps','revenue','pe','pb','ps'],functions:['sma','ema','rsi','atr','highest','lowest','roc','lag','cross_above','cross_below','std','variance','covariance']},
   universes:{market_cap:{available:true,start,end,usable_from:start,usable_until:end,snapshots:3},indices:['NIFTY 50','NIFTY 500','NIFTY TOTAL MARKET'].map(id=>({id,available:false}))},capabilities:[],source_archive:{financial_observations:0,dated_financial_observations:0}};
  function report(spec){
   const capital=Number(spec.capital)||100000;
   const curve=dates.map((date,i)=>({date,strategy:capital*(1+i*.0013+Math.sin(i/6)*.014),benchmark:capital*(1+i*.0008),drawdown:-Math.abs(Math.sin(i/8))*2.8}));
   curve[0].strategy=capital;
   const metrics={return_pct:8.4,cagr_pct:38.8,max_drawdown_pct:2.8,sharpe:1.31,volatility_pct:12.5,ending_value:curve.at(-1).strategy,trades:3,win_rate_pct:66.67,profit_factor:1.6,total_fees:450,exposure_pct:61,excess_return_pp:3.2};
   const trades=(spec.symbols.length?spec.symbols:symbols).slice(0,3).map((symbol,i)=>({symbol,entry_date:dates[5+i*3],exit_date:dates[25+i*3],quantity:10,entry_price:1000+i*200,exit_price:1040+i*200,pnl:380,fees:20,reason:'Exit rule'}));
   const monthly=[{month:'2025-01',strategy:3.1,benchmark:1.8},{month:'2025-02',strategy:-.7,benchmark:-.3},{month:'2025-03',strategy:5.9,benchmark:3.7}];
   const r={metrics,benchmark_metrics:{...metrics,return_pct:5.2,cagr_pct:23.5,max_drawdown_pct:3.1,sharpe:1.05},curve,trades,monthly,positions:[],start,end,sessions:dates.length,elapsed_ms:0,warnings:['SAMPLE UI FIXTURE: figures are illustrative and internally simplified. No strategy has been backtested.'],assumptions:['FRONTEND REVIEW ONLY. No market data, engine, AI, Yahoo or broker connection.','The same sample report is displayed for any edited strategy. These figures do not evaluate its rules.'],mode:'backtest',strategy:copy(spec),data_version:'SYNTHETIC-UI-FIXTURE',engine_version:'preview-only'};
   if(spec.taxes?.enabled)r.tax_comparison={summary:{stt:200,stamp_duty:15,gst_on_fees:81,capital_gains_tax:704,total_tax:1000},with_tax:{metrics:{...metrics,ending_value:metrics.ending_value-1000,return_pct:7.4},curve:curve.map((x,i)=>({...x,strategy:x.strategy-i/(curve.length-1)*1000})),monthly:copy(monthly)},assumptions:['Synthetic tax-view illustration, not a tax calculation.']};
   return r;
  }
  let counter=0;
  const id=()=>`sample-${++counter}`;
  const spec=makeSpec();
  const job={id:id(),state:'completed',progress:1,created:1735689600,request:{strategy:copy(spec),mode:'backtest'},result:report(spec)};
  const paperSpec={...makeSpec('rsi'),taxes:{...tax,enabled:false}};
  function portfolio(s){const r=report(s);r.positions=s.symbols.map((symbol,i)=>({symbol,model_quantity:i?0:20,last_price:1000,next_action:i?'ENTRY':'HOLD'}));r.cash=r.metrics.ending_value-20000;r.basis='SAMPLE portfolio for interface review. No prices have been downloaded and no forward trading is running.';return {id:id(),active:1,start,spec:copy(s),result:r,error:null}}
  let saved=[{id:id(),name:spec.name,spec:copy(spec)}],jobs=[job],paper=[portfolio(paperSpec)],watches=[{id:id(),spec:copy(paperSpec),active:1,last_date:end,error:null}];
  let alerts=[{symbol:'RELIANCE.NS',action:'ENTRY',bar_date:end,body:{name:'Sample daily signal',timing:'Illustration of a completed-candle signal.',basis:'SAMPLE ONLY. No market scan performed.'}}];
  function initial(){return {user:{id:'preview',name:'Frontend review',email:'No account required'},online:true,data:copy(catalog),runtime:{ready:true},spec:makeSpec(),space:{fast:'10, 20, 30',slow:'40, 50, 60'},jobs:copy(jobs),saved:copy(saved),paper:copy(paper),signalData:{watches:copy(watches),alerts:copy(alerts)}}}
  async function api(path,{method='GET',body}={}){
   const last=path.split('/').at(-1);
   if(path==='/api/data')return copy(catalog);
   if(path==='/api/auth/me')return initial().user;
   if(path==='/api/interpret')return {status:'ready',strategy:copy(body.defaults||spec),summary:'FRONTEND REVIEW: displaying the currently selected sample rules so you can inspect the confirmation flow. Your prompt has not been interpreted by AI. Choose a template or edit its fields to review another layout.',questions:[],sources:[],search_space:{}};
   if(path==='/api/coverage')return {ready:true,summary:'SAMPLE coverage screen only. Your dates and stock selection have not been checked against real data.',actual_start:body.start,actual_end:body.end,sessions:dates.length,missing_bars:0,affected_stocks:0,ranges:[],issues:[]};
   if(path==='/api/validate')return {valid:true};
   if(path==='/api/formulas')throw Error('Formula validation needs the backend. You can review the editor here; no formula was applied.');
   if(path==='/api/attachments')throw Error('Document processing is unavailable in frontend review. No file has been uploaded.');
   if(path==='/api/strategies'&&method==='POST'){saved.unshift({id:id(),name:body.name,spec:copy(body)});return {ok:true}}
   if(path==='/api/strategies')return copy(saved);
   if(path.startsWith('/api/strategies/')&&method==='DELETE'){saved=saved.filter(x=>x.id!==last);return {ok:true}}
   if(path==='/api/jobs'&&method==='POST'){
    const result=report(body.strategy);
    if(body.mode==='optimise')Object.assign(result,{mode:'optimise',training:report(body.strategy),validation:report(body.strategy),best_parameters:copy(body.strategy.parameters),selected_strategy:copy(body.strategy),leaderboard:[{parameters:copy(body.strategy.parameters),score:1.31,eligible:true,metrics:copy(result.metrics)}],trials:1,total_combinations:1,training_end:'2025-02-14',validation_start:'2025-02-17',seed:42,note:'SAMPLE UI. No candidates were evaluated or winner selected.'});
    const j={id:id(),state:'completed',progress:1,created:Date.now()/1000,request:copy(body),result};jobs.unshift(j);return {id:j.id}
   }
   if(path==='/api/jobs')return copy(jobs);
   if(path.startsWith('/api/jobs/')&&method==='DELETE'){jobs=jobs.filter(x=>x.id!==last);return {ok:true}}
   if(path.startsWith('/api/jobs/'))return copy(jobs.find(x=>x.id===last)||job);
   if(path==='/api/paper'&&method==='POST'){paper.unshift(portfolio(body));return {message:'Sample portfolio added for this review session. No live tracking started.'}}
   if(path==='/api/paper'||path==='/api/paper/refresh')return copy(paper);
   if(path.startsWith('/api/paper/')){if(method==='DELETE')paper=paper.filter(x=>x.id!==last);else{const p=paper.find(x=>x.id===last);if(p)p.active=body.active}return {ok:true}}
   if(path==='/api/signals'&&method==='POST'){watches.unshift({id:id(),spec:copy(body),active:1,last_date:end});return {message:'Sample watch added. No scan started.'}}
   if(path==='/api/signals'||path==='/api/signals/refresh')return copy({watches,alerts});
   if(path.startsWith('/api/signals/')){if(method==='DELETE')watches=watches.filter(x=>x.id!==last);else{const w=watches.find(x=>x.id===last);if(w)w.active=body.active}return {ok:true}}
   throw Error('This action requires the connected backend. Nothing was sent.');
  }
  return {initial,api};
 })();
}
