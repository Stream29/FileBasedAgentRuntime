"""Async main entry point for the FileSystem-based Agent."""

import asyncio
import sys
from pathlib import Path
import os

from .async_agent import AsyncAgentRuntime
from .config import AgentConfig
from .entities import Role, EventType


def print_welcome():
    """打印欢迎信息"""
    print("="*60)
    print("🤖 FileSystem-based Agent - 交互式模式 (异步版)")
    print("="*60)
    print("• 输入任务描述，Agent 会执行并回复")
    print("• 输入 'exit' 或 'quit' 退出")
    print("• 输入 'clear' 清空对话历史")
    print("• 输入 'help' 查看帮助")
    print("• 按 Ctrl+C 可以中断当前任务")
    print("• 🚀 支持流式输出和更好的性能")
    print("="*60)
    print()


def print_help():
    """打印帮助信息"""
    print("\n📚 可用命令：")
    print("  exit/quit  - 退出程序")
    print("  clear      - 清空对话历史并重置 context")
    print("  help       - 显示此帮助信息")
    print("  status     - 显示当前 context 状态")
    print("  其他输入   - 作为任务发送给 Agent\n")


async def async_main():
    """异步主函数"""
    # 检查环境变量
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ 错误: 未找到 ANTHROPIC_API_KEY")
        print("\n请先配置 .env 文件：")
        print("1. cp .env.example .env")
        print("2. 编辑 .env 文件，填入你的 API Key")
        sys.exit(1)
    
    try:
        # 初始化运行时
        print("🔄 正在初始化 Agent...")
        config = AgentConfig.from_env()
        runtime = AsyncAgentRuntime(project_root=Path.cwd(), config=config)
        print("✅ Agent 初始化成功\n")
        
        # 打印欢迎信息
        print_welcome()
        
        # 交互循环
        while True:
            try:
                # 获取用户输入
                user_input = input("👤 You: ").strip()
                
                if not user_input:
                    continue
                    
                # 处理特殊命令
                if user_input.lower() in ['exit', 'quit']:
                    print("\n👋 再见！")
                    break
                    
                elif user_input.lower() == 'clear':
                    print("\n🔄 清空对话历史...")
                    runtime.agent.execute_tool('sync_context', {})
                    # 重置 context
                    context_path = runtime.agent.path_manager.agent_root / "context_window_main.md"
                    context_path.write_text(runtime.agent._get_default_context(), encoding='utf-8')
                    # 清空消息历史
                    runtime.messages.clear()
                    print("✅ 对话历史已清空\n")
                    continue
                    
                elif user_input.lower() == 'help':
                    print_help()
                    continue
                    
                elif user_input.lower() == 'status':
                    # 显示当前 context 状态
                    context_path = runtime.agent.path_manager.agent_root / runtime.agent.context_file
                    if context_path.exists():
                        context = context_path.read_text(encoding='utf-8')
                        print("\n📄 当前 Context Window:")
                        print("-" * 40)
                        print(context)
                        print("-" * 40)
                    print(f"📊 对话历史: {len(runtime.agent.conversation_history)} 条记录")
                    print(f"📨 消息历史: {len(runtime.messages)} 条消息")
                    print(f"🔢 Token 使用: 输入 {runtime.total_usage.input_tokens}, 输出 {runtime.total_usage.output_tokens}\n")
                    continue
                
                # 执行任务（流式输出）
                print("\n🤖 Agent: ", end="", flush=True)
                
                # 标记是否有工具调用
                has_tool_calls = False
                
                async for event in runtime.invoke_stream(Role.User, user_input):
                    if event.type == EventType.Message and event.role == Role.Assistant:
                        if hasattr(event.content, 'text'):
                            # 流式输出文本
                            print(event.content.text, end="", flush=True)
                            
                    elif event.type == EventType.ToolUse:
                        # 显示工具调用
                        if not has_tool_calls:
                            print("\n", end="")  # 换行以区分工具调用
                            has_tool_calls = True
                        
                        if isinstance(event.content, list):
                            for tool in event.content:
                                print(f"   🔧 使用工具: {tool.name}", end="", flush=True)
                                
                    elif event.type == EventType.ToolResult:
                        # 工具执行完成
                        print(" ✓", flush=True)
                        
                    elif event.type == EventType.Thinking:
                        # 显示思考中
                        print("💭 [思考中...]", end="\r", flush=True)
                        
                    elif event.type == EventType.Error:
                        # 显示错误
                        print(f"\n❌ 错误: {event.content}", flush=True)
                
                print("\n")  # 确保换行
                
            except KeyboardInterrupt:
                print("\n\n⚠️  任务被中断")
                # 保存进展
                try:
                    runtime.agent.execute_tool('sync_context', {})
                    print("✓ Context 已自动保存")
                except:
                    pass
                print()  # 继续交互循环
                
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


def main():
    """主入口点"""
    # 加载环境变量
    from dotenv import load_dotenv
    load_dotenv()
    
    # 运行异步主函数
    asyncio.run(async_main())


if __name__ == "__main__":
    main()