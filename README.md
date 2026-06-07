# deepseek_cc_plugins

Claude Code 插件集合，针对 deepseek-v4-pro 模型优化。

## Task Tracker

防止模型在思考完成后意外中断，确保每个任务都能正常完成。

### 安装

```bash
cd your-project
bash task-tracker/install.sh
```

安装脚本会：
1. 将 hooks 配置写入 `.claude/settings.local.json`（项目级别）
2. 将 `task` 命令软链到 `~/.local/bin/task`（全局可用）
3. 创建 `~/.claude/task_records/` 数据目录

### 卸载

```bash
cd your-project
bash task-tracker/install.sh --uninstall
```

### task 命令

| 命令 | 说明 |
|------|------|
| `task init -s <id> -p <prompt>` | 创建/重置任务记录 |
| `task status -s <id>` | 查看单个任务状态 |
| `task status list` | 列出所有项目的任务 |
| `task finish -s <id> -m "<summary>"` | 标记完成，写入归档 |

### 工作原理

```
用户输入 prompt
  → UserPromptSubmit hook → task init (status=running)，注入完成提示
  → Claude 执行任务
  → Claude 尝试停止
  → Stop hook 检查 status
      ├─ finished → 允许退出
      └─ running  → 阻止退出，注入提示：执行 task finish
  → Claude 执行 task finish → 写入 .md 归档
  → 正常退出
```

### 文件结构

```
task-tracker/
├── scripts/task.py              # 核心命令
├── scripts/hook-up.py           # UserPromptSubmit hook
├── scripts/hook-stop.py         # Stop hook
├── bin/task                     # bash 包装器
├── statusline/project-status.js # 状态栏
├── hooks/hooks.json             # 插件 hooks 定义
├── .claude-plugin/plugin.json   # 插件清单
└── install.sh                   # 安装/卸载脚本
```
