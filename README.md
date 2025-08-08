# FileSystem-based Agent

一个基于文件系统的 AI Agent，通过文件系统管理所有状态，无需传统对话历史。

## 核心特性

- **无对话历史**：强制 Agent 将所有信息持久化到文件系统
- **Context Window 自管理**：Agent 自主决定保留什么信息
- **冷热数据分离**：自动归档历史到 storage
- **完全可观测**：所有操作都有详细日志记录
- **sync_context 机制**：优雅解决记忆更新的递归依赖问题
- **流式响应**：实时输出文本和工具调用，提供更好的交互体验
- **异步架构**：高性能处理，支持并发操作
- **直接 API 调用**：使用官方 Anthropic SDK，获得更精细的控制
- **思考模式支持**：支持 Claude 的思考功能（需要 API 权限）

## 系统架构

系统采用异步架构，直接调用 Anthropic API，完全移除了 LangChain 依赖，提供更好的性能和控制。

### 文件结构

```
FileSystemBasedAgent/
├── agent_root/               # Agent 的工作目录
│   ├── workspace/           # 工作空间（热数据）
│   ├── storage/             # 存储空间（冷数据）
│   │   ├── documents/      # 参考文档
│   │   ├── few_shots/      # 代码示例
│   │   └── history/        # 任务历史记录
│   ├── guideline.md        # Agent 行为准则
│   └── context_window_main.md # 工作记忆
├── logs/                    # 操作日志
└── src/                     # 源代码
```

## 快速开始

### 1. 安装依赖

```bash
# 确保已安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装项目依赖
uv sync
```

### 2. 配置 API Key

方法一：使用 `.env` 文件（推荐）
```bash
# 复制示例文件
cp .env.example .env

# 编辑 .env 文件，填入你的 API Key
# ANTHROPIC_API_KEY=your_api_key_here
# ANTHROPIC_API_BASE=https://api.anthropic.com  # 可选，使用自定义 API 端点
```

方法二：设置环境变量
```bash
export ANTHROPIC_API_KEY=your_api_key_here
export ANTHROPIC_API_BASE=https://api.anthropic.com  # 可选
```

### 3. 运行 Agent

启动交互式模式：
```bash
# 方式一：直接运行模块
uv run python -m src.main

# 方式二：使用命令别名（需要先 uv sync）
uv run fsagent
```

## 使用示例

### 交互式会话
```
🤖 FileSystem-based Agent - 交互式模式 (异步版)
============================================================
• 输入任务描述，Agent 会执行并回复
• 输入 'exit' 或 'quit' 退出
• 输入 'clear' 清空对话历史
• 输入 'help' 查看帮助
• 按 Ctrl+C 可以中断当前任务
• 🚀 支持流式输出和更好的性能
============================================================

👤 You: 创建一个计算斐波那契数列的 Python 脚本

🤖 Agent: 我来创建一个计算斐波那契数列的 Python 脚本...
   🔧 使用工具: write_file ✓
   🔧 使用工具: read_file ✓

文件已创建成功！我创建了 fibonacci.py，包含了一个递归实现的斐波那契函数...

👤 You: 运行这个脚本并显示前10个数

🤖 Agent: 执行脚本并显示结果...
   🔧 使用工具: execute_command ✓

输出结果：
0 1 1 2 3 5 8 13 21 34

👤 You: exit

👋 再见！
```

### 特殊命令
- `help` - 显示帮助信息
- `status` - 查看当前 context 状态和对话历史
- `clear` - 清空对话历史并重置 context
- `exit`/`quit` - 退出程序

## 工具说明

Agent 可以使用以下工具：

- `read_file(path, start_line?, end_line?)` - 读取文件
- `write_file(path, content)` - 写入文件
- `list_directory(path)` - 列出目录
- `execute_command(command, working_dir?)` - 执行命令
- `sync_context()` - 同步记忆（重要！）

## 开发测试

运行基本功能测试：
```bash
uv run python test_basic.py
```

运行单元测试：
```bash
uv run pytest
```

## 核心创新

**sync_context 机制**：
- Agent 可以连续执行多个工具调用
- 调用 sync_context 时才将对话历史压缩到 context window
- 自动分离冷热数据，归档历史信息
- 解决了记忆更新的递归依赖问题

## 注意事项

1. Agent 的所有文件操作都限制在 `agent_root` 目录内
2. 不会执行危险命令（如 `rm -rf /`, `sudo` 等）
3. 每 3-5 个操作后会自动提醒 sync_context
4. 所有操作都有详细日志，便于调试和监控

## 开发指南

### 代码质量检查

项目使用 ruff 和 mypy 进行代码质量检查：

```bash
# 运行所有检查
make check
# 或
python check.py

# 自动修复代码风格问题
make format

# 单独运行 linting
make lint

# 单独运行类型检查
make type
```

### 开发工作流程

1. 修改代码前，确保所有检查通过
2. 修改代码后，运行 `make format` 格式化代码
3. 运行 `make check` 确保没有引入新问题
4. 提交代码前，再次运行所有检查

### Makefile 命令

```bash
make help     # 查看所有可用命令
make install  # 安装依赖
make check    # 运行所有代码检查
make format   # 自动格式化代码
make lint     # 运行 linting 检查
make type     # 运行类型检查
make run      # 运行 Agent
make clean    # 清理临时文件
```

## License

MIT