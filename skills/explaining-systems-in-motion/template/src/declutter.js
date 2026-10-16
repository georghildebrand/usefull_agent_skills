/* Sign placement on screen: decides which signs stay visible so that none is cut off by the picture edge,
   none lies under a DOM box (title, caption) or a train car, and no two signs cover each other.
   Pure: no DOM, no three.js. Signs with a higher prio win; for equal prio the nearer one wins. */
(function (root, factory) {
  const m = factory();
  if (typeof module === "object" && module.exports) module.exports = m;
  else root.EX = Object.assign(root.EX || {}, m);
})(typeof self !== "undefined" ? self : this, function () {
  const hits = (a, b, pad) => Math.min(a.x1, b.x1) - Math.max(a.x0, b.x0) > -pad && Math.min(a.y1, b.y1) - Math.max(a.y0, b.y0) > -pad;
  /* items: [{x0, y0, x1, y1, prio, dist, owner?, overCars?}], view: {w, h}, keepOuts: [{x0, y0, x1, y1, owner?}]
     overCars: the sign may cover any box that has an owner (a train car), but never a DOM box
     returns [{show, why}] in the order of items; why is "out" (not in the picture), "edge" (cut by it), "box" or "overlap" for hidden signs */
  function declutter(items, view, keepOuts = [], pad = 3, margin = 0) {   /* margin: a sign nearer than this to the picture edge counts as cut */
    const res = items.map(() => ({ show: false, why: "" })), shown = [];
    const order = items.map((_, i) => i).sort((a, b) => (items[b].prio - items[a].prio) || (items[a].dist - items[b].dist) || a - b);
    for (const i of order) {
      const s = items[i];
      if (s.x1 <= 0 || s.y1 <= 0 || s.x0 >= view.w || s.y0 >= view.h) { res[i].why = "out"; continue; }   // not in the picture at all
      if (s.x0 < margin || s.y0 < margin || s.x1 > view.w - margin || s.y1 > view.h - margin) { res[i].why = "edge"; continue; }
      if (keepOuts.some(k => !(k.owner && (k.owner === s.owner || s.overCars)) && hits(s, k, 0))) { res[i].why = "box"; continue; }
      if (shown.some(o => hits(s, o, pad))) { res[i].why = "overlap"; continue; }
      res[i].show = true; shown.push(s);
    }
    return res;
  }
  return { declutter };
});
