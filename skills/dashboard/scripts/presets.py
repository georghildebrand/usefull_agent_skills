"""Dashboard presets: merge repo presets with the private presets file.

Private file layout: {"presets": {<name>: {...}}, "denyList": [<string>, ...]}.
Repo presets live in <repo_dir>/presets/<name>.json.
"""
import json
import os

TILE_KINDS = ["todos", "jira", "sessions", "status", "statustable", "feed", "list", "note"]
DEFAULT_PRIVATE = os.path.expanduser("~/.config/claude-dashboard/presets.json")


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


def add_tile(name, kind, private_path=DEFAULT_PRIVATE, w=6, h=4):
    if kind not in TILE_KINDS:
        raise ValueError("unknown tile kind: %s" % kind)
    data = _read(private_path)
    preset = data.setdefault("presets", {}).setdefault(name, {})
    tiles = preset.setdefault("tiles", [])
    y = max([t["y"] + t["h"] for t in tiles], default=0)
    tiles.append({"kind": kind, "x": 0, "y": y, "w": w, "h": h})
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


def secret_values(private_path=DEFAULT_PRIVATE):
    """Secret strings from the private file, unique, length >= 3.

    Only keys that hold secrets count: per preset `url`, `sources`, `filters`,
    plus the top-level `denyList`. Tile layouts and kind names are skipped.
    A multi-line value is split into its lines.
    """
    data = _read(private_path)
    if not isinstance(data, dict):
        raise ValueError("private file must hold a JSON object")
    nodes = [data.get("denyList")]
    for preset in (data.get("presets") or {}).values():
        if isinstance(preset, dict):
            nodes += [preset.get("url"), preset.get("sources"), preset.get("filters")]
    seen = []
    for node in nodes:
        for s in _strings(node):
            for line in s.splitlines():
                line = line.strip()
                if len(line) >= 3 and line not in seen:
                    seen.append(line)
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
