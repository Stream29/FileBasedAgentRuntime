# FileSystem-based Agent

一个基于文件系统的 AI Agent 开发框架，通过文件系统管理所有状态，无需传统对话历史。

## 架构设计

本项目采用 **Agent Runtime + Agent State** 的架构设计：

- **Agent Runtime**：提供基础的文件操作和命令行执行能力，是一个纯粹的工具提供者
- **Agent State**：所有 Agent 的状态、记忆、工作内容都保存在 `agent_root` 目录下
- **完全解耦**：Runtime 不关心 Agent 在做什么，只提供工具；Agent 通过文件系统自主管理状态

## 当前应用

Agent 当前被配置用于开发 Dify 的工具插件，`agent_root` 目录下已包含：
- 📚 **参考文档**：Dify 插件开发的完整文档
- 🔧 **代码示例**：多个插件实现示例（Google Calendar、HackerNews、SQLite 等）
- 📋 **开发指南**：最佳实践和发布指南

## 核心特性

- **无对话历史**：强制 Agent 将所有信息持久化到文件系统
- **Context Window 自管理**：Agent 自主决定保留什么信息
- **冷热数据分离**：自动归档历史到 storage
- **完全可观测**：所有操作都有详细日志记录
- **sync_context 机制**：优雅解决记忆更新的递归依赖问题
- **增量输出系统**：智能去重机制，保持详尽输出的同时避免重复内容，开发友好
- **异步架构**：高性能处理，支持并发操作
- **直接 API 调用**：使用官方 Anthropic SDK，获得更精细的控制
- **思考模式支持**：支持 Claude 的思考功能（需要 API 权限）
- **持久化 Shell 会话**：支持复合命令、管道、状态保持的真实 Shell 环境

## 系统架构

系统采用异步架构，直接调用 Anthropic API，完全移除了 LangChain 依赖，提供更好的性能和控制。

### 核心特性

- **完整目录树展示**：显示完整的文件系统结构，包含所有文件和目录，以及文件大小信息
- **智能文件命名**：归档文件使用描述性命名（如 `开发文件系统结构自动生成功能_20250808_1652.md`），Agent 无需打开文件就能理解内容
- **自动文件系统扫描**：每次生成 system message 时自动扫描并生成最新的目录结构
- **无需手动维护**：系统自动管理文件系统结构，Agent 可以专注于任务本身

### 项目结构

```
FileSystemBasedAgent/
├── src/                     # Runtime 源代码（工具提供者）
├── main.py                  # 主程序入口
├── logs/                    # 操作日志
└── agent_root/              # Agent 的完整状态（所有数据都在这里）
    ├── workspace/           # 工作空间（当前项目文件）
    ├── storage/             # 持久化存储
    │   ├── documents/       # 参考文档
    │   │   ├── plugins/     # Dify 插件开发文档
    │   │   ├── tools_summary.md
    │   │   └── available_tools_guide.md
    │   ├── few_shots/       # 代码示例
    │   │   ├── google_calendar/  # Google 日历插件
    │   │   ├── hackernews/      # HackerNews 插件
    │   │   ├── sqlite/          # SQLite 插件
    │   │   └── tools_usage_example.py
    │   └── history/         # 历史任务归档
    ├── guideline.md         # Agent 行为准则
    └── context_window_main.md # 当前工作记忆
```

**关键理念**：`agent_root` 是 Agent 的"大脑"，包含了它需要的所有知识、记忆和工作内容。Runtime 只是提供工具让 Agent 能够操作这个"大脑"。

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
# ANTHROPIC_MODEL=claude-3-5-sonnet-20241022   # 可选，选择不同的模型
```

方法二：设置环境变量
```bash
export ANTHROPIC_API_KEY=your_api_key_here
export ANTHROPIC_API_BASE=https://api.anthropic.com  # 可选
export ANTHROPIC_MODEL=claude-3-5-sonnet-20241022   # 可选
```

### 3. 运行 Agent

启动交互式模式：
```bash
# 方式一：直接运行 main.py
python main.py

# 方式二：使用 uv 运行（推荐，确保使用正确的环境）
uv run python main.py
```

## 使用示例

### 交互式会话
```
🤖 FileSystem-based Agent - 交互式模式
============================================================
• 输入任务描述，Agent 会执行并回复
• 输入 'exit' 或 'quit' 退出
• 输入 'clear' 清空对话历史
• 输入 'help' 查看可用命令
• 输入 'status' 查看当前 Agent 状态
• 按 Ctrl+C 可以中断当前任务
• 🚀 开发模式：显示详细输出，智能去重
============================================================

👤 You: 创建一个计算斐波那契数列的 Python 脚本

🤖 Agent: 我来创建一个计算斐波那契数列的 Python 脚本...

📄 create_file: fibonacci.py
✅ 文件创建成功

📖 读取文件: fibonacci.py [行 1-20]
✅ 读取到 15 行内容

文件已创建成功！我创建了 fibonacci.py，包含了一个递归实现的斐波那契函数...

👤 User: 运行这个脚本并显示前10个数

🤖 Agent: 执行脚本并显示结果...

🔧 执行命令: python fibonacci.py
✅ 命令完成 (退出码: 0)
输出:
   斐波那契数列前 10 个数:
   0, 1, 1, 2, 3, 5, 8, 13, 21, 34

👤 You: exit

👋 再见！
```

### 特殊命令
- `help` - 显示帮助信息
- `status` - 查看当前 context 状态和对话历史
- `clear` - 清空对话历史并重置 context
- `exit`/`quit` - 退出程序

## 工具说明

Agent 使用命令行优先的工具系统：

### 主要工具

1. **shell** - 持久化 Shell 会话（优先使用）
   - 支持所有标准命令：ls, cat, grep, sed, awk, python, git 等
   - 保持会话状态：别名、函数、变量、工作目录
   - 支持复合命令：`cd dir && ls`、管道、重定向
   - 自动处理交互式命令（检测并中断）

2. **edit_file** - 编辑文件特定行
   - 用于修改大文件的部分内容
   - 指定行号范围进行精确编辑

3. **create_file** - 创建新文件
   - 用于创建包含大量内容的文件

4. **sync_context** - 同步工作记忆
   - Agent 自主管理 context window
   - 决定保留哪些信息（热数据）和归档哪些（冷数据）

### 传统工具（向后兼容）

- `read_file(path, start_line?, end_line?)` - 读取文件
- `write_file(path, content)` - 写入文件
- `list_directory(path)` - 列出目录
- `execute_command(command, working_dir?)` - 执行命令

## Agent 能力与应用场景

### 当前能力

Agent 具备完整的软件开发能力：
- 📝 **文件操作**：创建、编辑、读取任意文件
- 🔧 **命令执行**：运行任何命令行工具（git、python、npm 等）
- 🧠 **记忆管理**：自主决定保留哪些信息，归档哪些历史
- 🔄 **状态保持**：通过持久化 Shell 会话保持完整的工作状态

### 适用场景

1. **插件开发**（当前应用）
   - 开发 Dify 工具插件
   - 参考已有示例和文档
   - 测试和调试插件功能

2. **代码生成与重构**
   - 根据需求生成完整项目
   - 重构现有代码
   - 添加测试用例

3. **自动化任务**
   - 批量文件处理
   - 代码分析和报告
   - 依赖管理和更新

4. **学习与实验**
   - 探索新技术栈
   - 创建概念验证
   - 编写技术文档

### 使用建议

1. **明确任务目标**：给 Agent 清晰的任务描述
2. **提供参考资料**：将相关文档放入 `storage/documents`
3. **定期检查进度**：查看 `workspace` 和 `context_window_main.md`
4. **保存重要成果**：Agent 会自动归档完成的任务

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

## 相关文档

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - 详细的架构设计说明
- **[DIFY_PLUGIN_DEVELOPMENT.md](DIFY_PLUGIN_DEVELOPMENT.md)** - Dify 插件开发指南
- **[PROJECT_STATUS.md](PROJECT_STATUS.md)** - 项目当前状态
- **[mvp_plan.md](mvp_plan.md)** - 技术实现细节和开发历程

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