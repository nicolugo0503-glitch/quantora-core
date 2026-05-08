/**
 * particles.js — Quantora Capital
 * WebGL gold-particle stream tracing the equity curve
 * Three.js r128 · 2800 particles · 60fps target
 */
(function () {
  'use strict';

  // ─── GUARD ─────────────────────────────────────────────────
  const canvas = document.getElementById('particle-canvas');
  if (!canvas || typeof THREE === 'undefined') return;

  // ─── RENDERER ──────────────────────────────────────────────
  const renderer = new THREE.WebGLRenderer({
    canvas,
    alpha:           true,
    antialias:       false,
    powerPreference: 'high-performance',
  });
  const DPR = Math.min(window.devicePixelRatio, 1.5);
  renderer.setPixelRatio(DPR);
  renderer.setSize(canvas.offsetWidth || window.innerWidth,
                   canvas.offsetHeight || window.innerHeight);
  renderer.setClearColor(0x000000, 0);

  // ─── SCENE / CAMERA ────────────────────────────────────────
  const scene  = new THREE.Scene();
  const W0 = canvas.offsetWidth  || window.innerWidth;
  const H0 = canvas.offsetHeight || window.innerHeight;
  const camera = new THREE.PerspectiveCamera(52, W0 / H0, 0.01, 200);
  camera.position.z = 9;

  // ─── BUILD EQUITY CURVE FROM REAL NAV DATA ─────────────────
  // Q.NAV is the array of monthly NAV values loaded in data.js
  function buildCurveLUT() {
    const nav = (typeof Q !== 'undefined' && Array.isArray(Q.NAV) && Q.NAV.length > 4)
      ? Q.NAV
      : (function () {
          // Fallback: synthetic exponential growth with realistic noise
          const n = 72, out = [100];
          for (let i = 1; i < n; i++) {
            const monthly = 0.022 + (Math.random() - 0.3) * 0.015;
            out.push(out[i - 1] * (1 + monthly));
          }
          return out;
        }());

    const n    = nav.length;
    let minV = Infinity, maxV = -Infinity;
    for (let i = 0; i < n; i++) {
      if (nav[i] < minV) minV = nav[i];
      if (nav[i] > maxV) maxV = nav[i];
    }

    // Map to world space: X = -6 → +6, Y = -2.2 → +2.2
    const WW = 12, WH = 4.4;
    const rawPts = [];
    for (let i = 0; i < n; i++) {
      rawPts.push(new THREE.Vector3(
        (i / (n - 1)) * WW - WW / 2,
        ((nav[i] - minV) / (maxV - minV)) * WH - WH / 2 - 0.4,
        0
      ));
    }

    // Smooth with CatmullRom, then bake to a lookup table (faster than getPoint per frame)
    const spline = new THREE.CatmullRomCurve3(rawPts, false, 'catmullrom', 0.5);
    const LUT    = 1200;
    const lx     = new Float32Array(LUT);
    const ly     = new Float32Array(LUT);
    for (let i = 0; i < LUT; i++) {
      const p = spline.getPoint(i / (LUT - 1));
      lx[i] = p.x;
      ly[i] = p.y;
    }
    return { lx, ly, LUT };
  }

  const { lx, ly, LUT } = buildCurveLUT();

  // Fast linear interpolation on the LUT
  function sampleLUT(t) {
    const fi = Math.min(Math.max(t, 0), 0.9999) * (LUT - 1);
    const lo = fi | 0;
    const fr = fi - lo;
    return {
      x: lx[lo] + (lx[lo + 1] - lx[lo]) * fr,
      y: ly[lo] + (ly[lo + 1] - ly[lo]) * fr,
    };
  }

  // ─── PARTICLE BUFFERS ──────────────────────────────────────
  const COUNT    = 2800;
  const posArr   = new Float32Array(COUNT * 3);
  const colArr   = new Float32Array(COUNT * 3);
  const sizeArr  = new Float32Array(COUNT);

  // Per-particle simulation state (not uploaded to GPU directly)
  const prog   = new Float32Array(COUNT);  // curve progress 0–1
  const spd    = new Float32Array(COUNT);  // individual speed
  const ox     = new Float32Array(COUNT);  // lateral scatter
  const oy     = new Float32Array(COUNT);  // vertical scatter
  const oz     = new Float32Array(COUNT);  // depth
  const ph     = new Float32Array(COUNT);  // oscillation phase
  const bsz    = new Float32Array(COUNT);  // base point size

  // Quantora gold palette (rgb 0–1)
  // Deep gold → mid gold → bright gold → white-gold
  const PAL = [
    [0.72, 0.51, 0.15],  // #B88226
    [0.87, 0.68, 0.37],  // #DEAD5E — primary
    [0.97, 0.82, 0.55],  // #F7D18C
    [1.00, 0.94, 0.76],  // #FFF0C2
  ];

  for (let i = 0; i < COUNT; i++) {
    // Stagger particles along curve so there are no gaps at start
    prog[i] = i / COUNT;
    spd[i]  = 0.00020 + Math.random() * 0.00035;

    // Scatter: tight around curve for most, loose outliers for depth
    const scatter = Math.random() < 0.85 ? 0.18 : 0.55;
    ox[i] = (Math.random() - 0.5) * scatter;
    oy[i] = (Math.random() - 0.5) * scatter * 0.45;
    oz[i] = (Math.random() - 0.5) * (Math.random() < 0.7 ? 0.8 : 2.2);
    ph[i] = Math.random() * Math.PI * 2;

    // Larger base size for particles closer to camera (small z)
    bsz[i] = 0.4 + Math.random() * 1.3 + (1 - Math.abs(oz[i]) * 0.3) * 0.6;

    // Seed initial positions
    const p = sampleLUT(prog[i]);
    posArr[i * 3]     = p.x + ox[i];
    posArr[i * 3 + 1] = p.y + oy[i];
    posArr[i * 3 + 2] = oz[i];

    // Color: weight toward middle palette, some bright highlights
    const ci = Math.random() < 0.12 ? 3
             : Math.random() < 0.35 ? 2
             : Math.random() < 0.60 ? 1
             :                        0;
    colArr[i * 3]     = PAL[ci][0];
    colArr[i * 3 + 1] = PAL[ci][1];
    colArr[i * 3 + 2] = PAL[ci][2];

    sizeArr[i] = bsz[i];
  }

  // ─── GEOMETRY ──────────────────────────────────────────────
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(posArr,  3));
  geo.setAttribute('color',    new THREE.BufferAttribute(colArr,  3));
  geo.setAttribute('aSize',    new THREE.BufferAttribute(sizeArr, 1));

  // ─── SHADER MATERIAL ───────────────────────────────────────
  // Additive blending: particles glow on the dark background.
  // The vertex shader scales point size by 1/distance for perspective.
  // The fragment shader draws a soft circular glow with a bright core.
  const mat = new THREE.ShaderMaterial({
    vertexShader: /* glsl */`
      attribute float aSize;
      attribute vec3  color;
      varying   vec3  vColor;
      varying   float vFade;

      void main() {
        vColor        = color;
        vec4 mvPos    = modelViewMatrix * vec4(position, 1.0);
        float dist    = -mvPos.z;
        // Fade based on depth (z further away = dimmer)
        vFade         = clamp(1.0 - abs(position.z) * 0.38, 0.08, 1.0);
        // Perspective-corrected size; 240px at unit distance
        gl_PointSize  = aSize * (240.0 / dist);
        gl_Position   = projectionMatrix * mvPos;
      }
    `,
    fragmentShader: /* glsl */`
      varying vec3  vColor;
      varying float vFade;

      void main() {
        // gl_PointCoord: 0–1 over point quad
        vec2  uv   = gl_PointCoord - 0.5;   // −0.5 … +0.5
        float d    = length(uv) * 2.0;       // 0 at centre, 1 at edge

        // Core disc + soft diffuse halo
        float core = smoothstep(1.0, 0.05, d);
        float halo = smoothstep(1.0, 0.0,  d * 0.55) * 0.45;
        float a    = clamp(core + halo, 0.0, 1.0) * vFade;

        if (a < 0.008) discard;

        // Colour: boost toward white-gold at the bright core
        vec3  col  = vColor + halo * vec3(0.30, 0.22, 0.05);
        gl_FragColor = vec4(col, a * 0.88);
      }
    `,
    transparent:  true,
    depthWrite:   false,
    depthTest:    false,
    blending:     THREE.AdditiveBlending,
    vertexColors: true,
  });

  const pts = new THREE.Points(geo, mat);
  scene.add(pts);

  // ─── ANIMATE ───────────────────────────────────────────────
  // Delay start until after intro overlay finishes (~3.5 s)
  let live = false;
  setTimeout(function () { live = true; }, 3600);

  // Pre-compute sin table to avoid calling Math.sin 2800×/frame
  const SIN_LUT  = 512;
  const sinTable = new Float32Array(SIN_LUT);
  for (let i = 0; i < SIN_LUT; i++) {
    sinTable[i] = Math.sin((i / SIN_LUT) * Math.PI * 2);
  }
  function fastSin(rad) {
    const idx = ((rad % (Math.PI * 2)) / (Math.PI * 2) * SIN_LUT + SIN_LUT) % SIN_LUT | 0;
    return sinTable[idx];
  }
  function fastCos(rad) { return fastSin(rad + Math.PI * 0.5); }

  function animate(t) {
    requestAnimationFrame(animate);
    if (!live) return;

    const tSec   = t * 0.001;
    const posA   = geo.attributes.position.array;
    const szA    = geo.attributes.aSize.array;

    for (let i = 0; i < COUNT; i++) {
      // Advance along curve; loop back at end
      prog[i] += spd[i];
      if (prog[i] >= 1.0) prog[i] -= 1.0;

      const p   = sampleLUT(prog[i]);
      const phi = ph[i];

      // Gentle oscillation of the scatter offsets over time
      const driftX = fastSin(tSec * 0.42 + phi) * 0.025;
      const driftY = fastCos(tSec * 0.35 + phi) * 0.018;

      const idx = i * 3;
      posA[idx]     = p.x + ox[i] + driftX;
      posA[idx + 1] = p.y + oy[i] + driftY;
      posA[idx + 2] = oz[i] + fastSin(tSec * 0.28 + phi * 1.7) * 0.08;

      // Size pulse: brighter particles near the "head" of the curve (t close to 1)
      const hot  = prog[i] * prog[i];             // quadratic weighting toward end
      const pulse = 0.88 + fastSin(tSec * 1.8 + phi) * 0.12;
      szA[i] = bsz[i] * (0.85 + hot * 0.55) * pulse;
    }

    geo.attributes.position.needsUpdate = true;
    geo.attributes.aSize.needsUpdate    = true;

    // Very subtle camera sway — gives the scene life without distracting
    camera.position.x = fastSin(tSec * 0.06) * 0.18;
    camera.position.y = fastCos(tSec * 0.04) * 0.09;
    camera.lookAt(0, -0.25, 0);

    renderer.render(scene, camera);
  }

  requestAnimationFrame(animate);

  // ─── RESIZE ────────────────────────────────────────────────
  function onResize() {
    const w = canvas.offsetWidth  || window.innerWidth;
    const h = canvas.offsetHeight || window.innerHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
  window.addEventListener('resize', onResize, { passive: true });

})();
