#!/usr/bin/env python3
"""主入口文件 - 使用新的流式处理架构"""

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

from src.async_agent import AsyncAgentRuntime
from src.config import AgentConfig
from src.console_handler import ConsoleStreamHandler

# 加载环境变量
load_dotenv()


def print_help():
    """打印帮助信息"""
    print("\n📚 可用命令:")
    print("  exit    - 退出程序")
    print("  clear   - 清空对话历史")
    print("  help    - 显示此帮助信息")
    print("  status  - 显示当前状态")
    print("\n💡 提示: 直接输入您的问题或任务即可。\n")


async def async_main():
    """异步主函数"""
    print("🚀 FileSystem-based AI Agent 启动中...")
    print("=" * 50)

    # 获取项目根目录
    project_root = Path.cwd()

    # 从环境变量创建配置
    config = AgentConfig.from_env()

    # 创建 Agent Runtime
    runtime = AsyncAgentRuntime(project_root, config)

    # 创建控制台处理器
    console_handler = ConsoleStreamHandler()

    print("✅ Agent 已就绪！")
    print_help()

    # 主循环
    while True:
        try:
            # 获取用户输入
            user_input = input("\n💭 You: ").strip()

            if not user_input:
                continue

            # 处理特殊命令
            if user_input.lower() == "exit":
                print("\n👋 再见！")
                break

            elif user_input.lower() == "clear":
                # 清空对话历史
                runtime.messages.clear()
                runtime.agent.conversation_history.clear()
                console_handler.reset()
                print("\n🗑️ 对话历史已清空。")
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

                # 显示控制台统计
                stats = console_handler.get_stats()
                print(f"📊 控制台统计: 输出 {stats['total_chars_output']} 字符")
                continue

            # 执行任务（使用新的接口）
            print("\n🤖 Agent: ", end="", flush=True)

            try:
                # 重置控制台处理器状态
                console_handler.reset()

                # 调用新的带控制台输出的接口
                response = await runtime.invoke_with_console(
                    role="user",
                    content=user_input,
                    console_handler=console_handler
                )

                # 工具执行结果已经在 invoke_with_console 中处理和显示

                # 如果有思考过程，显示它
                if response.thinking:
                    print(f"\n\n💭 思考过程:\n{response.thinking}")

                # 显示使用情况
                if response.usage:
                    input_tokens = response.usage.get("input_tokens", 0)
                    output_tokens = response.usage.get("output_tokens", 0)
                    runtime.total_usage.input_tokens += input_tokens
                    runtime.total_usage.output_tokens += output_tokens

                print()  # 确保换行

            except KeyboardInterrupt:
                print("\n\n⚠️ 已中断当前操作。")
                continue
            except Exception as e:
                print(f"\n❌ 错误: {e}")
                print("\n📋 详细堆栈信息：")
                import traceback
                traceback.print_exc()
                print()  # 额外换行，保持输出美观
                # 继续交互循环，不退出

        except KeyboardInterrupt:
            print("\n\n👋 再见！")
            break
        except Exception as e:
            print(f"\n❌ 发生未预期的错误: {e}")
            import traceback
            traceback.print_exc()
            # 主循环异常，退出程序
            sys.exit(1)


def main():
    """主函数"""
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\n\n👋 再见！")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
