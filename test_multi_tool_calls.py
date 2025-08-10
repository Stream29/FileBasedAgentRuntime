#!/usr/bin/env python3
"""测试多轮工具调用功能"""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 加载环境变量
load_dotenv()

from src.async_agent import AsyncAgentRuntime
from src.config import AgentConfig
from src.console_handler import ConsoleStreamHandler


async def test_multi_tool_calls():
    """测试多轮工具调用场景"""
    print("🚀 测试多轮工具调用功能...\n")
    
    # 创建项目路径
    project_root = Path(__file__).parent
    
    # 创建配置
    config = AgentConfig.from_env()
    
    # 创建 runtime
    runtime = AsyncAgentRuntime(project_root, config)
    
    # 创建控制台处理器
    console_handler = ConsoleStreamHandler()
    
    # 测试用例1：创建一个简单的文本文件并读取内容
    print("=" * 50)
    print("测试用例1：创建文件并读取内容")
    print("=" * 50)
    
    user_input = """创建一个名为 test_multi_turn.txt 的文件，内容是"Hello, Multi-turn!"，
然后读取这个文件的内容，最后告诉我文件的大小。"""
    
    print(f"\n💭 用户: {user_input}\n")
    print("🤖 Agent: ", end="", flush=True)
    
    try:
        response = await runtime.invoke_with_console(
            role="user",
            content=user_input,
            console_handler=console_handler
        )
        
        # 显示统计信息
        print(f"\n\n📊 统计信息:")
        print(f"  - 总文本长度: {len(response.text)}")
        print(f"  - 工具调用次数: {len(response.tool_calls)}")
        print(f"  - 工具调用详情:")
        for i, tool_call in enumerate(response.tool_calls, 1):
            print(f"    {i}. {tool_call.name}")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 清理测试文件
    print("\n\n🧹 清理测试文件...")
    try:
        test_file = project_root / "agent_root" / "test_multi_turn.txt"
        if test_file.exists():
            test_file.unlink()
            print("✅ 文件已清理")
    except Exception as e:
        print(f"⚠️ 清理失败: {e}")
    
    # 测试用例2：执行多个命令
    print("\n\n" + "=" * 50)
    print("测试用例2：执行多个命令")
    print("=" * 50)
    
    user_input2 = """帮我做以下事情：
1. 创建一个名为 test_dir 的目录
2. 在这个目录下创建一个 hello.py 文件，内容是 print("Hello from Python!")
3. 列出这个目录的内容
4. 删除这个目录"""
    
    print(f"\n💭 用户: {user_input2}\n")
    print("🤖 Agent: ", end="", flush=True)
    
    # 重置控制台处理器
    console_handler.reset()
    
    try:
        response2 = await runtime.invoke_with_console(
            role="user",
            content=user_input2,
            console_handler=console_handler
        )
        
        # 显示统计信息
        print(f"\n\n📊 统计信息:")
        print(f"  - 总文本长度: {len(response2.text)}")
        print(f"  - 工具调用次数: {len(response2.tool_calls)}")
        print(f"  - 工具调用详情:")
        for i, tool_call in enumerate(response2.tool_calls, 1):
            print(f"    {i}. {tool_call.name}")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n\n✅ 测试完成！")


if __name__ == "__main__":
    asyncio.run(test_multi_tool_calls())