function initWebGL() {
  const canvas = document.getElementById('hero-canvas');
  if (!canvas || typeof THREE === 'undefined') return;

  const W = window.innerWidth, H = window.innerHeight;

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
  renderer.setSize(W, H);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setClearColor(0x000509, 1);
  renderer.toneMapping = THREE.ReinhardToneMapping;
  renderer.toneMappingExposure = 1.2;

  const scene  = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(60, W / H, 0.1, 1000);
  camera.position.z = 340;

  // ── PARTICLES ──────────────────────────────────────────────
  const COUNT = 380;
  const pos   = new Float32Array(COUNT * 3);
  const col   = new Float32Array(COUNT * 3);
  const scale = new Float32Array(COUNT);
  const phase = new Float32Array(COUNT);

  for (let i = 0; i < COUNT; i++) {
    pos[i*3]   = (Math.random() - 0.5) * 880;
    pos[i*3+1] = (Math.random() - 0.5) * 660;
    pos[i*3+2] = (Math.random() - 0.5) * 480;
    // Gold with slight variation
    col[i*3]   = 0.75 + Math.random() * 0.12;
    col[i*3+1] = 0.62 + Math.random() * 0.10;
    col[i*3+2] = 0.18 + Math.random() * 0.08;
    scale[i] = Math.random() * 0.65 + 0.35;
    phase[i] = Math.random() * Math.PI * 2;
  }

  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(pos,   3));
  geo.setAttribute('aColor',   new THREE.BufferAttribute(col,   3));
  geo.setAttribute('aScale',   new THREE.BufferAttribute(scale, 1));
  geo.setAttribute('aPhase',   new THREE.BufferAttribute(phase, 1));

  const mat = new THREE.ShaderMaterial({
    uniforms: {
      uTime:       { value: 0 },
      uPixelRatio: { value: renderer.getPixelRatio() },
    },
    vertexShader: `
      attribute vec3  aColor;
      attribute float aScale;
      attribute float aPhase;
      uniform   float uTime;
      uniform   float uPixelRatio;
      varying   vec3  vColor;
      varying   float vAlpha;

      void main() {
        vColor = aColor;
        vec4 mv = modelViewMatrix * vec4(position, 1.0);

        float pulse = 0.55 + 0.45 * sin(uTime * 1.1 + aPhase);
        float depth = clamp((mv.z + 240.0) / 480.0, 0.1, 1.0);

        gl_PointSize = aScale * 7.0 * pulse * uPixelRatio * (260.0 / -mv.z);
        gl_PointSize = clamp(gl_PointSize, 0.8, 14.0);
        gl_Position  = projectionMatrix * mv;
        vAlpha = depth * pulse * 0.92;
      }
    `,
    fragmentShader: `
      varying vec3  vColor;
      varying float vAlpha;

      void main() {
        vec2  uv   = gl_PointCoord - 0.5;
        float d    = length(uv);
        float edge = 1.0 - smoothstep(0.28, 0.5, d);
        float glow = 1.0 - smoothstep(0.0,  0.5, d);
        vec3  c    = vColor * (1.0 + glow * 2.4);
        float a    = edge * vAlpha;
        if (a < 0.01) discard;
        gl_FragColor = vec4(c, a);
      }
    `,
    transparent: true,
    depthWrite:  false,
    blending:    THREE.AdditiveBlending,
  });

  const points = new THREE.Points(geo, mat);
  scene.add(points);

  // ── STATIC CONNECTION LINES ─────────────────────────────────
  const lineVerts = [];
  for (let i = 0; i < COUNT; i++) {
    for (let j = i + 1; j < COUNT; j++) {
      const dx = pos[i*3]-pos[j*3], dy = pos[i*3+1]-pos[j*3+1], dz = pos[i*3+2]-pos[j*3+2];
      if (Math.sqrt(dx*dx+dy*dy+dz*dz) < 115) {
        lineVerts.push(pos[i*3],pos[i*3+1],pos[i*3+2], pos[j*3],pos[j*3+1],pos[j*3+2]);
      }
    }
  }
  const lineGeo = new THREE.BufferGeometry();
  lineGeo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(lineVerts), 3));
  const lineMat = new THREE.LineBasicMaterial({ color:0xC6A23A, transparent:true, opacity:0.07, blending:THREE.AdditiveBlending });
  scene.add(new THREE.LineSegments(lineGeo, lineMat));

  // ── POST-PROCESSING (BLOOM) ─────────────────────────────────
  let composer = null;
  try {
    const renderPass = new THREE.RenderPass(scene, camera);
    const bloomPass  = new THREE.UnrealBloomPass(
      new THREE.Vector2(W, H),
      1.4,  // strength
      0.5,  // radius
      0.08  // threshold
    );
    composer = new THREE.EffectComposer(renderer);
    composer.addPass(renderPass);
    composer.addPass(bloomPass);
  } catch(e) {
    console.warn('Bloom unavailable, using plain renderer');
  }

  // ── MOUSE / CAMERA TILT ──────────────────────────────────────
  let tRX = 0, tRY = 0, cRX = 0, cRY = 0;
  window.addEventListener('mousemove', e => {
    tRY = (e.clientX / window.innerWidth  - 0.5) *  0.28;
    tRX = (e.clientY / window.innerHeight - 0.5) * -0.18;
  }, { passive: true });

  // ── ANIMATE ──────────────────────────────────────────────────
  const clock = new THREE.Clock();
  function animate() {
    requestAnimationFrame(animate);
    const t = clock.getElapsedTime();
    mat.uniforms.uTime.value = t;
    cRX += (tRX - cRX) * 0.035;
    cRY += (tRY - cRY) * 0.035;
    scene.rotation.x = cRX;
    scene.rotation.y = cRY + t * 0.014;
    composer ? composer.render() : renderer.render(scene, camera);
  }
  animate();

  // ── RESIZE ───────────────────────────────────────────────────
  window.addEventListener('resize', () => {
    const W2 = window.innerWidth, H2 = window.innerHeight;
    camera.aspect = W2 / H2;
    camera.updateProjectionMatrix();
    renderer.setSize(W2, H2);
    if (composer) composer.setSize(W2, H2);
  }, { passive: true });
}
