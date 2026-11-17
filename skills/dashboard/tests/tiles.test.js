#!/usr/bin/env node
/*
 * Tests for template/tiles.js (pure tile functions) and template/page.html.
 *
 * The data is hand-written and synthetic. No test reads ~/.claude or calls a
 * real API. The page itself needs a browser, so the page tests check only its
 * text: placeholders, meta tags, scripts and that the inline script parses.
 *
 * Run: node --test skills/dashboard/tests/
 */
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const ROOT = path.join(__dirname, '..');
const T = require(path.join(ROOT, 'template', 'tiles.js'));
const PAGE = path.join(ROOT, 'template', 'page.html');

const NOW = Date.parse('2026-11-17T10:00:00Z');
const DAY = 864e5;

function iso(ms) { return new Date(ms).toISOString().replace(/\.\d{3}Z$/, 'Z'); }

function todoList(items, extra) {
  return Object.assign({ id: 'p1', v: 1, syncedAt: iso(NOW), source: 'todos', project: 'p1', items: items }, extra || {});
}

const FLT = { q: '', project: '', status: '', prio: '', age: '', sq: '', ssort: 'active',
  jq: '', jproject: '', jrole: '', jstat: '', jtype: '', jage: '', fq: '', fsrc: '', fonly: '' };

function flt(over) { return Object.assign({}, FLT, over || {}); }

// ---- parseCommand ----

test('parseCommand: refresh with a known tile', () => {
  assert.deepEqual(T.parseCommand('dashboard refresh global jira'), { cmd: 'refresh', preset: 'global', tile: 'jira' });
});

test('parseCommand: free text is not a command', () => {
  assert.equal(T.parseCommand('bitte auffrischen'), null);
});

test('parseCommand: unknown tile is rejected', () => {
  assert.equal(T.parseCommand('dashboard refresh global nonsense'), null);
});

test('parseCommand: all, list:<skill-id> and sync', () => {
  assert.deepEqual(T.parseCommand('dashboard refresh global all'), { cmd: 'refresh', preset: 'global', tile: 'all' });
  assert.deepEqual(T.parseCommand('dashboard refresh p1 list:my-skill'), { cmd: 'refresh', preset: 'p1', tile: 'list:my-skill' });
  assert.deepEqual(T.parseCommand('dashboard sync global'), { cmd: 'sync', preset: 'global', tile: null });
});

test('parseCommand: extra words, bare list and missing parts are rejected', () => {
  assert.equal(T.parseCommand('dashboard refresh global jira now'), null);
  assert.equal(T.parseCommand('dashboard refresh global list'), null);
  assert.equal(T.parseCommand('dashboard refresh global list:'), null);
  assert.equal(T.parseCommand('dashboard refresh global'), null);
  assert.equal(T.parseCommand('dashboard sync global jira'), null);
  assert.equal(T.parseCommand('please run dashboard refresh global jira'), null);
  assert.equal(T.parseCommand(null), null);
});

// ---- validateList / limitItems ----

test('validateList: wrong version is not ok', () => {
  const r = T.validateList({ v: 2 });
  assert.equal(r.ok, false);
  assert.equal(typeof r.reason, 'string');
});

test('validateList: 600 items are ok; the tile keeps the first 500', () => {
  const items = [];
  for (let i = 0; i < 600; i++) items.push({ title: 'Item ' + i, status: 'open', date: iso(NOW - i * DAY) });
  const doc = { v: 1, title: 'Liste', syncedAt: iso(NOW), source: 'demo', items: items };
  assert.deepEqual(T.validateList(doc), { ok: true });
  const lim = T.limitItems(doc.items);
  assert.equal(lim.items.length, 500);
  assert.equal(lim.hidden, 100);
  assert.equal(lim.items[0].title, 'Item 0');
  assert.equal(lim.items[499].title, 'Item 499');
});

test('limitItems: short list keeps all, hidden 0', () => {
  assert.deepEqual(T.limitItems([{ title: 'a' }], 500), { items: [{ title: 'a' }], hidden: 0 });
  assert.deepEqual(T.limitItems(undefined), { items: [], hidden: 0 });
});

test('validateList: malformed shapes are not ok', () => {
  assert.equal(T.validateList(null).ok, false);
  assert.equal(T.validateList({ v: 1, title: 'x' }).ok, false);
  assert.equal(T.validateList({ v: 1, title: 'x', items: [{ status: 'open' }] }).ok, false);
  assert.equal(T.validateList({ v: 1, title: 'x', items: [{ title: 'a', link: 5 }] }).ok, false);
});

// ---- filterTodos ----

test('filterTodos: age 60 drops an item changed 61 days before now', () => {
  const lists = [todoList([
    { key: 'K1', title: 'recent', status: 'todo', priority: 'high', updatedAt: iso(NOW - 10 * DAY) },
    { key: 'K2', title: 'old', status: 'todo', priority: 'low', updatedAt: iso(NOW - 61 * DAY) },
  ])];
  const r = T.filterTodos(lists, flt({ age: '60' }), NOW);
  assert.equal(r.total, 2);
  assert.deepEqual(r.rows.map((x) => x.item.key), ['K1']);
  const all = T.filterTodos(lists, flt({ age: '' }), NOW);
  assert.deepEqual(all.rows.map((x) => x.item.key), ['K1', 'K2']);
});

test('filterTodos: project, status, prio and search filters; oldest syncedAt', () => {
  const lists = [
    todoList([{ key: 'A', title: 'Write docs', status: 'in_progress', priority: 'critical', updatedAt: iso(NOW - DAY) }], { syncedAt: '2026-11-17T09:00:00Z' }),
    todoList([{ key: 'B', title: 'Fix build', status: 'blocked', priority: 'low', updatedAt: iso(NOW - 2 * DAY) }], { id: 'p2', project: 'p2', syncedAt: '2026-11-16T09:00:00Z' }),
  ];
  assert.deepEqual(T.filterTodos(lists, flt({ project: 'p2' }), NOW).rows.map((x) => x.item.key), ['B']);
  assert.deepEqual(T.filterTodos(lists, flt({ status: 'in_progress' }), NOW).rows.map((x) => x.item.key), ['A']);
  assert.deepEqual(T.filterTodos(lists, flt({ prio: 'top' }), NOW).rows.map((x) => x.item.key), ['A']);
  assert.deepEqual(T.filterTodos(lists, flt({ q: 'BUILD' }), NOW).rows.map((x) => x.item.key), ['B']);
  const r = T.filterTodos(lists, flt(), NOW);
  assert.equal(r.syncedAt, '2026-11-16T09:00:00Z');
  assert.equal(r.rows[1].project, 'p2');
});

// ---- filterJira ----

test('filterJira: filters and newest first', () => {
  const doc = { v: 1, syncedAt: iso(NOW), source: 'jira', baseUrl: 'https://jira.example.test/browse/', items: [
    { key: 'ACME-1', title: 'One', project: 'ACME', type: 'Task', statusCat: 'new', role: 'assignee', updatedAt: iso(NOW - 3 * DAY) },
    { key: 'ACME-2', title: 'Two', project: 'ACME', type: 'Bug', statusCat: 'indeterminate', role: 'reporter', updatedAt: iso(NOW - DAY) },
    { key: 'DEMO-3', title: 'Three', project: 'DEMO', type: 'Task', statusCat: 'new', role: 'assignee', updatedAt: iso(NOW - 90 * DAY) },
  ] };
  assert.deepEqual(T.filterJira(doc, flt(), NOW).rows.map((x) => x.key), ['ACME-2', 'ACME-1', 'DEMO-3']);
  assert.deepEqual(T.filterJira(doc, flt({ jage: '60' }), NOW).rows.map((x) => x.key), ['ACME-2', 'ACME-1']);
  assert.deepEqual(T.filterJira(doc, flt({ jrole: 'reporter' }), NOW).rows.map((x) => x.key), ['ACME-2']);
  assert.deepEqual(T.filterJira(doc, flt({ jproject: 'DEMO' }), NOW).rows.map((x) => x.key), ['DEMO-3']);
  assert.deepEqual(T.filterJira(doc, flt({ jtype: 'Bug', jstat: 'indeterminate' }), NOW).rows.map((x) => x.key), ['ACME-2']);
  assert.deepEqual(T.filterJira(doc, flt({ jq: 'acme-1' }), NOW).rows.map((x) => x.key), ['ACME-1']);
  assert.equal(T.filterJira(null, flt(), NOW).total, 0);
});

// ---- sortSessions ----

test('sortSessions: search and the three sort orders', () => {
  const items = [
    { name: 'beta', cwd: '~/b', startedAt: '2026-11-10T00:00:00Z', lastActiveAt: '2026-11-17T09:00:00Z' },
    { name: 'alpha', cwd: '~/a', startedAt: '2026-11-12T00:00:00Z', lastActiveAt: '2026-11-16T09:00:00Z' },
  ];
  assert.deepEqual(T.sortSessions(items, flt({ ssort: 'active' })).map((s) => s.name), ['beta', 'alpha']);
  assert.deepEqual(T.sortSessions(items, flt({ ssort: 'started' })).map((s) => s.name), ['alpha', 'beta']);
  assert.deepEqual(T.sortSessions(items, flt({ ssort: 'name' })).map((s) => s.name), ['alpha', 'beta']);
  assert.deepEqual(T.sortSessions(items, flt({ sq: '~/b' })).map((s) => s.name), ['beta']);
  assert.equal(items[0].name, 'beta', 'input array is not changed');
});

// ---- filterFeed ----

test('filterFeed: read marks, unread filter, source filter and search', () => {
  const doc = { v: 1, syncedAt: iso(NOW), source: 'feed', items: [
    { id: 'c:1', title: 'Runbook', source: 'confluence', changedAt: '2026-11-15T12:00:00Z', why: 'mention' },
    { id: 'j:2', title: 'Ticket moved', source: 'jira', changedAt: '2026-11-16T12:00:00Z', why: 'changed' },
  ] };
  const read = { 'c:1': true };
  const r = T.filterFeed(doc, read, flt());
  assert.equal(r.total, 2);
  assert.equal(r.unread, 1);
  assert.deepEqual(r.rows.map((x) => [x.item.id, x.read]), [['j:2', false], ['c:1', true]]);
  assert.deepEqual(T.filterFeed(doc, read, flt({ fonly: 'unread' })).rows.map((x) => x.item.id), ['j:2']);
  assert.deepEqual(T.filterFeed(doc, read, flt({ fsrc: 'confluence' })).rows.map((x) => x.item.id), ['c:1']);
  assert.deepEqual(T.filterFeed(doc, null, flt({ fq: 'runbook' })).rows.map((x) => x.item.id), ['c:1']);
});

// ---- filterList ----

test('filterList: status filter, search and date sort', () => {
  const items = [
    { title: 'old open', status: 'open', date: '2026-11-01T00:00:00Z' },
    { title: 'new done', status: 'done', date: '2026-11-16T00:00:00Z' },
    { title: 'no date', status: 'open' },
  ];
  assert.deepEqual(T.filterList(items, { sort: 'date' }).map((i) => i.title), ['new done', 'old open', 'no date']);
  assert.deepEqual(T.filterList(items, { sort: '' }).map((i) => i.title), ['old open', 'new done', 'no date']);
  assert.deepEqual(T.filterList(items, { status: 'open', q: 'OLD' }).map((i) => i.title), ['old open']);
});

// ---- emptyText ----

test('emptyText: every kind and state has text', () => {
  assert.ok(T.emptyText('jira', 'empty').length > 0);
  for (const kind of ['todos', 'jira', 'sessions', 'status', 'statustable', 'feed', 'list']) {
    for (const state of ['none', 'loading', 'slow', 'empty', 'nomatch']) {
      const s = T.emptyText(kind, state);
      assert.equal(typeof s, 'string');
      assert.ok(s.length > 0, kind + '/' + state);
    }
  }
});

// ---- layout ----

test('validLayout: accepts known kinds, rejects unknown kinds and bad list ids', () => {
  const ok = { items: [{ id: 'jira', kind: 'jira', x: 0, y: 0, w: 6, h: 4 }, { id: 'list:demo', kind: 'list', x: 6, y: 0, w: 6, h: 4 }] };
  assert.deepEqual(T.validLayout(ok), ok.items);
  assert.equal(T.validLayout({ items: [{ id: 'x', kind: 'spark', x: 0, y: 0, w: 6, h: 4 }] }), null);
  assert.equal(T.validLayout({ items: [{ id: 'nope', kind: 'list', x: 0, y: 0, w: 6, h: 4 }] }), null);
  assert.equal(T.validLayout({ items: [{ id: 'a', kind: 'note', x: '0', y: 0, w: 6, h: 4 }] }), null);
  assert.equal(T.validLayout({}), null);
});

// ---- TILE_KINDS matches presets.py ----

test('TILE_KINDS equals the list in scripts/presets.py', () => {
  const py = fs.readFileSync(path.join(ROOT, 'scripts', 'presets.py'), 'utf8');
  const m = py.match(/^TILE_KINDS = (\[.*\])$/m);
  assert.ok(m, 'TILE_KINDS line found in presets.py');
  assert.deepEqual(T.TILE_KINDS, JSON.parse(m[1]));
});

// ---- page.html as text ----

function pageText() { return fs.readFileSync(PAGE, 'utf8'); }

function inlineScripts(html) {
  const out = [];
  const re = /<script(\s[^>]*)?>([\s\S]*?)<\/script>/g;
  let m;
  while ((m = re.exec(html))) if (!/\ssrc=|type="application\/json"/.test(m[1] || '')) out.push(m[2]);
  return out;
}

test('page: placeholders, meta tags and content-only form', () => {
  const html = pageText();
  assert.match(html, /<title>__TITLE__<\/title>/);
  assert.match(html, /<meta name="dashboard-preset" content="__PRESET__">/);
  assert.match(html, /<meta name="dashboard-template" content="1">/);
  assert.match(html, /<meta name="claude:viewport-fit-sides" content="cover">/);
  assert.doesNotMatch(html, /<!doctype|<html|<head|<body/i);
  assert.ok(Buffer.byteLength(html) < 16 * 1024 * 1024);
});

test('page: scripts come only from pinned jsDelivr or tiles.js, tiles.js before the inline script', () => {
  const html = pageText();
  const srcs = [...html.matchAll(/<script[^>]*\ssrc="([^"]+)"/g)].map((m) => m[1]);
  assert.ok(srcs.includes('tiles.js'));
  for (const s of srcs) {
    if (s === 'tiles.js') continue;
    assert.match(s, /^https:\/\/cdn\.jsdelivr\.net\/npm\/[a-z0-9-]+@\d+\.\d+\.\d+\//, s);
  }
  assert.ok(html.indexOf('src="tiles.js"') < html.indexOf('<script>'), 'tiles.js loads before the inline script');
});

test('page: theme tokens with both dark blocks and a body background', () => {
  const html = pageText();
  assert.match(html, /@media \(prefers-color-scheme: dark\)\s*\{\s*:root:not\(\[data-theme="light"\]\)/);
  assert.match(html, /:root\[data-theme="dark"\]/);
  assert.match(html, /body \{[^}]*background: var\(--bg\)/);
  assert.match(html, /max\(16px, env\(safe-area-inset-left/);
});

test('page: the inline script parses and uses the agreed documents and texts', () => {
  const html = pageText();
  const scripts = inlineScripts(html);
  assert.equal(scripts.length, 1);
  assert.doesNotThrow(() => new vm.Script(scripts[0], { filename: 'page-inline.js' }));
  const js = scripts[0];
  for (const s of ["'meta/layout'", "'lists'", "'statustable/current'", "'feed/items'", "'feed/read'",
    "'comments'", 'canSendToClaude', 'sendToClaude', 'anchorFor', 'Auffrischen angefordert um ', "'dashboard refresh '", 'limitItems']) {
    assert.ok(js.includes(s), 'inline script mentions ' + s);
  }
  assert.ok(!/localStorage\.setItem\(KEY/.test(js), 'layout no longer goes to localStorage');
  for (const gone of ['statA', 'statB', 'sparkHtml', 'barsHtml']) assert.ok(!js.includes(gone), 'demo tile removed: ' + gone);
});

// ---- start layout from the preset ----

test('presetLayout: preset tiles become meta/layout items; repeats get numbered ids', () => {
  const global = JSON.parse(fs.readFileSync(path.join(ROOT, 'presets', 'global.json'), 'utf8'));
  const r = T.presetLayout(global.tiles);
  assert.equal(r.skipped, 0);
  assert.deepEqual(r.items.map((i) => i.id), ['todos', 'jira', 'sessions', 'status', 'statustable', 'feed']);
  assert.deepEqual(r.items[0], { id: 'todos', kind: 'todos', x: 0, y: 0, w: 6, h: 4 });
  const two = T.presetLayout([{ kind: 'note', x: 0, y: 0, w: 3, h: 2 }, { kind: 'note', x: 3, y: 0, w: 3, h: 2 },
    { kind: 'list', id: 'list:demo', x: 0, y: 2, w: 6, h: 4 }]);
  assert.deepEqual(two.items.map((i) => i.id), ['note', 'note-2', 'list:demo']);
});

test('presetLayout: missing tiles give no items; a malformed tile is left out, the others stay', () => {
  assert.deepEqual(T.presetLayout(undefined), { items: null, skipped: 0 });
  assert.deepEqual(T.presetLayout([]), { items: null, skipped: 0 });
  const bad = [{ kind: 'list', x: 0, y: 0, w: 6, h: 4 }, { kind: 'spark', x: 0, y: 0, w: 6, h: 4 },
    { kind: 'jira', x: 0, y: 0, w: 6 }, null, { kind: 'list', id: 'list:..', x: 0, y: 0, w: 6, h: 4 }];
  assert.deepEqual(T.presetLayout(bad), { items: null, skipped: 5 });
  const mixed = T.presetLayout([{ kind: 'todos', x: 0, y: 0, w: 6, h: 4 }, { kind: 'list', x: 0, y: 4, w: 6, h: 4 },
    { kind: 'list', id: 'list:a', x: 6, y: 0, w: 6, h: 4 }, { kind: 'list', id: 'list:a', x: 6, y: 4, w: 6, h: 4 }]);
  assert.deepEqual(mixed.items.map((i) => i.id), ['todos', 'list:a'], 'list tile without id and repeated id left out');
  assert.equal(mixed.skipped, 2);
});

// ---- rows dropped for the size limit ----

test('truncated: filters report the dropped rows and the caption says so', () => {
  const jira = { v: 1, syncedAt: iso(NOW), source: 'jira', truncated: 192, items: [{ key: 'A-1', title: 'x', updatedAt: iso(NOW) }] };
  const r = T.filterJira(jira, flt(), NOW);
  assert.equal(r.truncated, 192);
  assert.equal(T.truncatedNote(r.truncated), ' · 192 weitere wegen Größenlimit nicht gezeigt');
  assert.equal(T.truncatedNote(0), '');
  assert.equal(T.filterJira({ items: [] }, flt(), NOW).truncated, 0);
  const todos = T.filterTodos([todoList([], { truncated: 2 }), todoList([], { id: 'p2', truncated: 5 }), todoList([])], flt(), NOW);
  assert.equal(todos.truncated, 7, 'todos add up truncated over all lists');
  assert.equal(T.filterFeed({ items: [], truncated: 4 }, {}, flt()).truncated, 4);
  assert.equal(T.truncatedOf({ truncated: 'many' }), 0);
  assert.equal(T.truncatedOf({ truncated: -1 }), 0);
  assert.equal(T.truncatedOf(null), 0);
});

// ---- page.html run against fake browser objects ----

// Runs the inline script with stub DOM, GridStack and db. Returns the handles a test needs.
function runPage(html) {
  const byId = {};
  function el(extra) {
    return Object.assign({ innerHTML: '', textContent: '', value: '', hidden: false, options: [], listeners: {},
      addEventListener(t, f) { (this.listeners[t] = this.listeners[t] || []).push(f); },
      querySelector() { return null; }, getAttribute() { return null; }, setAttribute() {},
      matches() { return false; }, closest() { return null; } }, extra || {});
  }
  const layoutBlock = html.match(/<script type="application\/json" id="dashboard-layout">([\s\S]*?)<\/script>/);
  const todoList = el();
  const todos = el({ querySelector: (s) => (s === '[data-todo-list]' ? todoList : null) });
  const document = {
    activeElement: null,
    getElementById(id) {
      if (id === 'dashboard-layout') return layoutBlock ? { textContent: layoutBlock[1] } : null;
      return (byId[id] = byId[id] || el());
    },
    querySelector(s) {
      const m = s.match(/^meta\[name="([^"]+)"\]$/);
      const meta = m && html.match(new RegExp('<meta name="' + m[1] + '" content="([^"]*)">'));
      return meta ? { getAttribute: () => meta[1] } : null;
    },
    querySelectorAll(s) { return s === '[data-todos]' ? [todos] : []; },
    addEventListener() {},
  };
  const grid = { loads: [], engine: { nodes: [] }, removeAll() { this.engine.nodes = []; },
    // Array.from makes an array of this realm, so deepEqual accepts it.
    load(ws) { this.loads.push(Array.from(ws, (w) => w.id));
      this.engine.nodes = ws.map((w) => ({ id: w.id, x: w.x, y: w.y, w: w.w, h: w.h })); },
    on() {}, getColumn() { return 12; }, setStatic() {}, addWidget() {}, removeWidget() {} };
  const subs = {}, writes = [], exists = {};
  // update() rejects on a document that does not exist, as the db contract says.
  function ref(p) {
    return { onSnapshot(cb) { subs[p] = cb; },
      set(d) { writes.push(['set', p, JSON.parse(JSON.stringify(d))]); exists[p] = true; return Promise.resolve(); },
      update(d) {
        writes.push(['update', p, JSON.parse(JSON.stringify(d))]);
        return exists[p] ? Promise.resolve() : Promise.reject(Object.assign(new Error('missing'), { code: 'invalid_argument' }));
      },
      get() { return new Promise(() => {}); } };
  }
  const db = { doc: ref, collection: ref };
  const ctx = { document, GridStack: { init: () => grid }, localStorage: { getItem: () => null, setItem() {} },
    setTimeout: () => 0, clearTimeout() {}, console,
    claude: { use: (n) => Promise.resolve(n === 'db' ? db : null) } };
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(path.join(ROOT, 'template', 'tiles.js'), 'utf8'), ctx);
  vm.runInContext(inlineScripts(html)[0], ctx);
  function doc(p, ex, data) { exists[p] = ex; subs[p]({ exists: ex, data: () => data, metadata: { hasPendingWrites: false } }); }
  function coll(p, docs) { subs[p]({ docs: docs.map((d) => ({ id: d.id, data: () => d })) }); }
  function change(attrs, value) {
    const sel = 'data-note' in attrs ? '[data-note]' : '[data-flag]';
    const target = { value, matches: (s) => s === sel, getAttribute: (a) => attrs[a] };
    byId.grid.listeners.change.forEach((f) => f({ target }));
  }
  return { grid, writes, doc, coll, change, todoList, byId, flush: () => new Promise((r) => setImmediate(r)) };
}

test('page: start layout comes from the preset block; reset returns to it', () => {
  const tiles = [{ kind: 'jira', x: 0, y: 0, w: 6, h: 4 }, { kind: 'list', id: 'list:demo', x: 6, y: 0, w: 6, h: 4 }];
  const html = pageText();
  assert.match(html, /<script type="application\/json" id="dashboard-layout">__LAYOUT__<\/script>/);
  const p = runPage(html.replace('__LAYOUT__', JSON.stringify(tiles)));
  assert.deepEqual(p.grid.loads[0], ['jira', 'list:demo']);
  p.byId['btn-reset'].listeners.click[0]();
  assert.deepEqual(p.grid.loads[p.grid.loads.length - 1], ['jira', 'list:demo']);
  const plain = runPage(html);
  assert.deepEqual(plain.grid.loads[0], ['todos', 'jira', 'sessions', 'status', 'statustable', 'feed'], 'unreplaced template falls back to the global tiles');
  assert.doesNotMatch(plain.byId.status.textContent, /ausgelassen|unbekanntes Format/);
});

test('page: a preset built with presets.add_tile(..., "list", skill_id=...) keeps its own tiles', () => {
  const { execFileSync } = require('node:child_process');
  const os = require('node:os');
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'dash-'));
  try {
    const priv = path.join(dir, 'p.json');
    const py = 'import sys; sys.path.insert(0, sys.argv[1]); import presets, json\n' +
      'presets.add_tile("work", "todos", sys.argv[2])\n' +
      'p = presets.add_tile("work", "list", sys.argv[2], skill_id="demo-skill")\n' +
      'print(json.dumps(p["tiles"]))';
    const tiles = JSON.parse(execFileSync('python3', ['-I', '-c', py, path.join(ROOT, 'scripts'), priv], { encoding: 'utf8' }));
    assert.equal(tiles[1].id, 'list:demo-skill');
    const html = pageText();
    const p = runPage(html.replace('__LAYOUT__', JSON.stringify(tiles)));
    assert.deepEqual(p.grid.loads[0], ['todos', 'list:demo-skill']);
    assert.doesNotMatch(p.byId.status.textContent, /ausgelassen/);

    // An old preset entry with a list tile but no id: the tile is left out, the others stay, the page says so.
    const old = tiles.concat([{ kind: 'list', x: 0, y: 8, w: 6, h: 4 }]);
    const q = runPage(html.replace('__LAYOUT__', JSON.stringify(old)));
    assert.deepEqual(q.grid.loads[0], ['todos', 'list:demo-skill']);
    assert.match(q.byId.status.textContent, /1 Widget aus dem Preset ausgelassen/);
    q.byId['btn-reset'].listeners.click[0]();
    assert.deepEqual(q.grid.loads[q.grid.loads.length - 1], ['todos', 'list:demo-skill']);
    assert.match(q.byId.status.textContent, /Startanordnung wiederhergestellt · 1 Widget aus dem Preset ausgelassen/);

    // No usable tile at all: global tiles, with a notice.
    const none = runPage(html.replace('__LAYOUT__', JSON.stringify([{ kind: 'list', x: 0, y: 0, w: 6, h: 4 }])));
    assert.deepEqual(none.grid.loads[0], ['todos', 'jira', 'sessions', 'status', 'statustable', 'feed']);
    assert.match(none.byId.status.textContent, /Die Widgets des Presets haben ein unbekanntes Format/);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('page: a mark stores the status seen at mark time, shows a hint after a source change, and taking it back removes it', async () => {
  const p = runPage(pageText());
  await p.flush();
  const list = (status) => todoList([{ key: 'T1', title: 'x', status, updatedAt: iso(Date.now()) }], { truncated: 3 });
  p.coll('todolists', [list('todo')]);
  p.doc('todostate/flags', false, {});
  p.doc('todostate/seen', false, {});
  p.doc('todostate/notes', true, { T1: 'why' });
  assert.match(p.todoList.innerHTML, /3 weitere wegen Größenlimit nicht gezeigt/);

  p.change({ 'data-flag': 'T1', 'data-shown': 'todo' }, 'done');
  await p.flush();
  assert.deepEqual(p.writes, [['set', 'todostate/seen', { T1: 'todo' }], ['set', 'todostate/flags', { T1: 'done' }]]);

  // The source moves T1 to in_progress; a refresh rewrites todolists.
  p.doc('todostate/flags', true, { T1: 'done' });
  p.doc('todostate/seen', true, { T1: 'todo' });
  p.coll('todolists', [list('in_progress')]);
  assert.match(p.todoList.innerHTML, /Der Status hat sich in zotero2ai geändert/);
  assert.match(p.todoList.innerHTML, /data-confirm-flag="T1"/);

  // Take the mark back: the first option has value ''.
  p.writes.length = 0;
  p.change({ 'data-flag': 'T1', 'data-shown': 'in_progress' }, '');
  await p.flush();
  assert.deepEqual(p.writes, [['set', 'todostate/flags', {}], ['set', 'todostate/seen', {}], ['set', 'todostate/notes', {}]]);
  assert.ok(!JSON.stringify(p.writes).includes('""'), 'no empty-string mark is written');
  assert.doesNotMatch(p.todoList.innerHTML, /Der Status hat sich/);
});

test('page: the first note on an empty database creates todostate/notes; later notes update it', async () => {
  const p = runPage(pageText());
  await p.flush();
  p.coll('todolists', [todoList([{ key: 'K1', title: 'x', status: 'todo', updatedAt: iso(Date.now()) }])]);
  p.doc('todostate/flags', false, {});
  p.doc('todostate/seen', false, {});
  p.doc('todostate/notes', false, {});
  p.change({ 'data-note': 'K1' }, 'Grund');
  await p.flush();
  assert.deepEqual(p.writes, [['set', 'todostate/notes', { K1: 'Grund' }]]);
  assert.doesNotMatch(p.todoList.innerHTML, /Schreibrecht/);

  p.doc('todostate/notes', true, { K1: 'Grund' });
  p.writes.length = 0;
  p.change({ 'data-note': 'K2' }, 'noch einer');
  await p.flush();
  assert.deepEqual(p.writes, [['update', 'todostate/notes', { K2: 'noch einer' }]]);
});

test('page: a note before todostate/notes has loaded is not written', async () => {
  const p = runPage(pageText());
  await p.flush();
  p.coll('todolists', [todoList([{ key: 'K1', title: 'x', status: 'todo', updatedAt: iso(Date.now()) }])]);
  p.change({ 'data-note': 'K1' }, 'Grund');
  await p.flush();
  assert.deepEqual(p.writes, []);
});

test('page: replacing every copy of the placeholders keeps the preset tiles', () => {
  const html = pageText();
  assert.equal(html.split('__LAYOUT__').length - 1, 1, '__LAYOUT__ appears only in the layout block');
  const tiles = [{ kind: 'jira', x: 0, y: 0, w: 6, h: 4 }];
  const filled = html.split('__LAYOUT__').join(JSON.stringify(tiles))
    .split('__TITLE__').join('Demo').split('__PRESET__').join('demo');
  assert.doesNotMatch(filled, /__(LAYOUT|TITLE|PRESET)__/);
  const p = runPage(filled);
  assert.deepEqual(p.grid.loads[0], ['jira']);
});

test('page: a preset grown by presets.add_tile on a repo preset keeps the repo tiles', () => {
  const { execFileSync } = require('node:child_process');
  const os = require('node:os');
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'dash-'));
  try {
    const priv = path.join(dir, 'p.json');
    const py = 'import sys; sys.path.insert(0, sys.argv[1]); import presets, json\n' +
      'presets.add_tile("global", "note", sys.argv[2], repo_dir=sys.argv[3])\n' +
      'p = presets.load("global", sys.argv[3], sys.argv[2])\n' +
      'print(json.dumps({"tiles": p["tiles"], "layout": presets.layout_items(p["tiles"])}))';
    const out = JSON.parse(execFileSync('python3', ['-I', '-c', py, path.join(ROOT, 'scripts'), priv, ROOT], { encoding: 'utf8' }));
    const ids = ['todos', 'jira', 'sessions', 'status', 'statustable', 'feed', 'note'];
    const p = runPage(pageText().replace('__LAYOUT__', JSON.stringify(out.tiles)));
    assert.deepEqual(p.grid.loads[0], ids);
    assert.deepEqual(T.presetLayout(out.tiles).items, out.layout, 'layout_items in Python matches presetLayout');
    assert.ok(T.validLayout({ items: out.layout }));
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});
