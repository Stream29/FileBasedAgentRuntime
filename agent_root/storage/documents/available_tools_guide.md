# FileSystem-based Agent 可用工具指南

## 工具概览

Agent 可以使用以下 5 个核心工具来完成各种任务：

1. **read_file** - 读取文件内容
2. **write_file** - 写入或创建文件
3. **list_directory** - 列出目录内容
4. **execute_command** - 执行 shell 命令
5. **sync_context** - 更新工作记忆

## 工具详细说明

### 1. read_file - 文件读取工具

**功能描述**：读取指定文件的内容，支持读取全文或指定行范围。

**参数说明**：
- `path` (必需，string): 要读取的文件路径（从 Agent 视角）
- `start_line` (可选，integer): 起始行号（1-indexed）
- `end_line` (可选，integer): 结束行号（包含）

**使用示例**：
```json
// 读取整个文件
{
  "path": "/workspace/main.py"
}

// 读取指定行范围
{
  "path": "/workspace/main.py",
  "start_line": 10,
  "end_line": 50
}
```

**返回结果**：文件内容的字符串

**注意事项**：
- 文件路径使用 Agent 视角（如 `/workspace/`），系统会自动映射到实际路径
- 大文件建议使用行范围读取以提高性能
- 支持 UTF-8 编码的文本文件

### 2. write_file - 文件写入工具

**功能描述**：写入内容到文件，如果文件不存在会自动创建，如果存在会覆盖原内容。

**参数说明**：
- `path` (必需，string): 目标文件路径（从 Agent 视角）
- `content` (必需，string): 要写入的内容

**使用示例**：
```json
{
  "path": "/workspace/hello.py",
  "content": "print('Hello, World!')\n"
}
```

**返回结果**：
```json
{
  "path": "/workspace/hello.py",
  "size": 24,  // 文件大小（字节）
  "lines": 2   // 行数
}
```

**注意事项**：
- 会自动创建不存在的父目录
- 总是覆盖原有内容，不支持追加模式
- 使用 UTF-8 编码保存

### 3. list_directory - 目录列表工具

**功能描述**：列出指定目录下的所有文件和子目录。

**参数说明**：
- `path` (必需，string): 目录路径（从 Agent 视角）

**使用示例**：
```json
{
  "path": "/workspace"
}
```

**返回结果**：
```json
[
  {
    "name": "main.py",
    "type": "file",
    "size": 1024  // 文件大小（字节）
  },
  {
    "name": "src",
    "type": "directory",
    "items": 5     // 子项数量
  }
]
```

**注意事项**：
- 结果按名称排序
- 目录会显示子项数量
- 不会递归列出子目录内容

### 4. execute_command - 命令执行工具

**功能描述**：执行 shell 命令，支持常用的开发工具和命令。

**参数说明**：
- `command` (必需，string): 要执行的 shell 命令
- `working_dir` (可选，string): 工作目录，默认为 `/workspace`

**使用示例**：
```json
// 执行 Python 脚本
{
  "command": "python main.py"
}

// 在特定目录执行命令
{
  "command": "uv add requests",
  "working_dir": "/workspace/my_project"
}
```

**返回结果**：
```json
{
  "command": "python main.py",
  "stdout": "Hello, World!\n",
  "stderr": "",
  "returncode": 0,
  "success": true
}
```

**支持的常用命令**：
- Python: `python`, `python3`, `pip`
- 包管理: `uv` (推荐), `npm`, `yarn`
- 版本控制: `git`
- 文件操作: `ls`, `cat`, `grep`, `find`
- 网络工具: `curl`, `wget`

**注意事项**：
- 命令有 5 分钟超时限制
- 使用 shell 模式，支持管道和重定向
- **不支持交互式命令**（会导致超时）
- 不支持 `sudo` 等需要权限的命令

**处理交互式命令的方法**：
1. **优先使用非交互参数**（推荐）：
   - `dify plugin init --quick --category tool --name my-tool`
   - `npm init -y`
   - `git clone --quiet url`
   - `apt-get install -y package`

2. **使用 echo 管道提供输入**：
   ```bash
   echo -e "1\nmy-plugin\nstream\nDescription\n" | dify plugin init
   ```

3. **使用 here document**：
   ```bash
   cat << EOF | interactive_command
   input1
   input2
   EOF
   ```

### 5. sync_context - 记忆同步工具

**功能描述**：更新 Agent 的工作记忆（context window），这是 Agent 管理其状态的核心机制。

**参数说明**：
- `new_context_content` (必需，string): 新的完整 context 内容

**使用示例**：
```json
{
  "new_context_content": "# Current Task\n正在开发一个 Flask Web 应用\n\n# Working Memory\n- 已创建 app.py 主文件\n- 安装了 flask 依赖\n- 设置了基本路由\n\n# Active Observations\n- 服务器在 5000 端口运行正常\n- 首页路由返回 'Hello, World!'\n\n# Next Steps\n- 添加用户认证功能\n- 创建数据库模型"
}
```

**返回结果**：
```json
{
  "status": "success",
  "message": "Context 已更新，清空了 5 条对话历史",
  "new_context_lines": 15,
  "archive_path": "开发Flask应用_20250108_1430.md"
}
```

**Context 结构规范**：
```markdown
# Current Task
[当前正在执行的任务描述]

# Working Memory
[关键信息、文件路径、重要发现等]

# Active Observations
[最近的重要观察结果]

# Next Steps
[下一步的计划]
```

**注意事项**：
- 需要提供完整的新 context 内容，不是增量更新
- Agent 自己决定保留哪些信息（热数据）和归档哪些信息（冷数据）
- 建议每 3-5 个操作后同步一次
- 保持 context 精简而完整，避免过度冗长

## 工具使用最佳实践

### 1. 文件操作流程
```
1. list_directory 查看目录结构
2. read_file 读取需要的文件
3. write_file 创建或修改文件
4. execute_command 运行测试
```

### 2. 开发工作流
```
1. 创建项目文件 (write_file)
2. 安装依赖 (execute_command: uv add)
3. 运行测试 (execute_command: python)
4. 同步进展 (sync_context)
```

### 3. 错误处理
- 遇到文件不存在：先 list_directory 确认路径
- 命令执行失败：检查 stderr 和 returncode
- 大文件处理：使用 read_file 的行范围功能

### 4. 性能优化
- 避免频繁读取大文件全文
- 批量操作后再调用 sync_context
- 使用 execute_command 的 working_dir 避免频繁 cd

## 路径映射说明

Agent 视角的路径会自动映射到实际文件系统：

| Agent 路径 | 实际路径 |
|-----------|---------|
| `/` | `{project_root}/agent_root/` |
| `/workspace/` | `{project_root}/agent_root/workspace/` |
| `/storage/` | `{project_root}/agent_root/storage/` |
| `/guideline.md` | `{project_root}/agent_root/guideline.md` |
| `/context_window_main.md` | `{project_root}/agent_root/context_window_main.md` |

## 安全限制

1. **路径限制**：只能在 agent_root 目录内操作
2. **命令限制**：不支持破坏性命令和系统级操作
3. **网络限制**：可以下载公开资源，但需遵守使用条款

## 工具调用日志

所有工具调用都会被记录到：
- 日志文件：`logs/agent.log`（JSONL 格式）
- 包含：操作类型、参数、结果、时间戳等信息

这些日志可用于审计、调试和分析 Agent 行为。