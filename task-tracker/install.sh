#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# install.sh  –  Install / uninstall the task-tracker plugin for Claude Code
#
# Usage:
#   bash install.sh              Install into the current project
#   bash install.sh --uninstall  Remove from the current project
# ---------------------------------------------------------------------------
set -euo pipefail

PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETTINGS_FILE="$(pwd)/.claude/settings.local.json"
TASK_RECORDS_DIR="$HOME/.claude/task_records"

# ---- helpers ---------------------------------------------------------------
bold()  { printf '\033[1m%s\033[0m'  "$1"; }
green() { printf '\033[32m%s\033[0m' "$1"; }
yellow(){ printf '\033[33m%s\033[0m' "$1"; }
red()   { printf '\033[31m%s\033[0m' "$1"; }

HOOK_UP_CMD="python3 ${PLUGIN_DIR}/scripts/hook-up.py"
HOOK_STOP_CMD="python3 ${PLUGIN_DIR}/scripts/hook-stop.py"
STATUSLINE_CMD="node ${PLUGIN_DIR}/statusline/project-status.js"

# ============================================================================
# install
# ============================================================================
do_install() {
    echo "================================================================="
    echo "  $(bold "Claude Code  Task Tracker  –  Installer")"
    echo "================================================================="
    echo "  Project : $(pwd)"
    echo "  Plugin  : $PLUGIN_DIR"
    echo "================================================================="

    # ---- 1. Make scripts executable ---------------------------------------
    echo ""
    echo "→ Making scripts executable …"
    chmod +x "$PLUGIN_DIR/bin/task"
    chmod +x "$PLUGIN_DIR/scripts/task.py"
    chmod +x "$PLUGIN_DIR/scripts/hook-up.py"
    chmod +x "$PLUGIN_DIR/scripts/hook-stop.py"
    chmod +x "$PLUGIN_DIR/statusline/project-status.js"
    echo "  $(green "Done.")"

    # ---- 2. Symlink task to user bin --------------------------------------
    echo ""
    echo "→ Registering 'task' command globally …"
    _symlink_task

    # ---- 3. Add hooks to project settings.local.json ----------------------
    echo ""
    echo "→ Registering hooks in .claude/settings.local.json …"
    _add_hooks

    # ---- 4. Add statusline to project settings.local.json -----------------
    echo ""
    echo "→ Registering statusline in .claude/settings.local.json …"
    _add_statusline

    # ---- 5. Create task-records root --------------------------------------
    mkdir -p "$TASK_RECORDS_DIR"
    echo "  $(green "✓")  Task records directory: ~/.claude/task_records/"

    # ---- Done --------------------------------------------------------------
    echo ""
    echo "================================================================="
    echo "  $(green "Installation complete!")"
    echo "================================================================="
    echo ""
    echo "Hooks active for: $(pwd)"
    echo "To install in another project, run this script from that directory."
    echo ""
}

# ============================================================================
# uninstall
# ============================================================================
do_uninstall() {
    echo "================================================================="
    echo "  $(bold "Claude Code  Task Tracker  –  Uninstaller")"
    echo "================================================================="
    echo "  Project : $(pwd)"
    echo "================================================================="

    # ---- 1. Remove hooks from settings.local.json -------------------------
    echo ""
    echo "→ Removing hooks from .claude/settings.local.json …"
    _remove_hooks

    # ---- 2. Remove statusline from settings.local.json --------------------
    echo ""
    echo "→ Removing statusline from .claude/settings.local.json …"
    _remove_statusline

    # ---- 3. Remove task symlink -------------------------------------------
    echo ""
    echo "→ Removing 'task' symlink …"
    _remove_symlink

    # ---- 4. Ask about task_records/ ---------------------------------------
    echo ""
    _cleanup_records

    # ---- Done --------------------------------------------------------------
    echo ""
    echo "================================================================="
    echo "  $(green "Uninstall complete!")"
    echo "================================================================="
    echo ""
}

# ============================================================================
# helpers – symlink
# ============================================================================
_symlink_task() {
    local target=""
    for candidate in "$HOME/.local/bin" "$HOME/bin" "/usr/local/bin"; do
        if echo "$PATH" | tr ':' '\n' | grep -Fxq "$candidate" 2>/dev/null; then
            if [ -w "$candidate" ] || [ -w "$(dirname "$candidate")" ]; then
                case "$candidate" in /usr/local/bin) continue ;; esac
                target="$candidate"
                break
            fi
        fi
    done
    if [ -z "$target" ]; then
        target="$HOME/.local/bin"
    fi
    mkdir -p "$target"

    local link="$target/task"
    if [ -L "$link" ] || [ -f "$link" ]; then
        echo "  $(yellow "⚠")  $link already exists — overwriting."
        rm -f "$link"
    fi
    ln -s "$PLUGIN_DIR/bin/task" "$link"
    echo "  $(green "✓")  task → $link"

    if ! echo "$PATH" | tr ':' '\n' | grep -Fxq "$target"; then
        echo "  $(yellow "⚠")  $target is NOT on PATH — add to ~/.zshrc:"
        echo "     export PATH=\"$target:\$PATH\""
    fi
}

_remove_symlink() {
    local found=0
    for candidate in "$HOME/.local/bin/task" "$HOME/bin/task" "/usr/local/bin/task"; do
        if [ -L "$candidate" ]; then
            local real="$(readlink "$candidate")"
            if [[ "$real" == *task-tracker* ]]; then
                rm -f "$candidate"
                echo "  $(green "✓")  Removed $candidate"
                found=1
            fi
        fi
    done
    if [ "$found" -eq 0 ]; then
        echo "  $(yellow "⚠")  No task symlink found."
    fi
}

# ============================================================================
# helpers – hooks (settings.local.json)
# ============================================================================
_add_hooks() {
    python3 -c "
import json, os, sys

sf = '${SETTINGS_FILE}'
up_cmd = '${HOOK_UP_CMD}'
stop_cmd = '${HOOK_STOP_CMD}'

# Load existing or create new
if os.path.exists(sf):
    with open(sf) as f:
        s = json.load(f)
else:
    s = {}
    os.makedirs(os.path.dirname(sf), exist_ok=True)

hooks = s.setdefault('hooks', {})

# --- UserPromptSubmit ---
ups = hooks.setdefault('UserPromptSubmit', [])
# Remove ALL old task-tracker entries (any path), then add fresh one
ups[:] = [e for e in ups if 'task-tracker' not in e.get('hooks', [{}])[0].get('command', '')]
ups_entry = {'matcher': '*', 'hooks': [{'type': 'command', 'command': up_cmd}]}
ups.append(ups_entry)

# --- Stop ---
stops = hooks.setdefault('Stop', [])
stops[:] = [e for e in stops if 'task-tracker' not in e.get('hooks', [{}])[0].get('command', '')]
stop_entry = {'matcher': '*', 'hooks': [{'type': 'command', 'command': stop_cmd}]}
stops.append(stop_entry)

with open(sf, 'w') as f:
    json.dump(s, f, indent=2, ensure_ascii=False)

print(f'  \033[32m✓\033[0m  Hooks written to {sf}')
for hook_name in ['UserPromptSubmit', 'Stop']:
    count = len(s['hooks'].get(hook_name, []))
    print(f'     {hook_name}: {count} handler(s)')
" 2>&1 || echo "  $(red "✗")  Failed to update settings.local.json"
}

_remove_hooks() {
    if [ ! -f "$SETTINGS_FILE" ]; then
        echo "  $(yellow "⚠")  No .claude/settings.local.json found — nothing to remove."
        return
    fi

    python3 -c "
import json, os, sys

sf = '${SETTINGS_FILE}'
up_cmd = '${HOOK_UP_CMD}'
stop_cmd = '${HOOK_STOP_CMD}'

with open(sf) as f:
    s = json.load(f)

hooks = s.get('hooks', {})
removed = 0

for key in ['UserPromptSubmit', 'Stop']:
    if key in hooks:
        before = len(hooks[key])
        hooks[key] = [e for e in hooks[key] if 'task-tracker' not in e.get('hooks', [{}])[0].get('command', '')]
        after = len(hooks[key])
        removed += (before - after)
        if not hooks[key]:
            del hooks[key]

# Clean up empty hooks
if 'hooks' in s and not s['hooks']:
    del s['hooks']

with open(sf, 'w') as f:
    json.dump(s, f, indent=2, ensure_ascii=False)

print(f'  \033[32m✓\033[0m  Removed {removed} hook(s) from {sf}')
" 2>&1 || echo "  $(red "✗")  Failed to update settings.local.json"
}

# ============================================================================
# helpers – statusline (settings.local.json)
# ============================================================================
_add_statusline() {
    python3 -c "
import json, os, sys

sf = '${SETTINGS_FILE}'
sl_cmd = '${STATUSLINE_CMD}'

if os.path.exists(sf):
    with open(sf) as f:
        s = json.load(f)
else:
    s = {}
    os.makedirs(os.path.dirname(sf), exist_ok=True)

s['statusLine'] = {'type': 'command', 'command': sl_cmd}

with open(sf, 'w') as f:
    json.dump(s, f, indent=2, ensure_ascii=False)

print(f'  \033[32m✓\033[0m  statusLine written to {sf}')
" 2>&1 || echo "  $(red "✗")  Failed to update settings.local.json"
}

_remove_statusline() {
    if [ ! -f "$SETTINGS_FILE" ]; then
        echo "  $(yellow "⚠")  No .claude/settings.local.json found."
        return
    fi

    python3 -c "
import json, os, sys

sf = '${SETTINGS_FILE}'

with open(sf) as f:
    s = json.load(f)

if 'statusLine' in s:
    del s['statusLine']
    with open(sf, 'w') as f:
        json.dump(s, f, indent=2, ensure_ascii=False)
    print(f'  \033[32m✓\033[0m  statusLine removed from {sf}')
else:
    print('  (no statusLine to remove)')
" 2>&1 || echo "  $(red "✗")  Failed to update settings.local.json"
}

# ============================================================================
# helpers – task_records cleanup
# ============================================================================
_cleanup_records() {
    if [ ! -d "$TASK_RECORDS_DIR" ]; then
        echo "  No task records directory found — skip."
        return
    fi

    local count
    count=$(find "$TASK_RECORDS_DIR" -type f 2>/dev/null | wc -l | tr -d ' ')
    echo "  Task records directory: ~/.claude/task_records/  ($count files)"

    # Non-interactive fallback
    if [ ! -t 0 ]; then
        echo "  (non-interactive — skipping cleanup, delete manually if needed)"
        return
    fi

    read -r -p "  Delete ~/.claude/task_records/ ? [Y/n] " REPLY
    case "${REPLY:-y}" in
        [Yy]*)
            rm -rf "$TASK_RECORDS_DIR"
            echo "  $(green "✓")  Deleted ~/.claude/task_records/"
            ;;
        *)
            echo "  $(yellow "⚠")  Kept ~/.claude/task_records/"
            ;;
    esac
}

# ============================================================================
# entry point
# ============================================================================
case "${1:-}" in
    --uninstall|-u)
        do_uninstall
        ;;
    *)
        do_install
        ;;
esac
