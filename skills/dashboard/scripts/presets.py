"""Dashboard presets: merge repo presets with the private presets file.

Private file layout: {"presets": {<name>: {...}}, "denyList": [<string>, ...]}.
Repo presets live in <repo_dir>/presets/<name>.json. repo_dir is the skill
directory (the folder that holds SKILL.md); SKILL_DIR is this skill's own one.
"""
import json
import os
import re

TILE_KINDS = ["todos", "jira", "sessions", "status", "statustable", "feed", "list", "note"]
# Same rule as SEGMENT in template/tiles.js: one database path segment.
SKILL_ID = re.compile(r"^[A-Za-z0-9_\-.~:@+]{1,200}\Z")
DEFAULT_PRIVATE = os.path.expanduser("~/.config/claude-dashboard/presets.json")
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def _write(path, data):
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def load(name, repo_dir, private_path=DEFAULT_PRIVATE):
    repo = _read(os.path.join(repo_dir, "presets", name + ".json"))
    priv = (_read(private_path).get("presets") or {}).get(name)
    if not repo and priv is None:
        raise KeyError(name)
    merged = {}
    merged.update(repo)
    merged.update(priv or {})
    return {
        "name": name,
        "url": merged.get("url"),
        "tiles": list(merged.get("tiles") or []),
        "filters": dict(merged.get("filters") or {}),
        "sources": dict(merged.get("sources") or {}),
    }


def set_url(name, url, private_path=DEFAULT_PRIVATE):
    data = _read(private_path)
    data.setdefault("presets", {}).setdefault(name, {})["url"] = url
    _write(private_path, data)


def _ids(tiles):
    """Tile ids as the page gives them (presetLayout in template/tiles.js).

    A tile with its own string id keeps it. Any other tile gets its kind, or
    <kind>-2, <kind>-3, ... when that id is taken.
    """
    used, out = set(), []
    for t in tiles:
        if not isinstance(t, dict):
            out.append(None)
            continue
        own = t.get("id") if isinstance(t.get("id"), str) and t.get("id") else ""
        tid, n = own or str(t.get("kind")), 2
        while tid in used and not own:
            tid, n = "%s-%d" % (t.get("kind"), n), n + 1
        used.add(tid)
        out.append(tid)
    return out


def _item(tile, tid):
    return {"id": tid, "kind": tile.get("kind"), "x": tile.get("x"), "y": tile.get("y"),
            "w": tile.get("w"), "h": tile.get("h")}


def _usable(item):
    """The per-item check of validLayout in template/tiles.js."""
    nums = all(isinstance(item[k], (int, float)) and not isinstance(item[k], bool) for k in "xywh")
    if not nums or item["kind"] not in TILE_KINDS:
        return False
    if item["kind"] != "list":
        return True
    sid = item["id"][len("list:"):] if item["id"].startswith("list:") else ""
    return bool(SKILL_ID.match(sid)) and sid not in (".", "..")


def layout_items(tiles):
    """meta/layout items for a preset's tiles, as presetLayout in template/tiles.js makes them.

    Same ids as the page gives them. A tile the page would leave out is left out.
    """
    used, items = set(), []
    for t in tiles or []:
        if not isinstance(t, dict):
            continue
        own = t.get("id") if isinstance(t.get("id"), str) and t.get("id") else ""
        tid, n = own or str(t.get("kind")), 2
        while tid in used and not own:
            tid, n = "%s-%d" % (t.get("kind"), n), n + 1
        item = _item(t, tid)
        if tid in used or not _usable(item):
            continue
        used.add(tid)
        items.append(item)
    return items


def append_to_layout(items, tile):
    """Return a copy of meta/layout items with tile added below the lowest item.

    The id is the tile's own id, or a new <kind>-<n> when another item has it.
    Raises ValueError when a list tile with that id is already on the page.
    """
    items = [dict(i) for i in items or [] if isinstance(i, dict)]
    taken = {i.get("id") for i in items}
    tid = tile.get("id") or tile["kind"]
    if tid in taken and tile["kind"] == "list":
        raise ValueError("this list is already on the page")
    n = 2
    while tid in taken:
        tid, n = "%s-%d" % (tile["kind"], n), n + 1
    y = max([i.get("y", 0) + i.get("h", 0) for i in items], default=0)
    items.append(dict(_item(tile, tid), x=0, y=y))
    return items


def add_tile(name, kind, private_path=DEFAULT_PRIVATE, w=6, h=4, skill_id=None, repo_dir=SKILL_DIR):
    """Append a tile below the lowest tile of the preset and return the private preset.

    When the private preset has no tiles yet, it first gets a copy of the repo
    preset's tiles (from repo_dir), so the preset keeps its own tiles. The new
    tile is the last one in the returned "tiles" and always has an id: the id the
    page gives it (kind, or kind-2, kind-3 for repeats). A list tile needs
    skill_id: its id is "list:<skill_id>", the id the page needs to find the
    document lists/<skill_id>. Raises ValueError for an unknown kind, a list
    tile without a valid skill_id, a list that is already in the preset, or a
    skill_id given for another kind.
    """
    if kind not in TILE_KINDS:
        raise ValueError("unknown tile kind: %s" % kind)
    tile = {"kind": kind}
    if kind == "list":
        if not skill_id or not SKILL_ID.match(skill_id) or skill_id in (".", ".."):
            raise ValueError("a list tile needs a skill id (one database path segment)")
        tile["id"] = "list:" + skill_id
    elif skill_id is not None:
        raise ValueError("skill_id is only for kind 'list'")
    data = _read(private_path)
    preset = data.setdefault("presets", {}).setdefault(name, {})
    if "tiles" not in preset:
        repo = _read(os.path.join(repo_dir, "presets", name + ".json"))
        preset["tiles"] = [dict(t) for t in repo.get("tiles") or [] if isinstance(t, dict)]
    tiles = preset["tiles"]
    if "id" in tile and any(t.get("id") == tile["id"] for t in tiles):
        raise ValueError("this list is already in the preset")
    if "id" not in tile:
        tile["id"] = _ids(tiles + [tile])[-1]
    y = max([t.get("y", 0) + t.get("h", 0) for t in tiles], default=0)
    tile.update({"x": 0, "y": y, "w": w, "h": h})
    tiles.append(tile)
    _write(private_path, data)
    return preset


def _strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for v in node.values():
            yield from _strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from _strings(v)


def _repo_names(repo_dir):
    try:
        return {f[:-5] for f in os.listdir(os.path.join(repo_dir, "presets")) if f.endswith(".json")}
    except OSError:
        return set()


def _kind_id(tid):
    """True for an id the page makes from a kind alone: todos, note-2, ..."""
    return re.match(r"^(%s)(-\d+)?\Z" % "|".join(TILE_KINDS), tid) is not None


def secret_values(private_path=DEFAULT_PRIVATE, repo_dir=SKILL_DIR):
    """Secret strings from the private file, unique, length >= 3.

    These fields are checked, and nothing else:
    - top-level `denyList`: each entry as written;
    - each preset name (a key of `presets`), except names of repo presets
      (<repo_dir>/presets/<name>.json, for example "global");
    - per preset `url`, as written;
    - per preset `sources`: each value as written, and each part split at
      commas, semicolons and spaces ("ACME, DEMO" gives "ACME" and "DEMO");
    - per preset `filters`: each value as written, and each part split at
      commas and semicolons;
    - per tile `id`, without the `list:` prefix. Ids made from a kind alone
      (todos, note-2) and the kind names are skipped.
    Every value is also split into its lines. Anything else that is secret
    must go into `denyList`.
    """
    data = _read(private_path)
    if not isinstance(data, dict):
        raise ValueError("private file must hold a JSON object")
    repo_names = _repo_names(repo_dir)
    found = []  # (string, split pattern or None)
    found += [(s, None) for s in _strings(data.get("denyList"))]
    for name, preset in (data.get("presets") or {}).items():
        if name not in repo_names:
            found.append((name, None))
        if not isinstance(preset, dict):
            continue
        found += [(s, None) for s in _strings(preset.get("url"))]
        found += [(s, r"[,;\s]+") for s in _strings(preset.get("sources"))]
        found += [(s, r"[,;]+") for s in _strings(preset.get("filters"))]
        for t in preset.get("tiles") or []:
            tid = t.get("id") if isinstance(t, dict) else None
            if isinstance(tid, str):
                tid = tid[len("list:"):] if tid.startswith("list:") else tid
                if not _kind_id(tid):
                    found.append((tid, None))
    seen = []
    for s, sep in found:
        for line in s.splitlines():
            parts = [line] + (re.split(sep, line) if sep else [])
            for part in parts:
                part = part.strip()
                if len(part) >= 3 and part not in seen:
                    seen.append(part)
    return seen


if __name__ == "__main__":
    import sys
    # Used by check-clean.sh: print one value per line. Exit 2 if the file is unreadable.
    try:
        values = secret_values(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PRIVATE)
    except (ValueError, OSError) as e:
        print("cannot read private file: %s" % type(e).__name__, file=sys.stderr)
        sys.exit(2)
    for v in values:
        print(v)
