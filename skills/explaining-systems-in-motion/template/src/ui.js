/* Overlay: fixed step panel (built from EX.STEPS), caption with progress dots, keys, free mode, click info cards,
   and in the voice build the spoken line of each scene (voice.js; key M mutes).
   Needs THREE, scene-data.js, engine.js, voice.js. */
(function () {
  const EX = self.EX;
  EX.createUI = function ({ story, rig, H, scenes, camera, dom, setCam, voice = EX.createVoice() }) {
    const $ = id => document.getElementById(id), dots = $("dots");
    const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

    /* step panel: 0 the question, 1..n the steps, n + 1 the "Then" line; a step {green, red} gets two halves */
    const SD = EX.STEPS, item = x => typeof x === "string" ? esc(x) : `<span data-part="green">${esc(x.green)}</span> <span data-part="red">${esc(x.red)}</span>`;
    $("steps").innerHTML = `<h2>${esc(SD.title)}</h2><p data-step="0">${esc(SD.question)}</p><ol>` +
      SD.items.map((x, i) => `<li data-step="${i + 1}">${item(x)}</li>`).join("") + `</ol><p data-step="${SD.items.length + 1}" class="then">${esc(SD.then)}</p>`;
    const steps = [...document.querySelectorAll("#steps [data-step]")];

    scenes.forEach((s, i) => {
      const d = document.createElement("i"); d.title = s.title;
      d.onclick = () => { leaveFree(); story.pause(); setCam(true); story.go(i); };
      dots.appendChild(d);
    });
    function help() {
      $("helpText").innerHTML = rig.free
        ? "drag to rotate · scroll to zoom · click a station · double-click flies there · <b>P</b> play again"
        : "<b>space</b> play / pause · <b>→</b> <b>←</b> scenes · <b>R</b> replay · <b>F</b> free mode";
      if (voice.available) $("helpText").innerHTML += " · <b>M</b> voice";
      $("state").textContent = (rig.free ? "free mode" : story.playing ? "playing" : "paused") + (voice.available ? (voice.muted ? " · voice off" : " · voice on") : "");
    }
    function onScene(n) {
      $("capk").textContent = `${n + 1} / ${scenes.length} · ${scenes[n].title}`; $("capt").textContent = scenes[n].text;
      [...dots.children].forEach((d, i) => (d.className = i === n ? "on" : i < n ? "done" : ""));
      /* the line of this scene is lit, earlier steps look done, later ones stay plain; the question line is never ticked */
      const k = EX.STEP_OF_SCENE[n];
      steps.forEach(e => { const i = Number(e.dataset.step); e.className = (i === k ? "on" : i < k && i > 0 ? "done" : "") + (e.classList.contains("then") ? " then" : ""); });
      const part = scenes[n].part || "";
      document.querySelectorAll("#steps [data-part]").forEach(e => (e.className = part && e.dataset.part !== part ? "part-off" : ""));
      if (rig.free) voice.stop(); else voice.scene(n);   /* the run buttons of free mode replay scenes without the voice */
      help();
    }
    /* free mode: the story stops, its camera flights stop (rig.setFree), and every sign the story switched off shows
       again (EX.allSigns). The off flags stay, so the story still has them when it takes over again.
       The step panel belongs to the fly-through: free mode shows its buttons in that place. */
    function enterFree() { voice.stop(); story.pause(); rig.setFree(true); EX.allSigns = true; H.focus([]); H.dim([]); $("free").hidden = false; $("steps").hidden = true; help(); }
    function leaveFree() { rig.setFree(false); EX.allSigns = false; $("free").hidden = true; $("steps").hidden = false; closeCard(); help(); }
    function tour() { leaveFree(); setCam(true); story.go(0); story.play(); help(); }
    /* sound may play only after the viewer pressed a key or clicked (browser autoplay rules) */
    addEventListener("pointerdown", () => voice.unlock(), true);
    addEventListener("keydown", e => {
      const k = e.key.toLowerCase();
      voice.unlock();
      if (e.key === " ") {
        e.preventDefault(); if (rig.free) return;
        if (story.playing) { story.pause(); voice.stop(); }
        else if (story.cur === scenes.length - 1) tour();
        else if (voice.on) { story.replay(); story.play(); }   /* with sound the scene starts again, so picture and line run together */
        else story.play();
        help();
      } else if (e.key === "ArrowRight") { leaveFree(); setCam(true); story.next(); }
      else if (e.key === "ArrowLeft") { leaveFree(); setCam(true); story.prev(); }
      else if (k === "r") { leaveFree(); setCam(true); story.replay(); }
      else if (k === "f") enterFree();
      else if (k === "p") tour();
      else if (k === "m" && voice.available) { voice.toggle(!rig.free && story.playing); help(); }
      else if (e.key === "Escape") closeCard();
    });
    /* the run buttons replay scenes without the camera (setCam false), so the viewer keeps the view they chose */
    const idx = key => scenes.findIndex(s => s.key === key);
    $("btnGreen").onclick = () => { closeCard(); setCam(false); story.go(idx("check")); story.play(idx("green")); help(); };
    $("btnRed").onclick = () => { closeCard(); setCam(false); story.go(idx("red")); story.play(idx("red")); help(); };
    $("btnTour").onclick = tour;
    $("cardX").onclick = () => closeCard();

    const ray = new THREE.Raycaster(), ndc = new THREE.Vector2(); let down = null;
    function pick(e) {
      const r = dom.getBoundingClientRect();
      ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1); ray.setFromCamera(ndc, camera);
      const hits = ray.intersectObjects(H.clickables, false); return hits.length ? hits[0].object : null;
    }
    function openCard(info) {
      if (!info) return;
      $("cardT").textContent = info.title; $("cardB").textContent = info.text;
      const a = $("cardL");
      if (info.link) { a.href = info.link; a.textContent = `${info.linkText || "open"} ↗`; a.hidden = false; } else a.hidden = true;
      $("card").hidden = false;
    }
    function closeCard() { $("card").hidden = true; }
    dom.addEventListener("pointerdown", e => (down = [e.clientX, e.clientY]));
    dom.addEventListener("pointerup", e => {
      if (!rig.free || !down) return;
      const moved = Math.hypot(e.clientX - down[0], e.clientY - down[1]); down = null;
      if (moved > 5) return;   /* a drag is not a click */
      const hit = pick(e); if (hit) openCard(hit.userData.info); else closeCard();
    });
    dom.addEventListener("dblclick", e => {
      if (!rig.free) return; const hit = pick(e); if (!hit) return;
      const p = new THREE.Vector3(); hit.getWorldPosition(p);
      rig.flyTo({ x: p.x, y: p.y, z: p.z, r: 8, theta: rig.pose.theta, phi: 0.95 }, 1200);
    });
    help();
    return { onScene, enterFree, leaveFree };
  };
})();
