/* Timing engine and story runner. Pure: no DOM, no three.js (node tests load it with require).
   tween/later schedule effects; createStory jumps between scenes by replaying earlier
   scenes instantly and animating only the current one. */
(function (root, factory) {
  const m = factory();
  if (typeof module === "object" && module.exports) module.exports = m;
  else root.EX = Object.assign(root.EX || {}, m);
})(typeof self !== "undefined" ? self : this, function () {
  const ease = t => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

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
    let cur = 0, playing = false, holdUntil = null, until = scenes.length - 1;
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
      holdUntil = null;
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
      play(u) { until = u === undefined ? scenes.length - 1 : Math.min(u, scenes.length - 1); playing = true; holdUntil = null; },
      pause() { playing = false; holdUntil = null; },
      /* call once per frame after engine.step(now) */
      tick(now) {
        if (!playing || engine.pending() > 0) return;
        if (cur >= until) { playing = false; holdUntil = null; if (hooks.onEnd) hooks.onEnd(cur); return; }
        if (holdUntil === null) { holdUntil = now + (scenes[cur].hold ?? HOLD); return; }
        if (now >= holdUntil) go(cur + 1);
      },
    };
  }

  return { ease, createEngine, createStory };
});
