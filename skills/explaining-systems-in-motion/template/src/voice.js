/* Spoken lines in the page, only in the voice build (python3 build.py --voice puts EX.VOICE, one audio data URI per
   scene, and EX.TIMING into the single file). Without EX.VOICE every call does nothing.
   The page plays a scene's line when the scene starts and stops it on the next scene change and in free mode.
   Browsers allow sound only after a key press or click on the page, so nothing plays before unlock(). */
(function () {
  const EX = self.EX;
  EX.createVoice = function (clips) {
    const list = Array.isArray(clips) ? clips : [], audio = [];
    let unlocked = false, muted = false, cur = -1;
    const get = n => list[n] ? (audio[n] = audio[n] || new Audio(list[n])) : null;
    function stop() { audio.forEach(a => { if (a && !a.paused) a.pause(); }); }
    function start(n) {
      const a = get(n); if (!a) return;
      a.currentTime = 0; a.play().catch(() => {});   /* a refused play (no user gesture yet) stays silent */
    }
    return {
      get available() { return list.length > 0; },
      get muted() { return muted; },
      /* sound would play now: a voice build, unlocked by the viewer, not muted */
      get on() { return list.length > 0 && unlocked && !muted; },
      unlock() { unlocked = true; },
      /* a scene starts: stop the old line, play the new one */
      scene(n) { stop(); cur = n; if (this.on) start(n); },
      stop,
      /* M: mute stops the line; unmute plays the current scene's line from its start */
      toggle(free) { muted = !muted; if (muted) stop(); else if (!free && cur >= 0 && this.on) start(cur); return muted; },
    };
  };
})();
