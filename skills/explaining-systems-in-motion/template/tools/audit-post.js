/* Audit helper for tools/audit.sh: after the page has drawn a few frames, it measures every visible sign on screen and
   reports signs cut by the picture edge, signs that overlap each other, signs that cover a visible cart, and signs under
   a DOM box (title, step panel, caption, help). The result goes into <pre id="audit"> as JSON for --dump-dom. */
(function () {
  const A = window.__audit, Q = new URLSearchParams(location.search);
  function visible(o) { for (; o; o = o.parent) if (!o.visible) return false; return true; }
  function run() {
    const W = innerWidth, Hh = innerHeight, cam = A.PerspectiveCamera;
    cam.updateMatrixWorld(true);
    const right = new THREE.Vector3(), up = new THREE.Vector3(), tmp = new THREE.Vector3();
    right.setFromMatrixColumn(cam.matrixWorld, 0); up.setFromMatrixColumn(cam.matrixWorld, 1);
    const proj = v => { tmp.copy(v).project(cam); return [(tmp.x + 1) / 2 * W, (1 - tmp.y) / 2 * Hh]; };
    const signs = [];
    A.Scene.traverse(o => {
      if (!o.isSprite || !o.userData.text || !visible(o)) return;
      o.updateMatrixWorld(true);
      const c = new THREE.Vector3().setFromMatrixPosition(o.matrixWorld), sc = new THREE.Vector3().setFromMatrixScale(o.matrixWorld);
      if (c.clone().applyMatrix4(cam.matrixWorldInverse).z > -0.3) return;   /* behind the camera */
      const p = [[-1, -1], [1, 1]].map(([a, b]) => proj(c.clone().addScaledVector(right, a * sc.x / 2).addScaledVector(up, b * sc.y / 2)));
      signs.push({ t: o.userData.text, x0: p[0][0], x1: p[1][0], y0: p[1][1], y1: p[0][1], o });
    });
    const hidden = EX.signs.filter(l => l.userData.culled && !["behind", "off", "out"].includes(l.userData.culled)).map(l => l.userData.culled + ":" + l.userData.text);
    const issues = [], r0 = Math.round, box = s => `${s.t} [${r0(s.x0)}-${r0(s.x1)},${r0(s.y0)}-${r0(s.y1)}]`;
    const doms = ["title", "steps", "cap", "help"].map(id => document.getElementById(id)).filter(e => e && !e.hidden && e.offsetWidth > 0).map(e => [e.id, e.getBoundingClientRect()]);
    signs.forEach(s => {
      if (s.x1 > 0 && s.x0 < W && s.y1 > 0 && s.y0 < Hh && (s.x0 < 0 || s.x1 > W || s.y0 < 0 || s.y1 > Hh)) issues.push("CUT " + box(s));
      doms.forEach(([id, r]) => { if (s.x0 < r.right && s.x1 > r.left && s.y0 < r.bottom && s.y1 > r.top) issues.push(`UNDER-${id.toUpperCase()} ${box(s)}`); });
    });
    for (let i = 0; i < signs.length; i++) for (let j = i + 1; j < signs.length; j++) {
      const a = signs[i], b = signs[j], w = Math.min(a.x1, b.x1, W) - Math.max(a.x0, b.x0, 0), h = Math.min(a.y1, b.y1, Hh) - Math.max(a.y0, b.y0, 0);
      if (w > 2 && h > 2) issues.push(`OVERLAP ${box(a)} x ${box(b)}`);
    }
    A.cars.filter(c => visible(c.obj)).forEach(c => {
      const wp = new THREE.Vector3().setFromMatrixPosition(c.obj.matrixWorld); wp.y += 0.3;
      if (wp.clone().applyMatrix4(cam.matrixWorldInverse).z > -0.3) return;
      const [px, py] = proj(wp);
      signs.forEach(s => { if (s.o !== c.label && !s.o.userData.overCars && px > s.x0 && px < s.x1 && py > s.y0 && py < s.y1) issues.push(`COVERS-CART ${c.kind} at ${r0(px)},${r0(py)} by ${box(s)}`); });
      if (px < 0 || px > W || py < 0 || py > Hh) issues.push(`CART-OFFSCREEN ${c.kind} ${r0(px)},${r0(py)}`);
    });
    if (Q.has("rects")) EX.signs.filter(l => l.userData.rect && !["off", "behind"].includes(l.userData.culled)).forEach(l => issues.push(`RECT ${l.userData.culled || "shown"} ${l.userData.text} [${l.userData.rect.map(r0).join(",")}]`));
    document.body.insertAdjacentHTML("beforeend", `<pre id="audit" style="display:none">${JSON.stringify({ n: signs.length + " viewport " + W + "x" + Hh + "; hidden by layout: " + hidden.length + " -> " + hidden.join(" | "), issues })}</pre>`);
  }
  setTimeout(run, 2500);
})();
