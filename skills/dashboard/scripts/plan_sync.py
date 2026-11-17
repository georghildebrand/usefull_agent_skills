"""Plan which page-side ToDo flags may be written back to the source system.

Pure function. It writes nothing. The /dashboard sync command shows the plan
and writes only after the user says yes.
"""

META_KEYS = {"createdAt"}
# The five zotero2ai ToDo statuses. A flag with any other value (for example
# "" from a mark taken back on an older page) is not a target and is skipped.
STATUSES = {"todo", "in_progress", "blocked", "done", "cancelled"}


def plan(flags, notes, current_todos, seen):
    """Return one row per flag: {key, title, from, to, note, action}.

    action is one of transition, changed_in_source, needs_reason, unknown_key.
    `seen` maps ToDo key to the status the page showed when the flag was set.
    The page stores it in `todostate/seen`; never take it from `todolists/*`,
    because a refresh rewrites those with the current source status.
    """
    by_key = {t["key"]: t for t in current_todos}
    rows = []
    for key, target in flags.items():
        if key in META_KEYS or not isinstance(target, str) or target not in STATUSES:
            continue
        note = notes.get(key)
        note = note if isinstance(note, str) else ""
        todo = by_key.get(key)
        if todo is None:
            rows.append({"key": key, "title": "", "from": None, "to": target,
                         "note": note, "action": "unknown_key"})
            continue
        current = todo.get("status")
        if key in seen and seen[key] != current:
            action = "changed_in_source"
        elif target == "blocked" and not note.strip():
            action = "needs_reason"
        else:
            action = "transition"
        rows.append({"key": key, "title": todo.get("title", ""), "from": current,
                     "to": target, "note": note, "action": action})
    return rows
