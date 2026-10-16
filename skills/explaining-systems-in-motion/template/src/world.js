/* The example world: floor, table, board, rails, stations, check lamps, signal, result panels, courier, and the carts.
   EX.buildWorld returns handles (H) that story.js switches; EX.createCarts builds the trains that run on the paths.
   Replace the models with your own system and keep the handle names that story.js uses.
   Needs THREE, util3d.js, track.js, engine.js. */
(function () {
  const EX = self.EX;
  const COL = { station: 0x3a4a52, roof: 0x6e2a20, lamp: 0x555f66, green: 0x14a83c, red: 0xe02020 };

  EX.buildWorld = function (scene, L, engine) {
    const { box, std, label, put, canvasTex, noise } = EX, Y = L.Y0, root = new THREE.Group(); scene.add(root);
    const H = { st: {}, lamps: [], clickables: [] };
    const stn = k => L.stations.find(s => s.key === k);
    const clickable = (obj, key) => { obj.userData.info = L.info[key]; H.clickables.push(obj); return obj; };
    /* a board sign; prio decides which sign wins when two would overlap. Signs inside a panel group keep their size (noscale) */
    const sign = (text, o, x, y, z, prio = 2, parent = root) => {
      const l = put(label(text, o), x, y, z, parent); l.userData.key = o.key;
      return EX.autoScale(l, prio, parent !== root ? { noscale: true } : {});
    };

    /* floor and table (backdrop, not clickable) */
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(200, 200), std(0x6b4a34, { roughness: 0.9 }));
    floor.rotation.x = -Math.PI / 2; floor.position.y = -7.6; floor.receiveShadow = true; root.add(floor);
    const wood = canvasTex(1024, 512, (g, w, h) => {
      g.fillStyle = "#7a4a2b"; g.fillRect(0, 0, w, h);
      for (let i = 0; i < 60; i++) { g.strokeStyle = "rgba(50,25,10,0.18)"; g.beginPath(); const y = Math.random() * h; g.moveTo(0, y); for (let x = 0; x < w; x += 40) g.lineTo(x, y + Math.sin(x * 0.01 + i) * 6); g.stroke(); }
      noise(g, w, h, 6000, 0.08);
    });
    const t = L.table, tableMat = std(0xffffff, { map: wood, roughness: 0.55 });
    box(t.w, 0.9, t.d, tableMat, 0, -0.45, 0, root);
    [[-1, -1], [1, -1], [-1, 1], [1, 1]].forEach(([sx, sz]) => box(0.9, 6.7, 0.9, tableMat, sx * (t.w / 2 - 1.4), -4.25, sz * (t.d / 2 - 1.2), root));

    /* the board: a green plate with an orange edge */
    const b = L.board, bw = b.x1 - b.x0, bd = b.z1 - b.z0, mx = (b.x0 + b.x1) / 2, mz = (b.z0 + b.z1) / 2;
    const lin = hex => new THREE.Color(hex).convertSRGBToLinear();   /* screen colours stay saturated after tone mapping */
    const edge = std(lin(0xf07c22), { emissive: lin(0xf07c22), emissiveIntensity: 0.5 });
    box(bw, Y, bd, std(lin(0x4f7a3f), { roughness: 1 }), mx, Y / 2, mz, root);
    [b.z0 + 0.1, b.z1 - 0.1].forEach(z => box(bw, 0.06, 0.2, edge, mx, Y + 0.03, z, root));
    [b.x0 + 0.1, b.x1 - 0.1].forEach(x => box(0.2, 0.06, bd, edge, x, Y + 0.03, mz, root));

    /* rails: two steel tubes and instanced sleepers per track part */
    const sleeperGeo = new THREE.BoxGeometry(0.62, 0.06, 0.16), sleeperMat = std(0x5a4030);
    const railMat = std(0xb8bec2, { metalness: 0.8, roughness: 0.35 }), dummy = new THREE.Object3D();
    Object.values(L.tracks).forEach(pts => {
      const p = EX.makePath(pts), n = Math.max(2, Math.floor(p.length / 0.42));
      const inst = new THREE.InstancedMesh(sleeperGeo, sleeperMat, n); inst.receiveShadow = true;
      for (let i = 0; i < n; i++) {
        const q = p.at((i * p.length) / (n - 1));
        dummy.position.set(q.x, Y + 0.03, q.z); dummy.rotation.set(0, -q.angle - Math.PI / 2, 0); dummy.updateMatrix(); inst.setMatrixAt(i, dummy.matrix);
      }
      root.add(inst);
      const m = Math.max(8, Math.ceil(p.length / 0.2));
      [-0.16, 0.16].forEach(off => {
        const v = [];
        for (let i = 0; i <= m; i++) { const q = p.at((i * p.length) / m); v.push(new THREE.Vector3(q.x - Math.sin(q.angle) * off, Y + 0.09, q.z + Math.cos(q.angle) * off)); }
        root.add(new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(v), m, 0.03, 5, false), railMat));
      });
    });

    /* stations with a house: house with a gable roof next to the track, sign above the roof */
    L.stations.filter(s => s.house).forEach(s => {
      const bz = s.z + s.house * 1.4;
      const base = box(2.0, 1.0, 1.2, std(s.color || COL.station, { roughness: 0.55 }), s.x, Y + 0.5, bz, root);
      const roof = box(2.1, 0.9, 0.9, std(COL.roof, { roughness: 0.7 }), s.x, Y + 1.0, bz, root); roof.rotation.x = Math.PI / 4;
      sign(s.label, { size: 0.6, sub: s.sub, key: s.key }, s.x, Y + 2.3, bz, 3);
      clickable(base, s.key); clickable(roof, s.key); H.st[s.key] = { base, roof, color: s.color || COL.station };
    });

    /* check: a dark stand behind the track with one lamp per check */
    const ck = stn("check"), sz = ck.z - 1.3;
    const stand = box(2.6, 1.3, 0.25, std(0x1a1f22), ck.x, Y + 1.15, sz, root);
    [-1.1, 1.1].forEach(dx => box(0.12, 0.5, 0.12, std(0x2b2b2b), ck.x + dx, Y + 0.25, sz, root));
    for (let i = 0; i < L.checks.n; i++) {
      const lamp = new THREE.Mesh(new THREE.SphereGeometry(0.12, 14, 10), std(COL.lamp, { roughness: 0.3 }));
      lamp.position.set(ck.x - 0.95 + (i % 6) * 0.38, Y + 1.38 - Math.floor(i / 6) * 0.45, sz + 0.16); root.add(lamp); H.lamps.push(lamp);
    }
    sign(ck.label, { size: 0.6, sub: ck.sub, key: "check" }, ck.x, Y + 2.5, sz, 3);
    clickable(stand, "check"); H.st.check = { base: stand, color: 0x1a1f22, dark: true, k: 0.12 };   /* dark: the stand keeps its colour, its glow shows */
    /* results of the check, each switched on by the scene where it happens (off until then) */
    H.passedSign = sign("12 of 12 checks passed", { size: 0.5, key: "passed", color: "#c8f5d4", bg: "rgba(14,60,30,0.92)" }, ck.x, Y + 0.3, ck.z + 1.5, 4);
    H.failSign = sign("example: check 8 fails", { size: 0.5, key: "fail", color: "#ffd0c8", bg: "rgba(110,20,20,0.95)" }, ck.x, Y + 0.3, ck.z + 1.5, 4);
    H.passedSign.userData.result = H.failSign.userData.result = true;   /* free mode does not show them in a scene before their result */

    /* signal: post, head, lamp with a halo and a small light */
    const sg = L.signal;
    box(0.14, 1.3, 0.14, std(0x2b2b2b), sg.x, Y + 0.65, sg.z, root);
    const head = box(0.7, 1.0, 0.26, std(0x1c1c1c), sg.x, Y + 1.7, sg.z, root);
    const lampMat = new THREE.MeshStandardMaterial({ color: 0x333333, roughness: 0.3 });
    const sigLamp = new THREE.Mesh(new THREE.SphereGeometry(0.3, 20, 14), lampMat); sigLamp.position.set(sg.x, Y + 1.75, sg.z + 0.14); root.add(sigLamp);
    const haloMat = new THREE.SpriteMaterial({ map: canvasTex(128, 128, (g, w) => { const r = g.createRadialGradient(w / 2, w / 2, 0, w / 2, w / 2, w / 2); r.addColorStop(0, "rgba(255,255,255,1)"); r.addColorStop(0.35, "rgba(255,255,255,0.55)"); r.addColorStop(1, "rgba(255,255,255,0)"); g.fillStyle = r; g.fillRect(0, 0, w, w); }), transparent: true, opacity: 0, depthWrite: false, blending: THREE.AdditiveBlending });
    const halo = new THREE.Sprite(haloMat); halo.scale.setScalar(2.4); halo.position.set(sg.x, Y + 1.75, sg.z + 0.3); root.add(halo);
    const sigLight = new THREE.PointLight(0xffffff, 0, 5, 2); sigLight.position.set(sg.x, Y + 1.75, sg.z + 0.6); root.add(sigLight);
    sign("signal", { size: 0.42, key: "signal" }, sg.x, Y + 2.75, sg.z, 2);
    clickable(head, "signal");
    H.signal = { set(c) {
      const hex = c === "green" ? COL.green : c === "red" ? COL.red : 0x333333;
      lampMat.color.setHex(hex); lampMat.emissive.setHex(c ? hex : 0); lampMat.emissiveIntensity = c ? 0.9 : 0;
      haloMat.color.setHex(hex); haloMat.opacity = c ? 0.9 : 0; sigLight.color.setHex(hex); sigLight.intensity = c ? 2 : 0;
    } };

    /* reject bin: an open box in front of the end of the red branch, its sign in front of it */
    const rj = stn("reject"), bin = new THREE.Group(); bin.position.set(rj.x, Y, rj.z + 1.5); root.add(bin);
    const binMat = std(0x44484c, { roughness: 0.6 });
    box(1.6, 0.08, 1.0, binMat, 0, 0.04, 0, bin); box(1.6, 0.7, 0.08, binMat, 0, 0.35, -0.5, bin); box(1.6, 0.7, 0.08, binMat, 0, 0.35, 0.5, bin);
    box(0.08, 0.7, 1.0, binMat, -0.8, 0.35, 0, bin); box(0.08, 0.7, 1.0, binMat, 0.8, 0.35, 0, bin);
    sign(rj.label, { size: 0.55, sub: rj.sub, key: "reject" }, rj.x + 0.2, Y + 0.3, rj.z + 2.75, 3);   /* in front of the bin */
    bin.children.forEach(m => clickable(m, "reject")); H.st.reject = { base: bin.children[1], color: 0x44484c };   /* all parts share binMat, so the whole bin glows */

    /* result panels: the ship board (green result) and the notice at the reject bin (red result); hidden until their scene */
    function panel(text, o, x, z) {
      const g = new THREE.Group(); g.position.set(x, Y, z); root.add(g);
      box(0.1, 0.6, 0.1, std(0x2b2b2b), 0, 0.3, 0, g);
      sign(text, o, 0, 1.05, 0, 4, g);   /* in the group: keeps its world size, showAt scales the group */
      g.visible = false; return g;
    }
    const sp = stn("ship");
    H.resultBoard = panel("ready: parcel 1", { size: 0.85, key: "result", sub: "all checks passed", color: "#c8f5d4", bg: "rgba(14,60,30,0.92)" }, sp.x - 2.4, sp.z - 2.6);
    H.notice = panel("held, not shipped", { size: 0.85, key: "notice", sub: "a person looks at it", color: "#ffd0c8", bg: "rgba(110,20,20,0.95)" }, rj.x - 3.0, rj.z + 2.0);

    /* courier: a figure next to the ship station; its sign is muted by the story until the last scene */
    const cr = L.courier, courier = new THREE.Group(); courier.position.set(cr.x, Y, cr.z); root.add(courier);
    const coat = std(0x2f6fd8, { roughness: 0.7 });
    const body = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.28, 0.9, 16), coat); body.position.y = 0.45; body.castShadow = true; courier.add(body);
    const headM = new THREE.Mesh(new THREE.SphereGeometry(0.2, 16, 12), std(0xe8c4a0)); headM.position.y = 1.08; courier.add(headM);
    courier.children.forEach(m => clickable(m, "courier")); H.courier = courier; H.courierAt = courier.position.clone();
    H.courierSign = sign("courier", { size: 0.6, sub: "by hand, once a day", key: "courier", color: "#ffe2a8", bg: "rgba(60,44,12,0.92)" }, cr.x - 1.2, Y + 0.3, cr.z + 0.9, 3);   /* on the ground in front of where the courier stops after H.courierWalk, clear of the cart */
    H.courierWalk = (delay = 0) => engine.tween(1600, k => { courier.position.x = H.courierAt.x - 1.2 * EX.ease(k); }, delay);

    /* ---- handles for the story ---- */
    /* focus: the signs with these keys win over other signs when they would overlap */
    H.focus = keys => EX.signs.forEach(l => (l.userData.prio = l.userData.prio0 + (keys.indexOf(l.userData.key) >= 0 ? 10 : 0)));
    /* a station's look: colour now (s.cur), glow (s.em) and dim factor (s.dim, 1 = not dimmed); paint writes them */
    const DIM = 0.6;
    const paint = s => {
      const m = s.base.material; m.color.copy(s.cur).multiplyScalar(s.dim); m.emissive.copy(s.em).multiplyScalar(s.dim);
      if (s.roof) s.roof.material.color.setHex(COL.roof).multiplyScalar(s.dim);
    };
    Object.values(H.st).forEach(s => { s.cur = new THREE.Color(s.color); s.em = new THREE.Color(0); s.dim = 1; });
    /* dim: the stations a scene is not about get a little darker; an empty list ends the dimming */
    H.dim = function (keys, ms = 500) {
      Object.entries(H.st).forEach(([k, s]) => {
        const from = s.dim, to = keys.length && keys.indexOf(k) < 0 ? DIM : 1;
        if (from !== to) engine.tween(ms, f => { s.dim = from + (to - from) * f; paint(s); });
      });
    };
    H.glow = function (key, color, delay = 0, ms = 500) {
      const s = H.st[key], from = new THREE.Color(s.color), to = new THREE.Color(color);
      engine.tween(ms, f => { if (!s.dark) s.cur.copy(from).lerp(to, f); s.em.copy(to).multiplyScalar((s.k || 0.45) * f); paint(s); }, delay);
    };
    /* setGlow: the end state of H.glow at once (null: back to the plain colour) */
    H.setGlow = function (key, color) {
      const s = H.st[key];
      if (color == null) { s.cur.setHex(s.color); s.em.setHex(0); }
      else { s.cur.setHex(s.dark ? s.color : color); s.em.setHex(color).multiplyScalar(s.k || 0.45); }
      paint(s);
    };
    /* mute: switch off the signs whose key starts with one of the prefixes; free mode shows them again (EX.allSigns) */
    H.mute = (prefixes, off = true) => EX.signs.forEach(l => { const k = l.userData.key || ""; if (prefixes.some(p => k.startsWith(p))) l.userData.off = off; });
    H.unmute = prefixes => H.mute(prefixes, false);
    H.signShow = (s, on, delay = 0) => engine.later(delay, () => (s.userData.off = !on));
    const lampLit = (l, i, failIndex) => {
      const hex = i === failIndex ? COL.red : COL.green;
      l.material.color.setHex(hex); l.material.emissive.setHex(hex); l.material.emissiveIntensity = i === failIndex ? 0.9 : 0.4; l.scale.setScalar(i === failIndex ? 1.6 : 1);
    };
    H.lampsGrey = () => H.lamps.forEach(l => { l.material.color.setHex(COL.lamp); l.material.emissive.setHex(0); l.scale.setScalar(1); });
    H.lampsRun = (failIndex, delay = 0, step = 120) => H.lamps.forEach((l, i) => engine.later(delay + i * step, () => lampLit(l, i, failIndex)));
    H.lampsSet = failIndex => H.lamps.forEach((l, i) => lampLit(l, i, failIndex));   /* the end state of lampsRun at once */
    H.signalTo = (color, delay = 0) => engine.later(delay, () => H.signal.set(color));
    /* showAt/hideAt grow or shrink a panel; the newest call wins (seq), so a reveal still pending cannot undo a later hide.
       showNow: full size at once */
    const s0 = o => o.userData.s0 || (o.userData.s0 = o.scale.clone());
    H.showNow = o => { o.userData.seq = (o.userData.seq || 0) + 1; o.scale.copy(s0(o)); o.visible = true; };
    H.showAt = function (o, delay = 0, ms = 600) {
      const a = s0(o), id = (o.userData.seq = (o.userData.seq || 0) + 1);
      engine.tween(ms, f => { if (o.userData.seq !== id) return; o.visible = f > 0; o.scale.copy(a).multiplyScalar(0.2 + 0.8 * EX.ease(f)); }, delay);
    };
    H.hideAt = function (o, delay = 0, ms = 400) {
      const a = s0(o), id = (o.userData.seq = (o.userData.seq || 0) + 1);
      engine.tween(ms, f => { if (o.userData.seq !== id) return; o.scale.copy(a).multiplyScalar(1 - 0.8 * EX.ease(f)); if (f >= 1) { o.visible = false; o.scale.copy(a); } }, delay);
    };
    /* reset: the state before scene 0; story.go calls it before it replays the earlier scenes */
    H.reset = function () {
      Object.values(H.st).forEach(s => { s.cur.setHex(s.color); s.em.setHex(0); s.dim = 1; paint(s); });
      H.lampsGrey(); H.signal.set(null); H.focus([]);
      [H.resultBoard, H.notice].forEach(p => { p.visible = false; p.userData.seq = 0; if (p.userData.s0) p.scale.copy(p.userData.s0); });
      H.courier.position.copy(H.courierAt);
      EX.signs.forEach(l => (l.userData.off = false)); H.passedSign.userData.off = true; H.failSign.userData.off = true;
    };
    H.reset();
    return H;
  };

  /* Carts: an engine and a cart with a parcel and a sign on a pole. A consist is a list of cars on one path. */
  EX.createCarts = function (scene, L, engine) {
    const { box, std, label } = EX, Y = L.Y0, SP = L.cart.spacing;
    const group = new THREE.Group(); scene.add(group);
    const wheelGeo = new THREE.CylinderGeometry(0.13, 0.13, 0.06, 14), wheelMat = std(0x222222, { metalness: 0.6, roughness: 0.4 });
    const poleGeo = new THREE.CylinderGeometry(0.015, 0.015, 1, 6), poleMat = new THREE.MeshBasicMaterial({ color: 0x1a1410 });
    function wheels(g) {
      [-0.3, 0.3].forEach(x => [-0.28, 0.28].forEach(z => { const w = new THREE.Mesh(wheelGeo, wheelMat); w.rotation.x = Math.PI / 2; w.position.set(x, 0.13, z); g.add(w); }));
    }
    function car(kind, text = "", color = 0x8b2a2a) {
      const g = new THREE.Group(); let cargo = null, lab = null;
      if (kind === "engine") {
        box(0.9, 0.4, 0.52, std(color, { roughness: 0.4, metalness: 0.3 }), 0.04, 0.4, 0, g);
        box(0.34, 0.6, 0.56, std(0x2b2b2b, { roughness: 0.5 }), -0.28, 0.55, 0, g);
        const chimney = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.1, 0.26, 12), std(0x222222)); chimney.position.set(0.3, 0.72, 0); g.add(chimney);
      } else {
        box(0.95, 0.12, 0.6, std(color, { roughness: 0.6 }), 0, 0.26, 0, g);
        cargo = new THREE.Group(); cargo.position.y = 0.52; g.add(cargo); cargo.visible = false;
        box(0.56, 0.4, 0.46, std(0xc49a5a, { roughness: 0.9 }), 0, 0, 0, cargo);
        box(0.3, 0.02, 0.2, std(0xf4efe6), 0, 0.21, 0, cargo);   /* the label on the parcel */
      }
      wheels(g);
      if (text) {
        /* the sign stands above its car on a thin pole; EX.updateSigns sets its height from its level (stack.n) */
        lab = EX.autoScale(label(text, { size: 0.4, bg: "rgba(20,16,12,0.9)" }), 5, { owner: g, key: "cart", stack: { base: 1.15, n: 0, poleFrom: 0.75 } });
        g.add(lab);
        const pole = new THREE.Mesh(poleGeo, poleMat); g.add(pole); lab.userData.pole = pole;
      }
      EX.keepOut.push({ obj: g, hx: 0.55, hy: 0.35 });   /* no other sign may cover a car */
      g.visible = false; group.add(g);
      return { kind, obj: g, cargo, label: lab };
    }
    function consist(cars, path) {
      return {
        cars, path, s: 0,
        place(s) {
          this.s = s;
          EX.carPositions(this.path, s, this.cars.length, SP).forEach((q, i) => {
            const o = this.cars[i].obj; o.visible = q.visible; o.position.set(q.x, Y + 0.05, q.z); o.rotation.y = -q.angle;
          });
        },
        drive(toS, ms, delay = 0) {
          let from = null;   /* read the start when the tween starts, not when it is scheduled */
          engine.tween(ms, f => { if (from === null) from = this.s; this.place(from + (toS - from) * EX.ease(f)); }, delay);
        },
        hide() { this.cars.forEach(k => (k.obj.visible = false)); },
      };
    }
    function loadCargo(cars, delay = 0) {
      cars.filter(k => k.cargo).forEach(k => engine.tween(400, f => { k.cargo.visible = f > 0; k.cargo.scale.setScalar(0.3 + 0.7 * f); }, delay));
    }
    /* clear runs on every scene change (story.go rebuilds the carts). three.js frees GPU buffers and textures only on
       dispose(), so every geometry, material and sign texture of the old cars is disposed here; shared ones stay. */
    const shared = new Set([wheelGeo, wheelMat, poleGeo, poleMat]);
    function clear() {
      const gone = new Set(group.children);
      EX.keepOut = EX.keepOut.filter(k => !gone.has(k.obj)); EX.signs = EX.signs.filter(l => !gone.has(l.parent));
      group.traverse(o => {
        if (o.geometry && !o.isSprite && !shared.has(o.geometry)) o.geometry.dispose();   /* all sprites share one geometry */
        if (o.material && !shared.has(o.material)) { if (o.material.map) o.material.map.dispose(); o.material.dispose(); }
      });
      while (group.children.length) group.remove(group.children[0]);
    }
    return { SP, car, consist, loadCargo, clear };
  };
})();
