# HOTFIX: 异步生成器返回 None 导致的错误

## 🐛 问题描述

**错误信息**：`'NoneType' object has no attribute 'type'`

**触发条件**：当 Agent 产生空的工具调用列表时

## 🔍 根本原因

在 `src/async_agent.py` 的 `_handle_tool_calls_stream` 方法中：

```python
async def _handle_tool_calls_stream(
    self, tool_uses: list[ToolUseContent]
) -> AsyncIterator[Event]:
    """Handle tool calls in streaming mode"""
    if not tool_uses:
        return  # ❌ 返回 None 而不是空的异步生成器
```

当 `tool_uses` 为空时，方法返回 `None`，导致调用方尝试迭代 `None` 对象时出错。

## ✅ 修复方案

```python
if not tool_uses:
    # 返回空的异步生成器而不是 None
    return
    yield  # 这行永远不会执行，但让函数成为生成器
```

## 📝 经验教训

1. **异步生成器函数必须始终返回生成器**
   - 即使要返回空结果，也要确保函数是生成器
   - 使用 `return; yield` 模式创建空生成器

2. **类型注解不保证运行时行为**
   - 即使声明返回 `AsyncIterator[Event]`，Python 仍允许返回 `None`
   - 需要在代码逻辑中确保正确性

3. **防御性编程**
   - 在迭代之前检查对象是否为 None
   - 或者确保生成器函数始终返回生成器

## 🔮 后续改进

1. 调查为什么 Agent 会产生空的工具调用
2. 添加更多的错误处理和日志
3. 考虑使用 `@ensure_generator` 装饰器来避免类似问题

## 📅 修复日期

2025-08-10