"""流式处理器 - 处理 Anthropic API 流并聚合完整数据"""

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    """工具调用"""
    id: str
    name: str
    input: dict[str, Any]


@dataclass
class CompleteResponse:
    """完整的响应"""
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str | None = None
    usage: dict[str, int] | None = None
    thinking: str | None = None  # 思考过程（如果有）
    tool_results: list[Any] | None = None  # 工具执行结果


class StreamProcessor:
    """处理 Anthropic 流式 API，输出完整的数据块"""

    def __init__(self):
        self.reset()

    def reset(self):
        """重置状态"""
        self.text_buffer = []
        self.thinking_buffer = []
        self.current_tool_use = None
        self.tool_uses = []
        self.stop_reason = None
        self.usage = None

    async def process_stream(
        self,
        stream,
        console_callback: Callable | None = None
    ) -> CompleteResponse:
        """
        处理流式事件

        Args:
            stream: Anthropic 的原始流
            console_callback: 控制台实时显示的回调函数

        Returns:
            完整的结构化响应
        """
        self.reset()

        async for event in stream:
            # 1. 实时输出到控制台（如果提供了回调）
            if console_callback:
                await console_callback(event)

            # 2. 根据事件类型聚合数据
            if event.type == "message_start":
                # 初始化使用情况
                if hasattr(event, 'message') and hasattr(event.message, 'usage'):
                    self.usage = {
                        "input_tokens": event.message.usage.input_tokens,
                        "output_tokens": event.message.usage.output_tokens
                    }

            elif event.type == "content_block_start":
                block = event.content_block
                if block.type == "text":
                    # 文本块开始
                    pass
                elif block.type == "tool_use":
                    # 工具调用开始
                    self.current_tool_use = {
                        "id": block.id,
                        "name": block.name,
                        "input_json": ""
                    }
                elif block.type == "thinking":
                    # 思考模式开始
                    pass

            elif event.type == "content_block_delta":
                delta = event.delta
                if hasattr(delta, 'text'):
                    # 累积文本
                    self.text_buffer.append(delta.text)
                elif hasattr(delta, 'partial_json'):
                    # 累积工具输入
                    if self.current_tool_use:
                        self.current_tool_use["input_json"] += delta.partial_json
                elif hasattr(delta, 'thinking'):
                    # 累积思考内容
                    self.thinking_buffer.append(delta.thinking)

            elif event.type == "content_block_stop":
                # 完成一个内容块
                if self.current_tool_use:
                    # 解析工具输入
                    try:
                        tool_input = json.loads(self.current_tool_use["input_json"])
                    except json.JSONDecodeError:
                        tool_input = {"error": "Failed to parse input", "raw": self.current_tool_use["input_json"]}

                    self.tool_uses.append(ToolCall(
                        id=self.current_tool_use["id"],
                        name=self.current_tool_use["name"],
                        input=tool_input
                    ))
                    self.current_tool_use = None

            elif event.type == "message_delta":
                # 更新停止原因和使用情况
                if hasattr(event, 'delta') and hasattr(event.delta, 'stop_reason'):
                    self.stop_reason = event.delta.stop_reason
                if hasattr(event, 'usage') and hasattr(event.usage, 'output_tokens'):
                    if self.usage:
                        self.usage["output_tokens"] = event.usage.output_tokens
                    else:
                        self.usage = {"output_tokens": event.usage.output_tokens}

        # 返回完整的响应
        return CompleteResponse(
            text="".join(self.text_buffer),
            tool_calls=self.tool_uses,
            stop_reason=self.stop_reason,
            usage=self.usage,
            thinking="".join(self.thinking_buffer) if self.thinking_buffer else None
        )
