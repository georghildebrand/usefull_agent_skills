/* The five scenes as actions on the world. Rule: every timed effect goes through engine.tween or engine.later
   (never setTimeout or a frame counter), so story.go(n) can replay scenes 0..n-1 instantly and animate only scene n.
   Needs scene-data.js, world.js, camera.js. */
(function () {
  const EX = self.EX;
  const C = { teal: 0x15a0a0, green: 0x37b673, red: 0xe05252 };
  EX.bindStory = function ({ engine, H, K, rig, L, P, camOn }) {
    const S = EX.SCENES, SP = K.SP;
    const stn = k => L.stations.find(s => s.key === k);
    const at = (path, k) => { const s = stn(k); return path.sOf(s.x, s.z); };
    const cam = fn => { if (camOn()) fn(); };   /* free mode replays a run without moving the viewer's camera */
    /* a train: engine in front, the cart one spacing behind it; cartTo stops the cart (not the engine) at a station */
    const train = (text, path) => K.consist([K.car("engine", "", 0x2f4f5f), K.car("cart", text, 0x6b4a2b)], path);
    const cartTo = (c, k, ms, delay) => c.drive(at(c.path, k) + SP, ms, delay);
    let st = {};
    const runs = [
      /* 0 receive */ () => {
        H.mute(["courier"]);   /* the courier comes with the last scene; free mode shows the sign again */
        H.focus(["receive"]); H.dim(["receive"]);
        cam(() => { Object.assign(rig.pose, S[0].start); rig.flyTo(S[0].pose, 4200, 200); });
        st.main = train("parcel 1", P.green); st.main.place(SP);
        st.main.cars[1].label.userData.off = true;   /* the cart sign comes with the parcel */
        cartTo(st.main, "receive", 2600, 1400); H.glow("receive", C.teal, 3800);
        K.loadCargo(st.main.cars, 4100); H.signShow(st.main.cars[1].label, true, 4300);
      },
      /* 1 check */ () => {
        H.focus(["check", "passed"]); H.dim(["check"]); cam(() => rig.flyTo(S[1].pose, 1400));
        cartTo(st.main, "check", 2400, 300); H.glow("check", C.teal, 2700);
        H.lampsRun(null, 2900); H.signShow(H.passedSign, true, 2900 + L.checks.n * 120 + 200);   /* the result shows when the lamps are done */
      },
      /* 2 green: ship */ () => {
        H.focus(["signal", "ship", "result"]); H.dim(["check", "ship"]); cam(() => rig.flyTo(S[2].pose, 1400));
        H.glow("check", C.green, 300); H.signalTo("green", 500);
        cartTo(st.main, "ship", 3000, 900); H.glow("ship", C.green, 4000); H.showAt(H.resultBoard, 4200, 700);
      },
      /* 3 red run (example): a second train on its own full path; the green result of scene 2 goes away */
      () => {
        H.focus(["signal", "fail", "reject", "notice"]); H.dim(["check", "reject"]); cam(() => rig.flyTo(S[3].pose, 1400));
        H.hideAt(H.resultBoard, 0, 400); H.setGlow("ship", null); st.main.hide();
        H.passedSign.userData.off = true;   /* the green totals of the real run do not stand next to the invented example */
        H.lampsGrey(); H.signal.set(null); H.setGlow("check", null);
        st.ex = train("example", P.red); st.ex.place(at(P.red, "check") + SP);
        const t0 = 800, tL = t0 + L.checks.n * 120;
        H.lampsRun(L.checks.failIndex, t0); H.glow("check", C.red, tL); H.signShow(H.failSign, true, tL); H.signalTo("red", tL + 300);
        st.ex.drive(P.red.length - 0.4, 2600, tL + 700);
        H.glow("reject", C.red, tL + 3300); H.showAt(H.notice, tL + 3400, 700);
      },
      /* 4 then: the red example is over, so the board goes back to the green end state of scene 2 first */
      () => {
        H.lampsSet(null); H.signal.set("green"); H.setGlow("check", C.green); H.setGlow("reject", null); H.setGlow("ship", C.green);
        H.showNow(H.resultBoard); H.hideAt(H.notice, 0, 300); H.failSign.userData.off = true; H.passedSign.userData.off = false;
        if (st.ex) st.ex.hide(); st.main.place(st.main.s);
        H.focus(["courier", "result"]); H.dim(["ship"]); cam(() => rig.flyTo(S[4].pose, 3200, 200));
        H.courierWalk(1200); H.signShow(H.courierSign, true, 2000);
      },
    ];
    return { scenes: runs.map((run, i) => Object.assign({}, S[i], { run })), reset() { st = {}; } };
  };
})();
