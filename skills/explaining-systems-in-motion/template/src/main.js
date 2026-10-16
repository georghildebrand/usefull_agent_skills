/* Wiring, loaded last: WebGL check, renderer, lights, world, carts, camera, story, UI and the frame loop.
   URL options: ?scene=N (start at scene N), &still (end state of scene N at once, for stills), ?free (free mode),
   ?autoplay, ?debug (fps and draw calls), ?nowebgl (test the fallback message). */
(function () {
  const EX = self.EX, Q = new URLSearchParams(location.search);
  function fallback(msg) {
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
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2)); renderer.setSize(innerWidth, innerHeight);
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
  const story = EX.createStory(bound.scenes, engine, {
    get still() { return still; },
    reset() { H.reset(); K.clear(); bound.reset(); },   /* K.clear disposes the old carts' geometries, materials and textures */
    onScene(n) { if (ui) ui.onScene(n); },
    onEnd() { camOn = true; if (ui) ui.enterFree(); },
  });
  ui = EX.createUI({ story, rig, H, scenes: bound.scenes, camera, dom: renderer.domElement, setCam: b => (camOn = b) });
  engine.step(performance.now());
  story.go(Number(Q.get("scene") || 0)); still = Q.has("still");
  if (Q.has("autoplay")) story.play();
  if (Q.has("free")) ui.enterFree();

  const dbg = Q.has("debug") ? document.getElementById("debug") : null; if (dbg) dbg.hidden = false;
  let frames = 0, last = performance.now();
  function frame(now) {
    engine.step(now); story.tick(now);
    rig.update();
    renderer.render(scene, camera);
    if (dbg && ++frames % 30 === 0) {
      dbg.textContent = `${(30000 / (now - last)).toFixed(0)} fps · ${renderer.info.render.calls} draw calls · ${renderer.info.render.triangles} triangles`; last = now;
    }
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
})();
