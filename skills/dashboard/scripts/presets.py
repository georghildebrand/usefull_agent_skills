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
    """Every string in the private file (deny list included), unique, length >= 3."""
    seen = []
    for s in _strings(_read(private_path)):
        if len(s) >= 3 and s not in seen:
            seen.append(s)
    return seen


if __name__ == "__main__":
    import sys
    # Used by check-clean.sh: print one value per line.
    for v in secret_values(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PRIVATE):
        if "\n" not in v:
            print(v)
