# Task Tracker — Claude Code 插件

防止 deepseek-v4-pro 等模型在思考完成后意外中断，确保每个任务都能正常完成。

## 工作原理

```
用户输入 prompt
  │
  ▼
UserPromptSubmit hook ──► 记录任务 (task init)，status=running
  │                         注入提示：完成后执行 task finish
  │
  ▼
Claude 执行任务 ...
  │
  ▼
Claude 尝试停止
  │
  ▼
Stop hook ──► 检查 status
  │              ├─ finished → 允许退出
  │              └─ running  → 阻止退出，注入提示：请执行 task finish
  │
  ▼
Claude 执行 task finish → status=finished，写入 .md 归档
  │
  ▼
正常退出
```

## 安装

```bash
cd your-project
bash path/to/task-tracker/install.sh
```

安装脚本会做三件事：

1. 将 hooks 配置写入 `.claude/settings.local.json`（项目级别，不影响其他项目）
2. 将 `task` 命令软链到 `~/.local/bin/task`（全局可用）
3. 创建 `~/.claude/task_records/` 目录

## 卸载

```bash
cd your-project
bash path/to/task-tracker/install.sh --uninstall
```

会清理 hooks 配置、移除 `task` 软链，并询问是否删除 `~/.claude/task_records/`。

## task 命令

| 命令 | 说明 |
|------|------|
| `task init -s <id> -p <prompt>` | 创建/重置任务记录 |
| `task status -s <id>` | 查看单个任务 JSON 状态 |
| `task status list` | 列出所有项目的任务 |
| `task finish -s <id> -m "<summary>"` | 标记完成，写入 .md 归档 |

## 数据存储

```
~/.claude/task_records/
└── <project-namespace>/       # /Users/.../my-project → -Users-...-my-project
    ├── <session_id>.json      # 任务状态
    └── <session_id>.md        # 完成后的归档记录
```

## 文件结构

```
task-tracker/
├── .claude-plugin/plugin.json
├── bin/task                    # bash 包装器
├── scripts/
│   ├── task.py                 # 核心命令
│   ├── hook-up.py              # UserPromptSubmit hook
│   └── hook-stop.py            # Stop hook
├── hooks/hooks.json            # 插件 hooks（备用）
├── statusline/project-status.js
├── install.sh
└── README.md
```
