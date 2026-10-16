/* All content of the example in one place: board layout, stations, track points, click cards, the step panel,
   and the five scenes (title, subtitle, camera pose, step line). Replace this file first for your own system.
   Pure data: no DOM, no three.js (node tests load it with require). */
(function (root, factory) {
  const m = factory();
  if (typeof module === "object" && module.exports) module.exports = m;
  else root.EX = Object.assign(root.EX || {}, m);
})(typeof self !== "undefined" ? self : this, function () {
  /* World units: the table top is at y = 0, the board top at y = Y0. x runs left to right, z from back (-) to front (+). */
  const LAYOUT = {
    Y0: 0.2,
    table: { w: 30, d: 18 },
    board: { x0: -11, x1: 11, z0: -6, z1: 6 },
    cart: { spacing: 1.2 },
    /* track control points [x, z]; the paths in track.js join main with one branch each */
    tracks: {
      main: [[-10, 1], [-6, 1], [-1, 1], [2.5, 1]],
      green: [[2.5, 1], [4.6, 0.1], [6.6, -1], [10, -1]],
      red: [[2.5, 1], [4.6, 1.9], [6.6, 3], [10, 3]],
    },
    /* house: -1 builds the house behind the track, +1 in front of it */
    stations: [
      { key: "receive", x: -6, z: 1, house: -1, label: "receive", sub: "puts a label on", color: 0x2d4f6b },
      { key: "check", x: -1, z: 1, label: "check", sub: "12 checks" },
      { key: "ship", x: 8, z: -1, house: -1, label: "ship", sub: "the parcel leaves", color: 0x2d4f45 },
      { key: "reject", x: 8, z: 3, label: "reject bin", sub: "a person looks at it" },
    ],
    signal: { x: 2.2, z: -0.4 },
    checks: { n: 12, failIndex: 7 },
    courier: { x: 10.4, z: 1.0 },   /* between the two branch ends, in front of the ship station */
    /* click cards in free mode: two or three plain sentences; add link and linkText to show a link */
    info: {
      receive: { title: "receive", text: "Takes a parcel from the start of the track and puts a label on it. Without the label the next stations do not know the parcel." },
      check: { title: "check", text: "Runs 12 checks on the parcel: size, weight, label, address and more. Each lamp is one check." },
      signal: { title: "signal", text: "Green when every check passed, red when one failed. The signal sets the switch to ship or to the reject bin." },
      ship: { title: "ship", text: "End of the track for good parcels. The board lists what is ready for the courier." },
      reject: { title: "reject bin", text: "A parcel with a failed check stops here. Nothing is shipped; a person looks at it." },
      courier: { title: "courier", text: "Collects the shipped parcels by hand once a day. Nothing on the table sends them." },
    },
  };

  /* The fixed step panel. Line numbers (data-step): 0 the question, 1..n the steps, n + 1 the "Then" line.
     A step given as {green, red} has two halves; a scene with part "green" or "red" makes the other half pale. */
  const STEPS = {
    title: "What the table decides",
    question: "Does a parcel leave only after it passed every check?",
    items: [
      "The receive station puts a label on the parcel.",
      "The check station runs 12 checks on it.",
      { green: "Green: the parcel goes to the ship station.", red: "Red: it goes to the reject bin, nothing is shipped." },
    ],
    then: "Then: a courier collects the shipped parcels by hand.",
  };

  /* pose: orbit camera at the end of the scene (target x, y, z; distance r; angles theta around y and phi from the top).
     Every playback pose shows the whole board from above at an angle; close views are for free mode only.
     Subtitles: why the step exists first, then what happens; at most 34 words.
     anim: how long the scene's animation runs, in ms (record mode logs the measured value). The video and the voice
     build give each scene at least anim + 600 ms. say (optional): the spoken form of the subtitle, when the
     subtitle has words a text-to-speech voice reads badly (short capital names, ids, version numbers). */
  const SCENES = [
    { key: "receive", title: "Receive", hold: 1800, anim: 4600,
      text: "The next stations must know which parcel they hold. So the receive station takes the parcel from the start of the track and puts a label on it.",
      start: { x: 0, y: 0, z: 2, r: 46, theta: -0.5, phi: 1.2 }, pose: { x: -1.9, y: 0, z: 0.6, r: 27, theta: 0, phi: 0.72 } },
    { key: "check", title: "Check", anim: 4700,
      text: "A broken parcel must not leave the house. The check station runs 12 checks; each lamp is one check. In this run all 12 pass.",
      pose: { x: -1.9, y: 0, z: 0.6, r: 27, theta: 0, phi: 0.72 } },
    { key: "green", title: "Green: ship", anim: 5000, part: "green",
      text: "Only a checked parcel may leave. The signal turns green, the cart takes the parcel to the ship station, and the board lists it as ready.",
      pose: { x: -1.9, y: 0, z: 0.6, r: 27, theta: 0, phi: 0.72 } },
    { key: "red", title: "Red run (example)", anim: 6500, part: "red",
      text: "An invented example of a failed check: one lamp turns red, the signal turns red, and the cart goes to the reject bin. Nothing is shipped.",
      pose: { x: -1.9, y: 0, z: 0.8, r: 27, theta: 0, phi: 0.72 } },
    { key: "then", title: "Then: the courier", anim: 3500, hold: 3000,
      text: "The track ends at the ship station. A courier collects the shipped parcels by hand once a day; nothing on the table sends them.",
      pose: { x: -1.6, y: 0, z: 0.4, r: 29, theta: 0.12, phi: 0.8 } },
  ];
  /* the line of the step panel that each scene highlights */
  const STEP_OF_SCENE = [1, 2, 3, 3, 4];
  return { LAYOUT, STEPS, SCENES, STEP_OF_SCENE };
});
