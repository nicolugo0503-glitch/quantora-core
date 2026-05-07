function initAnimations() {
  if (typeof gsap === 'undefined') return;

  gsap.registerPlugin(ScrollTrigger);

  // Wire ScrollTrigger to Lenis if available
  const lenis = getLenis?.();
  if (lenis) {
    lenis.on('scroll', ScrollTrigger.update);
    ScrollTrigger.scrollerProxy(document.body, {
      scrollTop(value) {
        if (arguments.length) lenis.scrollTo(value, { immediate: true });
        return lenis.animatedScroll;
      },
      getBoundingClientRect() {
        return { top: 0, left: 0, width: window.innerWidth, height: window.innerHeight };
      },
    });
    ScrollTrigger.defaults({ scroller: document.body });
  }

  // ── HERO ENTRANCE ──────────────────────────────────────────
  const heroTl = gsap.timeline({ delay: 3.2 }); // after intro
  heroTl
    .from('.h-eyebrow',  { duration: 0.8, opacity: 0, y: 16, ease: 'power3.out' })
    .from('.h-sub',      { duration: 0.8, opacity: 0, y: 16, ease: 'power3.out' }, '-=0.3')
    .from('.h-stats',    { duration: 0.8, opacity: 0, y: 16, ease: 'power3.out' }, '-=0.3')
    .from('.h-right',    { duration: 1.0, opacity: 0, x: 32, ease: 'power3.out' }, '-=0.9');

  // ── TYPEWRITER HEADLINE ────────────────────────────────────
  setTimeout(() => {
    const el    = document.getElementById('h-headline');
    if (!el) return;
    const lines = ['The market does not\nreward participation.\nIt rewards asymmetry.'];
    const full  = lines[0];
    let   i     = 0;
    el.innerHTML = '<span class="cursor-blink"></span>';
    const cursor = el.querySelector('.cursor-blink');

    const iv = setInterval(() => {
      if (i >= full.length) { clearInterval(iv); cursor.remove(); return; }
      const ch = full[i];
      const before = el.innerHTML.replace('<span class="cursor-blink"></span>', '');
      if (ch === '\n') el.innerHTML = before + '<br>' + '<span class="cursor-blink"></span>';
      else if (full.slice(i).startsWith('participation')) {
        el.innerHTML = before + '<em>participation</em>' + '<span class="cursor-blink"></span>';
        i += 'participation'.length - 1;
      } else {
        el.innerHTML = before + ch + '<span class="cursor-blink"></span>';
      }
      i++;
    }, 38);
  }, 3400);

  // ── COUNTER SCRAMBLE ───────────────────────────────────────
  function scramble(el, target, dp, sfx) {
    const dur = 1800; let s = null;
    function step(ts) {
      if (!s) s = ts;
      const p = Math.min((ts - s) / dur, 1);
      const ease = 1 - Math.pow(1 - p, 3);
      if (p < 0.65) {
        el.textContent = (Math.random() * target).toFixed(dp) + sfx;
      } else {
        el.textContent = (target * ((p - 0.65) / 0.35)).toFixed(dp) + sfx;
      }
      if (p < 1) requestAnimationFrame(step);
      else el.textContent = target.toFixed(dp) + sfx;
    }
    requestAnimationFrame(step);
  }

  // Trigger counters when hero is visible
  let heroFired = false;
  ScrollTrigger.create({
    trigger: '#hero',
    start: 'top 80%',
    onEnter: () => {
      if (heroFired) return; heroFired = true;
      document.querySelectorAll('[data-cnt]').forEach(el => {
        scramble(el, parseFloat(el.dataset.cnt), parseInt(el.dataset.dp || 0), el.dataset.sfx || '');
      });
    }
  });

  // ── KPI STRIP ──────────────────────────────────────────────
  gsap.from('.kpi', {
    scrollTrigger: { trigger: '#kpis', start: 'top 82%' },
    duration: 0.75, opacity: 0, y: 24, stagger: 0.07, ease: 'power2.out',
    onComplete() {
      document.querySelectorAll('.kpi [data-cnt]').forEach(el => {
        scramble(el, parseFloat(el.dataset.cnt), parseInt(el.dataset.dp || 0), el.dataset.sfx || '');
      });
    }
  });

  // ── MANIFESTO ──────────────────────────────────────────────
  gsap.from('.mani-q', {
    scrollTrigger: { trigger: '#manifesto', start: 'top 72%' },
    duration: 1.6, opacity: 0, scale: 0.975, ease: 'power3.out',
  });
  // Gold scan line — runs once
  gsap.fromTo('#mani-scan',
    { left: '-100%' },
    {
      left: '110%', duration: 2.8, ease: 'none',
      scrollTrigger: { trigger: '#manifesto', start: 'top 60%', once: true },
    }
  );

  // ── SECTION HEADERS ────────────────────────────────────────
  gsap.utils.toArray('.sec-badge, .sec-title').forEach(el => {
    gsap.from(el, {
      scrollTrigger: { trigger: el, start: 'top 88%' },
      duration: 0.9, opacity: 0, y: 22, ease: 'power2.out',
    });
  });

  // ── CHART CARDS (clip-path reveal) ─────────────────────────
  gsap.utils.toArray('.cc').forEach((el, i) => {
    gsap.from(el, {
      scrollTrigger: { trigger: el, start: 'top 88%' },
      duration: 0.7,
      opacity: 0,
      clipPath: 'inset(0 0 100% 0)',
      ease: 'power3.out',
      delay: (i % 3) * 0.08,
    });
  });

  // ── THESIS / TERMS / ACCESS ────────────────────────────────
  gsap.utils.toArray('.rv').forEach(el => {
    gsap.from(el, {
      scrollTrigger: { trigger: el, start: 'top 88%' },
      duration: 0.8, opacity: 0, y: 20, ease: 'power2.out',
    });
  });

  // ── HORIZONTAL SCROLL ANALYTICS ───────────────────────────
  const panels = gsap.utils.toArray('.h-panel');
  if (panels.length > 1) {
    const track = document.querySelector('.h-track');
    gsap.to(track, {
      xPercent: -100 * (panels.length - 1),
      ease: 'none',
      scrollTrigger: {
        trigger: '#analytics-h',
        pin: true,
        scrub: 1,
        snap: 1 / (panels.length - 1),
        end: () => '+=' + (panels.length - 1) * window.innerWidth,
      }
    });
  }

  // ── NAV SCROLL STATE ───────────────────────────────────────
  ScrollTrigger.create({
    start: 'top -60',
    onUpdate: self => document.getElementById('nav').classList.toggle('scrolled', self.scroll() > 60),
  });

  // ── CLOCK ──────────────────────────────────────────────────
  function updateClock() {
    const n = new Date();
    let h = n.getUTCHours() - 4; if (h < 0) h += 24;
    const el = document.getElementById('clk');
    if (el) el.textContent = `${String(h).padStart(2,'0')}:${String(n.getUTCMinutes()).padStart(2,'0')}:${String(n.getUTCSeconds()).padStart(2,'0')}`;
  }
  updateClock(); setInterval(updateClock, 1000);

  ScrollTrigger.refresh();
}
