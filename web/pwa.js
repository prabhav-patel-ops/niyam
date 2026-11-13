/* Installation and app navigation are enabled only for the public review build. */
'use strict';
if(window.NIYAM_PUBLIC_PREVIEW&&window.NIYAM_REVIEW_MODE){
 (function(){
  const installed=()=>window.matchMedia('(display-mode: standalone)').matches||navigator.standalone===true;
  const ios=/iPad|iPhone|iPod/.test(navigator.userAgent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
  const card=document.querySelector('#appInstall');
  const button=document.querySelector('#installNiyam');
  const help=document.querySelector('#installHelp');
  const offline=document.querySelector('#offlineReady');
  let promptEvent=null;
  document.body.classList.add('app-review');
  document.querySelector('#mobileAppNav').hidden=false;
  function showHelp(){
   help.hidden=false;
   help.textContent=installed()?'Niyam is already running as an app.':ios?
    'In Safari, tap Share → Add to Home Screen. Enable Open as Web App if offered, then tap Add. If you opened this in another app, open the link in Safari first.':
    'Open this link in Chrome on your phone. Tap the ⋮ menu → Install app or Add to Home screen → Install. If you are inside another app’s browser, choose Open in Chrome first.';
  }
  card.hidden=installed();
  button.addEventListener('click',async()=>{
   if(!promptEvent){showHelp();return;}
   const event=promptEvent;promptEvent=null;
   try{await event.prompt();const choice=await event.userChoice;if(choice.outcome!=='accepted')showHelp();}
   catch{showHelp();}
  });
  document.querySelector('#dismissInstall').addEventListener('click',()=>{card.hidden=true;});
  window.addEventListener('beforeinstallprompt',event=>{event.preventDefault();promptEvent=event;card.hidden=false;button.textContent='Install app';});
  window.addEventListener('appinstalled',()=>{card.hidden=true;promptEvent=null;});
  const nav=document.querySelector('#mobileAppNav');
  nav.querySelector('[data-app-menu]').addEventListener('click',()=>document.querySelector('#sidebar').classList.toggle('open'));
  function markNav(){nav.querySelectorAll('a').forEach(a=>{if(a.hash===(location.hash||'#studio'))a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});}
  window.addEventListener('hashchange',markNav);markNav();
  function status(){offline.textContent=navigator.onLine?'Preparing offline access…':'Offline · open once online to download the app';}
  status();
  if('serviceWorker' in navigator&&window.isSecureContext){
   navigator.serviceWorker.register('./sw.js',{scope:'./',updateViaCache:'none'}).then(async registration=>{
    await navigator.serviceWorker.ready;
    function connection(){offline.textContent=navigator.onLine?'Ready for offline review':'Offline · sample review available';}
    connection();window.addEventListener('online',connection);window.addEventListener('offline',connection);
    function updateReady(){
     if(!registration.waiting)return;
     const update=document.querySelector('#appUpdate');update.hidden=false;
     update.querySelector('button').onclick=()=>{registration.waiting.postMessage({type:'ACTIVATE_UPDATE'});};
    }
    updateReady();
    registration.addEventListener('updatefound',()=>registration.installing?.addEventListener('statechange',updateReady));
    let reloading=false;
    navigator.serviceWorker.addEventListener('controllerchange',()=>{if(registration.waiting===null&&document.querySelector('#appUpdate').hidden===false&&!reloading){reloading=true;location.reload();}});
   }).catch(()=>{offline.textContent='Online preview · offline download unavailable. Retry with a normal browser tab.';});
  }else offline.textContent='Open the HTTPS link in Safari or Chrome to install.';
 })();
}
