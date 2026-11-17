"""Plan which page-side ToDo flags may be written back to the source system.

Pure function. It writes nothing. The /dashboard sync command shows the plan
and writes only after the user says yes.
"""

META_KEYS = {"createdAt"}


def plan(flags, notes, current_todos, seen):
    """Return one row per flag: {key, title, from, to, note, action}.

    action is one of transition, changed_in_source, needs_reason, unknown_key.
    `seen` maps ToDo key to the status the page showed when the flag was set.
    """
    by_key = {t["key"]: t for t in current_todos}
    rows = []
    for key, target in flags.items():
        if key in META_KEYS or not isinstance(target, str):
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
