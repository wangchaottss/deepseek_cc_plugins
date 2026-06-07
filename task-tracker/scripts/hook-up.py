#!/usr/bin/env python3
"""UserPromptSubmit hook — records the start of every user prompt as a task.

Reads the hook input from stdin (JSON), calls ``task init``, and injects a
system message so Claude knows about task tracking.
"""

import json
import os
import subprocess
import sys

# Path to the task command (bash wrapper) inside this plugin
_PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TASK_CMD = os.path.join(_PLUGIN_ROOT, "bin", "task")


def _project_ns(cwd):
    return cwd.replace("/", "-")


def main():
    # ---- read hook input --------------------------------------------------
    try:
        inp = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, IOError):
        print(json.dumps({"decision": "approve"}))
        return

    session_id = inp.get("session_id", "")
    prompt = inp.get("prompt", "")
    cwd = inp.get("cwd", os.getcwd())

    if not session_id:
        print(json.dumps({"decision": "approve"}))
        return

    # ---- persist the task record ------------------------------------------
    try:
        subprocess.run(
            [_TASK_CMD, "init", "-s", session_id, "-p", prompt],
            capture_output=True,
            timeout=10,
            cwd=cwd,
        )
    except Exception:
        # Never block the user because of a bookkeeping glitch
        pass

    # ---- build injected context -------------------------------------------
    ns = _project_ns(cwd)
    records_hint = f"~/.claude/task_records/{ns}/"

    additional_context = (
        f"Task tracking is active.  Session ID: {session_id}\n\n"
        f"Before starting work you may check {records_hint} "
        f"for previous task records to understand the project context.\n\n"
        f"When you have COMPLETED the task you MUST run:\n"
        f"  task finish -s {session_id} -m \"<summary of what you did>\"\n\n"
        f"This is required — the session will be blocked from stopping "
        f"until the task is marked as finished."
    )

    output = {
        "decision": "approve",
        "systemMessage": additional_context,
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": additional_context,
        },
    }
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
