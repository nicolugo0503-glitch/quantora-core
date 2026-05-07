function initIntro(onComplete) {
  const overlay = document.getElementById('intro-overlay');
  const line = document.getElementById('intro-line');
  const name = document.getElementById('intro-name');
  const sub = document.getElementById('intro-sub');
  const WORD = 'QUANTORA'; let done = false;
  setTimeout(() => { line.style.transition='width 0.9s cubic-bezier(0.77,0,0.18,1)'; line.style.width='100%'; },200);
  setTimeout(() => { let i=0; const iv=setInterval(()=>{ name.textContent=WORD.slice(0,++i); if(i>=WORD.length){clearInterval(iv); setTimeout(()=>{ sub.style.opacity='1'; sub.style.transform='translateY(0)'; },180); } },72); },900);
  setTimeout(() => { overlay.style.transition='opacity 0.9s ease'; overlay.style.opacity='0'; setTimeout(()=>{ overlay.style.display='none'; if(!done){done=true; onComplete&&onComplete();} },900); },2600);
}
