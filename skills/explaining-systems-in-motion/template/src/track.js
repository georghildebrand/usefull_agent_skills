/* Track math: smooth paths through control points, arc-length positions, car positions behind
   a head, and the routes of the example. Pure: no DOM, no three.js (node tests load it with require). */
(function (root, factory) {
  const m = factory();
  if (typeof module === "object" && module.exports) module.exports = m;
  else root.EX = Object.assign(root.EX || {}, m);
})(typeof self !== "undefined" ? self : this, function () {
  function catmull(p0, p1, p2, p3, t) {
    const t2 = t * t, t3 = t2 * t;
    return [0, 1].map(j => 0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2 + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3));
  }

  function joinPoints(...lists) {
    const out = [];
    lists.forEach(l => l.forEach(p => {
      const q = out[out.length - 1];
      if (!q || Math.hypot(q[0] - p[0], q[1] - p[1]) > 1e-6) out.push([p[0], p[1]]);
    }));
    return out;
  }

  function makePath(points, perSeg = 20) {
    const n = points.length, pts = [];
    for (let i = 0; i < n - 1; i++) {
      const p0 = points[Math.max(i - 1, 0)], p1 = points[i], p2 = points[i + 1], p3 = points[Math.min(i + 2, n - 1)];
      for (let k = 0; k < perSeg; k++) pts.push(catmull(p0, p1, p2, p3, k / perSeg));
    }
    pts.push([points[n - 1][0], points[n - 1][1]]);
    const cum = [0];
    for (let i = 1; i < pts.length; i++) cum.push(cum[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
    const length = cum[cum.length - 1];
    function at(s) {
      s = Math.max(0, Math.min(length, s));
      let lo = 0, hi = cum.length - 1;
      while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (cum[mid] <= s) lo = mid; else hi = mid; }
      const seg = cum[hi] - cum[lo] || 1, f = (s - cum[lo]) / seg, a = pts[lo], b = pts[hi];
      return { x: a[0] + (b[0] - a[0]) * f, z: a[1] + (b[1] - a[1]) * f, angle: Math.atan2(b[1] - a[1], b[0] - a[0]) };
    }
    function sOf(x, z) {
      let best = 0, bd = Infinity;
      for (let i = 0; i < pts.length; i++) { const d = Math.hypot(pts[i][0] - x, pts[i][1] - z); if (d < bd) { bd = d; best = i; } }
      return cum[best];
    }
    return { points: pts, length, at, sOf };
  }

  function carPositions(path, headS, n, spacing) {
    const out = [];
    for (let i = 0; i < n; i++) {
      const s = headS - i * spacing, q = path.at(s);
      out.push({ x: q.x, z: q.z, angle: q.angle, s, visible: s >= 0 && s <= path.length });
    }
    return out;
  }

  /* Every route is one full path from the start of the track. A train that splits or takes another branch
     is a separate consist on its own full path, never a group re-parented at run time. */
  function buildPaths(L) {
    const T = L.tracks;
    return {
      green: makePath(joinPoints(T.main, T.green)),   /* start -> receive -> check -> ship */
      red: makePath(joinPoints(T.main, T.red)),       /* start -> receive -> check -> reject bin */
    };
  }

  return { makePath, joinPoints, carPositions, buildPaths };
});
