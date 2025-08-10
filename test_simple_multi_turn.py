#!/usr/bin/env python3
"""简单的多轮工具调用测试"""

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


async def test_simple():
    """测试简单的多轮工具调用"""
    print("🚀 测试多轮工具调用功能（简化版）...\n")
    
    # 创建项目路径
    project_root = Path(__file__).parent
    
    # 创建配置
    config = AgentConfig.from_env()
    
    # 创建 runtime
    runtime = AsyncAgentRuntime(project_root, config)
    
    # 创建控制台处理器
    console_handler = ConsoleStreamHandler()
    
    # 简单测试：创建目录、创建文件、列出内容
    user_input = """请帮我：
1. 创建一个名为 simple_test 的目录
2. 在这个目录下创建一个 info.txt 文件，内容是 'This is a test'
3. 列出这个目录的内容"""
    
    print(f"💭 用户: {user_input}\n")
    print("🤖 Agent: ", end="", flush=True)
    
    try:
        response = await runtime.invoke_with_console(
            role="user",
            content=user_input,
            console_handler=console_handler
        )
        
        print(f"\n\n📊 测试结果:")
        print(f"  - 工具调用次数: {len(response.tool_calls)}")
        print(f"  - 工具调用详情:")
        for i, tool_call in enumerate(response.tool_calls, 1):
            print(f"    {i}. {tool_call.name}")
        
        # 如果响应文本被截断了（在多轮的情况下），显示完整文本
        if len(response.tool_calls) > 1:
            print(f"\n  - 完整响应文本长度: {len(response.text)} 字符")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 清理
    print("\n\n🧹 清理测试文件...")
    try:
        test_dir = project_root / "agent_root" / "simple_test"
        if test_dir.exists():
            import shutil
            shutil.rmtree(test_dir)
            print("✅ 目录已清理")
    except Exception as e:
        print(f"⚠️ 清理失败: {e}")
    
    print("\n✅ 测试完成！")


if __name__ == "__main__":
    asyncio.run(test_simple())