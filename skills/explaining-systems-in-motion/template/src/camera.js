/* Camera rig: an orbit pose (target x, y, z; distance r; angles theta and phi) that the story flies between with
   engine tweens, and free orbit by mouse in free mode. There is no cab or chase view: playback stays wide.
   Needs THREE, engine.js, util3d.js. */
(function () {
  const EX = self.EX;
  EX.createRig = function (camera, engine, dom) {
    const pose = { x: 0, y: 0, z: 0, r: 30, theta: 0, phi: 0.8 }, KEYS = ["x", "y", "z", "r", "theta", "phi"];
    let free = false, drag = null, gen = 0;   /* gen: a flight belongs to the mode it was started in; a mode change stops older flights */
    const P = new THREE.Vector3();
    function flyTo(p, ms = 1600, delay = 0) {
      let a = null; const g = gen;
      engine.tween(ms, t => { if (g !== gen) return; if (!a) a = Object.assign({}, pose); const e = EX.ease(t); KEYS.forEach(k => (pose[k] = a[k] + (p[k] - a[k]) * e)); }, delay);
    }
    /* DOM boxes that signs must not lie under: title, step panel, caption and the other panels, when shown */
    function boxes() {
      return ["title", "steps", "cap", "help", "free", "card"].map(id => document.getElementById(id)).filter(e => e && !e.hidden && e.offsetWidth > 0)
        .map(e => { const r = e.getBoundingClientRect(); return { x0: r.left - 6, y0: r.top - 6, x1: r.right + 6, y1: r.bottom + 6 }; });
    }
    function update() {
      /* the poses are made for 16:9; a narrower screen moves the camera back so the same width stays in the picture */
      const s = Math.sin(pose.phi), r = pose.r * Math.max(1, 16 / 9 / camera.aspect);
      P.set(pose.x + r * s * Math.sin(pose.theta), pose.y + r * Math.cos(pose.phi), pose.z + r * s * Math.cos(pose.theta));
      camera.position.copy(P); camera.lookAt(pose.x, pose.y, pose.z);
      EX.updateSigns(camera, dom.clientWidth, dom.clientHeight, boxes());
    }
    dom.addEventListener("pointerdown", e => { if (free) drag = { x: e.clientX, y: e.clientY }; });
    addEventListener("pointerup", () => (drag = null));
    addEventListener("pointermove", e => {
      if (!drag) return;
      pose.theta -= (e.clientX - drag.x) * 0.005;
      pose.phi = Math.min(1.45, Math.max(0.2, pose.phi - (e.clientY - drag.y) * 0.004));
      drag = { x: e.clientX, y: e.clientY };
    });
    dom.addEventListener("wheel", e => { if (free) pose.r = Math.min(80, Math.max(4, pose.r * (1 + Math.sign(e.deltaY) * 0.08))); }, { passive: true });
    return {
      pose, flyTo, update,
      /* free mode takes the camera from the story: flights still running stop, so drag and scroll act at once */
      setFree(b) { if (b !== free) gen++; free = b; drag = null; },
      get free() { return free; },
    };
  };
})();
