#!/usr/bin/env python3
"""修复 tool_result 消息问题的示例"""

import asyncio
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 加载环境变量
load_dotenv()

from anthropic import AsyncAnthropic
from src.config import AgentConfig


async def test_correct_message_flow():
    """测试正确的消息流程"""
    print("🔍 测试正确的消息流程...\n")
    
    # 创建配置
    config = AgentConfig.from_env()
    
    # 创建客户端
    client = AsyncAnthropic(
        api_key=config.api_key,
        base_url=config.base_url,
    )
    
    # 构建消息历史
    messages = [
        {
            "role": "user",
            "content": "创建一个 test.txt 文件"
        },
        {
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": "我来创建文件。"
                },
                {
                    "type": "tool_use",
                    "id": "test_tool_id_1",
                    "name": "create_file",
                    "input": {
                        "path": "test.txt",
                        "content": "Hello World"
                    }
                }
            ]
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "test_tool_id_1",
                    "content": "文件创建成功"
                }
            ]
        }
    ]
    
    print("📋 当前消息历史:")
    for i, msg in enumerate(messages):
        print(f"\n消息 {i}: {msg['role']}")
        if isinstance(msg['content'], list):
            for content in msg['content']:
                print(f"  - {content.get('type', 'text')}")
    
    # 这里的关键是：最后一条消息是 tool_result，API 不允许这样
    # 我们需要调用 API 让 assistant 基于 tool_result 继续响应
    
    print("\n\n🔄 调用 API 继续对话...")
    try:
        # 创建流
        async with client.messages.stream(
            model=config.model,
            messages=messages,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
            tools=[
                {
                    "name": "create_file",
                    "description": "Create a file",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "content": {"type": "string"}
                        },
                        "required": ["path", "content"]
                    }
                }
            ]
        ) as stream:
            collected_text = []
            async for event in stream:
                if event.type == "content_block_delta":
                    if hasattr(event.delta, 'text') and event.delta.text:
                        collected_text.append(event.delta.text)
                        print(event.delta.text, end="", flush=True)
            
            print("\n\n✅ API 调用成功！")
            print(f"收集到的文本: {''.join(collected_text)}")
            
    except Exception as e:
        print(f"\n❌ API 调用失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_correct_message_flow())