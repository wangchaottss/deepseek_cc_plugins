#!/usr/bin/env python3
"""Stop hook — prevents the session from ending until the task is finished.

When Claude attempts to stop, this hook inspects the task record.  If the
status is anything other than ``"finished"`` it returns ``decision: block``
and injects a prompt telling Claude to call ``task finish``.
"""

import json
import os
import subprocess
import sys

_PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TASK_CMD = os.path.join(_PLUGIN_ROOT, "bin", "task")


def main():
    # ---- read hook input --------------------------------------------------
    try:
        inp = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, IOError):
        print(json.dumps({"decision": "approve"}))
        return

    session_id = inp.get("session_id", "")
    cwd = inp.get("cwd", os.getcwd())

    if not session_id:
        print(json.dumps({"decision": "approve"}))
        return

    # ---- query task status ------------------------------------------------
    try:
        result = subprocess.run(
            [_TASK_CMD, "status", "-s", session_id],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=cwd,
        )
    except (subprocess.TimeoutExpired, OSError):
        # If we can't check status, don't block
        print(json.dumps({"decision": "approve"}))
        return

    if result.returncode != 0:
        # No record exists — nothing to enforce
        print(json.dumps({"decision": "approve"}))
        return

    try:
        task_data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(json.dumps({"decision": "approve"}))
        return

    status = task_data.get("status", "")

    # ---- already finished → allow -----------------------------------------
    if status == "finished":
        print(json.dumps({"decision": "approve"}))
        return

    # ---- not finished → block + inject prompt -----------------------------
    prompt_preview = (task_data.get("prompt") or "unknown")[:100]

    additional_context = (
        f"⚠️  The task is NOT yet marked as finished!\n\n"
        f"Session : {session_id}\n"
        f"Task    : {prompt_preview}\n"
        f"Status  : {status}\n\n"
        f"Before this session can end you MUST mark it as finished:\n"
        f"  task finish -s {session_id} -m \"<summary of what you accomplished>\"\n\n"
        f"Include a concise summary of what was done.  "
        f"After the task is marked finished you may stop normally."
    )

    output = {
        "decision": "block",
        "reason": (
            f"Task {session_id} has status '{status}' — "
            f"must be 'finished' before stopping."
        ),
        "systemMessage": additional_context,
    }
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
