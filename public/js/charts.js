// ── CANVAS CHART ENGINE ────────────────────────────────────────

function cvSetup(id) {
  const cv = document.getElementById(id);
  if (!cv) return null;
  const W = cv.parentElement.clientWidth || cv.offsetWidth || 400;
  cv.width = W;
  return { cv, ctx: cv.getContext('2d'), W, H: cv.height };
}

function animChart(drawFn, dur = 1300) {
  let s = null;
  function step(ts) {
    if (!s) s = ts;
    const p = Math.min((ts - s) / dur, 1);
    drawFn(1 - Math.pow(1 - p, 3));
    if (p < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

// ── EQUITY CURVE (interactive) ────────────────────────────────
let curveMouseX = -1;

function drawCurve(prog) {
  const r = cvSetup('c-curve');
  if (!r) return;
  const { ctx, W, H } = r;
  const pL = 48, pR = 16, pT = 16, pB = 36;
  const cW = W - pL - pR, cH = H - pT - pB;
  ctx.clearRect(0, 0, W, H);

  const nPts = Math.round(Q.NAV.length * prog);
  const q = Q.NAV.slice(0, nPts), s = Q.SP.slice(0, nPts);
  if (q.length < 2) return;

  const maxV = Math.max(...Q.NAV, ...Q.SP) + 3;
  const minV = Math.min(...Q.NAV, ...Q.SP) - 3;
  const sX = i => pL + (i / (Q.NAV.length - 1)) * cW;
  const sY = v => pT + cH - ((v - minV) / (maxV - minV)) * cH;

  // Grid
  for (let i = 0; i <= 4; i++) {
    const y = pT + i * cH / 4;
    const v = maxV - (maxV - minV) * i / 4;
    ctx.strokeStyle = 'rgba(255,255,255,0.04)'; ctx.lineWidth = 0.5;
    ctx.beginPath(); ctx.moveTo(pL, y); ctx.lineTo(pL + cW, y); ctx.stroke();
    ctx.fillStyle = 'rgba(52,78,106,0.85)'; ctx.font = '9px Space Mono'; ctx.textAlign = 'right';
    ctx.fillText(Math.round(v), pL - 5, y + 3);
  }

  // Year markers
  ctx.fillStyle = 'rgba(52,78,106,0.7)'; ctx.font = '9px Space Mono'; ctx.textAlign = 'center';
  [2019,2020,2021,2022,2023,2024].forEach(yr => {
    const idx = yr === 2019 ? 6 : (yr - 2019) * 12 + 6;
    if (idx < Q.NAV.length) {
      ctx.fillText(yr, sX(idx), H - 8);
      ctx.strokeStyle = 'rgba(255,255,255,0.04)'; ctx.lineWidth = 0.5;
      ctx.beginPath(); ctx.moveTo(sX(idx), pT); ctx.lineTo(sX(idx), pT + cH); ctx.stroke();
    }
  });

  // S&P line
  ctx.beginPath(); ctx.moveTo(sX(0), sY(s[0]));
  s.forEach((v, i) => ctx.lineTo(sX(i), sY(v)));
  ctx.strokeStyle = 'rgba(26,46,68,0.85)'; ctx.lineWidth = 1.5; ctx.setLineDash([5, 4]); ctx.stroke(); ctx.setLineDash([]);

  // QTR fill
  const grd = ctx.createLinearGradient(0, pT, 0, pT + cH);
  grd.addColorStop(0, 'rgba(198,162,58,0.22)'); grd.addColorStop(1, 'rgba(198,162,58,0)');
  ctx.beginPath(); ctx.moveTo(sX(0), pT + cH); ctx.lineTo(sX(0), sY(q[0]));
  q.forEach((v, i) => ctx.lineTo(sX(i), sY(v)));
  ctx.lineTo(sX(q.length - 1), pT + cH); ctx.closePath(); ctx.fillStyle = grd; ctx.fill();

  // QTR line
  ctx.beginPath(); ctx.moveTo(sX(0), sY(q[0]));
  q.forEach((v, i) => ctx.lineTo(sX(i), sY(v)));
  ctx.strokeStyle = '#DEAD5E'; ctx.lineWidth = 2.5; ctx.stroke();

  // End dot + glow
  const ex = sX(q.length - 1), ey = sY(q[q.length - 1]);
  const glowGrd = ctx.createRadialGradient(ex, ey, 0, ex, ey, 14);
  glowGrd.addColorStop(0, 'rgba(222,173,94,0.35)'); glowGrd.addColorStop(1, 'rgba(222,173,94,0)');
  ctx.beginPath(); ctx.arc(ex, ey, 14, 0, Math.PI * 2); ctx.fillStyle = glowGrd; ctx.fill();
  ctx.beginPath(); ctx.arc(ex, ey, 4, 0, Math.PI * 2); ctx.fillStyle = '#DEAD5E'; ctx.fill();

  // Interactive crosshair
  if (curveMouseX > pL && curveMouseX < pL + cW && prog >= 1) {
    const frac = (curveMouseX - pL) / cW;
    const idx  = Math.round(frac * (Q.NAV.length - 1));
    const cx   = sX(idx), cy = sY(Q.NAV[idx]);

    ctx.strokeStyle = 'rgba(198,162,58,0.35)'; ctx.lineWidth = 1; ctx.setLineDash([3, 3]);
    ctx.beginPath(); ctx.moveTo(cx, pT); ctx.lineTo(cx, pT + cH); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(pL, cy); ctx.lineTo(pL + cW, cy); ctx.stroke();
    ctx.setLineDash([]);

    ctx.beginPath(); ctx.arc(cx, cy, 5, 0, Math.PI * 2);
    ctx.fillStyle = '#DEAD5E'; ctx.fill();

    // Tooltip
    const yr   = 2019 + Math.floor(idx / 12);
    const mo   = Q.MONTHS[idx % 12] || '';
    const ret  = ((Q.NAV[idx] / 100 - 1) * 100).toFixed(1);
    const tip  = `${mo} ${yr}  NAV ${Q.NAV[idx].toFixed(1)}  (+${ret}%)`;
    ctx.fillStyle = 'rgba(6,20,34,0.92)';
    const tw = ctx.measureText(tip).width + 16;
    const tx = Math.min(cx + 8, pL + cW - tw - 4);
    ctx.fillRect(tx, cy - 22, tw, 20);
    ctx.fillStyle = '#C8D8EE'; ctx.font = '9.5px Space Mono'; ctx.textAlign = 'left';
    ctx.fillText(tip, tx + 8, cy - 8);
  }
}

// ── SHARPE ────────────────────────────────────────────────────
function drawSharpe(prog) {
  const r = cvSetup('c-sharpe');
  if (!r) return;
  const { ctx, W, H } = r;
  const pL = 42, pR = 8, pT = 14, pB = 24;
  const cW = W - pL - pR, cH = H - pT - pB;
  ctx.clearRect(0, 0, W, H);
  const n = Math.round(Q.SHARPE.length * prog);
  const d = Q.SHARPE.slice(0, n);
  if (d.length < 2) return;
  const maxV = Math.max(...Q.SHARPE) + 0.4, minV = Math.min(0, ...Q.SHARPE) - 0.2;
  const sX = i => pL + (i / (Q.SHARPE.length - 1)) * cW;
  const sY = v => pT + cH - ((v - minV) / (maxV - minV)) * cH;
  const y0 = sY(0);
  [0,1,2,3,4].forEach(v => {
    const y = sY(v);
    ctx.strokeStyle = v === 0 ? 'rgba(255,255,255,0.09)' : 'rgba(255,255,255,0.03)';
    ctx.lineWidth = 0.5; ctx.beginPath(); ctx.moveTo(pL, y); ctx.lineTo(pL + cW, y); ctx.stroke();
    ctx.fillStyle = 'rgba(52,78,106,0.8)'; ctx.font = '9px Space Mono'; ctx.textAlign = 'right';
    ctx.fillText(v.toFixed(1), pL - 5, y + 3);
  });
  const grd = ctx.createLinearGradient(0, pT, 0, pT + cH);
  grd.addColorStop(0, 'rgba(24,150,90,0.24)'); grd.addColorStop(1, 'rgba(24,150,90,0)');
  ctx.beginPath(); ctx.moveTo(sX(0), y0); ctx.lineTo(sX(0), sY(d[0]));
  d.forEach((v, i) => ctx.lineTo(sX(i), sY(v)));
  ctx.lineTo(sX(d.length - 1), y0); ctx.closePath(); ctx.fillStyle = grd; ctx.fill();
  ctx.beginPath(); ctx.moveTo(sX(0), sY(d[0]));
  d.forEach((v, i) => ctx.lineTo(sX(i), sY(v)));
  ctx.strokeStyle = '#1FBC6E'; ctx.lineWidth = 2; ctx.stroke();
}

// ── DRAWDOWN ──────────────────────────────────────────────────
function drawDD(prog) {
  const r = cvSetup('c-dd');
  if (!r) return;
  const { ctx, W, H } = r;
  const pL = 44, pR = 6, pT = 10, pB = 20;
  const cW = W - pL - pR, cH = H - pT - pB;
  ctx.clearRect(0, 0, W, H);
  const n = Math.round(Q.DD.length * prog);
  const d = Q.DD.slice(0, n);
  if (d.length < 2) return;
  const minV = Math.min(...Q.DD) - 0.4, maxV = 0.4;
  const sX = i => pL + (i / (Q.DD.length - 1)) * cW;
  const sY = v => pT + cH - ((v - minV) / (maxV - minV)) * cH;
  const y0 = sY(0);
  [-2,-4,-6].forEach(v => {
    const y = sY(v);
    ctx.strokeStyle = 'rgba(255,255,255,0.04)'; ctx.lineWidth = 0.5;
    ctx.beginPath(); ctx.moveTo(pL, y); ctx.lineTo(pL + cW, y); ctx.stroke();
    ctx.fillStyle = 'rgba(52,78,106,0.8)'; ctx.font = '9px Space Mono'; ctx.textAlign = 'right';
    ctx.fillText(v + '%', pL - 4, y + 3);
  });
  const grd = ctx.createLinearGradient(0, pT, 0, pT + cH);
  grd.addColorStop(0, 'rgba(184,52,40,0.04)'); grd.addColorStop(1, 'rgba(184,52,40,0.42)');
  ctx.beginPath(); ctx.moveTo(sX(0), y0); ctx.lineTo(sX(0), sY(d[0]));
  d.forEach((v, i) => ctx.lineTo(sX(i), sY(v)));
  ctx.lineTo(sX(d.length - 1), y0); ctx.closePath(); ctx.fillStyle = grd; ctx.fill();
  ctx.beginPath(); ctx.moveTo(sX(0), sY(d[0]));
  d.forEach((v, i) => ctx.lineTo(sX(i), sY(v)));
  ctx.strokeStyle = '#E04535'; ctx.lineWidth = 1.5; ctx.stroke();
}

// ── RADAR ─────────────────────────────────────────────────────
function drawRadar(prog) {
  const r = cvSetup('c-radar');
  if (!r) return;
  const { ctx, W, H } = r;
  ctx.clearRect(0, 0, W, H);
  const cx = W / 2, cy = H / 2 + 6, rad = Math.min(W, H) * 0.33;
  const n = Q.FAC_LBL.length;
  [0.25,0.5,0.75,1].forEach(t => {
    ctx.beginPath();
    for (let i = 0; i < n; i++) {
      const a = i / n * Math.PI * 2 - Math.PI / 2;
      const x = cx + Math.cos(a) * rad * t, y = cy + Math.sin(a) * rad * t;
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }
    ctx.closePath(); ctx.strokeStyle = `rgba(255,255,255,${t===1?0.07:0.03})`; ctx.lineWidth = 0.5; ctx.stroke();
  });
  for (let i = 0; i < n; i++) {
    const a = i / n * Math.PI * 2 - Math.PI / 2;
    ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + Math.cos(a) * rad, cy + Math.sin(a) * rad);
    ctx.strokeStyle = 'rgba(255,255,255,0.05)'; ctx.lineWidth = 0.5; ctx.stroke();
  }
  ctx.font = '9px Inter'; ctx.textAlign = 'center';
  Q.FAC_LBL.forEach((f, i) => {
    const a = i / n * Math.PI * 2 - Math.PI / 2;
    ctx.fillStyle = Math.abs(Q.FAC_VAL[i]) > 0.5 ? 'rgba(198,162,58,0.88)' : 'rgba(120,152,190,0.8)';
    ctx.fillText(f, cx + Math.cos(a) * (rad + 18), cy + Math.sin(a) * (rad + 18) + 3);
  });
  const pts = Q.FAC_VAL.map((v, i) => {
    const norm = (v + 1) / 2, a = i / n * Math.PI * 2 - Math.PI / 2;
    return [cx + Math.cos(a) * rad * norm * prog, cy + Math.sin(a) * rad * norm * prog];
  });
  const grd = ctx.createRadialGradient(cx, cy, 0, cx, cy, rad);
  grd.addColorStop(0, 'rgba(198,162,58,0.28)'); grd.addColorStop(1, 'rgba(198,162,58,0.04)');
  ctx.beginPath(); pts.forEach(([x, y], i) => i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y));
  ctx.closePath(); ctx.fillStyle = grd; ctx.fill();
  ctx.strokeStyle = 'rgba(198,162,58,0.82)'; ctx.lineWidth = 1.5; ctx.stroke();
  pts.forEach(([x, y]) => {
    ctx.beginPath(); ctx.arc(x, y, 3, 0, Math.PI * 2); ctx.fillStyle = '#DEAD5E'; ctx.fill();
  });
}

// ── HISTOGRAM ─────────────────────────────────────────────────
function drawHist(prog) {
  const r = cvSetup('c-hist');
  if (!r) return;
  const { ctx, W, H } = r;
  const pL = 10, pR = 10, pT = 10, pB = 22;
  const cW = W - pL - pR, cH = H - pT - pB;
  ctx.clearRect(0, 0, W, H);
  const maxC = Math.max(...Q.HIST_COUNTS), bw = cW / Q.HIST_COUNTS.length, gap = 2;
  Q.HIST_COUNTS.forEach((c, i) => {
    const bh = (c / maxC) * cH * prog, x = pL + i * bw + gap / 2, y = pT + cH - bh;
    ctx.fillStyle = Q.HIST_BINS[i] >= 0
      ? `rgba(24,150,90,${0.38 + 0.48 * (c / maxC)})`
      : `rgba(184,52,40,${0.32 + 0.42 * (c / maxC)})`;
    ctx.fillRect(x, y, bw - gap, bh);
    if (i % 3 === 0) {
      ctx.fillStyle = 'rgba(52,78,106,0.7)'; ctx.font = '8px Space Mono'; ctx.textAlign = 'center';
      ctx.fillText(Q.HIST_BINS[i] + '%', x + (bw - gap) / 2, H - 5);
    }
  });
  const mean = 1.8, std = 1.9;
  ctx.beginPath();
  for (let px = 0; px < cW; px++) {
    const xv = Q.HIST_BINS[0] + px / cW * (Q.HIST_BINS[Q.HIST_BINS.length - 1] - Q.HIST_BINS[0]);
    const pdf = Math.exp(-((xv - mean) ** 2) / (2 * std ** 2));
    const py  = pT + cH - pdf * cH * prog * 0.93;
    px === 0 ? ctx.moveTo(pL + px, py) : ctx.lineTo(pL + px, py);
  }
  ctx.strokeStyle = 'rgba(198,162,58,0.52)'; ctx.lineWidth = 1.5; ctx.setLineDash([3,3]); ctx.stroke(); ctx.setLineDash([]);
}

// ── CORRELATION MATRIX ────────────────────────────────────────
function drawCorr(prog) {
  const r = cvSetup('c-corr');
  if (!r) return;
  const { ctx, W, H } = r;
  ctx.clearRect(0, 0, W, H);
  const n = Q.CORR_LBL.length, lW = 40, lH = 28;
  const cW = (W - lW) / n, cH = (H - lH) / n;
  ctx.font = '700 9.5px Space Mono'; ctx.textAlign = 'center';
  ctx.fillStyle = 'rgba(120,152,190,0.85)';
  Q.CORR_LBL.forEach((l, i) => ctx.fillText(l, lW + (i + 0.5) * cW, lH - 8));
  ctx.textAlign = 'right';
  Q.CORR_LBL.forEach((l, i) => ctx.fillText(l, lW - 4, lH + (i + 0.62) * cH));
  Q.CORR.forEach((row, ri) => {
    row.forEach((val, ci) => {
      const x = lW + ci * cW, y = lH + ri * cH;
      let rr, gg, bb, aa;
      if (val > 0)      { rr=198; gg=162; bb=58;  aa = 0.10 + val * 0.58; }
      else if (val < 0) { rr=184; gg=52;  bb=40;  aa = 0.10 + Math.abs(val) * 0.55; }
      else              { rr=30;  gg=50;  bb=80;  aa = 0.18; }
      ctx.fillStyle = `rgba(${rr},${gg},${bb},${aa * prog})`;
      ctx.fillRect(x + 1, y + 1, cW - 2, cH - 2);
      ctx.font = `${ri===ci?'700':'500'} 9.5px Space Mono`; ctx.textAlign = 'center';
      ctx.fillStyle = Math.abs(val) > 0.5 ? 'rgba(240,248,255,0.92)' : 'rgba(120,152,190,0.82)';
      ctx.fillText((val * prog).toFixed(2), x + cW / 2, y + cH / 2 + 4);
    });
  });
}

// ── HERO MINI-CURVE ────────────────────────────────────────────
function drawHeroCurve() {
  const cv = document.getElementById('c-hero-curve');
  if (!cv) return;
  const W = cv.offsetWidth; cv.width = W; cv.height = 170;
  const H = 170, p = 8, ctx = cv.getContext('2d');
  const maxV = Math.max(...Q.NAV,...Q.SP)+2, minV = Math.min(...Q.NAV,...Q.SP)-2;
  const sX = i => p + (i/(Q.NAV.length-1))*(W-2*p);
  const sY = v => H-p-((v-minV)/(maxV-minV))*(H-2*p);
  ctx.beginPath(); ctx.moveTo(sX(0),sY(Q.SP[0]));
  Q.SP.forEach((v,i)=>ctx.lineTo(sX(i),sY(v)));
  ctx.strokeStyle='rgba(26,46,68,0.85)'; ctx.lineWidth=1.5; ctx.setLineDash([4,4]); ctx.stroke(); ctx.setLineDash([]);
  const grd=ctx.createLinearGradient(0,0,0,H);
  grd.addColorStop(0,'rgba(198,162,58,0.25)'); grd.addColorStop(1,'rgba(198,162,58,0)');
  ctx.beginPath(); ctx.moveTo(sX(0),H); ctx.lineTo(sX(0),sY(Q.NAV[0]));
  Q.NAV.forEach((v,i)=>ctx.lineTo(sX(i),sY(v)));
  ctx.lineTo(sX(Q.NAV.length-1),H); ctx.closePath(); ctx.fillStyle=grd; ctx.fill();
  ctx.beginPath(); ctx.moveTo(sX(0),sY(Q.NAV[0]));
  Q.NAV.forEach((v,i)=>ctx.lineTo(sX(i),sY(v)));
  ctx.strokeStyle='#DEAD5E'; ctx.lineWidth=2.2; ctx.stroke();
  ctx.beginPath(); ctx.arc(sX(Q.NAV.length-1),sY(Q.NAV[Q.NAV.length-1]),4,0,Math.PI*2);
  ctx.fillStyle='#DEAD5E'; ctx.fill();
}

// ── INTERACTIVE CURSOR ON CURVE ───────────────────────────────
function initCurveInteraction() {
  const cv = document.getElementById('c-curve');
  if (!cv) return;
  cv.addEventListener('mousemove', e => {
    const rect = cv.getBoundingClientRect();
    curveMouseX = (e.clientX - rect.left) * (cv.width / rect.width);
    drawCurve(1);
  }, { passive: true });
  cv.addEventListener('mouseleave', () => {
    curveMouseX = -1;
    drawCurve(1);
  });
}

// ── RESIZE ALL CHARTS ──────────────────────────────────────────
const chartFns = {
  'c-curve':  () => animChart(drawCurve,  1600),
  'c-sharpe': () => animChart(drawSharpe, 1400),
  'c-dd':     () => animChart(drawDD,     1200),
  'c-radar':  () => animChart(drawRadar,  1100),
  'c-hist':   () => animChart(drawHist,   1000),
  'c-corr':   () => animChart(drawCorr,    900),
};
const chartTriggered = new Set();

function initChartObserver() {
  const obs = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting && !chartTriggered.has(e.target.id)) {
        chartTriggered.add(e.target.id);
        chartFns[e.target.id]?.();
      }
    });
  }, { threshold: 0.12 });
  Object.keys(chartFns).forEach(id => {
    const el = document.getElementById(id);
    if (el) obs.observe(el);
  });
}

let resizeTimer;
window.addEventListener('resize', () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    drawHeroCurve();
    Object.keys(chartFns).forEach(id => {
      if (chartTriggered.has(id)) chartFns[id]?.();
    });
  }, 180);
}, { passive: true });
