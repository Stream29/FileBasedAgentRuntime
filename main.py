#!/usr/bin/env python3
"""FileSystem-based Agent 主程序"""

import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# 导入 Agent 相关模块
from src.async_agent import AsyncAgentRuntime
from src.config import AgentConfig
from src.entities import EventType, Role


def print_welcome() -> None:
    """打印欢迎信息"""
    print("=" * 60)
    print("🤖 FileSystem-based Agent - 交互式模式")
    print("=" * 60)
    print("• 输入任务描述，Agent 会执行并回复")
    print("• 输入 'exit' 或 'quit' 退出")
    print("• 输入 'clear' 清空对话历史")
    print("• 输入 'help' 查看可用命令")
    print("• 输入 'status' 查看当前 Agent 状态")
    print("• 按 Ctrl+C 可以中断当前任务")
    print("• 🚀 支持流式输出和更好的性能")
    print("=" * 60)
    print()


def print_help() -> None:
    """打印帮助信息"""
    print("\n📚 可用命令：")
    print("  exit/quit  - 退出程序")
    print("  clear      - 清空对话历史并重置 context")
    print("  help       - 显示此帮助信息")
    print("  status     - 显示当前 context 和文件系统状态")


async def async_main() -> None:
    """异步主函数"""
    print_welcome()

    # 加载环境变量
    load_dotenv()

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ 错误: 未找到 ANTHROPIC_API_KEY")
        print("\n请先配置 .env 文件：")
        print("1. cp .env.example .env")
        print("2. 编辑 .env 文件，填入你的 API Key")
        sys.exit(1)

    project_root = Path.cwd()
    config = AgentConfig.from_env()
    runtime = AsyncAgentRuntime(project_root, config)

    try:
        while True:
            user_input = input("👤 User: ").strip()
            if not user_input:
                continue

            # 处理特殊命令
            if user_input.lower() in ["exit", "quit"]:
                print("\n👋 再见！")
                break

            elif user_input.lower() == "clear":
                print("\n🔄 清空对话历史...")
                runtime.agent.execute_tool(
                    "sync_context",
                    {"new_context_content": runtime.agent._get_default_context()},
                )
                # 重置 context
                context_path = runtime.agent.path_manager.agent_root / "context_window_main.md"
                context_path.write_text(runtime.agent._get_default_context(), encoding="utf-8")
                # 清空消息历史
                runtime.messages.clear()
                print("✅ 对话历史已清空\n")
                continue

            elif user_input.lower() == "help":
                print_help()
                continue

            elif user_input.lower() == "status":
                # 显示当前 context 状态
                context_path = runtime.agent.path_manager.agent_root / runtime.agent.context_file
                if context_path.exists():
                    context = context_path.read_text(encoding="utf-8")
                    print("\n📄 当前 Context Window:")
                    print("-" * 40)
                    print(context)
                    print("-" * 40)
                else:
                    print("\n📄 Context Window 文件不存在。")

                # 显示文件系统结构
                print("\n📁 文件系统结构:")
                print(runtime._generate_directory_structure())
                print("-" * 40)

                print(f"📊 对话历史: {len(runtime.agent.conversation_history)} 条记录")
                print(f"📨 消息历史: {len(runtime.messages)} 条消息")
                print(
                    f"🔢 Token 使用: 输入 {runtime.total_usage.input_tokens}, "
                    f"输出 {runtime.total_usage.output_tokens}\n"
                )
                continue

            # 执行任务（流式输出）
            print("\n🤖 Agent: ", end="", flush=True)
            try:
                async for event in runtime.invoke_stream(Role.User, user_input):
                    if event.type == EventType.Message and event.role == Role.Assistant:
                        if hasattr(event.content, "text"):
                            # 流式输出文本
                            print(event.content.text, end="", flush=True)
                    elif event.type == EventType.ToolUse:
                        # 打印工具调用
                        if isinstance(event.content, list):
                            tool_calls_str = ", ".join(
                                f"{tc.name}({json.dumps(tc.input, ensure_ascii=False)})"
                                for tc in event.content
                            )
                            print(f"\n⚙️ 调用工具: {tool_calls_str}", end="", flush=True)
                    elif event.type == EventType.ToolResult:
                        # 打印工具结果
                        if isinstance(event.content, list):
                            tool_results_str = "\n".join(
                                f"  - {tr.tool_use_id}: {tr.content}" for tr in event.content
                            )
                            print(f"\n✅ 工具结果:\n{tool_results_str}", end="", flush=True)
                    elif event.type == EventType.Thinking:
                        # 打印思考过程
                        if hasattr(event.content, "thinking"):
                            print(f"\n🧠 思考: {event.content.thinking}", end="", flush=True)
                    elif event.type == EventType.Error and hasattr(event.content, "text"):
                        print(f"\n❌ 错误: {event.content.text}", end="", flush=True)

                print()  # 确保换行

            except Exception as e:
                print(f"\n❌ 错误: {e}\n")
                # 继续交互循环，不退出

    except KeyboardInterrupt:
        print("\n\n👋 再见！")

    except Exception as e:
        print(f"\n❌ 初始化失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


def main() -> None:
    """Main entry point for the application."""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
