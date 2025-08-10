"""控制台流式输出处理器"""

import re


class ConsoleStreamHandler:
    """专门处理控制台的流式输出，优化显示效果"""

    def __init__(self):
        self.reset()

    def reset(self):
        """重置状态"""
        self.text_buffer: list[str] = []
        self.last_text_output = ""
        self.repeat_count = 0
        self.total_chars_output = 0
        self.current_tool_name: str | None = None
        self.shown_tool_starts: set[str] = set()

    async def handle_stream_event(self, event):
        """处理单个流式事件用于控制台显示"""
        event_type = event.type

        if event_type == "content_block_start":
            if hasattr(event, 'content_block'):
                block = event.content_block
                if block.type == "tool_use":
                    # 显示工具调用开始
                    tool_id = f"{block.name}_{block.id[:8]}"
                    if tool_id not in self.shown_tool_starts:
                        print(f"\n🔧 调用工具: {block.name}", flush=True)
                        self.shown_tool_starts.add(tool_id)
                        self.current_tool_name = block.name
                elif block.type == "thinking":
                    # 显示思考开始
                    print("\n💭 思考中...", flush=True)

        elif event_type == "content_block_delta":
            if hasattr(event, 'delta'):
                delta = event.delta
                if hasattr(delta, 'text'):
                    # 处理文本
                    self.buffer_text(delta.text)
                elif hasattr(delta, 'partial_json') and self.current_tool_name:
                    # 可选：显示工具输入进度（通常不显示以避免混乱）
                    pass
                elif hasattr(delta, 'thinking'):
                    # 可选：显示思考进度（通常不显示详细内容）
                    pass

        elif event_type == "content_block_stop":
            # 刷新缓冲区
            self.flush_buffer()
            if self.current_tool_name:
                self.current_tool_name = None

        elif event_type == "message_stop":
            # 消息结束，确保所有内容都已输出
            self.flush_buffer()

    def buffer_text(self, text: str):
        """智能文本缓冲，避免重复和过度碎片化"""
        if not text:
            return

        # 检测重复
        if text == self.last_text_output and len(text) > 10:
            self.repeat_count += 1
            if self.repeat_count > 3:
                # 忽略过度重复
                return
        else:
            self.repeat_count = 0
            self.last_text_output = text

        self.text_buffer.append(text)

        # 判断是否应该输出
        should_flush = False
        buffer_text = ''.join(self.text_buffer)

        # 条件1：遇到自然断点
        if text.endswith(('。', '！', '？', '\n', '：', ':', ';', '；')) or len(self.text_buffer) > 5 or len(buffer_text) > 50 or (re.search(r'\s+$', buffer_text) and len(buffer_text.strip()) > 20):
            should_flush = True

        if should_flush:
            self.flush_buffer()

    def flush_buffer(self):
        """输出缓冲区内容"""
        if self.text_buffer:
            output = ''.join(self.text_buffer)
            if output.strip():  # 只输出非空内容
                print(output, end='', flush=True)
                self.total_chars_output += len(output)
            self.text_buffer = []

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "total_chars_output": self.total_chars_output,
            "shown_tool_starts": len(self.shown_tool_starts)
        }
