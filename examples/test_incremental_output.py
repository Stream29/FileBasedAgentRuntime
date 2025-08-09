#!/usr/bin/env python3
"""测试增量输出格式化器"""

import json
from src.incremental_output_formatter import IncrementalOutputFormatter


def test_incremental_formatter():
    """测试增量输出格式化器的去重功能"""
    
    print("=" * 60)
    print("测试 IncrementalOutputFormatter 的增量输出效果")
    print("=" * 60)
    
    formatter = IncrementalOutputFormatter()
    
    # 模拟实际使用场景
    print("\n[场景1: 重复的工具调用]")
    
    # 第一次调用
    output = formatter.format_tool_call("read_file", {"path": "/workspace/test.py", "start_line": 1, "end_line": 10})
    if output:
        print(output)
    
    # 相同的调用（应该被忽略）
    output = formatter.format_tool_call("read_file", {"path": "/workspace/test.py", "start_line": 1, "end_line": 10})
    if output:
        print(output)
    else:
        print("  (重复调用被忽略)")
    
    # 不同行范围的调用（应该显示）
    output = formatter.format_tool_call("read_file", {"path": "/workspace/test.py", "start_line": 11, "end_line": 20})
    if output:
        print(output)
    
    print("\n[场景2: sync_context 的智能处理]")
    
    # 第一次 sync_context
    context1 = "# Current Task\n学习 Dify 插件开发\n\n## 进度\n- 阅读文档"
    output = formatter.format_tool_call("sync_context", {"new_context_content": context1})
    if output:
        print(output)
    
    # 相同内容的 sync_context（应该被忽略）
    output = formatter.format_tool_call("sync_context", {"new_context_content": context1})
    if output:
        print(output)
    else:
        print("  (相同内容的 sync_context 被忽略)")
    
    # 不同内容的 sync_context（应该显示）
    context2 = context1 + "\n- 开始实现计算器插件"
    output = formatter.format_tool_call("sync_context", {"new_context_content": context2})
    if output:
        print(output)
    
    print("\n[场景3: Shell 命令的处理]")
    
    # Shell 命令可以重复执行
    output = formatter.format_tool_call("shell", {"command": "ls -la"})
    print(output)
    
    output = formatter.format_tool_call("shell", {"command": "ls -la"})
    print(output)
    
    print("\n[场景4: 文件操作计数]")
    
    # 对同一文件的多次操作
    for i in range(3):
        output = formatter.format_tool_call("edit_file", {
            "file_path": "/workspace/hello.py",
            "start_line": i * 10 + 1,
            "end_line": (i + 1) * 10
        })
        print(output)
    
    print("\n[场景5: 结果输出的智能处理]")
    
    # Shell 命令结果（测试 JSON 字符串形式）
    result1 = json.dumps({
        "exit_code": 0,
        "stdout": "file1.txt\nfile2.txt\nfile3.txt\ndir1/\ndir2/\n" + "\n".join([f"file{i}.txt" for i in range(100)]),
        "stderr": ""
    })
    output = formatter.format_tool_result("tool_1", result1)
    print(output)
    
    # sync_context 结果（测试 JSON 字符串形式）
    result2 = json.dumps({
        "status": "success",
        "message": "Context 已更新，清空了 5 条对话历史",
        "archive_path": "学习_Dify_插件开发_20250809_1700.md"
    }, ensure_ascii=False)
    output = formatter.format_tool_result("tool_2", result2)
    print(output)
    
    # 错误结果（测试 JSON 字符串形式）
    result3 = json.dumps({
        "exit_code": 1,
        "stdout": "",
        "stderr": "Error: file not found"
    })
    output = formatter.format_tool_result("tool_3", result3)
    print(output)


if __name__ == "__main__":
    test_incremental_formatter()