import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { CSS2DRenderer, CSS2DObject } from "three/addons/renderers/CSS2DRenderer.js";

const data = JSON.parse(document.getElementById("graph-data").textContent);
const stage = document.getElementById("stage");
const tooltip = document.getElementById("tooltip");
const detail = document.getElementById("detail");

const PATH_COLORS = ["#ef4444", "#f59e0b", "#fbbf24"];
const TYPE_ORDER = ["NetworkZone", "Asset", "Vulnerability", "Secret", "Identity", "Permission", "AttackTechnique", "Data"];

// ---------- scene setup ----------
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0b1020);
scene.fog = new THREE.FogExp2(0x0b1020, 0.012);
const camera = new THREE.PerspectiveCamera(50, stage.clientWidth / stage.clientHeight, 0.1, 500);
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setSize(stage.clientWidth, stage.clientHeight);
stage.appendChild(renderer.domElement);

const labelRenderer = new CSS2DRenderer();
labelRenderer.setSize(stage.clientWidth, stage.clientHeight);
Object.assign(labelRenderer.domElement.style, { position: "absolute", top: "0", pointerEvents: "none" });
stage.appendChild(labelRenderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;

scene.add(new THREE.AmbientLight(0xffffff, 0.55));
const keyLight = new THREE.DirectionalLight(0xffffff, 1.1);
keyLight.position.set(10, 20, 15);
scene.add(keyLight);

// ---------- nodes ----------
const nodeObjects = new Map(); // id -> {mesh, label, data}

function geometryFor(shape) {
  switch (shape) {
    case "octahedron": return new THREE.OctahedronGeometry(0.75);
    case "cube": return new THREE.BoxGeometry(1.1, 1.1, 1.1);
    case "tetrahedron": return new THREE.TetrahedronGeometry(0.85);
    case "cylinder": return new THREE.CylinderGeometry(0.45, 0.45, 0.9, 20);
    case "torus": return new THREE.TorusGeometry(0.65, 0.22, 16, 40);
    case "cone": return new THREE.ConeGeometry(0.55, 1.1, 20);
    case "glow_sphere": return new THREE.SphereGeometry(0.8, 32, 32);
    default: return new THREE.SphereGeometry(0.65, 32, 32);
  }
}

function glowSprite(color) {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 128;
  const ctx = canvas.getContext("2d");
  const g = ctx.createRadialGradient(64, 64, 0, 64, 64, 64);
  g.addColorStop(0, color);
  g.addColorStop(1, "rgba(0,0,0,0)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 128, 128);
  const material = new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(canvas), blending: THREE.AdditiveBlending, depthWrite: false });
  const sprite = new THREE.Sprite(material);
  sprite.scale.set(4, 4, 1);
  return sprite;
}

function createNode(n) {
  const material = new THREE.MeshStandardMaterial({
    color: n.color, emissive: n.color, emissiveIntensity: n.onPath ? 0.55 : 0.12,
    metalness: 0.2, roughness: 0.45, transparent: true,
  });
  const mesh = new THREE.Mesh(geometryFor(n.shape), material);
  mesh.position.set(...n.pos);
  mesh.userData.id = n.id;
  if (n.shape === "glow_sphere") mesh.add(glowSprite(n.color));
  if (n.onPath) mesh.scale.setScalar(1.25);

  const div = document.createElement("div");
  div.className = "node-label" + (n.onPath ? " on-path" : "");
  div.textContent = n.label;
  const label = new CSS2DObject(div);
  label.position.set(0, 1.2, 0);
  mesh.add(label);

  scene.add(mesh);
  nodeObjects.set(n.id, { mesh, label: div, data: n, baseScale: mesh.scale.x });
}
data.nodes.forEach(createNode);

// ---------- edges ----------
const edgeObjects = []; // {objects: [...], data}

function edgeEndpoints(e) {
  const a = nodeObjects.get(e.source).mesh.position;
  const b = nodeObjects.get(e.target).mesh.position;
  return [a, b];
}

function arrowHead(a, b, color, size) {
  const dir = new THREE.Vector3().subVectors(b, a);
  const cone = new THREE.Mesh(
    new THREE.ConeGeometry(size, size * 2.6, 12),
    new THREE.MeshBasicMaterial({ color, transparent: true }),
  );
  cone.position.copy(a).addScaledVector(dir, 0.72);
  cone.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.clone().normalize());
  return cone;
}

function createEdge(e) {
  const [a, b] = edgeEndpoints(e);
  const objects = [];
  if (e.pathRank === null || e.pathRank === undefined) {
    const geom = new THREE.BufferGeometry().setFromPoints([a, b]);
    objects.push(new THREE.Line(geom, new THREE.LineBasicMaterial({ color: 0x94a3b8, transparent: true, opacity: 0.3 })));
    objects.push(arrowHead(a, b, 0x94a3b8, 0.12));
  } else {
    const color = PATH_COLORS[Math.min(e.pathRank, PATH_COLORS.length - 1)];
    const radius = e.pathRank === 0 ? 0.11 : 0.05;
    const curve = new THREE.LineCurve3(a.clone(), b.clone());
    const material = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: e.pathRank === 0 ? 0.95 : 0.6 });
    objects.push(new THREE.Mesh(new THREE.TubeGeometry(curve, 1, radius, 10, false), material));
    objects.push(arrowHead(a, b, color, e.pathRank === 0 ? 0.25 : 0.16));
  }
  objects.forEach((o) => scene.add(o));
  edgeObjects.push({ objects, data: e });
}
data.edges.forEach(createEdge);

// ---------- flowing particles along the top path ----------
const particles = [];
function createPathParticles(pathIds) {
  if (!pathIds || pathIds.length < 2) return;
  const points = pathIds.map((id) => nodeObjects.get(id).mesh.position.clone());
  const curve = new THREE.CatmullRomCurve3(points, false, "catmullrom", 0);
  for (let i = 0; i < 14; i++) {
    const p = new THREE.Mesh(new THREE.SphereGeometry(0.12, 8, 8), new THREE.MeshBasicMaterial({ color: 0xfff1f2 }));
    p.userData = { curve, t: i / 14 };
    scene.add(p);
    particles.push(p);
  }
}
createPathParticles(data.paths[0]);

// ---------- camera framing ----------
function frameAll() {
  const box = new THREE.Box3();
  nodeObjects.forEach(({ mesh }) => box.expandByPoint(mesh.position));
  const center = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3()).length();
  camera.position.set(center.x - size * 0.15, center.y + size * 0.35, center.z + size * 0.85);
  controls.target.copy(center);
  controls.update();
}
frameAll();

// ---------- legend ----------
const legend = document.getElementById("legend");
const typeColors = new Map(data.nodes.map((n) => [n.type, n.color]));
TYPE_ORDER.filter((t) => typeColors.has(t)).forEach((t) => {
  const row = document.createElement("div");
  const sw = document.createElement("span");
  sw.className = "sw";
  sw.style.background = typeColors.get(t);
  row.append(sw, document.createTextNode(t));
  legend.appendChild(row);
});
if (data.paths.length) {
  const row = document.createElement("div");
  row.innerHTML = '<span class="sw" style="background:#ef4444"></span>Top Attack Path';
  legend.appendChild(row);
}

// ---------- interaction ----------
const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
let hovered = null;
let selected = null;

function pick(event) {
  const rect = renderer.domElement.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const meshes = [...nodeObjects.values()].map((o) => o.mesh);
  const hit = raycaster.intersectObjects(meshes, false)[0];
  return hit ? nodeObjects.get(hit.object.userData.id) : null;
}

function setHover(obj, event) {
  if (hovered && hovered !== obj) hovered.mesh.scale.setScalar(hovered.baseScale);
  hovered = obj;
  if (!obj) { tooltip.style.display = "none"; renderer.domElement.style.cursor = "default"; return; }
  obj.mesh.scale.setScalar(obj.baseScale * 1.25);
  renderer.domElement.style.cursor = "pointer";
  tooltip.textContent = `${obj.data.label} (${obj.data.type})`;
  const rect = stage.getBoundingClientRect();
  tooltip.style.left = `${event.clientX - rect.left + 12}px`;
  tooltip.style.top = `${event.clientY - rect.top + 12}px`;
  tooltip.style.display = "block";
}

function neighborIds(id) {
  const ids = new Set([id]);
  data.edges.forEach((e) => {
    if (e.source === id) ids.add(e.target);
    if (e.target === id) ids.add(e.source);
  });
  return ids;
}

function setOpacity(objects, value) {
  objects.forEach((o) => { if (o.material) o.material.opacity = value; });
}

function applySelection(id) {
  const keep = id ? neighborIds(id) : null;
  nodeObjects.forEach((o, nid) => {
    const visible = !keep || keep.has(nid);
    o.mesh.material.opacity = visible ? 1 : 0.15;
    o.mesh.children.forEach((c) => { if (c.isSprite) c.material.opacity = visible ? 1 : 0.1; });
    o.mesh.material.emissiveIntensity = nid === id ? 0.9 : (o.data.onPath ? 0.55 : 0.12);
    o.label.classList.toggle("dim", !visible);
  });
  edgeObjects.forEach(({ objects, data: e }) => {
    const touches = !keep || e.source === id || e.target === id;
    const base = e.pathRank === null || e.pathRank === undefined ? 0.3 : (e.pathRank === 0 ? 0.95 : 0.6);
    setOpacity(objects, touches ? (keep ? Math.max(base, 0.85) : base) : 0.05);
  });
}

function renderDetail(obj) {
  detail.replaceChildren();
  if (!obj) { detail.style.display = "none"; return; }
  const close = document.createElement("span");
  close.className = "close";
  close.textContent = "✕";
  close.onclick = () => select(null);
  const title = document.createElement("h3");
  title.textContent = obj.data.label;
  const table = document.createElement("table");
  const rows = [["type", obj.data.type], ["id", obj.data.id], ...Object.entries(obj.data.attrs)];
  if (obj.data.onPath) rows.push(["attack path", "Top 1 経路上"]);
  rows.push(["neighbors", [...neighborIds(obj.data.id)].filter((i) => i !== obj.data.id)
    .map((i) => nodeObjects.get(i).data.label).join(", ")]);
  rows.forEach(([k, v]) => {
    const tr = table.insertRow();
    tr.insertCell().textContent = k;
    tr.insertCell().textContent = String(v);
  });
  detail.append(close, title, table);
  detail.style.display = "block";
}

function select(obj) {
  selected = obj;
  applySelection(obj ? obj.data.id : null);
  renderDetail(obj);
}

renderer.domElement.addEventListener("pointermove", (ev) => setHover(pick(ev), ev));
renderer.domElement.addEventListener("click", (ev) => select(pick(ev)));

// ---------- loop ----------
function animate() {
  requestAnimationFrame(animate);
  particles.forEach((p) => {
    p.userData.t = (p.userData.t + 0.0025) % 1;
    p.position.copy(p.userData.curve.getPointAt(p.userData.t));
  });
  nodeObjects.forEach(({ mesh, data: n }) => { if (n.shape !== "glow_sphere") mesh.rotation.y += 0.004; });
  controls.update();
  renderer.render(scene, camera);
  labelRenderer.render(scene, camera);
}
animate();

window.addEventListener("resize", () => {
  camera.aspect = stage.clientWidth / stage.clientHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(stage.clientWidth, stage.clientHeight);
  labelRenderer.setSize(stage.clientWidth, stage.clientHeight);
});

// Expose for debugging / automated checks.
function screenPosition(id) {
  const obj = nodeObjects.get(id);
  if (!obj) return null;
  const v = obj.mesh.getWorldPosition(new THREE.Vector3()).project(camera);
  const rect = renderer.domElement.getBoundingClientRect();
  return { x: rect.left + ((v.x + 1) / 2) * rect.width, y: rect.top + ((1 - v.y) / 2) * rect.height };
}

window.attackGraph = {
  nodeCount: nodeObjects.size,
  edgeCount: edgeObjects.length,
  select: (id) => select(nodeObjects.get(id) || null),
  screenPosition,
};
