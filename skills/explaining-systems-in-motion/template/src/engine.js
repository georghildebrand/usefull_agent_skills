/* Timing engine and story runner. Pure: no DOM, no three.js (node tests load it with require).
   tween/later schedule effects; createStory jumps between scenes by replaying earlier
   scenes instantly and animating only the current one; driftPose is the slow camera move after a scene's animation. */
(function (root, factory) {
  const m = factory();
  if (typeof module === "object" && module.exports) module.exports = m;
  else root.EX = Object.assign(root.EX || {}, m);
})(typeof self !== "undefined" ? self : this, function () {
  const ease = t => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

  /* The camera pose ms after a scene's animation ended, while the scene still runs (its spoken line is longer).
     The camera turns slowly round its target (at most 0.14 rad, towards the front) and moves 4 % closer, then back,
     every 16 s. It starts and turns with zero speed, so it joins the flights before and after it without a jerk.
     The pose stays a wide shot: the distance never drops below 96 % of the scene pose. */
  const DRIFT = { period: 16000, theta: 0.14, r: 0.04 };
  function driftPose(base, ms) {
    const k = (1 - Math.cos((2 * Math.PI * Math.max(0, ms)) / DRIFT.period)) / 2, dir = base.theta > 0 ? -1 : 1;
    return Object.assign({}, base, { theta: base.theta + dir * DRIFT.theta * k, r: base.r * (1 - DRIFT.r * k) });
  }

  function createEngine() {
    let gen = 0, list = [], instant = false, clock = 0;
    return {
      get instant() { return instant; },
      setInstant(b) { instant = !!b; },
      /* fn(t) with t in [0,1]; in instant mode fn(1) runs at once */
      tween(ms, fn, delay = 0) {
        if (instant) { fn(1); return; }
        list.push({ t0: clock + delay, ms: Math.max(1, ms), fn });
      },
      later(delay, fn) { this.tween(1, t => { if (t >= 1) fn(); }, delay); },
      cancelAll() { gen++; list = []; },
      pending() { return list.length; },
      /* advance to absolute time now (ms); tweens added by callbacks start next step */
      step(now) {
        clock = now;
        const g = gen, cur = list, keep = [];
        list = [];
        for (const tw of cur) {
          const t = (now - tw.t0) / tw.ms;
          if (t < 0) { keep.push(tw); continue; }
          tw.fn(Math.min(1, t));
          if (gen !== g) return;                  // a callback jumped to another scene
          if (t < 1) keep.push(tw);
        }
        list = keep.concat(list);
      },
    };
  }

  function createStory(scenes, engine, hooks = {}) {
    const HOLD = 2200;
    /* t0: the time of the first tick of the current scene. A scene with dur (ms, from the narration) ends at t0 + dur,
       or when its animation ends if that is later; a scene without dur holds for hold ms after its animation */
    let cur = 0, playing = false, holdUntil = null, until = scenes.length - 1, t0 = null;
    function go(n) {
      n = Number.isFinite(n) ? n : 0;
      cur = Math.max(0, Math.min(scenes.length - 1, Math.round(n)));
      engine.cancelAll();
      if (hooks.reset) hooks.reset();
      engine.setInstant(true);
      for (let i = 0; i < cur; i++) scenes[i].run();
      engine.setInstant(!!hooks.still);
      scenes[cur].run();
      engine.setInstant(false);
      holdUntil = null; t0 = null;
      if (hooks.onScene) hooks.onScene(cur);
      return cur;
    }
    return {
      go,
      get cur() { return cur; },
      get playing() { return playing; },
      next() { return go(cur + 1); },
      prev() { return go(cur - 1); },
      replay() { return go(cur); },
      /* t0 starts again at the next tick: after a long pause the scene still holds for its full dur, not 0 ms */
      play(u) { until = u === undefined ? scenes.length - 1 : Math.min(u, scenes.length - 1); playing = true; holdUntil = null; t0 = null; },
      pause() { playing = false; holdUntil = null; },
      /* call once per frame after engine.step(now) */
      tick(now) {
        if (t0 === null) t0 = now;
        if (!playing || engine.pending() > 0) return;
        const s = scenes[cur], last = cur >= until;
        if (holdUntil === null) holdUntil = s.dur ? Math.max(now, t0 + s.dur) : last ? now : now + (s.hold ?? HOLD);
        if (now < holdUntil) return;
        if (last) { playing = false; holdUntil = null; if (hooks.onEnd) hooks.onEnd(cur); return; }
        go(cur + 1); t0 = now;
      },
    };
  }

  return { ease, driftPose, createEngine, createStory };
});
