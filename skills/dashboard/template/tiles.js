/*
 * Pure tile functions for the dashboard page. No DOM access here.
 * The page loads this file as <script src="tiles.js"> and reads window.DashTiles.
 * Node tests load it with require().
 */
(function (root) {
  'use strict';

  // Same values as TILE_KINDS in scripts/presets.py (a test compares them).
  var TILE_KINDS = ['todos', 'jira', 'sessions', 'status', 'statustable', 'feed', 'list', 'note'];
  var LIST_MAX = 500;
  var SEGMENT = /^[A-Za-z0-9_\-.~:@+]{1,200}$/;
  var PRESET = /^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/;

  function str(x) { return x == null ? '' : String(x); }
  function low(x) { return str(x).trim().toLowerCase(); }
  function ms(isoText) { var t = Date.parse(isoText); return isNaN(t) ? null : t; }
  function tooOld(isoText, maxDays, now) {
    if (!maxDays || !isoText) return false;
    var t = ms(isoText);
    return t !== null && Number(now) - t > Number(maxDays) * 864e5;
  }
  function newestFirst(field) {
    return function (a, b) { return str(b[field]).localeCompare(str(a[field])); };
  }
  function arr(x) { return Array.isArray(x) ? x : []; }

  // Rows that common.fit_document dropped to keep a document under 256 KiB.
  function truncatedOf(doc) {
    var n = doc && typeof doc === 'object' ? Number(doc.truncated) : 0;
    return n > 0 && isFinite(n) ? Math.floor(n) : 0;
  }
  /** Caption suffix for a cut-down tile, '' when nothing was dropped. */
  function truncatedNote(n) {
    return n > 0 ? ' · ' + n + ' weitere wegen Größenlimit nicht gezeigt' : '';
  }

  // A list tile id is "list:<skill-id>"; the skill id is one database path segment.
  function listIdOf(tileId) {
    var s = str(tileId);
    if (s.indexOf('list:') !== 0) return null;
    var id = s.slice(5);
    return id && SEGMENT.test(id) && id !== '.' && id !== '..' ? id : null;
  }

  /**
   * ToDo rows from all todolists documents.
   * Returns {total, rows: [{item, listId, project}], syncedAt, truncated}. syncedAt is the
   * OLDEST syncedAt over the lists, so the tile never looks fresher than it is.
   * truncated adds up the rows each list dropped for its size limit.
   */
  function filterTodos(lists, flt, now) {
    flt = flt || {};
    var q = low(flt.q), total = 0, rows = [], synced = '', cut = 0;
    arr(lists).forEach(function (l) {
      if (!l || typeof l !== 'object') return;
      cut += truncatedOf(l);
      if (typeof l.syncedAt === 'string' && l.syncedAt && (!synced || l.syncedAt < synced)) synced = l.syncedAt;
      arr(l.items).forEach(function (t) {
        if (!t || typeof t !== 'object') return;
        total++;
        if (flt.project && l.id !== flt.project) return;
        if (flt.status && t.status !== flt.status) return;
        if (flt.prio === 'top' && t.priority !== 'critical' && t.priority !== 'high') return;
        if (tooOld(t.updatedAt, flt.age, now)) return;
        if (q && low(t.title).indexOf(q) < 0) return;
        rows.push({ item: t, listId: l.id, project: l.project || l.id });
      });
    });
    rows.sort(function (a, b) { return str(b.item.updatedAt).localeCompare(str(a.item.updatedAt)); });
    return { total: total, rows: rows, syncedAt: synced, truncated: cut };
  }

  /** Jira rows from jira/open. Returns {total, rows, truncated}, newest change first. */
  function filterJira(doc, flt, now) {
    flt = flt || {};
    var all = doc && typeof doc === 'object' ? arr(doc.items) : [];
    var q = low(flt.jq);
    var rows = all.filter(function (t) {
      if (!t || typeof t !== 'object') return false;
      if (flt.jproject && t.project !== flt.jproject) return false;
      if (flt.jrole && t.role !== flt.jrole) return false;
      if (flt.jstat && t.statusCat !== flt.jstat) return false;
      if (flt.jtype && t.type !== flt.jtype) return false;
      if (tooOld(t.updatedAt, flt.jage, now)) return false;
      if (q && low(str(t.key) + ' ' + str(t.title)).indexOf(q) < 0) return false;
      return true;
    }).sort(newestFirst('updatedAt'));
    return { total: all.length, rows: rows, truncated: truncatedOf(doc) };
  }

  /** Session rows from sessions/list: search by name or folder, then sort. New array. */
  function sortSessions(items, flt) {
    flt = flt || {};
    var q = low(flt.sq);
    var out = arr(items).filter(function (s) {
      return s && typeof s === 'object' && (!q || low(str(s.name) + ' ' + str(s.cwd)).indexOf(q) >= 0);
    });
    if (flt.ssort === 'name') out.sort(function (a, b) { return str(a.name).localeCompare(str(b.name), 'de'); });
    else out.sort(newestFirst(flt.ssort === 'started' ? 'startedAt' : 'lastActiveAt'));
    return out;
  }

  /** Feed rows from feed/items with read marks from feed/read. Returns {total, unread, rows: [{item, read}], truncated}. */
  function filterFeed(doc, read, flt) {
    flt = flt || {};
    read = read && typeof read === 'object' ? read : {};
    var all = doc && typeof doc === 'object' ? arr(doc.items).filter(function (i) { return i && typeof i === 'object'; }) : [];
    var q = low(flt.fq), unread = 0;
    all.forEach(function (i) { if (read[i.id] !== true) unread++; });
    var rows = all.map(function (i) { return { item: i, read: read[i.id] === true }; }).filter(function (r) {
      if (flt.fonly === 'unread' && r.read) return false;
      if (flt.fsrc && r.item.source !== flt.fsrc) return false;
      if (q && low(str(r.item.title) + ' ' + str(r.item.why)).indexOf(q) < 0) return false;
      return true;
    });
    rows.sort(function (a, b) { return str(b.item.changedAt).localeCompare(str(a.item.changedAt)); });
    return { total: all.length, unread: unread, rows: rows, truncated: truncatedOf(doc) };
  }

  /**
   * Check a lists/<skill-id> document:
   * {v: 1, title, syncedAt, source, items: [{title, link?, status?, date?, group?}]}.
   */
  function validateList(doc) {
    if (!doc || typeof doc !== 'object' || Array.isArray(doc)) return { ok: false, reason: 'not an object' };
    if (doc.v !== 1) return { ok: false, reason: 'v is not 1' };
    if (typeof doc.title !== 'string') return { ok: false, reason: 'title is not a string' };
    if (!Array.isArray(doc.items)) return { ok: false, reason: 'items is not a list' };
    var opt = ['link', 'status', 'date', 'group'];
    for (var i = 0; i < doc.items.length; i++) {
      var it = doc.items[i];
      if (!it || typeof it !== 'object' || typeof it.title !== 'string') return { ok: false, reason: 'item ' + i + ' has no title' };
      for (var k = 0; k < opt.length; k++) {
        if (it[opt[k]] != null && typeof it[opt[k]] !== 'string') return { ok: false, reason: 'item ' + i + ' field ' + opt[k] + ' is not a string' };
      }
    }
    return { ok: true };
  }

  /** The first `max` items and how many were left out. */
  function limitItems(items, max) {
    max = max == null ? LIST_MAX : max;
    var a = arr(items);
    return { items: a.slice(0, max), hidden: Math.max(0, a.length - max) };
  }

  /** List tile rows: f = {q, status, sort}; sort 'date' puts the newest date first, items without date last. */
  function filterList(items, f) {
    f = f || {};
    var q = low(f.q);
    var out = arr(items).filter(function (i) {
      if (f.status && i.status !== f.status) return false;
      if (q && low(str(i.title) + ' ' + str(i.group)).indexOf(q) < 0) return false;
      return true;
    });
    if (f.sort === 'date') {
      out = out.map(function (i, n) { return { i: i, n: n }; }).sort(function (a, b) {
        var da = str(a.i.date), db = str(b.i.date);
        if (da === db) return a.n - b.n;
        if (!da) return 1;
        if (!db) return -1;
        return db.localeCompare(da);
      }).map(function (x) { return x.i; });
    }
    return out;
  }

  /**
   * Comment text from the refresh and sync buttons, accepted exactly:
   *   dashboard refresh <preset> <tile|all>   (a list tile is list:<skill-id>)
   *   dashboard sync <preset>
   */
  function parseCommand(text) {
    if (typeof text !== 'string') return null;
    var p = text.trim().split(/\s+/);
    if (p[0] !== 'dashboard') return null;
    if (p[1] === 'sync' && p.length === 3 && PRESET.test(p[2])) return { cmd: 'sync', preset: p[2], tile: null };
    if (p[1] !== 'refresh' || p.length !== 4 || !PRESET.test(p[2])) return null;
    var tile = p[3];
    var ok = tile === 'all' || (tile !== 'list' && TILE_KINDS.indexOf(tile) >= 0) || listIdOf(tile) !== null;
    return ok ? { cmd: 'refresh', preset: p[2], tile: tile } : null;
  }

  /** A meta/layout document's items, or null when any item is malformed. */
  function validLayout(doc) {
    var items = doc && typeof doc === 'object' ? doc.items : null;
    if (!Array.isArray(items) || !items.length) return null;
    var seen = {};
    for (var i = 0; i < items.length; i++) {
      var it = items[i];
      if (!it || typeof it.id !== 'string' || !it.id || seen[it.id] || TILE_KINDS.indexOf(it.kind) < 0) return null;
      if (it.kind === 'list' && listIdOf(it.id) === null) return null;
      if (['x', 'y', 'w', 'h'].some(function (k) { return typeof it[k] !== 'number' || !isFinite(it[k]); })) return null;
      seen[it.id] = 1;
    }
    return items;
  }

  /**
   * The start layout from the preset's tiles ([{kind, x, y, w, h, id?}], as in
   * presets/<name>.json). The id is the tile's own id, else its kind, else
   * kind-2, kind-3 for repeats. A list tile must carry id "list:<skill-id>".
   * A malformed tile (unknown kind, list tile without a valid id, missing size,
   * repeated id) is left out; the other tiles stay.
   * Returns {items, skipped}: items are meta/layout items, or null when no tile
   * is left; skipped is the number of tiles left out.
   */
  function presetLayout(tiles) {
    if (!Array.isArray(tiles) || !tiles.length) return { items: null, skipped: 0 };
    var used = {}, items = [], skipped = 0;
    for (var i = 0; i < tiles.length; i++) {
      var t = tiles[i];
      var own = t && typeof t === 'object' && typeof t.id === 'string' && t.id ? t.id : '';
      var id = own || str(t && t.kind);
      for (var n = 2; used[id] && !own; n++) id = str(t.kind) + '-' + n;
      var item = t && typeof t === 'object' ? { id: id, kind: t.kind, x: t.x, y: t.y, w: t.w, h: t.h } : null;
      if (!item || used[id] || !validLayout({ items: [item] })) { skipped++; continue; }
      used[id] = 1;
      items.push(item);
    }
    return { items: items.length ? items : null, skipped: skipped };
  }

  // German page copy for a tile without rows. Keys: none = no database in this
  // view, loading, slow = not reached after 10 s, empty = no data yet, nomatch = filters hide all.
  var NOUN = {
    todos: ['Die Aufgaben sind', 'Aufgaben', 'Noch keine Aufgaben abgeglichen. Claude schreibt die offenen ToDos aus zotero2ai in der Sitzung hierher.'],
    jira: ['Die Tickets sind', 'Tickets', 'Noch keine Tickets abgeglichen. Claude schreibt deine offenen Jira-Tickets in der Sitzung hierher.'],
    sessions: ['Die Sitzungen sind', 'Sitzungen', 'Noch keine Sitzungen eingetragen. Claude schreibt die laufenden Claude-Code-Sitzungen dieses Rechners hierher.'],
    status: ['Der Status ist', 'Status', 'Noch kein Status gespeichert. Claude schreibt den Stand der Sitzung hierher.'],
    statustable: ['Die Statustabelle ist', 'Statustabelle', 'Noch keine Statustabelle gespeichert. Claude schreibt die Zeilen der Statustabelle in der Sitzung hierher.'],
    feed: ['Die Neuigkeiten sind', 'Neuigkeiten', 'Noch keine Neuigkeiten abgeglichen. Claude schreibt neue Änderungen aus Confluence und Jira in der Sitzung hierher.'],
    list: ['Die Liste ist', 'Liste', 'Diese Liste ist noch leer. Der Skill, der sie füllt, schreibt seine Einträge in der Sitzung hierher.']
  };

  function emptyText(kind, state) {
    var n = NOUN[kind] || NOUN.list;
    switch (state) {
      case 'none': return n[0] + ' in dieser Ansicht nicht erreichbar.';
      case 'loading': return 'Lade ' + n[1] + ' …';
      case 'slow': return n[0] + ' noch nicht erreichbar. Die Seite versucht es weiter.';
      case 'nomatch': return 'Kein Treffer mit diesen Filtern.';
      default: return n[2];
    }
  }

  var api = {
    TILE_KINDS: TILE_KINDS,
    LIST_MAX: LIST_MAX,
    filterTodos: filterTodos,
    filterJira: filterJira,
    sortSessions: sortSessions,
    filterFeed: filterFeed,
    filterList: filterList,
    validateList: validateList,
    limitItems: limitItems,
    listIdOf: listIdOf,
    parseCommand: parseCommand,
    validLayout: validLayout,
    presetLayout: presetLayout,
    truncatedOf: truncatedOf,
    truncatedNote: truncatedNote,
    emptyText: emptyText
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) root.DashTiles = api;
})(typeof window !== 'undefined' ? window : null);
