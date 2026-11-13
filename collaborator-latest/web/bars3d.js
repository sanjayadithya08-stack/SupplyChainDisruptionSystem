// Small orbitable 3D bar chart with HTML labels projected from bar tops.
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

export function createBars3D(container, items, { format = v => v } = {}) {
  container.innerHTML = '';
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  container.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
  camera.position.set(0, 5.2, 9.5);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true; controls.enablePan = false; controls.enableZoom = false;
  controls.minPolarAngle = 0.5; controls.maxPolarAngle = 1.35;
  controls.autoRotate = true; controls.autoRotateSpeed = 0.6;
  controls.target.set(0, 1.1, 0);

  scene.add(new THREE.AmbientLight(0x8899ff, 0.7));
  const key = new THREE.DirectionalLight(0xffffff, 1.3); key.position.set(4, 8, 6); scene.add(key);
  const fill = new THREE.PointLight(0x38e1ff, 12, 20); fill.position.set(-5, 3, -3); scene.add(fill);

  const grid = new THREE.GridHelper(12, 24, 0x2a4a8a, 0x15264a);
  grid.material.transparent = true; grid.material.opacity = 0.5; scene.add(grid);

  const max = Math.max(...items.map(i => i.value), 1);
  const n = items.length;
  const radius = Math.max(2.6, n * 0.48);
  const bars = [];
  const labels = [];
  items.forEach((it, i) => {
    const a = (i / n) * Math.PI * 2;
    const h = 0.25 + (it.value / max) * 3.4;
    const geo = new THREE.BoxGeometry(0.62, 1, 0.62); geo.translate(0, 0.5, 0);
    const color = new THREE.Color(it.color);
    const mat = new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: 0.35, metalness: 0.3, roughness: 0.35, transparent: true, opacity: 0.92 });
    const bar = new THREE.Mesh(geo, mat);
    bar.position.set(Math.cos(a) * radius, 0, Math.sin(a) * radius);
    bar.scale.y = 0.001;
    bar.userData = { h, delay: i * 0.07 };
    const edges = new THREE.LineSegments(new THREE.EdgesGeometry(geo), new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.25 }));
    bar.add(edges);
    scene.add(bar); bars.push(bar);

    const el = document.createElement('div');
    el.className = 'bar-label';
    el.innerHTML = `<b>${format(it.value)}</b>${it.label}`;
    container.appendChild(el); labels.push(el);
  });

  function resize() {
    const w = container.clientWidth, h = container.clientHeight;
    renderer.setSize(w, h); camera.aspect = w / h; camera.updateProjectionMatrix();
  }
  const ro = new ResizeObserver(resize); ro.observe(container); resize();

  const clock = new THREE.Clock();
  const v = new THREE.Vector3();
  let alive = true;
  function frame() {
    if (!alive) return;
    requestAnimationFrame(frame);
    if (document.hidden || !container.isConnected || container.offsetParent === null) return;
    const t = clock.getElapsedTime();
    controls.update();
    const w = container.clientWidth, h = container.clientHeight;
    bars.forEach((b, i) => {
      const k = Math.min(1, Math.max(0, (t - b.userData.delay) / 0.9));
      b.scale.y = Math.max(0.001, b.userData.h * (1 - Math.pow(1 - k, 3)));
      v.set(b.position.x, b.scale.y + 0.25, b.position.z).project(camera);
      const el = labels[i];
      el.style.left = `${(v.x * 0.5 + 0.5) * w}px`;
      el.style.top = `${(-v.y * 0.5 + 0.5) * h}px`;
      el.style.opacity = v.z < 1 ? 1 : 0;
    });
    renderer.render(scene, camera);
  }
  frame();
  return { dispose() { alive = false; ro.disconnect(); renderer.dispose(); container.innerHTML = ''; } };
}
