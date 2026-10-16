/* Scene lengths from the narration. tools/narrate.sh writes durations.json: fps, total_frames and per scene the
   spoken text, frames and start_frame. Record mode (the video) and the voice build (build.py --voice) use it, so each
   scene lasts exactly as long as its spoken line. Without narration, timingFromScenes makes the same table from each
   scene's anim + hold. Pure: no DOM, no clock (node tests load it with require). */
(function (root, factory) {
  const m = factory();
  if (typeof module === "object" && module.exports) module.exports = m;
  else root.EX = Object.assign(root.EX || {}, m);
})(typeof self !== "undefined" ? self : this, function () {
  const HOLD = 2200;
  /* frame n of the video has the time n * 1000 / fps ms */
  const frameTime = (n, fps) => (n * 1000) / fps;
  /* the spoken line of a scene: its say field when the caption reads badly aloud, else the caption */
  const lineOf = s => String(s.say || s.text).replace(/\s+/g, " ").trim();

  /* errors make the table unusable; warnings are printed and the table is still used */
  function checkTiming(d, scenes) {
    const errors = [], warnings = [];
    if (!d || !Array.isArray(d.scenes)) return { errors: ["no scenes in the timing file"], warnings };
    if (!(d.fps > 0)) errors.push("fps is missing");
    if (d.scenes.length !== scenes.length) errors.push(`the timing file has ${d.scenes.length} scenes, the page has ${scenes.length}`);
    let start = 0;
    d.scenes.forEach((s, i) => {
      const sc = scenes[i]; if (!sc) return;
      const name = `scene ${i + 1} (${sc.key})`;
      if (!(s.frames > 0)) errors.push(`${name}: frames is missing`);
      if (s.start_frame !== start) errors.push(`${name}: start_frame ${s.start_frame}, expected ${start}`);
      const ms = (s.frames * 1000) / d.fps;
      if (sc.anim && ms < sc.anim + 300) errors.push(`${name}: ${ms.toFixed(0)} ms is shorter than its animation (${sc.anim} ms) + 300 ms; make the line longer or set MIN_S`);
      if (s.text !== undefined && s.text !== lineOf(sc)) warnings.push(`${name}: the voice was made from other words than the scene line (run render.sh with VOICE=new)`);
      start += s.frames || 0;
    });
    if (d.total_frames !== undefined && d.total_frames !== start) errors.push(`total_frames ${d.total_frames}, the scenes add up to ${start}`);
    return { errors, warnings };
  }

  /* the length of every scene in ms */
  const sceneMs = d => d.scenes.map(s => (s.frames * 1000) / d.fps);
  const sceneStarts = d => d.scenes.map(s => s.start_frame);
  /* the scene that holds frame n; the last scene for frames after the end */
  function sceneAt(d, n) {
    const sc = d.scenes;
    for (let i = 0; i < sc.length; i++) if (n >= sc[i].start_frame && n < sc[i].start_frame + sc[i].frames) return i;
    return n < 0 ? 0 : sc.length - 1;
  }
  /* a silent video: each scene lasts its anim + hold */
  function timingFromScenes(scenes, fps) {
    let start = 0;
    const out = scenes.map(s => {
      const frames = Math.round(((s.anim || 0) + (s.hold ?? HOLD)) * fps / 1000), r = { frames, start_frame: start };
      start += frames; return r;
    });
    return { fps, total_frames: start, total_s: +(start / fps).toFixed(3), scenes: out };
  }
  return { frameTime, lineOf, checkTiming, sceneMs, sceneStarts, sceneAt, timingFromScenes };
});
