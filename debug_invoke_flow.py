#!/usr/bin/env python3
"""调试 invoke 方法的消息流程"""

import asyncio
import json
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
from src.entities import Role, EventType, TextContent, ToolUseContent, ToolResultContent


# 创建一个自定义的 AsyncAgentRuntime 来调试
class DebugAsyncAgentRuntime(AsyncAgentRuntime):
    async def invoke_with_console(
        self,
        role: str = "user",
        content: str = "",
        console_handler: ConsoleStreamHandler = None,
        max_rounds: int = 10
    ):
        """重写方法以添加调试信息"""
        print("🔍 开始 invoke_with_console 调试...\n")
        
        # 只在有内容时添加初始用户消息（第一轮）
        if role and content:
            print(f"📝 添加初始用户消息: {content[:50]}...")
            await self.create_event(Role(role), EventType.Message, TextContent(text=content))
        
        # 如果没有提供控制台处理器，创建一个
        if console_handler is None:
            console_handler = ConsoleStreamHandler()
        
        # 累积的完整响应
        final_response = {
            "text": "",
            "tool_calls": [],
            "stop_reason": None,
            "usage": None,
            "thinking": None,
            "tool_results": []
        }
        
        # 循环处理，最多 max_rounds 轮
        for round_num in range(max_rounds):
            print(f"\n\n{'='*50}")
            print(f"🔄 第 {round_num + 1} 轮")
            print(f"{'='*50}")
            
            # 打印当前消息历史
            print("\n📋 当前消息历史:")
            api_messages = [msg.transform_api() for msg in self.messages]
            for i, msg in enumerate(api_messages):
                print(f"\n消息 {i} ({msg['role']}):")
                if isinstance(msg['content'], list):
                    for content in msg['content']:
                        print(f"  - {content.get('type')}")
                        if content.get('type') == 'tool_result':
                            print(f"    tool_use_id: {content.get('tool_use_id')}")
                else:
                    print(f"  - text: {str(msg['content'])[:50]}...")
            
            # 检查最后一条消息
            if api_messages:
                last_msg = api_messages[-1]
                print(f"\n⚠️ 最后一条消息的角色: {last_msg['role']}")
                if isinstance(last_msg['content'], list):
                    for content in last_msg['content']:
                        if content.get('type') == 'tool_result':
                            print("❌ 警告：最后一条消息包含 tool_result！")
            
            # 如果已经有足够的响应，提前结束
            if round_num > 0 and not api_messages:
                print("✅ 没有更多消息，结束循环")
                break
            
            # 尝试调用 API
            try:
                print("\n🚀 调用 API...")
                # 这里模拟调用，实际上会失败
                await super().invoke_with_console(role="", content="", console_handler=console_handler, max_rounds=1)
            except Exception as e:
                print(f"\n❌ API 调用失败: {e}")
                # 为了调试，我们继续模拟
                break
        
        return final_response


async def test_debug():
    """测试调试流程"""
    print("🚀 开始调试测试...\n")
    
    # 创建项目路径
    project_root = Path(__file__).parent
    
    # 创建配置
    config = AgentConfig.from_env()
    
    # 创建调试 runtime
    runtime = DebugAsyncAgentRuntime(project_root, config)
    
    # 测试
    user_input = "创建一个 test.txt 文件"
    
    try:
        await runtime.invoke_with_console(
            role="user",
            content=user_input,
            max_rounds=3
        )
    except Exception as e:
        print(f"\n最终错误: {e}")


if __name__ == "__main__":
    asyncio.run(test_debug())