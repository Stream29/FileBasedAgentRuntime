#!/usr/bin/env python3
"""测试基本的消息流程"""

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
from src.entities import Role


async def test_basic():
    """测试基本流程"""
    print("🚀 测试基本流程...\n")
    
    # 创建项目路径
    project_root = Path(__file__).parent
    
    # 创建配置
    config = AgentConfig.from_env()
    
    # 创建 runtime
    runtime = AsyncAgentRuntime(project_root, config)
    
    # 先测试一个不需要工具的简单问题
    user_input = "你好，请告诉我现在的日期"
    
    print(f"💭 用户: {user_input}\n")
    
    try:
        # 使用 invoke 而不是 invoke_with_console，以便更好地调试
        response = await runtime.invoke(
            role="user",
            content=user_input,
            max_rounds=2  # 限制为2轮
        )
        
        print(f"\n✅ 响应成功!")
        print(f"文本: {response.text[:100]}..." if response.text else "无文本")
        print(f"工具调用数: {len(response.tool_calls)}")
        
        # 打印最终的消息历史
        print("\n📋 最终消息历史:")
        for i, msg in enumerate(runtime.messages):
            api_msg = msg.transform_api()
            print(f"\n消息 {i} ({api_msg['role']}):")
            if isinstance(api_msg['content'], list):
                for content in api_msg['content']:
                    print(f"  - {content.get('type', 'unknown')}")
            else:
                print(f"  - text")
                
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        
        # 即使出错也打印消息历史
        print("\n📋 出错时的消息历史:")
        for i, msg in enumerate(runtime.messages):
            api_msg = msg.transform_api()
            print(f"\n消息 {i} ({api_msg['role']}):")
            print(json.dumps(api_msg, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(test_basic())