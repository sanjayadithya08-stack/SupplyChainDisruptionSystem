// Interactive 3D globe: land dot-matrix, animated trade-route arcs, moving shipments, pulsing geo events.
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

export const RISK_COLORS = { LOW: '#2fe39a', MEDIUM: '#ffc845', HIGH: '#ff8a3d', CRITICAL: '#ff3d71', UNKNOWN: '#8898b8' };
export const STATUS_COLORS = { 'In Transit': '#38e1ff', Delayed: '#ff3d71', Pending: '#ffc845', Delivered: '#8898b8' };

const D2R = Math.PI / 180;
const R = 1;

export function latLonToVec3(lat, lon, r = R) {
  const phi = (90 - lat) * D2R, th = (lon + 180) * D2R;
  return new THREE.Vector3(-r * Math.sin(phi) * Math.cos(th), r * Math.cos(phi), r * Math.sin(phi) * Math.sin(th));
}

function glowTexture() {
  const c = document.createElement('canvas'); c.width = c.height = 64;
  const g = c.getContext('2d');
  const grad = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  grad.addColorStop(0, 'rgba(255,255,255,1)');
  grad.addColorStop(0.25, 'rgba(255,255,255,.55)');
  grad.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = grad; g.fillRect(0, 0, 64, 64);
  return new THREE.CanvasTexture(c);
}

function dotTexture() {
  const c = document.createElement('canvas'); c.width = c.height = 32;
  const g = c.getContext('2d');
  g.fillStyle = '#fff'; g.beginPath(); g.arc(16, 16, 14, 0, Math.PI * 2); g.fill();
  return new THREE.CanvasTexture(c);
}

/** Smooth arc over the sphere through every waypoint, lifted by a single global altitude bump. */
function buildArcPoints(path) {
  const vs = path.map(([lat, lon]) => latLonToVec3(lat, lon));
  const segAngles = vs.slice(1).map((v, i) => vs[i].angleTo(v));
  const total = segAngles.reduce((a, b) => a + b, 0) || 1e-6;
  const H = Math.min(0.34, total * 0.13) + 0.025;
  const pts = [];
  let acc = 0;
  segAngles.forEach((ang, i) => {
    const n = Math.max(10, Math.ceil(ang * 48));
    for (let k = i === 0 ? 0 : 1; k <= n; k++) {
      const t = k / n;
      const v = new THREE.Vector3().copy(vs[i]).lerp(vs[i + 1], t).normalize();
      const T = (acc + ang * t) / total;
      pts.push(v.multiplyScalar(R + 0.004 + H * Math.sin(Math.PI * T)));
    }
    acc += ang;
  });
  return pts;
}

const arcVertex = /* glsl */`
  varying vec2 vUv;
  void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`;
const arcFragment = /* glsl */`
  uniform vec3 uColor; uniform float uTime; uniform float uOffset; uniform float uDim;
  varying vec2 vUv;
  void main() {
    float d = fract(vUv.x * 2.0 - uTime * 0.22 + uOffset);
    float pulse = smoothstep(0.0, 0.12, d) * smoothstep(0.3, 0.12, d);
    float a = (0.22 + pulse * 0.95) * uDim;
    gl_FragColor = vec4(uColor * (0.75 + pulse * 0.9), a);
  }`;

const atmoVertex = /* glsl */`
  varying vec3 vNormal; varying vec3 vView;
  void main() {
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    vNormal = normalize(normalMatrix * normal); vView = normalize(-mv.xyz);
    gl_Position = projectionMatrix * mv;
  }`;
const atmoFragment = /* glsl */`
  uniform vec3 uColor; uniform float uPower; uniform float uStrength; uniform float uBack;
  varying vec3 vNormal; varying vec3 vView;
  void main() {
    float f = uBack > 0.5 ? pow(max(0.0, 0.72 - dot(vNormal, vView)), uPower)
                          : pow(1.0 - max(0.0, dot(vNormal, vView)), uPower);
    gl_FragColor = vec4(uColor, 1.0) * f * uStrength;
  }`;

export function createGlobe(container, { onSelect, onHover, onAutoRotateChange } = {}) {
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  container.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(42, 1, 0.01, 100);
  camera.position.copy(latLonToVec3(28, 40, window.innerWidth < 820 ? 3.6 : 4.1));

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true; controls.dampingFactor = 0.06;
  controls.enablePan = false; controls.minDistance = 1.55; controls.maxDistance = 5.5;
  controls.rotateSpeed = 0.55; controls.zoomSpeed = 0.7;
  controls.autoRotate = true; controls.autoRotateSpeed = 0.35;

  scene.add(new THREE.AmbientLight(0x6688cc, 0.55));
  const sun = new THREE.DirectionalLight(0xbfd6ff, 1.1); sun.position.set(-3, 2, 4); scene.add(sun);

  // Starfield
  {
    const n = 1800, pos = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      const v = new THREE.Vector3().randomDirection().multiplyScalar(18 + Math.random() * 20);
      pos.set([v.x, v.y, v.z], i * 3);
    }
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    scene.add(new THREE.Points(g, new THREE.PointsMaterial({ color: 0x8fb4ff, size: 0.06, transparent: true, opacity: 0.55, depthWrite: false })));
  }

  const world = new THREE.Group(); scene.add(world);

  // Ocean sphere + atmosphere
  const earth = new THREE.Mesh(
    new THREE.SphereGeometry(R * 0.995, 96, 96),
    new THREE.MeshPhongMaterial({ color: 0x07142e, emissive: 0x030a1c, shininess: 18, specular: 0x1d3a7a }));
  world.add(earth);
  const rim = new THREE.Mesh(new THREE.SphereGeometry(R * 1.001, 96, 96), new THREE.ShaderMaterial({
    vertexShader: atmoVertex, fragmentShader: atmoFragment, transparent: true, depthWrite: false,
    blending: THREE.AdditiveBlending,
    uniforms: { uColor: { value: new THREE.Color('#3b7bff') }, uPower: { value: 3.2 }, uStrength: { value: 0.9 }, uBack: { value: 0 } } }));
  world.add(rim);
  const halo = new THREE.Mesh(new THREE.SphereGeometry(R * 1.16, 64, 64), new THREE.ShaderMaterial({
    vertexShader: atmoVertex, fragmentShader: atmoFragment, transparent: true, depthWrite: false,
    side: THREE.BackSide, blending: THREE.AdditiveBlending,
    uniforms: { uColor: { value: new THREE.Color('#2f8bff') }, uPower: { value: 4.0 }, uStrength: { value: 1.05 }, uBack: { value: 1 } } }));
  world.add(halo);

  // Graticule
  {
    const mat = new THREE.LineBasicMaterial({ color: 0x2a4a8a, transparent: true, opacity: 0.18 });
    for (let lat = -60; lat <= 60; lat += 30) {
      const pts = []; for (let lon = -180; lon <= 180; lon += 4) pts.push(latLonToVec3(lat, lon, R * 1.0005));
      world.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), mat));
    }
    for (let lon = -180; lon < 180; lon += 30) {
      const pts = []; for (let lat = -90; lat <= 90; lat += 4) pts.push(latLonToVec3(lat, lon, R * 1.0005));
      world.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), mat));
    }
  }

  const GLOW = glowTexture();
  const layers = { routes: new THREE.Group(), shipments: new THREE.Group(), events: new THREE.Group(), hubs: new THREE.Group() };
  Object.values(layers).forEach(g => world.add(g));

  // Selection marker
  const marker = new THREE.Mesh(new THREE.RingGeometry(0.035, 0.042, 48),
    new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.9, side: THREE.DoubleSide, depthWrite: false }));
  marker.visible = false; world.add(marker);
  let markerTarget = null;

  const routeCurves = new Map();
  const shipmentObjs = new Map();
  const pickables = [];
  const arcMaterials = [];
  const eventRings = [];

  async function loadLand() {
    try {
      const [{ geoPath, geoEquirectangular }, topojson] = await Promise.all([import('d3-geo'), import('topojson-client')]);
      const res = await fetch('https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/land-110m.json');
      const topo = await res.json();
      const land = topojson.feature(topo, topo.objects.land);
      const W = 1440, H = 720;
      const c = document.createElement('canvas'); c.width = W; c.height = H;
      const g = c.getContext('2d', { willReadFrequently: true });
      const proj = geoEquirectangular().scale(W / (2 * Math.PI)).translate([W / 2, H / 2]);
      g.fillStyle = '#fff'; g.beginPath(); geoPath(proj, g)(land); g.fill();
      const px = g.getImageData(0, 0, W, H).data;
      const positions = [], colors = [];
      const step = 0.62;
      const cA = new THREE.Color('#2a63ff'), cB = new THREE.Color('#5fe3ff');
      for (let lat = -84; lat <= 84; lat += step) {
        const ring = Math.max(1, Math.floor(Math.cos(lat * D2R) * 360 / step));
        for (let i = 0; i < ring; i++) {
          const lon = -180 + (i / ring) * 360;
          const x = Math.floor((lon + 180) / 360 * W), y = Math.floor((90 - lat) / 180 * H);
          if (px[(y * W + x) * 4 + 3] > 128) {
            const v = latLonToVec3(lat, lon, R * 1.002);
            positions.push(v.x, v.y, v.z);
            const col = cA.clone().lerp(cB, (lat + 84) / 168 * 0.7 + Math.random() * 0.3);
            colors.push(col.r, col.g, col.b);
          }
        }
      }
      const geo = new THREE.BufferGeometry();
      geo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
      geo.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
      const pts = new THREE.Points(geo, new THREE.PointsMaterial({
        size: 0.0105, map: dotTexture(), vertexColors: true, transparent: true, alphaTest: 0.3, opacity: 0.95, depthWrite: false }));
      world.add(pts);
    } catch (e) {
      console.warn('Land data unavailable; rendering ocean-only globe.', e);
    }
  }

  function clearLayer(g) {
    while (g.children.length) {
      const o = g.children.pop();
      o.traverse?.(n => { n.geometry?.dispose?.(); if (n.material && n.material !== marker.material) n.material.dispose?.(); });
    }
  }

  function setData(net) {
    Object.values(layers).forEach(clearLayer);
    routeCurves.clear(); shipmentObjs.clear(); pickables.length = 0; arcMaterials.length = 0; eventRings.length = 0;

    // Routes
    net.routes.forEach((r, i) => {
      const pts = buildArcPoints(r.path);
      const curve = new THREE.CatmullRomCurve3(pts);
      routeCurves.set(r.id, curve);
      const mat = new THREE.ShaderMaterial({
        vertexShader: arcVertex, fragmentShader: arcFragment, transparent: true, depthWrite: false,
        blending: THREE.AdditiveBlending,
        uniforms: { uColor: { value: new THREE.Color(RISK_COLORS[r.risk_level] || '#38e1ff') },
          uTime: { value: 0 }, uOffset: { value: i * 0.137 }, uDim: { value: 1 } } });
      arcMaterials.push(mat);
      const radius = r.risk_level === 'CRITICAL' ? 0.0042 : 0.003;
      const tube = new THREE.Mesh(new THREE.TubeGeometry(curve, Math.min(400, pts.length * 2), radius, 6, false), mat);
      tube.userData = { kind: 'route', data: r };
      layers.routes.add(tube);
    });

    // Hubs
    net.hubs.forEach(h => {
      const p = latLonToVec3(h.lat, h.lon, R * 1.003);
      const dot = new THREE.Mesh(new THREE.SphereGeometry(0.0085, 12, 12), new THREE.MeshBasicMaterial({ color: 0xdff6ff }));
      dot.position.copy(p);
      const beam = new THREE.Mesh(new THREE.CylinderGeometry(0.0015, 0.0015, 0.06, 6),
        new THREE.MeshBasicMaterial({ color: 0x38e1ff, transparent: true, opacity: 0.55 }));
      beam.position.copy(latLonToVec3(h.lat, h.lon, R * 1.033));
      beam.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), p.clone().normalize());
      const glow = new THREE.Sprite(new THREE.SpriteMaterial({ map: GLOW, color: 0x38e1ff, transparent: true, opacity: 0.6, depthWrite: false, blending: THREE.AdditiveBlending }));
      glow.scale.setScalar(0.06); glow.position.copy(p);
      dot.userData = { kind: 'hub', data: h };
      layers.hubs.add(dot, beam, glow); pickables.push(dot);
    });

    // Shipments
    net.shipments.forEach((s, i) => {
      const curve = routeCurves.get(s.route_id);
      if (!curve) return;
      const color = new THREE.Color(STATUS_COLORS[s.status] || '#38e1ff');
      const m = new THREE.Mesh(new THREE.SphereGeometry(0.0125, 14, 14), new THREE.MeshBasicMaterial({ color }));
      const glow = new THREE.Sprite(new THREE.SpriteMaterial({ map: GLOW, color, transparent: true, opacity: 0.85, depthWrite: false, blending: THREE.AdditiveBlending }));
      glow.scale.setScalar(0.075); m.add(glow);
      m.userData = { kind: 'shipment', data: s, curve, base: s.progress ?? 0.5, phase: i * 1.7, glow };
      m.position.copy(curve.getPointAt(Math.min(0.999, Math.max(0, m.userData.base))));
      layers.shipments.add(m); pickables.push(m); shipmentObjs.set(s.id, m);
    });

    // Geo events
    net.events.forEach(ev => {
      const color = new THREE.Color(RISK_COLORS[ev.severity] || '#ffc845');
      const n = latLonToVec3(ev.lat, ev.lon, 1).normalize();
      const grp = new THREE.Group();
      grp.position.copy(n.clone().multiplyScalar(R * 1.004));
      grp.lookAt(n.clone().multiplyScalar(2));
      for (let k = 0; k < 2; k++) {
        const ring = new THREE.Mesh(new THREE.RingGeometry(0.03, 0.036, 48),
          new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.8, side: THREE.DoubleSide, depthWrite: false, blending: THREE.AdditiveBlending }));
        ring.userData.phase = k * 0.5;
        grp.add(ring); eventRings.push(ring);
      }
      const core = new THREE.Mesh(new THREE.CircleGeometry(0.014, 24),
        new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.95, side: THREE.DoubleSide, depthWrite: false }));
      core.userData = { kind: 'event', data: ev };
      grp.add(core); pickables.push(core);
      layers.events.add(grp);
    });
  }

  function setShipmentRisk(riskById) {
    shipmentObjs.forEach((m, id) => {
      const label = riskById?.[id];
      const c = new THREE.Color(label ? RISK_COLORS[label] : (STATUS_COLORS[m.userData.data.status] || '#38e1ff'));
      m.material.color.copy(c); m.userData.glow.material.color.copy(c);
      const big = label === 'CRITICAL' ? 0.13 : label === 'HIGH' ? 0.1 : 0.075;
      m.userData.glow.scale.setScalar(big);
    });
  }

  // ── Camera flights ──
  let flight = null;
  function flyTo(lat, lon, dist) {
    const from = camera.position.clone();
    const d = dist ?? Math.min(from.length(), 3.0);
    const to = latLonToVec3(lat, lon, 1).normalize().multiplyScalar(d);
    flight = { from, to, t: 0 };
    setAutoRotate(false);
  }
  function setAutoRotate(on) {
    controls.autoRotate = on; onAutoRotateChange?.(on);
  }

  function focusShipment(id) {
    const m = shipmentObjs.get(id); if (!m) return;
    const p = m.position.clone().normalize();
    const lat = 90 - Math.acos(p.y) / D2R;
    const lon = ((Math.atan2(p.z, -p.x) / D2R) - 180 + 540) % 360 - 180;
    flyTo(lat, lon, 2.6);
    select(m);
  }

  function select(obj) {
    markerTarget = obj;
    marker.visible = !!obj;
    onSelect?.(obj ? obj.userData : null);
  }

  // ── Picking ──
  const ray = new THREE.Raycaster(); ray.params.Points = { threshold: 0 };
  const ndc = new THREE.Vector2();
  let down = null, hovered = null;
  function pick(ev) {
    const rect = renderer.domElement.getBoundingClientRect();
    ndc.set(((ev.clientX - rect.left) / rect.width) * 2 - 1, -((ev.clientY - rect.top) / rect.height) * 2 + 1);
    ray.setFromCamera(ndc, camera);
    const visible = pickables.filter(o => o.parent?.visible !== false && (o.parent?.parent?.visible ?? true));
    const hits = ray.intersectObjects([earth, ...visible], false);
    // also test enlarged spheres for tiny targets
    if (!hits.length || hits[0].object === earth) {
      const earthHit = hits.find(h => h.object === earth);
      let best = null, bestD = 0.035;
      visible.forEach(o => {
        const wp = o.getWorldPosition(new THREE.Vector3());
        if (earthHit && wp.distanceTo(camera.position) > earthHit.distance + 0.02) return;
        const d = ray.ray.distanceToPoint(wp) / (wp.distanceTo(camera.position) / 2.5);
        if (d < bestD) { bestD = d; best = o; }
      });
      return best;
    }
    return hits[0].object;
  }
  renderer.domElement.addEventListener('pointerdown', e => { down = { x: e.clientX, y: e.clientY }; });
  renderer.domElement.addEventListener('pointerup', e => {
    if (down && Math.hypot(e.clientX - down.x, e.clientY - down.y) < 5) {
      const o = pick(e);
      select(o);
      if (o) setAutoRotate(false);
    }
    down = null;
  });
  renderer.domElement.addEventListener('pointermove', e => {
    if (e.buttons) { onHover?.(null, e); return; }
    const o = pick(e);
    if (o !== hovered) { hovered = o; renderer.domElement.style.cursor = o ? 'pointer' : ''; }
    onHover?.(o ? o.userData : null, e);
  });
  renderer.domElement.addEventListener('pointerleave', e => onHover?.(null, e));
  controls.addEventListener('start', () => { flight = null; });

  // ── Resize & loop ──
  function resize() {
    const w = container.clientWidth, h = container.clientHeight;
    renderer.setSize(w, h, false);
    renderer.domElement.style.width = w + 'px'; renderer.domElement.style.height = h + 'px';
    camera.aspect = w / h;
    // shift the globe left on wide screens so right-hand panels don't cover it
    camera.setViewOffset(w, h, w > 1100 && document.body.dataset.view !== 'command' ? w * 0.17 : 0, 0, w, h);
    camera.updateProjectionMatrix();
  }
  new ResizeObserver(resize).observe(container);
  resize();

  const clock = new THREE.Clock();
  const tmp = new THREE.Vector3();
  function frame() {
    requestAnimationFrame(frame);
    if (document.hidden) return;
    const dt = Math.min(clock.getDelta(), 0.05), t = clock.elapsedTime;

    if (flight) {
      flight.t = Math.min(1, flight.t + dt / 1.3);
      const e = 1 - Math.pow(1 - flight.t, 3);
      const dir = flight.from.clone().normalize().lerp(flight.to.clone().normalize(), e).normalize();
      camera.position.copy(dir.multiplyScalar(THREE.MathUtils.lerp(flight.from.length(), flight.to.length(), e)));
      if (flight.t >= 1) flight = null;
    }
    controls.update();

    arcMaterials.forEach(m => { m.uniforms.uTime.value = t; });
    shipmentObjs.forEach(m => {
      const u = m.userData;
      const p = Math.min(0.995, Math.max(0.005, u.base + 0.012 * Math.sin(t * 0.25 + u.phase)));
      u.curve.getPointAt(p, m.position);
      m.scale.setScalar(1 + 0.12 * Math.sin(t * 3 + u.phase));
    });
    eventRings.forEach(r => {
      const k = ((t * 0.55 + r.userData.phase) % 1);
      r.scale.setScalar(0.6 + k * 2.2); r.material.opacity = 0.85 * (1 - k);
    });
    if (markerTarget) {
      markerTarget.getWorldPosition(tmp);
      marker.position.copy(tmp);
      marker.lookAt(camera.position);
      marker.scale.setScalar(1 + 0.15 * Math.sin(t * 4));
    }
    renderer.render(scene, camera);
  }
  frame();
  const landReady = loadLand();

  return {
    landReady, setData, setShipmentRisk, flyTo, focusShipment, setAutoRotate, resize,
    setLayer(name, on) { if (layers[name]) layers[name].visible = on; if (name === 'routes') layers.hubs.visible = on; },
    clearSelection() { select(null); },
  };
}
