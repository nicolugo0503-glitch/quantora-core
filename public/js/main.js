// ── MAIN ENTRY POINT -------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
  initIntro(() => { initWebGL(); setTimeout(drawHeroCurve,120); initCurveInteraction(); initChartObserver(); });
  initSmooth();
  initTicker(); buildHeatmap(); initCursor();
  requestAnimationFrame(() => initAnimations());
  window.addEventListener('scroll', () => { const pct=window.scrollY/(document.body.scrollHeight-window.innerHeight)*100; const bar=document.getElementById('progress-bar'); if(bar)bar.style.width=pct.toFixed(1)+'%'; },{passive:true});
  const sndBtn=document.getElementById('sound-btn'), sndEl=document.getElementById('ambient-sound');
  if(sndBtn&&sndEl)sndBtn.addEventListener('click',()=>{if(sndEl.paused){sndEl.volume=0.08;sndEl.play().catch(()=>{});sndBtn.classList.add('on');sndBtn.textContent='◼ SOUND';}else{sndEl.pause();sndBtn.classList.remove('on');sndBtn.textContent='▶ SOUND';}});
  setInterval(()=>{document.querySelectorAll('.h-stat-v[data-cnt]').forEach(el=>{const base=parseFloat(el.dataset.cnt),dp=parseInt(el.dataset.dp||0),sfx=el.dataset.sfx||''; el.textContent=(base+(Math.random()-0.5)*0.04).toFixed(dp)+sfx;});},4500);
});
