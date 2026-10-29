const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const stopToken=require('node:crypto').randomBytes(24).toString('hex');
const base='http://127.0.0.1:8177';
const artifactDir=path.resolve('artifacts/browser-'+Date.now());fs.mkdirSync(artifactDir,{recursive:true});
const python=process.env.NIYAM_TEST_PYTHON||(process.platform==='win32'?'.venv/Scripts/python.exe':'.venv/bin/python');
const child=spawn(python,['tests/browser_server.py'],{env:{...process.env,NIYAM_BROWSER_FIXTURE:artifactDir,NIYAM_TEST_STOP_TOKEN:stopToken},stdio:['ignore','pipe','pipe']});
let log='';child.stdout.on('data',x=>log+=x);child.stderr.on('data',x=>log+=x);
const delay=ms=>new Promise(r=>setTimeout(r,ms));
async function waitForService(){for(let i=0;i<100;i++){if(child.exitCode!==null)throw Error(log);try{if((await fetch(base+'/api/ready')).ok)return}catch{}await delay(200)}throw Error('Fixture failed to start: '+log)}
(async()=>{
 let browser;
 try{
 await waitForService();
 browser=await chromium.launch({headless:true,...(process.env.NIYAM_BROWSER_CHANNEL?{channel:process.env.NIYAM_BROWSER_CHANNEL}:{})});
 const context=await browser.newContext({viewport:{width:1440,height:1000}});const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(base);await page.getByText('Workspace online',{exact:true}).waitFor();
 assert.equal(await page.locator('#backendUrl,.setup-strip,[href="#data"]').count(),0);
 await page.locator('#authButton').click();await page.getByRole('button',{name:'Create account',exact:true}).click();
 await page.locator('[name=name]').fill('Browser researcher');await page.locator('[name=email]').fill('browser@example.com');await page.locator('[name=password]').fill('Browser-test-password-123');
 await page.locator('#authForm').getByRole('button',{name:/Create account/}).click();await page.locator('.recovery-code').waitFor();await page.getByRole('button',{name:'I have saved it'}).click();
 await page.locator('[data-kind=trend]').click();assert.equal(await page.locator('[data-spec=symbols]').inputValue(),'TEST');
 await page.locator('[data-action=interpret]').click();await page.getByText('Synthetic fixture:',{exact:false}).waitFor();
 await page.locator('[data-action=run]').click();await page.locator('.metric-grid').waitFor({timeout:60000});assert.ok(await page.getByRole('tab',{name:'Trade ledger'}).count());
 await page.getByRole('tab',{name:'Trade ledger'}).click();await page.getByRole('columnheader',{name:'Stock',exact:true}).waitFor();assert.ok(await page.locator('tbody tr').count()>0);
 const downloaded=page.waitForEvent('download');await page.getByRole('button',{name:'Download CSV'}).click();assert.equal((await downloaded).suggestedFilename(),'niyam-trades.csv');
 await page.getByRole('button',{name:'Watch this strategy'}).click();await page.getByText('Moving average crossover',{exact:true}).waitFor();
 await page.locator('a[href="#studio"]').first().click();await page.locator('[data-action="optimise"]').click();
 await page.locator('[data-range=fast]').fill('5, 10, 20');await page.locator('[data-range=slow]').fill('30, 50');await page.locator('#minTrades').fill('1');
 await page.locator('[data-action=run-optimise]').click();await page.getByText('These are validation results.',{exact:true}).waitFor({timeout:60000});
 await page.screenshot({path:path.join(artifactDir,'desktop-report.png'),fullPage:true});
 await page.reload();await page.locator('#authButton').getByText('Browser',{exact:false}).waitFor();assert.equal(await page.evaluate(()=>sessionStorage.getItem('niyam.token')),null);
 await page.locator('#authButton').click();await page.getByRole('button',{name:'Sign out',exact:true}).click();await page.locator('#authButton').getByText('Sign in',{exact:false}).waitFor();
 assert.equal((await context.request.get(base+'/api/auth/me')).status(),401);
 await context.close();
 const mobile=await browser.newContext({viewport:{width:390,height:844},isMobile:true,deviceScaleFactor:1});const phone=await mobile.newPage();phone.on('pageerror',e=>errors.push(e.message));await phone.goto(base);await phone.getByText('Workspace online',{exact:true}).waitFor();
 assert.equal(await phone.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'mobile page must not overflow horizontally');
 await phone.screenshot({path:path.join(artifactDir,'phone-studio.png'),fullPage:true});
 await phone.locator('.mobile-menu').click();await phone.locator('#nav a[href="#guide"]').click();await phone.getByRole('heading',{name:'Review the rules',exact:true}).waitFor();
 assert.equal(await phone.locator('#backendUrl,.setup-strip,[href="#data"]').count(),0);await mobile.close();assert.deepEqual(errors,[]);
 console.log('Browser flow passed: cookie signup, provider interpretation, backtest, CSV, paper watch, optimisation, session restore, logout, mobile layout.');console.log('Screenshots: '+artifactDir);
 }finally{if(browser)await browser.close();try{await fetch(base+'/__test__/stop',{method:'POST',headers:{'X-Test-Token':stopToken}})}catch{}for(let i=0;i<50&&child.exitCode===null;i++)await delay(100);if(child.exitCode===null)child.kill();child.stdout.destroy();child.stderr.destroy();child.unref();fs.writeFileSync(path.join(artifactDir,'server.log'),log)}
})().catch(e=>{console.error(e);process.exitCode=1});

