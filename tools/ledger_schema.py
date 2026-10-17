"""Schema-v1 ledger validation; no file or browser state."""

import datetime as dt

KINDS = {"planning", "decision", "implementation", "qualification"}
STATUSES = {"planned", "active", "review", "blocked", "done", "deferred"}
TASK_FIELDS = {
    "id", "title", "phase", "kind", "status", "depends_on", "scope",
    "acceptance", "validation", "model_role", "owner", "evidence", "review",
    "blocked_reason", "notes",
}


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate(data: dict) -> list[str]:
    errors: list[str] = []
    require(data.get("schema_version") == 1, "schema_version must equal 1", errors)
    milestone = data.get("milestone")
    require(isinstance(milestone, dict), "milestone must be an object", errors)
    if isinstance(milestone, dict):
        for field in ("id", "title", "updated_at", "baseline_status"):
            require(isinstance(milestone.get(field), str) and bool(milestone[field].strip()),
                    f"milestone.{field} must be a nonempty string", errors)
        stamp = milestone.get("updated_at")
        if isinstance(stamp, str):
            try:
                parsed = dt.datetime.fromisoformat(stamp.replace("Z", "+00:00"))
                require(parsed.tzinfo is not None, "milestone.updated_at must include a UTC offset", errors)
            except ValueError:
                errors.append("milestone.updated_at must be an ISO 8601 timestamp")

    phases = data.get("phases")
    tasks = data.get("tasks")
    require(isinstance(phases, list), "phases must be an array", errors)
    require(isinstance(tasks, list), "tasks must be an array", errors)
    if not isinstance(phases, list) or not isinstance(tasks, list):
        return errors

    phase_ids: list[str] = []
    for index, phase in enumerate(phases):
        prefix = f"phases[{index}]"
        require(isinstance(phase, dict), f"{prefix} must be an object", errors)
        if not isinstance(phase, dict):
            continue
        for field in ("id", "title", "outcome", "gate"):
            require(isinstance(phase.get(field), str) and bool(phase[field].strip()),
                    f"{prefix}.{field} must be a nonempty string", errors)
        if isinstance(phase.get("id"), str):
            phase_ids.append(phase["id"])
    duplicates = sorted({value for value in phase_ids if phase_ids.count(value) > 1})
    if duplicates:
        errors.append("duplicate phase ids: " + ", ".join(duplicates))

    task_ids: list[str] = []
    for index, task in enumerate(tasks):
        prefix = f"tasks[{index}]"
        require(isinstance(task, dict), f"{prefix} must be an object", errors)
        if not isinstance(task, dict):
            continue
        missing = sorted(TASK_FIELDS - set(task))
        if missing:
            errors.append(f"{prefix} missing fields: {', '.join(missing)}")
        for field in ("id", "title", "phase", "kind", "status", "model_role", "owner"):
            require(isinstance(task.get(field), str) and bool(task[field].strip()),
                    f"{prefix}.{field} must be a nonempty string", errors)
        for field in ("depends_on", "scope", "acceptance", "validation", "evidence"):
            value = task.get(field)
            require(isinstance(value, list) and all(isinstance(item, str) and item.strip() for item in value),
                    f"{prefix}.{field} must be an array of nonempty strings", errors)
        for field in ("review", "blocked_reason", "notes"):
            require(isinstance(task.get(field), str), f"{prefix}.{field} must be a string", errors)
        task_id = task.get("id")
        if "tags" in task:
            tags = task.get("tags")
            valid_tags = (isinstance(tags, list) and bool(tags) and
                          all(isinstance(tag, str) and bool(tag.strip()) and tag == tag.strip()
                              for tag in tags))
            require(valid_tags, f"{prefix}.tags must be a nonempty array of labels", errors)
            if valid_tags:
                require(len({tag.casefold() for tag in tags}) == len(tags),
                        f"{prefix}.tags must be unique", errors)
        if isinstance(task_id, str):
            task_ids.append(task_id)
        phase_id = task.get("phase")
        kind = task.get("kind")
        status = task.get("status")
        require(isinstance(phase_id, str) and phase_id in phase_ids,
                f"{prefix}.phase references an unknown phase", errors)
        require(isinstance(kind, str) and kind in KINDS, f"{prefix}.kind is invalid", errors)
        require(isinstance(status, str) and status in STATUSES, f"{prefix}.status is invalid", errors)
        if task.get("status") == "active":
            require(isinstance(task.get("owner"), str) and
                    task["owner"].strip().lower() not in ("", "unassigned"),
                    f"{prefix} active task needs a named owner", errors)
            require(bool(task.get("scope")), f"{prefix} active task needs a bounded scope", errors)
        if task.get("status") == "blocked":
            require(bool(str(task.get("blocked_reason", "")).strip()),
                    f"{prefix} is blocked but has no blocked_reason", errors)
        if task.get("status") == "done":
            require(bool(task.get("evidence")), f"{prefix} is done but has no evidence", errors)
            require(bool(str(task.get("review", "")).strip()), f"{prefix} is done but has no review", errors)
            validation = task.get("validation")
            if isinstance(validation, list):
                normalized = [item.strip().lower() for item in validation if isinstance(item, str)]
                require(any(item.startswith("passed:") for item in normalized),
                        f"{prefix} is done but has no passed: validation result", errors)
                recognized = ("passed:", "failed:", "not run:", "waived:", "pending:", "expected:")
                require(all(item.startswith(recognized) for item in normalized),
                        f"{prefix} is done with an unrecognized validation result prefix", errors)
                disallowed = ("pending:", "expected:", "failed:")
                require(not any(item.startswith(disallowed) for item in normalized),
                        f"{prefix} is done with pending, expected, or failed validation", errors)
                if task.get("kind") == "qualification":
                    require(not any(item.startswith("not run:") for item in normalized),
                            f"{prefix} qualification is done with validation not run", errors)
    duplicates = sorted({value for value in task_ids if task_ids.count(value) > 1})
    if duplicates:
        errors.append("duplicate task ids: " + ", ".join(duplicates))
    if errors:
        return errors

    task_map = {task.get("id"): task for task in tasks if isinstance(task, dict) and isinstance(task.get("id"), str)}
    for task_id, task in task_map.items():
        deps = task.get("depends_on", [])
        if not isinstance(deps, list):
            continue
        repeated = sorted({dep for dep in deps if deps.count(dep) > 1})
        if repeated:
            errors.append(f"{task_id} repeats dependencies: {', '.join(repeated)}")
        missing = sorted(dep for dep in deps if dep not in task_map)
        if missing:
            errors.append(f"{task_id} has missing dependencies: {', '.join(missing)}")
        if task_id in deps:
            errors.append(f"{task_id} cannot depend on itself")
        if task.get("status") in {"active", "review", "done"}:
            incomplete = [dep for dep in deps if dep in task_map and task_map[dep].get("status") != "done"]
            if incomplete:
                errors.append(
                    f"{task_id} is {task.get('status')} before dependencies: {', '.join(incomplete)}"
                )

    visiting: set[str] = set()
    visited: set[str] = set()
    def visit(task_id: str, trail: list[str]) -> None:
        if task_id in visited:
            return
        if task_id in visiting:
            start = trail.index(task_id)
            errors.append("dependency cycle: " + " -> ".join(trail[start:] + [task_id]))
            return
        visiting.add(task_id)
        trail.append(task_id)
        for dep in task_map[task_id].get("depends_on", []):
            if dep in task_map:
                visit(dep, trail)
        trail.pop()
        visiting.remove(task_id)
        visited.add(task_id)
    for task_id in task_map:
        visit(task_id, [])
    return errors
