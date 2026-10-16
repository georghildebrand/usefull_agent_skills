/* Record mode (the video), started by main.js for ?record. Time comes from the frame number only: frame n has the
   time n * 1000 / fps ms, so a slow frame cannot skip a tween, and two runs give the same frames.
   Each scene starts at its start_frame from the timing table (the narration, see timing.js).
   Per frame: engine.step(t); at a scene start story.go(i) and one more engine.step(t), so the new scene draws its first
   state in this frame; idle(t) (the slow camera move after the animation); rig.update(); then, from frame `start` on,
   render, copy the WebGL picture onto a 2D canvas, draw the overlays on it (paint2d.js) and POST the image to
   /frame/<n+1>. Each POST is awaited, so the page never runs ahead of the receiver. At the end POST /log (animation
   and drift lengths per scene) and /done; on any error POST /fail with the stack. Contract of tools/record.py.
   Needs timing.js and paint2d.js. Reads no clock. */
(function () {
  const EX = self.EX;
  const post = (path, body, type) => fetch(path, { method: "POST", body, headers: { "Content-Type": type } })
    .then(r => { if (!r.ok) throw new Error(path + " -> " + r.status); });
  EX.postFail = e => post("/fail", String((e && e.stack) || e), "text/plain").catch(() => {});

  EX.startRecord = async function ({ renderer, camera, scene, story, engine, rig, idle, timing, overlay, W, H, fps, fmt, start }) {
    try {
      const type = fmt === "jpeg" ? "image/jpeg" : "image/png";
      const starts = EX.sceneStarts(timing), lens = EX.sceneMs(timing), last = timing.total_frames;
      const out = document.createElement("canvas"); out.width = W; out.height = H;
      const ctx = out.getContext("2d");
      const sx = W / innerWidth, sy = H / innerHeight, log = [];
      if (Math.abs(sx - 1) > 0.01 || Math.abs(sy - 1) > 0.01) log.push(`window ${innerWidth}x${innerHeight} differs from the video ${W}x${H}; the overlay is scaled`);
      let i = 0, animEnd = null, t0 = 0;
      const report = () => log.push(`scene ${i + 1}: animation ${animEnd === null ? "until the end" : Math.round(animEnd - t0) + " ms"}, scene ${Math.round(lens[i])} ms`);
      for (let n = 0; n < last; n++) {
        const t = EX.frameTime(n, fps);
        engine.step(t);
        const k = starts.indexOf(n);
        if (k > 0 && engine.pending() > 0)
          throw new Error(`scene ${i + 1} still animates at frame ${n}: its narrated length is shorter than its animation; raise its anim in scene-data.js (render.sh passes anim + 600 ms to narrate.sh as MIN_S) or make the line longer`);
        if (k >= 0) { if (k > 0) report(); i = k; t0 = t; animEnd = null; story.go(k); engine.step(t); }
        if (animEnd === null && engine.pending() === 0) animEnd = t;
        idle(t);
        rig.update();
        if (n < start) continue;                 /* resume: the state above runs for every frame, only the picture is skipped */
        renderer.render(scene, camera);
        ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.clearRect(0, 0, W, H);
        ctx.drawImage(renderer.domElement, 0, 0, W, H);
        EX.paintOverlay(ctx, overlay, sx, sy);
        const blob = await new Promise(r => out.toBlob(r, type, 0.92));
        if (!blob) throw new Error("toBlob gave no image at frame " + (n + 1));
        await post("/frame/" + (n + 1), blob, type);
      }
      report();
      await post("/log", log.join("\n"), "text/plain");
      await post("/done", "{}", "application/json");
    } catch (e) {
      await EX.postFail(e);
    }
  };
})();
