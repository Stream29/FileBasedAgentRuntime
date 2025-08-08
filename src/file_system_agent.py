"""Core FileSystemAgent implementation without LangChain dependencies."""

from datetime import datetime
from pathlib import Path
from typing import Any

from .logger import OperationLogger
from .path_manager import PathManager
from .tools import ObservableTools


class FileSystemAgent:
    """基于文件系统的 Agent 实现"""

    def __init__(self, agent_id: str, context_file: str, project_root: Path):
        self.agent_id = agent_id
        self.context_file = context_file

        # 初始化组件
        self.path_manager = PathManager(project_root)
        self.logger = OperationLogger(project_root / "logs")
        self.tools = ObservableTools(self.logger, self.path_manager)

        # 对话历史（临时缓冲，直到 sync_context）
        self.conversation_history: list[dict[str, Any]] = []

        # 确保必要文件存在
        self._ensure_files_exist()

    def _ensure_files_exist(self) -> None:
        """确保 guideline.md 和 context_window.md 存在"""
        guideline_path = self.path_manager.agent_root / "guideline.md"
        context_path = self.path_manager.agent_root / self.context_file

        if not guideline_path.exists():
            guideline_path.write_text(self._get_default_guideline(), encoding="utf-8")

        if not context_path.exists():
            context_path.write_text(self._get_default_context(), encoding="utf-8")

    def execute_tool(self, tool_name: str, params: dict[str, Any]) -> Any:
        """执行工具调用"""
        # 记录工具调用
        self.conversation_history.append(
            {
                "type": "tool_call",
                "tool": tool_name,
                "params": params,
                "timestamp": datetime.now().isoformat(),
            }
        )

        # 工具映射
        tool_mapping = {
            "read_file": self.tools.read_file,
            "write_file": self.tools.write_file,
            "list_directory": self.tools.list_directory,
            "execute_command": self.tools.execute_command,
            "sync_context": self._sync_context,
        }

        if tool_name not in tool_mapping:
            raise ValueError(f"Unknown tool: {tool_name}")

        # 执行工具
        try:
            result = tool_mapping[tool_name](**params)

            # 记录结果
            self.conversation_history.append(
                {
                    "type": "tool_result",
                    "tool": tool_name,
                    "result": self._truncate_result(result),
                    "timestamp": datetime.now().isoformat(),
                }
            )

            return result

        except Exception as e:
            # 记录错误
            self.conversation_history.append(
                {
                    "type": "tool_error",
                    "tool": tool_name,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            )
            raise

    def _sync_context(self, new_context_content: str) -> dict[str, Any]:
        """同步对话历史到 context window - 由模型决定新的 context 内容"""
        try:
            # 保存旧的 context 作为备份（可选）
            context_path = self.path_manager.agent_root / self.context_file
            if context_path.exists():
                old_context = context_path.read_text(encoding="utf-8")
                # 可以选择归档旧的 context
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                archive_path = (
                    self.path_manager.agent_root / "storage" / "history" / f"context_{timestamp}.md"
                )
                archive_path.parent.mkdir(parents=True, exist_ok=True)
                archive_path.write_text(old_context, encoding="utf-8")

            # 写入新的 context
            context_path.write_text(new_context_content, encoding="utf-8")

            # 记录操作历史条数（用于返回信息）
            history_count = len(self.conversation_history)

            # 清空对话历史
            self.conversation_history = []

            # 记录操作
            self.logger.log_operation(
                "sync_context",
                {
                    "new_context_size": len(new_context_content),
                    "history_cleared": history_count,
                    "archive_path": str(archive_path) if "archive_path" in locals() else None,
                },
                "Context synchronized successfully",
            )

            return {
                "status": "success",
                "message": f"Context 已更新，清空了 {history_count} 条对话历史",
                "new_context_lines": len(new_context_content.splitlines()),
                "archive_path": str(archive_path.name) if "archive_path" in locals() else None,
            }

        except Exception as e:
            self.logger.log_operation("sync_context", {"error": str(e)}, None, str(e))
            raise

    def _truncate_result(self, result: Any) -> Any:
        """截断结果避免对话历史过大"""
        if isinstance(result, str) and len(result) > 500:
            return result[:500] + "... (truncated)"
        elif isinstance(result, dict):
            # 对字典进行递归截断
            truncated = {}
            for key, value in result.items():
                truncated[key] = self._truncate_result(value)
            return truncated
        elif isinstance(result, list) and len(str(result)) > 500:
            return f"[List with {len(result)} items]"
        return result

    def _get_default_guideline(self) -> str:
        """获取默认的 guideline 内容"""
        return """# Agent 行为准则

## 你的身份
你是一个基于文件系统的 AI Agent，所有记忆和状态都通过文件系统管理。

## 文件系统规范
你的文件系统结构：
```
/                           # 你认为的根目录
├── workspace/             # 工作区（创建项目文件）
├── storage/               # 存储区（归档历史）
│   ├── documents/        # 参考文档
│   ├── few_shots/        # 代码示例
│   └── history/          # 任务历史
├── guideline.md          # 行为准则（本文件）
└── context_window_main.md # 你的工作记忆
```

## 核心工作流程

1. **开始时**：你的记忆（context window）已自动加载
2. **执行中**：连续使用工具完成任务
3. **同步时**：每 3-5 个操作调用 sync_context 保存进展
4. **结束时**：确保调用 sync_context 保存最终状态

## 工具使用规范

### 文件操作
- `read_file(path, start_line?, end_line?)` - 读取文件内容
- `write_file(path, content)` - 写入文件（会覆盖）
- `list_directory(path)` - 列出目录内容

### 命令执行
- `execute_command(command, working_dir?)` - 执行 shell 命令
  - 默认工作目录: /workspace/
  - 支持常用命令: python, uv, git, npm 等

### 记忆同步
- `sync_context(new_context_content)` - 更新你的工作记忆
  - 你需要全量生成新的 context window 内容
  - 自己决定什么信息该保留，什么该归档
  - 保持 context 精简而完整

## 记忆管理准则

### Context Window 结构
你的 context_window_main.md 应该包含以下部分：
```markdown
# Current Task
[描述当前正在执行的任务]

# Working Memory
[关键信息、文件路径、重要发现等]

# Active Observations
[最近的重要观察结果]

# Next Steps
[下一步计划]
```

### 热数据（保留在 context）
- 当前任务状态和目标
- 关键文件路径和项目结构
- 重要的错误信息或发现
- 必要的上下文信息
- 下一步行动计划

### 冷数据（可归档或省略）
- 详细的命令输出（只保留关键结果）
- 中间调试信息
- 已解决的错误细节
- 大段的文件内容（只记录路径）
- 重复或冗余的信息

### 归档策略
当需要归档信息时，你可以：
1. 将详细内容写入 /storage/history/ 下的文件
2. 在 context 中只保留摘要和文件路径
3. 例如：`详细调试日志已保存至 /storage/history/debug_20240101.md`

## 最佳实践

1. **编程任务**
   - 先创建主文件
   - 使用 `uv add` 添加必要的依赖
   - 使用 `uv run` 执行测试验证功能
   - 处理错误并迭代

2. **文件组织**
   - 项目文件放在 /workspace/ 下
   - 可创建子目录组织复杂项目
   - 临时文件用完即删

3. **错误处理**
   - 遇到错误时分析原因
   - 尝试修复并重试
   - 必要时查看详细错误信息

## 安全约束

1. **路径限制**
   - 只在提供的目录结构内操作
   - 不使用 .. 进行路径遍历
   - 不访问系统目录（/etc, /usr 等）

2. **命令限制**
   - 不执行破坏性命令（rm -rf /, sudo 等）
   - 不修改系统配置
   - 不安装系统级软件包

3. **网络限制**
   - 可以下载公开资源
   - 不进行未授权的网络访问
   - 遵守 robots.txt 和使用条款

## 记住
- 你没有传统的对话历史，一切都通过文件系统持久化
- 通过 sync_context 主动管理你的记忆
- 保持专业、高效、安全的工作方式"""

    def _get_default_context(self) -> str:
        """获取默认的 context window 内容"""
        return """# Current Task
[等待任务]

# Working Memory
[空]

# Active Observations
[空]

# Next Steps
[等待指示]"""
