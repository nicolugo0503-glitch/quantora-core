let lenisInstance = null;

function initSmooth() {
  if (typeof Lenis === 'undefined') return;

  lenisInstance = new Lenis({
    duration: 1.25,
    easing: t => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
    direction: 'vertical',
    smooth: true,
  });

  if (typeof gsap !== 'undefined') {
    gsap.ticker.add(time => lenisInstance.raf(time * 1000));
    gsap.ticker.lagSmoothing(0);
  } else {
    (function raf(time) { lenisInstance.raf(time); requestAnimationFrame(raf); })(0);
  }

  lenisInstance.on('scroll', ({ scroll, progress }) => {
    document.documentElement.style.setProperty('--scroll-y', scroll + 'px');
    const bar = document.getElementById('progress-bar');
    if (bar) bar.style.width = (progress * 100) + '%';
  });
}

function getLenis() { return lenisInstance; }
