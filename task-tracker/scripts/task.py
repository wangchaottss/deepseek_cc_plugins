#!/usr/bin/env python3
"""Task record manager for Claude Code sessions.

Manages JSON state files and markdown archives in ~/.claude/task_records/
to track task lifecycle across Claude Code sessions.

Usage:
    task init -s <session-id> -p <prompt>
    task status [-s <session-id> | list]
    task finish -s <session-id> -m <summary>
"""

import json
import os
import sys
import argparse
from datetime import datetime

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
TASK_RECORDS_DIR = os.path.expanduser("~/.claude/task_records")


def get_project_namespace(cwd=None):
    """Convert an absolute project path to a filesystem-safe namespace.

    /Users/wangchao/TestAICoding/20260607/ds_cc_p
    -> -Users-wangchao-TestAICoding-20260607-ds_cc_p
    """
    if cwd is None:
        cwd = os.getcwd()
    return cwd.replace("/", "-")


def get_records_dir(cwd=None):
    """Return the records directory for *cwd*, creating it if needed."""
    ns = get_project_namespace(cwd)
    d = os.path.join(TASK_RECORDS_DIR, ns)
    os.makedirs(d, exist_ok=True)
    return d


def _sanitize_filename(session_id):
    """Replace characters that are unsafe in filenames."""
    return session_id.replace("/", "-").replace("\x00", "")


def _json_path(records_dir, session_id):
    return os.path.join(records_dir, f"{_sanitize_filename(session_id)}.json")


def _md_path(records_dir, session_id):
    return os.path.join(records_dir, f"{_sanitize_filename(session_id)}.md")


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_init(session_id, prompt, cwd=None):
    """Create or reset a task record to 'running'."""
    records_dir = get_records_dir(cwd)
    jp = _json_path(records_dir, session_id)
    now = _now()

    if os.path.exists(jp):
        with open(jp, "r") as fh:
            data = json.load(fh)
        data["status"] = "running"
        data["prompt"] = prompt
        data["start_time"] = now
    else:
        data = {
            "session_id": session_id,
            "project_path": cwd or os.getcwd(),
            "start_time": now,
            "prompt": prompt,
            "status": "running",
        }

    with open(jp, "w") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)

    print(f"[task] Initialised  session={session_id}  status=running", file=sys.stderr)


def cmd_status(session_id=None, cwd=None):
    """Print JSON status for *session_id*, or list records."""
    records_dir = get_records_dir(cwd)

    # ---- query a single session -------------------------------------------
    if session_id:
        jp = _json_path(records_dir, session_id)
        if not os.path.exists(jp):
            print("null")
            sys.exit(1)
        with open(jp) as fh:
            print(json.dumps(json.load(fh), indent=2, ensure_ascii=False))
        return

    # ---- list current project ---------------------------------------------
    if not os.path.isdir(records_dir):
        print("No task records found.", file=sys.stderr)
        return

    records = []
    for fn in sorted(os.listdir(records_dir)):
        if fn.endswith(".json"):
            with open(os.path.join(records_dir, fn)) as fh:
                records.append(json.load(fh))

    if not records:
        print("No task records found.", file=sys.stderr)
        return

    for r in records:
        st = r.get("status", "?")
        sid = r.get("session_id", "?")
        ts = r.get("start_time", "?")
        prompt = r.get("prompt", "")[:70]
        print(f"[{st}] {sid}  {ts}  {prompt}")


def cmd_list_all():
    """List records across every known project."""
    if not os.path.isdir(TASK_RECORDS_DIR):
        print("No task records found.", file=sys.stderr)
        return

    found = False
    for proj_dir in sorted(os.listdir(TASK_RECORDS_DIR)):
        proj_path = os.path.join(TASK_RECORDS_DIR, proj_dir)
        if not os.path.isdir(proj_path):
            continue
        json_files = sorted(
            f for f in os.listdir(proj_path) if f.endswith(".json")
        )
        if not json_files:
            continue

        found = True
        proj_label = proj_dir.replace("-", "/")
        if proj_label.startswith("/"):
            pass  # already absolute-looking
        else:
            proj_label = "/" + proj_label

        print(f"\n[{proj_label}]")
        for fn in json_files:
            with open(os.path.join(proj_path, fn)) as fh:
                d = json.load(fh)
            st = d.get("status", "?")
            sid = d.get("session_id", "?")
            ts = d.get("start_time", "?")
            prompt = d.get("prompt", "")[:70]
            print(f"  [{st}] {sid}  {ts}  {prompt}")

    if not found:
        print("No task records found.", file=sys.stderr)


def cmd_finish(session_id, summary, cwd=None):
    """Mark a task as 'finished' and write/append the markdown archive."""
    records_dir = get_records_dir(cwd)
    jp = _json_path(records_dir, session_id)

    if not os.path.exists(jp):
        print(
            f"[task] ERROR: no record for session {session_id}", file=sys.stderr
        )
        sys.exit(1)

    with open(jp) as fh:
        data = json.load(fh)

    now = _now()
    data["status"] = "finished"
    data["finish_time"] = now
    data["summary"] = summary

    with open(jp, "w") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)

    # ---- markdown archive -------------------------------------------------
    mp = _md_path(records_dir, session_id)
    entry = (
        f"# time: {data['start_time']}\n"
        f"- user-prompt\n"
        f"{data['prompt']}\n"
        f"- summary\n"
        f"{summary}\n"
    )

    if os.path.exists(mp):
        with open(mp, "a") as fh:
            fh.write("\n---\n")
            fh.write(entry)
    else:
        with open(mp, "w") as fh:
            fh.write(entry)

    print(f"[task] Finished  session={session_id}", file=sys.stderr)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        prog="task", description="Claude Code task-record manager"
    )
    sub = parser.add_subparsers(dest="command")

    # init
    p_init = sub.add_parser("init", help="Create / reset a task record")
    p_init.add_argument("-s", "--session-id", required=True)
    p_init.add_argument("-p", "--prompt", required=True)

    # status
    p_status = sub.add_parser("status", help="Query task status")
    # Accept  task status <session-id>  or  task status list
    p_status.add_argument(
        "arg", nargs="?", default=None, metavar="SESSION_ID|list"
    )
    p_status.add_argument("-s", "--session-id", default=None)

    # finish
    p_finish = sub.add_parser("finish", help="Mark a task as finished")
    p_finish.add_argument("-s", "--session-id", required=True)
    p_finish.add_argument("-m", "--summary", required=True)

    args = parser.parse_args()

    if args.command == "init":
        cmd_init(args.session_id, args.prompt)
    elif args.command == "status":
        if args.arg == "list":
            cmd_list_all()
        elif args.session_id:
            cmd_status(args.session_id)
        elif args.arg:
            cmd_status(args.arg)
        else:
            cmd_status()
    elif args.command == "finish":
        cmd_finish(args.session_id, args.summary)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
