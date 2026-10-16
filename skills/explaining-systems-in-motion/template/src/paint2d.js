/* Draws HTML overlay boxes (title, step panel, caption) onto a 2D canvas, at the place where the browser laid them out.
   Record mode needs this: the video frame is a canvas, and ffmpeg on many machines has no drawtext or subtitles filter,
   so all text must already be in the frame. Because it reads the live DOM (positions, computed styles, the ::before
   marks), the video shows the same overlay as the page, also after you change index.html or its CSS.
   Covers what the template's overlay uses: background colour, border, rounded corners, an inset box-shadow bar,
   opacity, text with letter-spacing and text-transform, and ::before text with absolute position.
   Not covered: backdrop-filter, gradients, images, text-shadow. Needs a browser (DOM and canvas). */
(function () {
  const EX = self.EX;
  const clear = c => !c || c === "transparent" || /rgba\([^)]*,\s*0\)$/.test(c);
  const px = v => parseFloat(v) || 0;
  const fontOf = cs => `${cs.fontStyle} ${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
  const caseOf = (t, cs) => (cs.textTransform === "uppercase" ? t.toUpperCase() : cs.textTransform === "lowercase" ? t.toLowerCase() : t);

  function shape(ctx, x, y, w, h, r) { ctx.beginPath(); ctx.roundRect(x, y, w, h, Math.min(r, w / 2, h / 2)); }

  function box(ctx, r, cs) {
    const rad = cs.borderTopLeftRadius.endsWith("%") ? (px(cs.borderTopLeftRadius) / 100) * Math.min(r.width, r.height) : px(cs.borderTopLeftRadius);
    if (!clear(cs.backgroundColor)) { shape(ctx, r.left, r.top, r.width, r.height, rad); ctx.fillStyle = cs.backgroundColor; ctx.fill(); }
    /* an inset shadow with only an x offset, like "inset 3px 0 0 <colour>": a bar on the left (or right) edge */
    const m = /(rgba?\([^)]*\))\s+(-?[\d.]+)px\s+(-?[\d.]+)px[^,]*inset/.exec(cs.boxShadow);
    if (m && px(m[2])) {
      const w = Math.abs(px(m[2]));
      ctx.save(); shape(ctx, r.left, r.top, r.width, r.height, rad); ctx.clip();
      ctx.fillStyle = m[1]; ctx.fillRect(px(m[2]) > 0 ? r.left : r.right - w, r.top, w, r.height); ctx.restore();
    }
    const bw = px(cs.borderTopWidth);
    if (bw && cs.borderTopStyle !== "none" && !clear(cs.borderTopColor)) {
      shape(ctx, r.left + bw / 2, r.top + bw / 2, r.width - bw, r.height - bw, Math.max(0, rad - bw / 2));
      ctx.strokeStyle = cs.borderTopColor; ctx.lineWidth = bw; ctx.stroke();
    }
  }

  function textStyle(ctx, cs) {
    ctx.font = fontOf(cs); ctx.fillStyle = cs.color; ctx.textBaseline = "alphabetic"; ctx.textAlign = "left";
    ctx.letterSpacing = cs.letterSpacing === "normal" ? "0px" : cs.letterSpacing;
  }

  /* each word of a text node at the rectangle the browser gave it; the rectangle's top is the top of the font's ascent */
  function words(ctx, node, cs, range) {
    const s = node.data, re = /\S+/g; let m;
    if (!s.trim()) return;
    textStyle(ctx, cs);
    while ((m = re.exec(s))) {
      range.setStart(node, m.index); range.setEnd(node, m.index + m[0].length);
      const r = range.getClientRects()[0]; if (!r || !r.width) continue;
      const t = caseOf(m[0], cs);
      ctx.fillText(t, r.left, r.top + ctx.measureText(t).fontBoundingBoxAscent);
    }
  }

  /* ::before with content like "?", "→" or attr(data-step) "." and position absolute (left, top inside the element) */
  function before(ctx, el, r) {
    const ps = getComputedStyle(el, "::before"), c = ps.content;
    if (!c || c === "none" || c === "normal" || ps.display === "none") return;
    let t = "", m; const re = /"((?:[^"\\]|\\.)*)"|attr\(([\w-]+)\)/g;
    while ((m = re.exec(c))) t += m[1] !== undefined ? m[1].replace(/\\(.)/g, "$1") : el.getAttribute(m[2]) || "";
    if (!t) return;
    textStyle(ctx, ps);
    const x = r.left + (ps.position === "absolute" ? px(ps.left) : px(getComputedStyle(el).paddingLeft));
    const y = r.top + (ps.position === "absolute" ? px(ps.top) : px(getComputedStyle(el).paddingTop));
    const mt = ctx.measureText(t), asc = mt.fontBoundingBoxAscent, h = asc + mt.fontBoundingBoxDescent;
    const lh = ps.lineHeight === "normal" ? h : px(ps.lineHeight);
    ctx.fillText(caseOf(t, ps), x, y + (lh - h) / 2 + asc);
  }

  function paint(ctx, el, alpha, range) {
    if (el.hidden) return;
    const cs = getComputedStyle(el);
    if (cs.display === "none" || cs.visibility === "hidden") return;
    const a = alpha * px(cs.opacity === "" ? "1" : cs.opacity), r = el.getBoundingClientRect();
    ctx.globalAlpha = a;
    if (r.width && r.height) box(ctx, r, cs);
    before(ctx, el, r);
    for (const n of el.childNodes) {
      ctx.globalAlpha = a;
      if (n.nodeType === 3) words(ctx, n, cs, range);
      else if (n.nodeType === 1) paint(ctx, n, a, range);
    }
  }

  /* ids: the overlay elements to draw, in order; sx, sy: canvas pixels per CSS pixel */
  EX.paintOverlay = function (ctx, ids, sx = 1, sy = sx) {
    const range = document.createRange();
    ctx.save(); ctx.setTransform(sx, 0, 0, sy, 0, 0);
    ids.forEach(id => { const el = document.getElementById(id); if (el) paint(ctx, el, 1, range); });
    ctx.restore();
  };
})();
