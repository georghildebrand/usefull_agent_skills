/* three.js helpers for world.js: canvas textures, materials, boxes, and sprite signs that stay readable.
   EX.updateSigns runs once per frame and hides signs that would be cut, covered or overlapping. Needs THREE, declutter.js. */
(function () {
  const EX = (self.EX = self.EX || {});
  EX.canvasTex = function (w, h, draw, repeat) {
    const c = document.createElement("canvas"); c.width = w; c.height = h; draw(c.getContext("2d"), w, h);
    const t = new THREE.CanvasTexture(c); t.encoding = THREE.sRGBEncoding; t.anisotropy = 8;
    if (repeat) { t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(repeat[0], repeat[1]); }
    return t;
  };
  EX.noise = function (g, w, h, n, a) {
    for (let i = 0; i < n; i++) { g.fillStyle = `rgba(0,0,0,${Math.random() * a})`; g.fillRect(Math.random() * w, Math.random() * h, 1 + Math.random() * 2, 1); }
  };
  EX.std = (color, o = {}) => new THREE.MeshStandardMaterial(Object.assign({ color, roughness: 0.8, metalness: 0 }, o));
  EX.box = function (w, h, d, mat, x, y, z, parent) {
    const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
    m.position.set(x, y, z); m.castShadow = m.receiveShadow = true; parent.add(m); return m;
  };
  EX.put = (obj, x, y, z, parent) => { obj.position.set(x, y, z); parent.add(obj); return obj; };

  /* A sign: a sprite with a canvas texture, one bold title line and optional smaller sub lines ("\n" splits them).
     size is the height in world units before EX.autoScale changes it. */
  EX.label = function (text, { size = 0.5, color = "#f4efe6", bg = "rgba(20,16,12,0.8)", sub = "", subColor = "#d8cdbb", subK = 0.84 } = {}) {
    const fs = 64, pad = 26, lp = fs * subK / 0.84, c = document.createElement("canvas"), g = c.getContext("2d");
    const f1 = `700 ${fs}px system-ui, -apple-system, "Segoe UI", sans-serif`;
    const f2 = `600 ${Math.round(fs * subK)}px system-ui, -apple-system, "Segoe UI", sans-serif`;
    const lines = sub ? String(sub).split("\n") : [];
    g.font = f1; let w = g.measureText(text).width;
    g.font = f2; lines.forEach(ln => (w = Math.max(w, g.measureText(ln).width)));
    c.width = Math.ceil(w + pad * 2); c.height = Math.round(lines.length ? fs * 1.4 + lp * lines.length : fs * 1.45);
    if (bg) {
      g.fillStyle = bg; const r = 26; g.beginPath(); g.moveTo(r, 0);
      g.arcTo(c.width, 0, c.width, c.height, r); g.arcTo(c.width, c.height, 0, c.height, r);
      g.arcTo(0, c.height, 0, 0, r); g.arcTo(0, 0, c.width, 0, r); g.fill();
    }
    g.textBaseline = "middle"; g.fillStyle = color; g.font = f1; g.fillText(text, pad, lines.length ? fs * 0.72 : c.height / 2);
    g.font = f2; g.fillStyle = subColor; lines.forEach((ln, i) => g.fillText(ln, pad, fs * 1.18 + lp * (0.5 + i)));
    const t = new THREE.CanvasTexture(c); t.encoding = THREE.sRGBEncoding; t.anisotropy = 8;
    const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: t, depthWrite: false, transparent: true }));
    s.scale.set((size * c.width) / c.height, size, 1); s.renderOrder = 10;
    s.userData.text = sub ? text + " / " + String(sub).replace(/\n/g, " ") : text; return s;
  };

  /* Signs are drawn over the models (depthTest off), so roofs and rails never cut their text. EX.updateSigns keeps them
     readable: a sign keeps a similar size on screen (it shrinks when the camera comes close, down to KMIN, and grows
     when the camera is far, up to KMAX), and it is hidden when it would be cut by the picture edge, lie under a DOM box
     (title, caption, step panel) or a cart, or cover a sign with a higher prio.
     userData of a sign: key (name used by H.focus and H.mute), prio (higher wins; prio0 is the base value),
     off (switched off by the story; EX.allSigns = true in free mode ignores it, except for result signs: result true), owner (cart whose keep-out box it may cover),
     overCars (may cover any cart), stack (cart sign on a pole: base height and level n), noscale (the story scales it),
     culled ("" when shown, else the reason). */
  const NEAR = 22, KMIN = 0.42, KMAX = 1.3, wp = new THREE.Vector3(), cp = new THREE.Vector3(), rt = new THREE.Vector3(), up = new THREE.Vector3(), q = new THREE.Vector3();
  EX.signs = []; EX.keepOut = [];   /* keepOut entries: {obj, hx, hy}: a screen box of half size hx, hy (world units) around obj */
  EX.allSigns = false;
  EX.autoScale = function (l, prio = 2, o = {}) {
    l.material.depthTest = false; Object.assign(l.userData, { prio, prio0: prio, culled: "", s0: l.scale.clone() }, o);
    EX.signs.push(l); return l;
  };
  function chainVisible(o) { for (; o; o = o.parent) if (!o.visible) return false; return true; }
  const isOff = l => l.userData.off && (!EX.allSigns || l.userData.result);   /* a result sign stays with its scene, also in free mode */
  EX.updateSigns = function (cam, W, Hh, boxes = []) {
    cam.updateMatrixWorld(); const inv = cam.matrixWorldInverse, f = cam.projectionMatrix.elements[5] * Hh / 2;
    rt.setFromMatrixColumn(cam.matrixWorld, 0); up.setFromMatrixColumn(cam.matrixWorld, 1);
    const toPx = v => { q.copy(v).project(cam); return [(q.x + 1) / 2 * W, (1 - q.y) / 2 * Hh]; };
    const items = [], list = [];
    EX.signs.forEach(l => {
      l.userData.culled = "";
      if (!chainVisible(l.parent)) return;
      l.updateWorldMatrix(true, false); wp.setFromMatrixPosition(l.matrixWorld);
      if (!l.userData.noscale) {
        const k = Math.min(KMAX, Math.max(KMIN, cam.position.distanceTo(wp) / NEAR));
        l.scale.copy(l.userData.s0).multiplyScalar(k);
        const st = l.userData.stack;   /* cart sign: bottom edge at base, one sign height (plus a gap) per level; the pole reaches up to it */
        if (st) {
          l.position.y = st.base + st.n * l.scale.y * 1.2 + l.scale.y / 2;
          const pl = l.userData.pole, len = l.position.y - l.scale.y / 2 - st.poleFrom;
          if (pl) { pl.scale.y = Math.max(0.01, len); pl.position.y = st.poleFrom + len / 2; }
        }
        l.updateWorldMatrix(true, false); wp.setFromMatrixPosition(l.matrixWorld);
      }
      if (wp.clone().applyMatrix4(inv).z > -0.3) { l.userData.culled = "behind"; l.visible = false; return; }
      cp.setFromMatrixScale(l.matrixWorld);
      const a = toPx(q.copy(wp).addScaledVector(rt, -cp.x / 2).addScaledVector(up, cp.y / 2)), b = toPx(q.copy(wp).addScaledVector(rt, cp.x / 2).addScaledVector(up, -cp.y / 2));
      l.userData.rect = [a[0], a[1], b[0], b[1]];   /* screen box, for tools/audit.sh RECTS=1 */
      items.push({ x0: a[0], y0: a[1], x1: b[0], y1: b[1], prio: isOff(l) ? -99 : l.userData.prio, dist: cam.position.distanceTo(wp), owner: l.userData.owner, overCars: l.userData.overCars });
      list.push(l);
    });
    const keeps = boxes.slice();
    EX.keepOut.forEach(k => {
      if (!chainVisible(k.obj)) return;
      wp.setFromMatrixPosition(k.obj.matrixWorld); wp.y += 0.3; const z = -wp.clone().applyMatrix4(inv).z;
      if (z < 0.3) return;
      const c = toPx(wp), px = f / z;
      keeps.push({ x0: c[0] - k.hx * px, x1: c[0] + k.hx * px, y0: c[1] - k.hy * px, y1: c[1] + k.hy * px, owner: k.obj });
    });
    /* gap between signs: 10 px on a 1080 px high picture, less on a smaller one; 8 px from the picture edge */
    const res = EX.declutter(items, { w: W, h: Hh }, keeps, 10 * Math.min(1, Hh / 1080), 8);
    list.forEach((l, i) => { l.userData.culled = isOff(l) ? "off" : res[i].show ? "" : res[i].why; l.visible = !l.userData.culled; });
    EX.signs.forEach(l => { if (l.userData.pole) l.userData.pole.visible = l.visible; });   /* a cart's pole shows only with its sign */
  };
})();
