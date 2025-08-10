# 基于文件系统的 Agent MVP 实现方案

> **重要设计理念**：我们相信大模型的能力。sync_context 不是由代码自动实现冷热数据分离，而是让模型自己决定如何管理 context。模型需要全量生成新的 context window 内容，自主决定什么该保留（热数据）和什么该归档（冷数据）。我们只是提供工具和引导。

## 1. MVP 目标

验证核心理念：**文件系统即状态，无对话历史**

### 1.1 核心功能
- Agent 通过文件系统管理所有状态
- Context Window 作为 Agent 的工作记忆
- 通过 sync_context 机制解决记忆更新问题
- 所有操作可观测，便于开发调试

### 1.2 MVP 范围
- ✅ 基础文件操作（读写、列目录）
- ✅ 命令执行
- ✅ sync_context 同步机制
- ✅ 操作日志记录
- ❌ 子 Agent（后续迭代）
- ❌ Git 集成（后续迭代）
- ❌ API 接口（后续迭代）
- ❌ 容器化（后续迭代）

## 2. 系统架构

### 2.1 目录结构
```
FileSystemBasedAgent/           # 项目根目录
├── src/                       # 源代码
│   ├── __init__.py           # 包初始化
│   ├── file_system_agent.py  # Agent 文件系统核心功能
│   ├── async_agent.py        # 异步 Agent 运行时（直接调用 Anthropic API）
│   ├── async_main.py         # 异步交互式主程序
│   ├── config.py             # Agent 配置管理
│   ├── entities.py           # 数据结构定义
│   ├── tools.py              # 工具实现
│   ├── logger.py             # 操作日志
│   ├── path_manager.py       # 路径管理
│   └── main.py               # 入口程序（重定向到 async_main）
├── agent_root/               # Agent 的工作目录
│   ├── workspace/            # 工作空间（热数据）
│   ├── storage/              # 存储空间（冷数据）
│   │   ├── documents/        # 参考文档
│   │   ├── few_shots/        # 示例代码
│   │   └── history/          # 任务历史记录
│   ├── guideline.md          # Agent 行为准则
│   └── context_window_main.md # 工作记忆
├── logs/                     # 操作日志
├── tests/                    # 测试代码
├── pyproject.toml           # uv 项目配置
├── uv.lock                  # 锁定的依赖版本
└── .venv/                   # uv 虚拟环境
```

### 2.2 工具系统

只实现最基础的工具：

1. **文件操作**
   - `read_file(path, start_line=None, end_line=None)`
   - `write_file(path, content)`
   - `list_directory(path)`

2. **命令执行**
   - `execute_command(command, working_dir=None)`

3. **记忆同步**
   - `sync_context()` - 核心创新点

## 3. 核心实现

### 3.1 路径管理器
```python
from pathlib import Path

class PathManager:
    """管理 Agent 的文件系统路径"""
    
    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.agent_root = self.project_root / "agent_root"
        self.agent_root.mkdir(parents=True, exist_ok=True)
        
        # 创建基础目录结构
        self.workspace = self.agent_root / "workspace"
        self.storage = self.agent_root / "storage"
        
        # 创建子目录
        directories = [
            self.workspace,
            self.storage / "documents",
            self.storage / "few_shots", 
            self.storage / "history",
        ]
        
        for dir_path in directories:
            dir_path.mkdir(parents=True, exist_ok=True)
            
    def resolve_agent_path(self, agent_path: str) -> Path:
        """将 Agent 视角的路径转换为实际路径"""
        # Agent 认为 /workspace 是根目录下的
        if agent_path.startswith("/"):
            return self.agent_root / agent_path.lstrip("/")
        else:
            # 相对路径默认相对于 workspace
            return self.workspace / agent_path
```

### 3.2 操作日志系统
```python
import json
import logging
from datetime import datetime

class OperationLogger:
    """记录所有 Agent 操作，确保可观测性"""
    
    def __init__(self, log_dir: Path):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 操作日志文件（JSONL 格式）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.operation_log = self.log_dir / f"operations_{timestamp}.jsonl"
        
        # 配置标准日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_dir / 'agent.log'),
                logging.StreamHandler()  # 同时输出到控制台
            ]
        )
        self.logger = logging.getLogger('FileSystemAgent')
        
    def log_operation(self, operation_type: str, params: dict, 
                     result: any = None, error: str = None):
        """记录一次操作"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'operation': operation_type,
            'params': params,
            'result': self._serialize_result(result),
            'error': error,
            'success': error is None
        }
        
        # 写入 JSONL
        with open(self.operation_log, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
            
        # 同时记录到标准日志
        if error:
            self.logger.error(f"{operation_type} failed: {error}")
        else:
            self.logger.info(f"{operation_type} completed")
            
    def _serialize_result(self, result):
        """序列化结果，处理不可JSON序列化的对象"""
        if result is None:
            return None
        elif isinstance(result, (str, int, float, bool, list, dict)):
            return result
        else:
            return str(result)
```

### 3.3 工具实现
```python
import subprocess
import shlex
from typing import Optional, List, Dict

class ObservableTools:
    """提供基础工具，所有操作都被记录"""
    
    def __init__(self, logger: OperationLogger, path_manager: PathManager):
        self.logger = logger
        self.path_manager = path_manager
        
    def read_file(self, file_path: str, 
                  start_line: Optional[int] = None,
                  end_line: Optional[int] = None) -> str:
        """读取文件内容"""
        try:
            resolved_path = self.path_manager.resolve_agent_path(file_path)
            
            with open(resolved_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # 处理行范围
            if start_line is not None and end_line is not None:
                # 转换为 0-indexed
                start_idx = max(0, start_line - 1)
                end_idx = min(len(lines), end_line)
                result = ''.join(lines[start_idx:end_idx])
            else:
                result = ''.join(lines)
                
            self.logger.log_operation('read_file', {
                'file_path': file_path,
                'start_line': start_line,
                'end_line': end_line,
                'resolved_path': str(resolved_path),
                'size': len(result)
            }, f"Read {len(result)} characters")
            
            return result
            
        except Exception as e:
            self.logger.log_operation('read_file', 
                                    {'file_path': file_path}, 
                                    None, str(e))
            raise
            
    def write_file(self, file_path: str, content: str) -> Dict[str, any]:
        """写入文件（覆盖）"""
        try:
            resolved_path = self.path_manager.resolve_agent_path(file_path)
            
            # 确保父目录存在
            resolved_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入文件
            with open(resolved_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            result = {
                'path': file_path,
                'size': len(content),
                'lines': content.count('\n') + 1
            }
            
            self.logger.log_operation('write_file', {
                'file_path': file_path,
                'content_size': len(content)
            }, result)
            
            return result
            
        except Exception as e:
            self.logger.log_operation('write_file',
                                    {'file_path': file_path},
                                    None, str(e))
            raise
            
    def list_directory(self, dir_path: str) -> List[Dict[str, any]]:
        """列出目录内容"""
        try:
            resolved_path = self.path_manager.resolve_agent_path(dir_path)
            
            if not resolved_path.is_dir():
                raise NotADirectoryError(f"{dir_path} is not a directory")
                
            items = []
            for item in sorted(resolved_path.iterdir()):
                items.append({
                    'name': item.name,
                    'type': 'directory' if item.is_dir() else 'file',
                    'size': item.stat().st_size if item.is_file() else None
                })
                
            self.logger.log_operation('list_directory', {
                'dir_path': dir_path
            }, f"Found {len(items)} items")
            
            return items
            
        except Exception as e:
            self.logger.log_operation('list_directory',
                                    {'dir_path': dir_path},
                                    None, str(e))
            raise
            
    def execute_command(self, command: str, 
                       working_dir: Optional[str] = None) -> Dict[str, any]:
        """执行 shell 命令"""
        try:
            # 解析工作目录
            if working_dir:
                cwd = self.path_manager.resolve_agent_path(working_dir)
            else:
                cwd = self.path_manager.workspace
                
            self.logger.logger.info(f"Executing: {command}")
            self.logger.logger.info(f"Working dir: {cwd}")
            
            # 执行命令
            result = subprocess.run(
                shlex.split(command),
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            output = {
                'command': command,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode,
                'success': result.returncode == 0
            }
            
            self.logger.log_operation('execute_command', {
                'command': command,
                'working_dir': working_dir
            }, {
                # 只记录部分输出避免日志过大
                'stdout_preview': result.stdout[:500],
                'stderr_preview': result.stderr[:500],
                'returncode': result.returncode
            })
            
            return output
            
        except subprocess.TimeoutExpired:
            error = "Command timed out after 5 minutes"
            self.logger.log_operation('execute_command',
                                    {'command': command},
                                    None, error)
            raise TimeoutError(error)
        except Exception as e:
            self.logger.log_operation('execute_command',
                                    {'command': command},
                                    None, str(e))
            raise
```

### 3.4 Agent 基类
```python
from typing import Dict, Any, List
from datetime import datetime

class FileSystemAgent:
    """基于文件系统的 Agent 实现"""
    
    def __init__(self, agent_id: str, context_file: str, project_root: Path):
        self.agent_id = agent_id
        self.context_file = context_file
        
        # 初始化组件
        self.path_manager = PathManager(project_root)
        self.logger = OperationLogger(project_root / "logs")
        self.tools = ObservableTools(self.logger, self.path_manager)
        self.context_sync = ContextSynchronizer(
            self.path_manager.agent_root, 
            self.logger
        )
        
        # 对话历史（临时缓冲，直到 sync_context）
        self.conversation_history: List[Dict[str, Any]] = []
        
        # 确保必要文件存在
        self._ensure_files_exist()
        
    def _ensure_files_exist(self):
        """确保 guideline.md 和 context_window.md 存在"""
        guideline_path = self.path_manager.agent_root / "guideline.md"
        context_path = self.path_manager.agent_root / self.context_file
        
        if not guideline_path.exists():
            guideline_path.write_text(self._get_default_guideline())
            
        if not context_path.exists():
            context_path.write_text(self._get_default_context())
            
    def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """执行工具调用"""
        # 记录到对话历史
        self.conversation_history.append({
            'type': 'tool_call',
            'tool': tool_name,
            'params': params,
            'timestamp': datetime.now().isoformat()
        })
        
        # 工具映射
        tool_mapping = {
            'read_file': self.tools.read_file,
            'write_file': self.tools.write_file,
            'list_directory': self.tools.list_directory,
            'execute_command': self.tools.execute_command,
            'sync_context': self._sync_context
        }
        
        if tool_name not in tool_mapping:
            raise ValueError(f"Unknown tool: {tool_name}")
            
        # 执行工具
        try:
            result = tool_mapping[tool_name](**params)
            
            # 记录结果
            self.conversation_history.append({
                'type': 'tool_result',
                'tool': tool_name,
                'result': self._truncate_result(result),
                'timestamp': datetime.now().isoformat()
            })
            
            return result
            
        except Exception as e:
            # 记录错误
            self.conversation_history.append({
                'type': 'tool_error',
                'tool': tool_name,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            raise
            
    def _sync_context(self, new_context_content: str) -> Dict[str, Any]:
        """同步对话历史到 context window - 由模型决定新的 context 内容"""
        # 保存新的 context（模型全量生成的）
        context_path = self.path_manager.agent_root / self.context_file
        context_path.write_text(new_context_content, encoding='utf-8')
        
        # 记录并清空对话历史
        history_count = len(self.conversation_history)
        self.conversation_history = []
        
        return {
            'status': 'success',
            'message': f'Context 已更新，清空了 {history_count} 条对话历史',
            'new_context_lines': len(new_context_content.splitlines())
        }
        
    def _truncate_result(self, result: Any) -> Any:
        """截断结果避免对话历史过大"""
        if isinstance(result, str) and len(result) > 500:
            return result[:500] + "... (truncated)"
        elif isinstance(result, dict):
            # 对字典递归处理
            return {k: self._truncate_result(v) for k, v in result.items()}
        else:
            return result
            
    def _get_default_guideline(self) -> str:
        """默认的 guideline 内容"""
        return """# Agent 行为准则

## 文件系统规范
你的文件系统结构：
- /workspace/ - 工作区，创建和修改文件
- /storage/ - 存储区，归档历史信息
- /guideline.md - 行为准则（本文件）
- /context_window_main.md - 你的工作记忆

## 核心原则
1. 你的记忆（context window）会在对话开始时自动加载
2. 执行 3-5 个相关操作后，调用 sync_context 保存进展
3. 保持记忆精简，详细信息归档到 /storage/history/
4. 所有任务相关文件在 /workspace/ 下操作

## 工具使用
- read_file(path, start_line?, end_line?) - 读取文件
- write_file(path, content) - 写入文件
- list_directory(path) - 列出目录
- execute_command(command, working_dir?) - 执行命令
- sync_context() - 同步记忆（重要！）

## 安全约束
- 不访问项目目录之外的文件
- 不执行危险命令（rm -rf /, sudo 等）
- 优先使用相对路径
"""
        
    def _get_default_context(self) -> str:
        """默认的 context window 模板"""
        return """# Current Task
[等待任务]

# Working Memory
[空]

# Active Observations  
[空]

# Next Steps
[等待指示]
"""
```

### 3.5 Context 同步机制
```python
import re
from typing import List, Dict, Tuple, Optional

class ContextSynchronizer:
    """负责对话历史和 context window 的智能同步"""
    
    def __init__(self, agent_root: Path, logger: OperationLogger):
        self.agent_root = Path(agent_root)
        self.logger = logger
        self.context_file = self.agent_root / "context_window_main.md"
        self.history_dir = self.agent_root / "storage" / "history"
        self.history_dir.mkdir(parents=True, exist_ok=True)
        
    def sync_context(self, conversation_history: List[Dict], 
                    current_context: str) -> Dict[str, Any]:
        """
        智能同步：分析对话历史，更新 context，归档冷数据
        """
        try:
            # 1. 分析对话历史，分离冷热数据
            hot_data, cold_data = self._analyze_conversation(conversation_history)
            
            # 2. 归档冷数据
            archive_path = None
            if cold_data:
                archive_path = self._archive_cold_data(cold_data)
                
            # 3. 解析当前 context 结构
            context_sections = self._parse_context(current_context)
            
            # 4. 更新各个部分
            updated_sections = self._update_context_sections(
                context_sections, 
                hot_data,
                archive_path
            )
            
            # 5. 重组并写入新 context
            new_context = self._format_context(updated_sections)
            self.context_file.write_text(new_context, encoding='utf-8')
            
            # 6. 记录同步操作
            self.logger.log_operation('sync_context', {
                'history_items': len(conversation_history),
                'hot_data_items': len(hot_data),
                'cold_data_archived': bool(cold_data),
                'archive_path': str(archive_path) if archive_path else None,
                'context_size': len(new_context)
            }, "Context synchronized successfully")
            
            return {
                'status': 'success',
                'hot_data_items': len(hot_data),
                'cold_data_archived': bool(cold_data),
                'archive_path': str(archive_path) if archive_path else None,
                'new_context_lines': len(new_context.split('\n'))
            }
            
        except Exception as e:
            self.logger.log_operation('sync_context', {}, None, str(e))
            raise
            
    def _analyze_conversation(self, history: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """分析对话历史，分离冷热数据"""
        hot_data = []
        cold_data = []
        
        for item in history:
            # 工具调用和结果的分类逻辑
            if item['type'] == 'tool_call':
                tool = item['tool']
                
                # sync_context 调用本身不记录
                if tool == 'sync_context':
                    continue
                    
                # 文件创建/修改是热数据
                if tool in ['write_file', 'execute_command']:
                    hot_data.append(item)
                else:
                    cold_data.append(item)
                    
            elif item['type'] == 'tool_result':
                # 重要结果保留为热数据
                if self._is_important_result(item):
                    hot_data.append(item)
                else:
                    cold_data.append(item)
                    
            elif item['type'] == 'tool_error':
                # 错误信息都是热数据
                hot_data.append(item)
                
        return hot_data, cold_data
        
    def _is_important_result(self, item: Dict) -> bool:
        """判断结果是否重要（应保留在热数据中）"""
        # 文件操作结果
        if item.get('tool') in ['write_file', 'list_directory']:
            return True
            
        # 命令执行的错误
        if item.get('tool') == 'execute_command':
            result = item.get('result', {})
            if isinstance(result, dict) and not result.get('success', True):
                return True
                
        # 其他都归档
        return False
        
    def _archive_cold_data(self, cold_data: List[Dict]) -> Path:
        """归档冷数据到 storage/history/"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_file = self.history_dir / f"session_{timestamp}.md"
        
        # 格式化归档内容
        content = f"# Session History - {timestamp}\n\n"
        
        for item in cold_data:
            content += f"## {item['timestamp']} - {item['type']}\n"
            
            if item['type'] == 'tool_call':
                content += f"**Tool**: {item['tool']}\n"
                content += f"**Params**: {json.dumps(item['params'], indent=2)}\n"
                
            elif item['type'] == 'tool_result':
                content += f"**Tool**: {item['tool']}\n"
                content += f"**Result**: {item.get('result', 'N/A')}\n"
                
            content += "\n---\n\n"
            
        archive_file.write_text(content, encoding='utf-8')
        return archive_file
        
    def _parse_context(self, context: str) -> Dict[str, str]:
        """解析 context window 的各个部分"""
        sections = {
            'current_task': '',
            'working_memory': '',
            'active_observations': '',
            'next_steps': ''
        }
        
        # 使用正则表达式解析各部分
        patterns = {
            'current_task': r'# Current Task\s*\n(.*?)(?=\n#|$)',
            'working_memory': r'# Working Memory\s*\n(.*?)(?=\n#|$)',
            'active_observations': r'# Active Observations\s*\n(.*?)(?=\n#|$)',
            'next_steps': r'# Next Steps\s*\n(.*?)(?=\n#|$)'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, context, re.DOTALL)
            if match:
                sections[key] = match.group(1).strip()
                
        return sections
        
    def _update_context_sections(self, sections: Dict[str, str], 
                               hot_data: List[Dict],
                               archive_path: Optional[Path]) -> Dict[str, str]:
        """基于热数据更新 context 各部分"""
        # 提取关键信息
        recent_files = []
        recent_commands = []
        recent_errors = []
        
        for item in hot_data:
            if item['type'] == 'tool_call':
                if item['tool'] == 'write_file':
                    recent_files.append(item['params']['file_path'])
                elif item['tool'] == 'execute_command':
                    recent_commands.append(item['params']['command'])
                    
            elif item['type'] == 'tool_error':
                recent_errors.append(f"{item['tool']}: {item['error']}")
                
        # 更新 working memory
        memory_items = []
        if recent_files:
            memory_items.append(f"- 最近创建/修改的文件: {', '.join(recent_files)}")
        if recent_commands:
            memory_items.append(f"- 最近执行的命令: {len(recent_commands)} 个")
        if archive_path:
            memory_items.append(f"- 详细历史已归档: {archive_path.name}")
            
        sections['working_memory'] = '\n'.join(memory_items) if memory_items else sections['working_memory']
        
        # 更新 active observations
        obs_items = []
        if recent_errors:
            obs_items.append("- 遇到错误，需要处理:")
            for error in recent_errors[-3:]:  # 只保留最近3个错误
                obs_items.append(f"  - {error}")
                
        # 检查最后的命令执行结果
        for item in reversed(hot_data):
            if item['type'] == 'tool_result' and item['tool'] == 'execute_command':
                result = item.get('result', {})
                if isinstance(result, dict):
                    if result.get('success'):
                        obs_items.append(f"- 命令执行成功")
                    else:
                        obs_items.append(f"- 命令执行失败: {result.get('stderr', '')[:100]}")
                break
                
        if obs_items:
            sections['active_observations'] = '\n'.join(obs_items)
            
        return sections
        
    def _format_context(self, sections: Dict[str, str]) -> str:
        """格式化 context window 内容"""
        return f"""# Current Task
{sections['current_task']}

# Working Memory
{sections['working_memory']}

# Active Observations
{sections['active_observations']}

# Next Steps
{sections['next_steps']}
"""
```

### 3.6 运行时实现
```python
from typing import List, Dict, Any, Optional
import openai  # 或 anthropic

class AgentRuntime:
    """Agent 运行时，负责与 LLM 交互和工具调用协调"""
    
    def __init__(self, project_root: Path, llm_provider: str = "openai", api_key: str = None):
        self.project_root = Path(project_root)
        self.agent = FileSystemAgent("main", "context_window_main.md", project_root)
        self.llm_provider = llm_provider
        self.api_key = api_key or os.getenv(f"{llm_provider.upper()}_API_KEY")
        
        # 配置 LLM
        if llm_provider == "openai":
            openai.api_key = self.api_key
            self.model = "gpt-4"  # 或 gpt-3.5-turbo
        # 可扩展支持其他 LLM
        
    def run(self, user_input: str) -> str:
        """执行用户请求"""
        # 1. 加载 guideline 和 context
        guideline = self._load_guideline()
        context = self._load_context()
        
        # 2. 获取目录结构
        workspace_structure = self._get_directory_structure()
        
        # 3. 构建系统提示
        system_prompt = self._build_system_prompt(guideline, context, workspace_structure)
        
        # 4. 进入对话循环
        return self._conversation_loop(system_prompt, user_input)
        
    def _load_guideline(self) -> str:
        """加载 guideline.md"""
        guideline_path = self.agent.path_manager.agent_root / "guideline.md"
        if guideline_path.exists():
            return guideline_path.read_text(encoding='utf-8')
        else:
            # 使用默认 guideline
            return self.agent._get_default_guideline()
            
    def _load_context(self) -> str:
        """加载 context window"""
        context_path = self.agent.path_manager.agent_root / self.agent.context_file
        if context_path.exists():
            return context_path.read_text(encoding='utf-8')
        else:
            return self.agent._get_default_context()
            
    def _get_directory_structure(self) -> str:
        """获取当前目录结构的字符串表示"""
        workspace = self.agent.path_manager.workspace
        storage = self.agent.path_manager.storage
        
        structure = "当前文件系统结构:\n"
        structure += "```\n"
        structure += "/\n"
        structure += "├── workspace/\n"
        
        # 列出 workspace 内容
        for item in sorted(workspace.iterdir()):
            if item.is_file():
                structure += f"│   └── {item.name}\n"
            else:
                structure += f"│   └── {item.name}/\n"
                
        structure += "├── storage/\n"
        structure += "│   ├── documents/\n"
        structure += "│   ├── few_shots/\n"
        structure += "│   └── history/\n"
        
        # 统计历史文件数量
        history_count = len(list((storage / "history").glob("*.md")))
        if history_count > 0:
            structure += f"│       └── ({history_count} 个归档文件)\n"
            
        structure += "├── guideline.md\n"
        structure += "└── context_window_main.md\n"
        structure += "```"
        
        return structure
        
    def _build_system_prompt(self, guideline: str, context: str, structure: str) -> str:
        """构建系统提示"""
        return f"""# 你的身份和能力
你是一个基于文件系统的 AI Agent。你的所有记忆和状态都通过文件系统管理。

# 你的行为准则
{guideline}

# 你的当前记忆
{context}

# {structure}

# 重要提醒
1. 这是你的工作记忆，已经自动加载，无需再次读取
2. 可以连续执行多个工具，然后调用 sync_context 保存进展
3. 每 3-5 个操作后同步一次，避免丢失重要信息
4. 保持 context 精简，详细信息及时归档

# 工具调用格式
使用以下 JSON 格式调用工具：
{{
    "tool": "tool_name",
    "params": {{
        "param1": "value1",
        "param2": "value2"
    }}
}}
"""
        
    def _conversation_loop(self, system_prompt: str, initial_input: str) -> str:
        """对话循环，支持多轮交互直到 sync_context"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": initial_input}
        ]
        
        max_rounds = 10  # 防止无限循环
        final_response = ""
        
        for round_num in range(max_rounds):
            # 1. 调用 LLM
            response = self._call_llm(messages)
            final_response = response  # 保存最后的响应
            
            # 2. 解析工具调用
            tool_calls = self._parse_tool_calls(response)
            
            if not tool_calls:
                # 没有工具调用，对话结束
                break
                
            # 3. 执行工具调用
            tool_results = []
            sync_called = False
            
            for tool_call in tool_calls:
                try:
                    result = self.agent.execute_tool(
                        tool_call['tool'],
                        tool_call['params']
                    )
                    tool_results.append({
                        'tool': tool_call['tool'],
                        'success': True,
                        'result': result
                    })
                    
                    if tool_call['tool'] == 'sync_context':
                        sync_called = True
                        
                except Exception as e:
                    tool_results.append({
                        'tool': tool_call['tool'],
                        'success': False,
                        'error': str(e)
                    })
                    
            # 4. 构建工具结果消息
            tool_message = self._format_tool_results(tool_results)
            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "user", "content": tool_message})
            
            # 5. 如果调用了 sync_context，重新加载 context
            if sync_called:
                new_context = self._load_context()
                # 更新 system prompt 中的 context 部分
                system_prompt = self._update_context_in_prompt(system_prompt, new_context)
                messages[0]['content'] = system_prompt
                
                # 询问是否继续
                messages.append({
                    "role": "user", 
                    "content": "Context 已同步。是否需要继续执行其他任务？"
                })
                
        # 如果超过最大轮数，强制同步
        if round_num >= max_rounds - 1 and not sync_called:
            self.agent.execute_tool('sync_context', {})
            final_response += "\n\n[系统提示：已自动执行 sync_context 保存进展]"
            
        return final_response
        
    def _call_llm(self, messages: List[Dict[str, str]]) -> str:
        """调用 LLM API"""
        if self.llm_provider == "openai":
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )
            return response.choices[0].message.content
        else:
            raise NotImplementedError(f"LLM provider {self.llm_provider} not implemented")
            
    def _parse_tool_calls(self, response: str) -> List[Dict[str, Any]]:
        """从 LLM 响应中解析工具调用"""
        import json
        import re
        
        tool_calls = []
        
        # 查找 JSON 格式的工具调用
        json_pattern = r'\{[^{}]*"tool"[^{}]*\}'
        matches = re.findall(json_pattern, response, re.DOTALL)
        
        for match in matches:
            try:
                tool_call = json.loads(match)
                if 'tool' in tool_call and 'params' in tool_call:
                    tool_calls.append(tool_call)
            except json.JSONDecodeError:
                continue
                
        return tool_calls
        
    def _format_tool_results(self, results: List[Dict[str, Any]]) -> str:
        """格式化工具执行结果"""
        formatted = "工具执行结果:\n\n"
        
        for result in results:
            tool_name = result['tool']
            if result['success']:
                formatted += f"✓ {tool_name} 执行成功\n"
                # 格式化不同工具的结果
                if tool_name == 'write_file':
                    formatted += f"  文件已写入: {result['result']['path']}\n"
                elif tool_name == 'execute_command':
                    res = result['result']
                    formatted += f"  返回码: {res['returncode']}\n"
                    if res['stdout']:
                        formatted += f"  输出: {res['stdout'][:200]}...\n"
                    if res['stderr']:
                        formatted += f"  错误: {res['stderr'][:200]}...\n"
                elif tool_name == 'sync_context':
                    formatted += f"  Context 已同步，归档: {result['result'].get('archive_path', 'N/A')}\n"
            else:
                formatted += f"✗ {tool_name} 执行失败: {result['error']}\n"
                
            formatted += "\n"
            
        return formatted
        
    def _update_context_in_prompt(self, prompt: str, new_context: str) -> str:
        """更新 prompt 中的 context 部分"""
        # 使用正则表达式替换 context 部分
        pattern = r'(# 你的当前记忆\n)(.*?)(\n\n#)'
        replacement = f'\\1{new_context}\\3'
        return re.sub(pattern, replacement, prompt, flags=re.DOTALL)
```

### 3.7 入口程序
```python
# src/main.py
import argparse
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description='FileSystem-based Agent')
    parser.add_argument('task', help='Task description for the agent')
    parser.add_argument('--project-root', default='.', help='Project root directory')
    parser.add_argument('--llm-provider', default='openai', choices=['openai', 'anthropic'])
    parser.add_argument('--api-key', help='API key for LLM provider')
    parser.add_argument('--model', default='gpt-4', help='Model to use')
    
    args = parser.parse_args()
    
    # 初始化运行时
    from agent import AgentRuntime
    
    runtime = AgentRuntime(
        project_root=Path(args.project_root),
        llm_provider=args.llm_provider,
        api_key=args.api_key
    )
    
    if args.model:
        runtime.model = args.model
    
    try:
        # 执行任务
        print(f"🤖 Agent 开始执行任务: {args.task}\n")
        response = runtime.run(args.task)
        print(f"\n✅ 任务完成:\n{response}")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断执行")
        # 强制同步未保存的进展
        try:
            runtime.agent.execute_tool('sync_context', {})
            print("✓ Context 已自动保存")
        except:
            pass
            
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

## 4. 错误处理和边界情况

### 4.1 错误处理策略

1. **工具执行错误**
   - 所有异常都被捕获并记录到对话历史
   - 错误信息返回给 LLM，让其决定如何处理
   - 关键错误（如文件权限）提供清晰的错误信息

2. **LLM 调用错误**
   - API 限流：实现指数退避重试
   - 网络错误：最多重试 3 次
   - Token 超限：截断历史消息

3. **文件系统错误**
   - 路径不存在：自动创建父目录
   - 权限错误：返回明确的错误信息
   - 磁盘满：检测并提前警告

### 4.2 边界情况处理

```python
# 在 PathManager 中添加安全检查
def resolve_agent_path(self, agent_path: str) -> Path:
    """安全地解析路径"""
    # 防止路径遍历攻击
    if ".." in agent_path:
        raise ValueError("Path traversal not allowed")
        
    # 防止访问系统目录
    if agent_path.startswith(("/etc", "/usr", "/home", "/var")):
        raise ValueError("Access to system directories not allowed")
        
    # 正常解析逻辑...
```

## 5. Context Window 设计

保持极简的结构：

```markdown
# Current Task
[当前任务描述]

# Working Memory
[关键信息：文件位置、状态等]

# Active Observations
[最新观察结果]

# Next Steps
[下一步计划]
```

### 5.1 Context 管理原则

1. **保持精简**：每个部分不超过 5-10 行
2. **及时更新**：重要变化立即反映
3. **定期清理**：完成的任务移到历史
4. **结构化**：便于程序解析和更新

## 6. 使用示例

### 6.1 简单任务：创建 Python 脚本
```bash
uv run python main.py "创建一个计算斐波那契数列的 Python 脚本"
```

**Agent 执行流程：**
1. 创建 `/workspace/fibonacci.py`
2. 写入递归实现
3. 执行测试命令
4. 调用 sync_context 保存进展

### 6.2 复杂任务：Web 爬虫
```bash
uv run python main.py "创建一个爬取 Hacker News 首页标题的 Python 爬虫"
```

**Agent 执行流程：**
1. 创建 `/workspace/hn_scraper.py`
2. 写入 requests + BeautifulSoup 代码
3. 创建 `pyproject.toml` 或更新依赖
4. 执行 `uv add requests beautifulsoup4`
5. 运行爬虫测试 `uv run python hn_scraper.py`
6. 调用 sync_context
7. 如遇错误，修复并重试
8. 最终 sync_context

### 6.3 Context 演化示例

**初始 Context：**
```markdown
# Current Task
[等待任务]

# Working Memory
[空]

# Active Observations
[空]

# Next Steps
[等待指示]
```

**执行中 Context：**
```markdown
# Current Task
创建 Hacker News 爬虫

# Working Memory
- 最近创建/修改的文件: /workspace/hn_scraper.py, /workspace/pyproject.toml
- 最近执行的命令: 2 个

# Active Observations
- 依赖已安装成功
- 爬虫测试通过，获取到 30 条新闻

# Next Steps
- 添加错误处理
- 保存结果到 JSON
```

**任务完成后 Context：**
```markdown
# Current Task
✓ Hacker News 爬虫已完成

# Working Memory
- 文件: /workspace/hn_scraper.py (完整爬虫)
- 文件: /workspace/pyproject.toml (包含依赖)
- 详细历史已归档: session_20240115_152030.md

# Active Observations
- 爬虫功能正常，可获取首页新闻
- 结果保存为 JSON 格式

# Next Steps
[等待新任务]
```

## 7. Guideline 核心内容

完整的 guideline.md 应包含：

```markdown
# Agent 行为准则

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
你的 context_window_main.md 应该包含：
- Current Task: 当前正在执行的任务
- Working Memory: 关键信息、文件路径、重要发现
- Active Observations: 最近的重要观察结果
- Next Steps: 下一步计划

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
- 大段的文件内容

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
- 保持专业、高效、安全的工作方式
```

## 8. MVP 开发计划（1周）

### Day 1-2: 基础框架
- [ ] 初始化 uv 项目：`uv init`
- [ ] 配置 pyproject.toml 依赖
- [ ] 创建项目结构
- [ ] 实现 PathManager 和 Logger
- [ ] 基础文件操作工具

### Day 3-4: 核心机制
- [ ] 实现 ContextSynchronizer
- [ ] 实现 Agent 主循环
- [ ] 集成 LLM API（OpenAI/Anthropic）

### Day 5-6: 测试优化
- [ ] 编写测试用例
- [ ] 优化 sync_context 逻辑
- [ ] 完善 guideline.md

### Day 7: 文档部署
- [ ] 编写使用文档
- [ ] 创建示例任务
- [ ] 本地部署测试

## 9. 依赖和环境

### 9.1 Python 依赖

使用 uv 管理依赖，在 `pyproject.toml` 中配置：

```toml
[project]
name = "filesystembasedagent"
version = "0.1.0"
description = "A file system based AI agent"
requires-python = ">=3.12"
dependencies = [
    "openai>=1.0.0",  # 或 "anthropic>=0.18.0"
    "pytest>=7.0.0",  # 测试框架
]

[project.scripts]
agent = "src.main:main"

[tool.uv]
dev-dependencies = [
    "pytest-cov>=4.0.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
]
```

### 9.2 开发环境
- Python 3.12+（根据 pyproject.toml）
- 安装 uv：`curl -LsSf https://astral.sh/uv/install.sh | sh`
- 设置环境变量：`OPENAI_API_KEY`

### 9.3 项目初始化
```bash
# 安装依赖
uv sync

# 运行 Agent
uv run python main.py "你的任务"
# 或使用脚本入口
uv run agent "你的任务"
```

## 10. 测试策略

### 10.1 单元测试

运行测试：
```bash
# 运行所有测试
uv run pytest

# 带覆盖率报告
uv run pytest --cov=src
```

示例测试：
```python
# test_path_manager.py
def test_resolve_agent_path():
    pm = PathManager(Path("/tmp/test"))
    
    # 测试绝对路径
    assert pm.resolve_agent_path("/workspace/test.py") == Path("/tmp/test/agent_root/workspace/test.py")
    
    # 测试相对路径
    assert pm.resolve_agent_path("test.py") == Path("/tmp/test/agent_root/workspace/test.py")
    
    # 测试安全检查
    with pytest.raises(ValueError):
        pm.resolve_agent_path("../../../etc/passwd")
```

### 10.2 集成测试场景
1. **基础文件操作**：创建、读取、修改文件
2. **命令执行**：Python 脚本运行、uv 依赖管理
3. **Context 同步**：验证冷热分离逻辑
4. **错误恢复**：工具失败后的处理
5. **多轮对话**：直到 sync_context 的完整流程

## 11. 成功标准

MVP 成功的标志：
1. Agent 能自主管理 context，无需手动干预
2. 能完成简单编程任务（如创建脚本、运行测试）
3. 冷热数据分离有效，context 保持精简
4. 所有操作有日志，便于调试
5. 能处理常见错误并恢复

## 12. 下一步

MVP 验证成功后，可以考虑：
- 子 Agent 机制
- Git 集成实现版本控制
- API 接口对外服务
- 更智能的 context 压缩算法
- 支持更多 LLM（Claude、本地模型等）

但这些都是后话，**先把核心跑通**！

## 总结

这个 MVP 计划提供了足够的实现细节，让你可以：
1. 理解系统架构和数据流
2. 直接开始编码实现
3. 处理常见的边界情况
4. 测试和验证系统功能

核心创新在于 **sync_context 机制**，它优雅地解决了记忆更新的递归依赖问题，让 Agent 能够自然地管理自己的状态。

## 13. 后续改进（已实现）

### 13.1 直接使用 Anthropic API

从 LangChain 迁移到直接调用 Anthropic API，获得了：

1. **更精细的控制**
   - 直接处理流式响应
   - 支持 Claude 特有功能（如思考模式）
   - 更灵活的工具调用处理

2. **实现的新组件**
   - `src/entities.py`: 事件和消息类型定义
   - `src/config.py`: Agent 配置管理
   - `src/async_agent.py`: 异步 Agent 运行时
   - `src/async_main.py`: 异步交互式界面

3. **核心改进**
   - 异步架构提升性能
   - 流式输出改善用户体验
   - 更准确的 Token 使用统计
   - 支持中断和恢复

### 13.2 流式响应

实现了完整的流式响应支持：
- 文本逐字输出
- 工具调用实时显示
- 思考过程指示器
- 更好的错误处理

### 13.3 思考模式

添加了 Claude 的思考模式支持（需要 API 权限）：
- 配置思考预算
- 处理思考内容块
- 分离思考和响应内容

### 13.4 使用方式

系统现在支持两种模式：
1. **同步模式**（兼容原有代码）：通过 `AgentRuntime`
2. **异步模式**（推荐）：通过 `AsyncAgentRuntime`

主程序已自动切换到异步模式，提供更好的交互体验。

## 14. 持久化 Shell 会话（已实现）

### 背景
原始的 `StatefulShell` 实现存在严重问题：
- 每个命令都在新进程中执行，无法保持状态
- 别名、函数、shell 选项等无法在命令间保持
- 手动维护的状态（cd、环境变量）不够完整
- 无法处理交互式命令

### 实现方案
使用 `pexpect` 库实现真正的持久化 Shell 会话：

1. **核心组件**
   - `src/persistent_shell.py`: 持久化 Shell 实现
   - `PersistentShell`: 同步版本，使用 pexpect 管理 bash 进程
   - `AsyncPersistentShell`: 异步包装器

2. **主要特性**
   - **真正的状态保持**：别名、函数、变量、工作目录都能持久
   - **支持复杂 Shell 特性**：管道、重定向、复合命令、作业控制
   - **交互式命令处理**：自动检测并中断交互式命令
   - **合理的超时机制**：超时发送 Ctrl+C 而非终止进程

3. **实现细节**
   ```python
   # 使用 pexpect 启动持久进程
   self.shell = pexpect.spawn('/bin/bash', ...)
   
   # 发送命令并等待完成
   self.shell.sendline(command)
   self.shell.expect(prompt_pattern)
   
   # 检测交互式提示
   if pattern in ['Password:', '(y/n)', ...]:
       self.shell.sendcontrol('c')  # 发送 Ctrl+C
   ```

4. **解决的问题**
   - ✅ 别名和函数现在能正常工作
   - ✅ 环境变量在整个会话中保持
   - ✅ cd 命令的效果能正确体现
   - ✅ 交互式命令不会导致挂起

5. **错误处理**
   - 命令超时：发送 Ctrl+C 并返回错误
   - Shell 意外终止：自动重启
   - 交互式命令：检测并中断，返回提示信息

## 15. 架构设计理念（核心）

### Runtime + State 分离

本项目的核心架构理念是将 Agent 系统分为两个完全独立的部分：

1. **Agent Runtime（运行时）**
   - 无状态的工具提供者
   - 不保存任何业务数据
   - 只负责执行操作和返回结果
   - 可以随时替换或升级

2. **Agent State（状态）**
   - 完全保存在 `agent_root` 目录
   - 包含所有知识、记忆、工作内容
   - 可以完整迁移到任何环境
   - 支持版本控制和历史追踪

### 设计优势

1. **解耦性**：Runtime 和 State 完全解耦，互不依赖
2. **可迁移**：整个 `agent_root` 可以打包带走
3. **透明性**：所有状态都是可见的文件
4. **可调试**：可以直接查看和修改 Agent 的状态
5. **多实例**：可以同时运行多个不同状态的 Agent

### 实际应用

当前 Agent 被配置用于开发 Dify 工具插件：
- `storage/documents/plugins/` - Dify 插件开发文档
- `storage/few_shots/` - 多个插件实现示例
- `workspace/` - 插件开发工作区

这种架构使得 Agent 可以轻松切换到其他任务，只需要：
1. 归档当前的 `agent_root`
2. 创建新的 `agent_root` 并提供相应资源
3. Agent 立即可以开始新任务

## 16. 增量输出改进（已实现）

### 背景

Agent 的控制台输出存在可读性问题：
- 工具调用显示过于冗长，特别是 `sync_context` 调用
- 重复内容反复显示，如相同的文件读取操作
- 开发阶段需要详细信息，但又不想被重复内容淹没

### 解决方案：增量输出格式化器

#### 16.1 IncrementalOutputFormatter 类

创建了 `src/incremental_output_formatter.py`，专注于"增量输出"而非"分级输出"：

```python
class IncrementalOutputFormatter:
    """格式化 Agent 的输出，确保只显示增量内容"""
```

#### 16.2 核心特性

1. **去重机制**：
   - 记录已显示的工具调用，避免重复显示相同操作
   - `sync_context` 只在内容真正变化时显示
   - Shell 命令可重复执行，但会标记为"重复执行"

2. **智能格式化**：
   - 文件操作显示操作次数（第 1 次、第 2 次...）
   - 长输出智能截断（显示前 10 行和后 5 行）
   - 根据工具类型使用不同图标（🔧 命令、📖 读取、✏️ 编辑等）

3. **详细但不冗余**：
   - 保留所有必要的开发信息
   - 自动过滤重复内容
   - 命令输出使用缩进，提高可读性

#### 16.3 改进效果

**改进前**：
```
⚙️ 调用工具: sync_context("{\"new_context_content\": \"# Current Task\\n总结计
⚙️ 调用工具: sync_context("{\"new_context_content\": \"# Current Task\\n总结计算器
...（重复几十次，每次输入一个字符）...
```

**改进后**：
```
📝 更新 Context (37 行, 第 1 次更新)
（相同内容的 sync_context 被自动忽略）
📝 更新 Context (45 行, 第 2 次更新)
```

**文件操作示例**：
```
📖 读取文件: /workspace/test.py [行 1-10]
（相同的读取被忽略）
📖 读取文件: /workspace/test.py [行 11-20] (第 2 次)
✏️ 编辑文件: /workspace/test.py [行 5-8] (第 3 次)
```

**命令输出示例**：
```
🔧 执行命令: ls -la workspace/
✅ 命令完成 (退出码: 0)
输出:
   total 32
   drwxr-xr-x  6 user  staff   192 Aug  9 17:00 .
   drwxr-xr-x  8 user  staff   256 Aug  9 16:30 ..
   -rw-r--r--  1 user  staff  1024 Aug  9 17:00 main.py
   ... (省略 90 行) ...
   -rw-r--r--  1 user  staff   512 Aug  9 16:45 utils.py
```

#### 16.4 技术实现

1. **状态跟踪**：
   - `shown_tool_calls`: 记录已显示的工具调用
   - `shown_results`: 记录已显示的结果
   - `file_operations`: 跟踪每个文件的操作次数
   - `last_sync_context`: 记录上次 context 内容

2. **重置机制**：
   - `reset_for_new_conversation()` 方法清空所有状态
   - 在 `clear` 命令时自动调用

这个改进保持了开发阶段所需的详细信息，同时通过智能去重大大提升了输出的可读性。

## 17. 模型配置支持（已实现）

### 背景

之前模型选择硬编码在 `src/config.py` 中，用户无法灵活切换不同的 Claude 模型。

### 解决方案

通过最小改动，支持从环境变量配置模型：

1. **修改 `AgentConfig.from_env()`**：
   ```python
   model = os.getenv("ANTHROPIC_MODEL")
   if model:
       config_dict["model"] = model
   ```

2. **更新 `.env.example`**：
   ```bash
   # Optional: Model selection
   # ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
   ```

3. **保持向后兼容**：
   - 不设置时使用默认模型
   - kwargs 优先级最高

### 使用效果

用户现在可以：
- 在 `.env` 中配置：`ANTHROPIC_MODEL=claude-3-5-haiku-20241022`
- 通过环境变量：`export ANTHROPIC_MODEL=claude-3-5-haiku-20241022`
- 根据任务需求选择合适的模型（速度 vs 能力）

## 18. 流式输出和 Shell 输出优化（已实现）

### 背景

控制台输出存在以下问题：
1. 空工具调用：输出不完整的工具调用 JSON
2. Shell 输出格式不干净：包含命令回显、控制字符、提示符等

### 解决方案

1. **修复空工具调用**
   - 移除 `ContentBlockStart` 和 `InputJsonDelta` 时的 yield
   - 只在 `ContentBlockStop` 时输出完整的工具调用

2. **优化 Shell 输出**
   - 移除命令回显（第一行）
   - 移除提示符（最后一行）
   - 清理控制字符

3. **改进错误显示**
   - 添加完整的堆栈跟踪信息
   - 工具执行错误时显示 traceback

### 效果

- 控制台输出更清晰
- 工具调用信息完整
- Shell 输出干净无冗余

## 19. 流式处理架构重构（已实现）

### 背景

原有的流式处理存在严重问题：
1. **文本过度碎片化**：一个简单句子被分成 570+ 个片段
2. **大量重复输出**：某些文本片段重复 1200+ 次
3. **职责混乱**：AgentRuntime 既处理流式又处理业务逻辑

### 问题分析

通过直接调用 Anthropic API 测试发现：
- API 本身返回的事件是正常的
- 问题出在 `_process_stream` 的设计上
- 每个小片段都创建新事件，导致大量冗余

### 解决方案

#### 1. 架构重新设计

```
Anthropic API 
    ↓
StreamProcessor (聚合完整数据)
    ├→ ConsoleStreamHandler (实时控制台输出)
    └→ CompleteResponse → AgentRuntime (只处理完整数据)
```

#### 2. 核心组件

**StreamProcessor** (`src/stream_processor.py`)
- 处理原始流式事件
- 聚合成完整的数据块
- 返回结构化的 `CompleteResponse`

**ConsoleStreamHandler** (`src/console_handler.py`)
- 专门处理控制台显示
- 智能文本缓冲，避免过度碎片化
- 去重和自然断点检测

**新的 AsyncAgentRuntime 接口**
- `invoke()`: 纯数据接口，不处理流式
- `invoke_with_console()`: 带控制台输出的接口

#### 3. 实现细节

1. **文本缓冲策略**
   - 遇到句号、感叹号等自然断点时输出
   - 缓冲区达到一定大小时输出
   - 避免重复输出相同内容

2. **工具调用处理**
   - 累积完整的 JSON 后再解析
   - 显示工具执行进度和结果

3. **职责分离**
   - StreamProcessor: 数据聚合
   - ConsoleStreamHandler: 显示优化
   - AgentRuntime: 业务逻辑

### 测试结果

1. **效率提升**
   - 文本片段从 570+ 降到 13 个
   - 输出效率 1.00（无重复）

2. **用户体验改善**
   - 流畅的实时输出
   - 清晰的工具调用信息
   - 无重复、无碎片

### 使用方式

```python
# 创建运行时和控制台处理器
runtime = AsyncAgentRuntime(project_root, config)
console_handler = ConsoleStreamHandler()

# 调用新接口
response = await runtime.invoke_with_console(
    role="user",
    content=user_input,
    console_handler=console_handler
)
```