/* Wiring, loaded last: WebGL check, renderer, lights, world, carts, camera, story, UI and the frame loop.
   URL options: ?scene=N (start at scene N), &still (end state of scene N at once, for stills), ?free (free mode),
   ?autoplay, ?debug (fps and draw calls), ?nowebgl (test the fallback message).
   ?record&w=&h=&fps=&fmt=&start=&timing=<url of durations.json> is the video (record.js, driven by tools/record.py):
   no frame loop, the frame number is the clock. EX.TIMING (voice build) and the timing file make each scene as long
   as its spoken line. */
(function () {
  const EX = self.EX, Q = new URLSearchParams(location.search), REC = Q.has("record");
  function fallback(msg) {
    if (REC) { EX.postFail(msg); return; }
    document.getElementById("fallback").hidden = false; document.getElementById("fallbackMsg").textContent = msg;
    ["cap", "help", "title", "steps"].forEach(id => (document.getElementById(id).hidden = true));
  }
  if (typeof THREE === "undefined") { fallback("three.js is missing: run bash tools/fetch-three.sh, or open the built single file."); return; }
  let renderer;
  try {
    if (Q.has("nowebgl")) throw new Error("switched off with ?nowebgl");
    const c = document.createElement("canvas");
    if (!(c.getContext("webgl2") || c.getContext("webgl"))) throw new Error("no WebGL context");
    renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  } catch (e) { fallback(`This page needs WebGL, and this browser has none (${e.message}).`); return; }
  /* record mode: the drawing buffer has the video size (tools/record.py opens a window of that size) */
  const RW = +Q.get("w") || innerWidth, RH = +Q.get("h") || innerHeight;
  renderer.setPixelRatio(REC ? RW / innerWidth : Math.min(devicePixelRatio, 2)); renderer.setSize(innerWidth, innerHeight);
  renderer.outputEncoding = THREE.sRGBEncoding; renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.05;
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  document.body.prepend(renderer.domElement);
  const scene = new THREE.Scene(); scene.background = new THREE.Color(0x2a1d15); scene.fog = new THREE.Fog(0x2a1d15, 70, 140);
  const camera = new THREE.PerspectiveCamera(38, innerWidth / innerHeight, 0.1, 400);
  addEventListener("resize", () => { camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); renderer.setSize(innerWidth, innerHeight); });

  /* lights: warm sky fill, a low sun that casts shadows, a cool fill from the front */
  scene.add(new THREE.HemisphereLight(0xfff1dc, 0x3a2a20, 0.6));
  const sun = new THREE.DirectionalLight(0xffd2a1, 1.2); sun.position.set(18, 30, -14); scene.add(sun);
  sun.castShadow = true; sun.shadow.mapSize.set(2048, 2048); sun.shadow.bias = -0.0004;
  Object.assign(sun.shadow.camera, { left: -18, right: 18, top: 12, bottom: -12, near: 1, far: 90 });
  const fill = new THREE.DirectionalLight(0xc9dcff, 0.35); fill.position.set(-10, 18, 25); scene.add(fill);

  const L = EX.LAYOUT, engine = EX.createEngine(), P = EX.buildPaths(L);
  const H = EX.buildWorld(scene, L, engine), K = EX.createCarts(scene, L, engine);
  const rig = EX.createRig(camera, engine, renderer.domElement);
  /* camOn false: the story leaves the camera alone (run buttons in free mode). still: the current scene also runs without animation */
  let camOn = true, ui = null, still = Q.has("still") || Q.has("free");
  const bound = EX.bindStory({ engine, H, K, rig, L, P, camOn: () => camOn });
  /* drift: when a playing or recorded scene has no tweens left but still runs (its spoken line is longer), the camera
     moves slowly (EX.driftPose), so the picture is never fully still for long */
  const drift = { t0: null, base: null };
  function idle(now, on) {
    if (!on || rig.free || !camOn || engine.pending() > 0) { drift.t0 = null; return; }
    if (drift.t0 === null) { drift.t0 = now; drift.base = Object.assign({}, rig.pose); }
    Object.assign(rig.pose, EX.driftPose(drift.base, now - drift.t0));
  }
  /* go(n) replays scenes 0..n-1 instantly, which puts the camera on the end pose of scene n-1. When the story moves on
     by one scene, the camera goes back to where it was (after the drift), so the next flight starts there without a jump */
  let saved = null, prev = -1;
  const story = EX.createStory(bound.scenes, engine, {
    get still() { return still; },
    reset() { saved = Object.assign({}, rig.pose); H.reset(); K.clear(); bound.reset(); },   /* K.clear disposes the old carts' geometries, materials and textures */
    onScene(n) {
      if (n === prev + 1 && n > 0 && !still && camOn && saved) Object.assign(rig.pose, saved);
      prev = n; drift.t0 = null;
      if (ui) ui.onScene(n);
    },
    onEnd() { camOn = true; if (ui) ui.enterFree(); },
  });
  /* a timing table (voice build: EX.TIMING; video: the timing file) sets each scene's length (dur, ms) */
  function useTiming(T) {
    const c = EX.checkTiming(T, bound.scenes);
    c.warnings.forEach(w => console.warn("timing: " + w));
    if (!c.errors.length) EX.sceneMs(T).forEach((ms, i) => (bound.scenes[i].dur = ms));
    return c.errors;
  }
  if (!REC && EX.TIMING) useTiming(EX.TIMING).forEach(e => console.warn("timing not used: " + e));
  ui = EX.createUI({ story, rig, H, scenes: bound.scenes, camera, dom: renderer.domElement, setCam: b => (camOn = b), voice: EX.createVoice(EX.VOICE) });
  engine.step(REC ? 0 : performance.now());
  story.go(REC ? 0 : Number(Q.get("scene") || 0)); still = Q.has("still");

  if (REC) {
    document.getElementById("help").hidden = true;   /* not in the video, so signs need not keep out of it */
    const fps = +Q.get("fps") || 30, url = Q.get("timing");
    (async () => {
      try {
        const T = url ? await fetch(url).then(r => { if (!r.ok) throw new Error(`timing file ${url}: HTTP ${r.status}`); return r.json(); })
          : EX.timingFromScenes(bound.scenes, fps);
        if (T.fps !== fps) throw new Error(`the timing file has ${T.fps} fps, the recording ${fps} fps`);
        const errors = useTiming(T); if (errors.length) throw new Error("timing: " + errors.join("; "));
        await document.fonts.ready;
        await EX.startRecord({ renderer, camera, scene, story, engine, rig, idle: t => idle(t, true), timing: T,
          overlay: ["title", "steps", "cap"], W: RW, H: RH, fps, fmt: Q.get("fmt") === "jpeg" ? "jpeg" : "png", start: +Q.get("start") || 0 });
      } catch (e) { EX.postFail(e); }
    })();
    return;
  }
  if (Q.has("autoplay")) story.play();
  if (Q.has("free")) ui.enterFree();

  const dbg = Q.has("debug") ? document.getElementById("debug") : null; if (dbg) dbg.hidden = false;
  let frames = 0, last = performance.now();
  function frame(now) {
    engine.step(now); story.tick(now);
    idle(now, story.playing);
    rig.update();
    renderer.render(scene, camera);
    if (dbg && ++frames % 30 === 0) {
      dbg.textContent = `${(30000 / (now - last)).toFixed(0)} fps · ${renderer.info.render.calls} draw calls · ${renderer.info.render.triangles} triangles`; last = now;
    }
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
})();
