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
  while ((m = re.exec(html))) if (!/\ssrc=/.test(m[1] || '')) out.push(m[2]);
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
