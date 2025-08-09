# 增量输出设计文档

## 设计理念

根据用户反馈，开发阶段需要尽可能详尽的输出，但不要有重复内容反复显示。这引出了"增量输出"的核心理念：

- **详尽但不冗余** - 显示所有必要信息，但智能去重
- **开发友好** - 保留开发和调试所需的所有细节
- **增量显示** - 只显示新增或变化的内容

## 实现方案

### IncrementalOutputFormatter 类

位于 `src/incremental_output_formatter.py`，负责智能格式化 Agent 的输出。

### 核心机制

1. **去重跟踪**
   ```python
   self.shown_tool_calls: Set[str] = set()  # 已显示的工具调用
   self.shown_results: Set[str] = set()     # 已显示的结果
   self.last_sync_context: Optional[str] = None  # 上次的 context 内容
   ```

2. **智能处理不同工具**
   - `sync_context`: 只在内容变化时显示
   - `shell`: 允许重复，但标记为"重复执行"
   - 文件操作: 显示操作次数计数

3. **输出优化**
   - 长输出智能截断（保留前后关键信息）
   - 使用缩进提高可读性
   - 根据工具类型使用不同图标

## 典型场景

### 场景1: sync_context 的频繁调用

**问题**: Agent 在输入时会频繁调用 sync_context
**解决**: 只在内容真正变化时显示

```
📝 更新 Context (37 行, 第 1 次更新)
（后续相同内容的调用被自动忽略）
📝 更新 Context (45 行, 第 2 次更新)
```

### 场景2: 文件的多次操作

**问题**: 对同一文件的多次操作难以追踪
**解决**: 显示操作计数

```
📖 读取文件: config.py [行 1-50]
✏️ 编辑文件: config.py [行 10-15] (第 2 次)
✏️ 编辑文件: config.py [行 30-35] (第 3 次)
```

### 场景3: 长命令输出

**问题**: 命令输出过长影响可读性
**解决**: 智能截断，保留关键信息

```
🔧 执行命令: find . -name "*.py"
✅ 命令完成 (退出码: 0)
输出:
   ./main.py
   ./src/agent.py
   ./src/tools.py
   ... (省略 50 行) ...
   ./tests/test_agent.py
   ./tests/test_tools.py
```

## 与之前方案的对比

### 之前的分级输出方案
- 提供 minimal/normal/verbose 三个级别
- 用户需要手动切换级别
- 不同级别隐藏不同信息

### 现在的增量输出方案
- 单一模式，自动优化
- 保留所有信息，智能去重
- 更适合开发阶段使用

## 技术细节

### 工具调用去重
```python
tool_call_id = f"{tool_name}:{json.dumps(tool_input, sort_keys=True)}"
if tool_call_id in self.shown_tool_calls:
    # 已显示过，根据工具类型决定是否再次显示
```

### 结果签名
```python
result_signature = content_str[:100]  # 使用前100字符作为签名
if result_signature in self.shown_results:
    return None  # 避免重复显示
```

### 状态重置
```python
def reset_for_new_conversation(self):
    """为新对话重置所有状态"""
    self.shown_tool_calls.clear()
    self.shown_results.clear()
    # ...
```

## 未来改进方向

1. **可配置的去重规则** - 允许用户定义哪些工具可以重复显示
2. **更智能的截断** - 根据内容类型使用不同的截断策略
3. **统计信息** - 在对话结束时显示调用统计
4. **导出功能** - 支持导出完整日志供离线分析