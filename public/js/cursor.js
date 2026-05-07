function initCursor() {
  if (window.matchMedia('(pointer: coarse)').matches) return;
  document.documentElement.style.cursor = 'none';
  const cross = document.getElementById('cursor-cross');
  const ring  = document.getElementById('cursor-ring');
  if (!cross || !ring) return;
  let mx = -100, my = -100, rx = -100, ry = -100, hovered = false;
  document.addEventListener('mousemove', e => { mx = e.clientX; my = e.clientY; cross.style.transform = `translate(${mx}px,${my}px) translate(-50%,-50%)`; }, {passive:true});
  (function lerpRing() { rx += (mx-rx)*0.10; ry += (my-ry)*0.10; ring.style.transform = `translate(${rx}px,${ry}px) translate(-50%,-50%) scale(${hovered?1.6:1})`; requestAnimationFrame(lerpRing); })();
  const onEnter = () => { hovered=true; cross.classList.add('hov'); ring.classList.add('hov'); };
  const onLeave = () => { hovered=false; cross.classList.remove('hov'); ring.classList.remove('hov'); };
  document.querySelectorAll('a,button,.kpi,.cc,.h-stat,.term-blk,.access-card').forEach(el => { el.addEventListener('mouseenter',onEnter); el.addEventListener('mouseleave',onLeave); });
}
