#!/usr/bin/env python3
"""调试消息历史格式"""

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


async def debug_messages():
    """调试消息历史格式"""
    print("🔍 调试消息历史格式...\n")
    
    # 创建项目路径
    project_root = Path(__file__).parent
    
    # 创建配置
    config = AgentConfig.from_env()
    
    # 创建 runtime
    runtime = AsyncAgentRuntime(project_root, config)
    
    # 首先添加一个用户消息
    await runtime.create_event(
        role=Role.User,
        event_type=EventType.Message,
        content=TextContent(text="创建一个 test.txt 文件")
    )
    
    # 然后添加一个助手消息带工具调用
    await runtime.create_event(
        role=Role.Assistant,
        event_type=EventType.Message,
        content=[
            TextContent(text="我来创建文件。"),
            ToolUseContent(
                id="test_tool_id_1",
                name="shell",
                input={"command": "touch test.txt"}
            )
        ]
    )
    
    # 添加工具结果
    await runtime.create_event(
        role=Role.User,
        event_type=EventType.ToolResult,
        content=[
            ToolResultContent(
                tool_use_id="test_tool_id_1",
                content="文件创建成功"
            )
        ]
    )
    
    # 打印消息历史
    print("📋 内部消息格式:")
    for i, msg in enumerate(runtime.messages):
        print(f"\n消息 {i}:")
        print(f"  角色: {msg.role}")
        print(f"  类型: {msg.type}")
        print(f"  内容: {msg.content}")
    
    # 转换为 API 格式
    print("\n\n📋 API 消息格式:")
    api_messages = [msg.transform_api() for msg in runtime.messages]
    for i, msg in enumerate(api_messages):
        print(f"\n消息 {i}:")
        print(json.dumps(msg, indent=2, ensure_ascii=False))
    
    # 现在尝试第二轮
    print("\n\n🔄 模拟第二轮调用...")
    
    # 添加第二个助手消息（模拟第一轮的响应）
    await runtime.create_event(
        role=Role.Assistant,
        event_type=EventType.Message,
        content=TextContent(text="文件已创建。现在让我查看一下。")
    )
    
    # 再次打印 API 格式
    print("\n📋 第二轮前的 API 消息格式:")
    api_messages = [msg.transform_api() for msg in runtime.messages]
    for i, msg in enumerate(api_messages):
        print(f"\n消息 {i}:")
        print(json.dumps(msg, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(debug_messages())