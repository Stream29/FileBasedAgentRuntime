"""Async agent implementation using direct Anthropic API."""

import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from anthropic import AsyncAnthropic, AsyncMessageStream, MessageStreamEvent
from anthropic.types import TextBlock, TextDelta, ThinkingBlock, ThinkingDelta, ToolUseBlock
from anthropic.types.input_json_delta import InputJsonDelta
from dotenv import load_dotenv

from .config import AgentConfig
from .console_handler import ConsoleStreamHandler
from .entities import (
    ContentDeltaType,
    ContentType,
    Event,
    EventType,
    Role,
    StopReason,
    TextContent,
    ThinkingContent,
    ToolResultContent,
    ToolUseContent,
    Usage,
)
from .file_system_agent import FileSystemAgent
from .stream_processor import CompleteResponse, StreamProcessor
from .tools_registry import ToolsRegistry


class ChunkType(str):
    """Message chunk types"""

    MessageStart = "message_start"
    MessageDelta = "message_delta"
    MessageStop = "message_stop"
    ContentBlockStart = "content_block_start"
    ContentBlockDelta = "content_block_delta"
    ContentBlockStop = "content_block_stop"


class AsyncAgentRuntime:
    """Async agent runtime using direct Anthropic API"""

    def __init__(self, project_root: Path, config: AgentConfig | None = None):
        self.project_root = Path(project_root)
        self.agent = FileSystemAgent("main", "context_window_main.md", project_root)

        # Load environment variables
        load_dotenv()

        # Initialize configuration
        self.config = config or AgentConfig.from_env()
        if not self.config.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")

        # Create Anthropic client
        self._client: AsyncAnthropic | None = None

        # Message history for the current conversation
        self.messages: list[Event] = []

        # Usage tracking
        self.total_usage = Usage()

    @property
    def client(self) -> AsyncAnthropic:
        """Get or create Anthropic client"""
        if self._client is None:
            self._client = AsyncAnthropic(
                api_key=self.config.api_key, base_url=self.config.base_url
            )
        return self._client

    def _format_tools(self) -> list[dict[str, Any]]:
        """Convert tools to Claude API format"""
        # 从统一的工具注册中心获取工具定义
        return ToolsRegistry.get_all_tools()

    def _build_request_params(self) -> dict[str, Any]:
        """Build request parameters"""
        params = self.config.get_request_params()
        params["tools"] = self._format_tools()
        return params

    async def _load_system_context(self) -> str:
        """Load guideline and context window"""
        # This is synchronous for now, matching the original implementation
        guideline_path = self.agent.path_manager.agent_root / "guideline.md"
        context_path = self.agent.path_manager.agent_root / self.agent.context_file

        guideline = guideline_path.read_text(encoding="utf-8") if guideline_path.exists() else ""
        context = context_path.read_text(encoding="utf-8") if context_path.exists() else ""

        # 自动生成文件系统结构
        structure = self._generate_directory_structure()

        return self._build_system_prompt(guideline, context, structure)

    def _build_system_prompt(self, guideline: str, context: str, structure: str) -> str:
        """Build system prompt from components"""
        system_prompt = f"""# 你的行为准则
{guideline}

# 你的当前记忆
{context}

# 你的文件系统结构
{structure}

# 工具使用说明
你可以使用以下工具：
1. shell - 执行命令行工具（优先使用）
   - 支持 ls, cat, grep, sed, awk, python, git, curl 等
   - Shell 会话保持状态，cd 会改变目录
2. edit_file - 编辑文件的特定行（用于大文件）
3. create_file - 创建包含大量内容的新文件
4. sync_context - 更新你的工作记忆

# 重要提醒
1. 优先使用 shell 命令解决问题
2. 所有路径都是真实路径，相对于 {self.agent.path_manager.agent_root}
3. 调用 sync_context 时需要提供完整的新 context 内容
4. 每 3-5 个操作后同步一次，保持 context 精简而完整

当需要使用工具时，请直接调用相应的工具。系统会自动处理工具调用和结果返回。
"""
        return system_prompt

    def _generate_directory_structure(self, max_depth: int = 10) -> str:
        """生成完整的目录树结构"""
        lines = ["```"]
        lines.append("/")

        def walk_directory(path, prefix="", depth=0, is_last_parent=True):
            if depth >= max_depth:
                return

            try:
                # 获取并排序目录内容：先目录后文件
                items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))

                for i, item in enumerate(items):
                    is_last = i == len(items) - 1

                    # 确定前缀
                    if depth == 0:
                        current_prefix = "└── " if is_last else "├── "
                        next_prefix = "    " if is_last else "│   "
                    else:
                        current_prefix = "└── " if is_last else "├── "
                        next_prefix = prefix + ("    " if is_last else "│   ")

                    # 跳过一些系统文件
                    if item.name in [".DS_Store", "__pycache__", ".git", ".gitkeep"]:
                        continue

                    if item.is_dir():
                        # 目录显示
                        lines.append(f"{prefix}{current_prefix}{item.name}/")
                        # 递归处理子目录
                        walk_directory(item, next_prefix, depth + 1, is_last)
                    else:
                        # 文件显示，包含大小信息
                        try:
                            size = item.stat().st_size
                            if size < 1024:
                                size_str = f" ({size}B)"
                            elif size < 1024 * 1024:
                                size_str = f" ({size / 1024:.1f}KB)"
                            else:
                                size_str = f" ({size / 1024 / 1024:.1f}MB)"
                        except Exception:
                            size_str = ""

                        lines.append(f"{prefix}{current_prefix}{item.name}{size_str}")

            except Exception as e:
                lines.append(f"{prefix}[Error: {e}]")

        # 从 agent_root 开始遍历
        walk_directory(self.agent.path_manager.agent_root)
        lines.append("```")

        return "\n".join(lines)

    async def invoke(self, role: str = "user", content: str = "", max_rounds: int = 10) -> CompleteResponse:
        """
        非流式接口，返回完整响应，支持多轮工具调用

        Args:
            role: 消息角色
            content: 消息内容
            max_rounds: 最大轮数（防止无限循环）

        Returns:
            CompleteResponse: 包含完整文本、工具调用、使用情况等
        """
        # 只在有内容时添加初始用户消息（第一轮）
        if role and content:
            await self.create_event(Role(role), EventType.Message, TextContent(text=content))

        # 累积的完整响应
        final_response = CompleteResponse(
            text="",
            tool_calls=[],
            stop_reason=None,
            usage=None,
            thinking=None,
            tool_results=[]
        )

        # 循环处理，最多 max_rounds 轮
        for round_num in range(max_rounds):  # noqa: B007
            # 加载系统上下文
            system_prompt = await self._load_system_context()
            self.config.system_prompt = system_prompt

            # 准备 API 消息
            api_messages = [msg.transform_api() for msg in self.messages]

            # 创建流
            stream_params = {
                "model": self.config.model,
                "messages": api_messages,
                **self._build_request_params(),
                "timeout": self.config.timeout,
            }

            # 添加 beta 特性（如果启用）
            if self.config.beta and self.config.betas():
                stream_call = self.client.beta.messages.stream
                stream_params["betas"] = self.config.betas()
            else:
                stream_call = self.client.messages.stream

            # 使用 StreamProcessor 处理流
            processor = StreamProcessor()

            async with stream_call(**stream_params) as stream:
                response = await processor.process_stream(stream)

            # 累积响应内容
            if response.text:
                final_response.text += response.text

            # 更新使用情况
            final_response.usage = response.usage
            final_response.stop_reason = response.stop_reason

            # 如果有思考内容，累积
            if response.thinking:
                final_response.thinking = (final_response.thinking or "") + response.thinking

            # 创建 assistant 消息（包含文本和工具调用）
            assistant_content = []
            if response.text:
                assistant_content.append(TextContent(text=response.text))
            if response.tool_calls:
                for tool_call in response.tool_calls:
                    assistant_content.append(
                        ToolUseContent(
                            id=tool_call.id,
                            name=tool_call.name,
                            input=tool_call.input
                        )
                    )

            if assistant_content:
                # 如果只有一个 TextContent，可以直接传递；否则必须传递列表
                if len(assistant_content) == 1 and isinstance(assistant_content[0], TextContent):
                    content = assistant_content[0]
                else:
                    content = assistant_content

                await self.create_event(
                    Role.Assistant,
                    EventType.Message,
                    content
                )

            # 如果没有工具调用，结束循环
            if not response.tool_calls:
                break

            # 处理工具调用
            final_response.tool_calls.extend(response.tool_calls)

            # 执行工具并收集结果
            tool_results = []
            for tool_call in response.tool_calls:
                try:
                    result = self.agent.execute_tool(tool_call.name, tool_call.input)
                    tool_results.append(
                        ToolResultContent(
                            tool_use_id=tool_call.id,
                            content=self._format_tool_result(result)
                        )
                    )
                except Exception as e:
                    import traceback
                    error_msg = f"Tool execution error: {e!s}\n\n📋 详细堆栈信息：\n{traceback.format_exc()}"
                    tool_results.append(
                        ToolResultContent(
                            tool_use_id=tool_call.id,
                            content=error_msg
                        )
                    )

            # 将工具结果添加到消息历史
            await self.create_event(
                Role.User,
                EventType.ToolResult,
                tool_results
            )

            # 累积工具结果
            if final_response.tool_results is None:
                final_response.tool_results = []
            final_response.tool_results.extend([r.content for r in tool_results])

            # 如果达到 MaxTokens 或其他停止原因，结束循环
            if response.stop_reason in [StopReason.MaxTokens, StopReason.Refusal]:
                break

        return final_response

    async def invoke_with_console(
        self,
        role: str = "user",
        content: str = "",
        console_handler: ConsoleStreamHandler = None,
        max_rounds: int = 10
    ) -> CompleteResponse:
        """
        带控制台输出的接口，支持多轮工具调用

        Args:
            role: 消息角色
            content: 消息内容
            console_handler: 控制台处理器
            max_rounds: 最大轮数（防止无限循环）

        Returns:
            CompleteResponse: 完整响应
        """
        # 只在有内容时添加初始用户消息（第一轮）
        if role and content:
            await self.create_event(Role(role), EventType.Message, TextContent(text=content))

        # 如果没有提供控制台处理器，创建一个
        if console_handler is None:
            console_handler = ConsoleStreamHandler()

        # 累积的完整响应
        final_response = CompleteResponse(
            text="",
            tool_calls=[],
            stop_reason=None,
            usage=None,
            thinking=None,
            tool_results=[]
        )

        # 循环处理，最多 max_rounds 轮
        for round_num in range(max_rounds):
            # 加载系统上下文
            system_prompt = await self._load_system_context()
            self.config.system_prompt = system_prompt

            # 准备 API 消息
            api_messages = [msg.transform_api() for msg in self.messages]

            # 创建流
            stream_params = {
                "model": self.config.model,
                "messages": api_messages,
                **self._build_request_params(),
                "timeout": self.config.timeout,
            }

            # 添加 beta 特性（如果启用）
            if self.config.beta and self.config.betas():
                stream_call = self.client.beta.messages.stream
                stream_params["betas"] = self.config.betas()
            else:
                stream_call = self.client.messages.stream

            # 使用 StreamProcessor 处理流，同时输出到控制台
            processor = StreamProcessor()

            async with stream_call(**stream_params) as stream:
                response = await processor.process_stream(
                    stream,
                    console_callback=console_handler.handle_stream_event
                )

            # 累积响应内容
            if response.text:
                final_response.text += response.text

            # 更新使用情况
            final_response.usage = response.usage
            final_response.stop_reason = response.stop_reason

            # 如果有思考内容，累积
            if response.thinking:
                final_response.thinking = (final_response.thinking or "") + response.thinking
                if round_num == 0:  # 只在第一轮显示思考过程
                    print(f"\n\n💭 思考过程:\n{response.thinking}")

            # 创建 assistant 消息（包含文本和工具调用）
            assistant_content = []
            if response.text:
                assistant_content.append(TextContent(text=response.text))
            if response.tool_calls:
                for tool_call in response.tool_calls:
                    assistant_content.append(
                        ToolUseContent(
                            id=tool_call.id,
                            name=tool_call.name,
                            input=tool_call.input
                        )
                    )

            if assistant_content:
                # 如果只有一个 TextContent，可以直接传递；否则必须传递列表
                if len(assistant_content) == 1 and isinstance(assistant_content[0], TextContent):
                    content = assistant_content[0]
                else:
                    content = assistant_content

                await self.create_event(
                    Role.Assistant,
                    EventType.Message,
                    content
                )

            # 如果没有工具调用，结束循环
            if not response.tool_calls:
                break

            # 处理工具调用
            final_response.tool_calls.extend(response.tool_calls)

            # 执行工具并收集结果
            tool_results = []
            for tool_call in response.tool_calls:
                try:
                    print(f"\n⚙️ 执行工具: {tool_call.name}")
                    result = self.agent.execute_tool(tool_call.name, tool_call.input)
                    tool_results.append(
                        ToolResultContent(
                            tool_use_id=tool_call.id,
                            content=self._format_tool_result(result)
                        )
                    )
                    print("✅ 工具执行完成")

                    # 显示工具结果
                    if isinstance(result, dict):
                        if result.get("stdout"):
                            print(f"\n📄 工具结果:\n{result['stdout']}")
                        elif result.get("output"):
                            print(f"\n📄 工具结果:\n{result['output']}")
                        elif result.get("stderr"):
                            print(f"\n⚠️ 错误输出:\n{result['stderr']}")
                    elif isinstance(result, str) and result.strip():
                        print(f"\n📄 工具结果:\n{result}")

                except Exception as e:
                    import traceback
                    error_msg = f"Tool execution error: {e!s}\n\n📋 详细堆栈信息：\n{traceback.format_exc()}"
                    tool_results.append(
                        ToolResultContent(
                            tool_use_id=tool_call.id,
                            content=error_msg
                        )
                    )
                    print(f"❌ 工具执行失败: {e}")

            # 将工具结果添加到消息历史
            await self.create_event(
                Role.User,
                EventType.ToolResult,
                tool_results
            )

            # 累积工具结果
            if final_response.tool_results is None:
                final_response.tool_results = []
            final_response.tool_results.extend([r.content for r in tool_results])

            # 如果达到 MaxTokens 或其他停止原因，结束循环
            if response.stop_reason in [StopReason.MaxTokens, StopReason.Refusal]:
                break

        return final_response

    async def create_event(
        self,
        role: Role,
        event_type: EventType,
        content: (
            TextContent | list[ThinkingContent | ToolUseContent | ToolResultContent | TextContent]
        ),
    ) -> Event:
        """Create and store an event"""
        event = Event(id=len(self.messages), role=role, type=event_type, content=content)
        self.messages.append(event)
        return event

    async def run(self, user_input: str) -> str:
        """Run a single turn (non-streaming) - compatible with existing interface"""
        # Collect all content from streaming
        full_response = ""

        async for event in self.invoke_stream(Role.User, user_input):
            if event.type == EventType.Message and event.role == Role.Assistant:
                if isinstance(event.content, TextContent):
                    full_response = event.content.text
                elif isinstance(event.content, list):
                    # Extract text from content list
                    for content in event.content:
                        if isinstance(content, TextContent):
                            full_response += content.text

        return full_response

    async def invoke_stream(
        self, role: Role | None = None, content: str | None = None
    ) -> AsyncIterator[Event]:
        """Stream chat response with full support for text, tool calls, and thoughts"""
        try:
            # Add user message if provided
            if role and content:
                yield await self.create_event(role, EventType.Message, TextContent(text=content))

            # Load system context
            system_prompt = await self._load_system_context()
            self.config.system_prompt = system_prompt

            # Prepare messages for API
            api_messages = [msg.transform_api() for msg in self.messages]

            # Create stream
            stream_params = {
                "model": self.config.model,
                "messages": api_messages,
                **self._build_request_params(),
                "timeout": self.config.timeout,
            }

            # Add beta features if enabled
            if self.config.beta and self.config.betas():
                stream_call = self.client.beta.messages.stream
                stream_params["betas"] = self.config.betas()
            else:
                stream_call = self.client.messages.stream

            async with stream_call(**stream_params) as stream:
                async for item in self._process_stream(stream):
                    yield item

        except Exception as e:
            # Create error event
            yield await self.create_event(
                Role.Assistant, EventType.Error, TextContent(text=f"Error: {e!s}")
            )

    async def _process_stream(
        self,
        stream: AsyncMessageStream,
    ) -> AsyncIterator[Event]:
        """Process the streaming response"""
        current_event: Event | None = None
        tool_uses: list[ToolUseContent] = []

        async for _chunk in stream:
            chunk: MessageStreamEvent = _chunk
            chunk_type = chunk.type

            if chunk_type == ChunkType.MessageStart:
                # Track usage
                usage = chunk.message.usage
                self.total_usage.merge(
                    Usage(
                        cache_creation_input_tokens=usage.cache_creation_input_tokens,
                        cache_read_input_tokens=usage.cache_read_input_tokens,
                        input_tokens=usage.input_tokens,
                        output_tokens=usage.output_tokens,
                    )
                )
                current_event = None
                continue

            if chunk_type == ChunkType.ContentBlockStart:
                content_block_type = chunk.content_block.type

                if content_block_type == ContentType.Text:
                    content_block: TextBlock = chunk.content_block
                    # 只创建事件，不立即输出，等待增量内容
                    current_event = await self.create_event(
                        role=Role.Assistant,
                        event_type=EventType.Message,
                        content=TextContent(text=""),  # 初始为空
                    )

                elif content_block_type == ContentType.Thinking:
                    content_block: ThinkingBlock = chunk.content_block
                    # 只创建事件，不立即输出
                    current_event = await self.create_event(
                        role=Role.Assistant,
                        event_type=EventType.Thinking,
                        content=ThinkingContent(thinking=""),  # 初始为空
                    )

                elif content_block_type == ContentType.ToolUse:
                    content_block: ToolUseBlock = chunk.content_block
                    current_event = await self.create_event(
                        role=Role.Assistant,
                        event_type=EventType.ToolUse,
                        content=[
                            ToolUseContent(
                                id=content_block.id,
                                name=content_block.name,
                                input=content_block.input or "",
                            )
                        ],
                    )
                    # 不要在这里 yield，等到 ContentBlockStop 时再输出完整的工具调用

            if chunk_type == ChunkType.ContentBlockDelta:
                content_block_type = chunk.delta.type

                if content_block_type == ContentDeltaType.Text:
                    delta: TextDelta = chunk.delta
                    # 只输出增量文本，不累积
                    delta_event = await self.create_event(
                        role=Role.Assistant,
                        event_type=EventType.Message,
                        content=TextContent(text=delta.text)
                    )
                    yield delta_event
                    # 累积到当前事件中，用于后续处理
                    if current_event and isinstance(current_event.content, TextContent):
                        current_event.content.text += delta.text

                elif content_block_type == ContentDeltaType.Thinking:
                    delta: ThinkingDelta = chunk.delta
                    # 只输出增量思考内容
                    delta_event = await self.create_event(
                        role=Role.Assistant,
                        event_type=EventType.Thinking,
                        content=ThinkingContent(thinking=delta.thinking)
                    )
                    yield delta_event
                    # 累积到当前事件中
                    if current_event and isinstance(current_event.content, ThinkingContent):
                        current_event.content.thinking += delta.thinking

                elif content_block_type == ContentDeltaType.InputJson:
                    delta: InputJsonDelta = chunk.delta
                    if (
                        current_event
                        and isinstance(current_event.content, list)
                        and current_event.content
                    ):
                        # Get the last content block which should be ToolUseContent
                        last_content = current_event.content[-1]
                        if isinstance(last_content, ToolUseContent):
                            last_content.input = (
                                last_content.input + delta.partial_json
                                if isinstance(last_content.input, str)
                                else delta.partial_json
                            )
                            # 不要在这里 yield，等到工具调用完成时再输出

            if (
                chunk_type == ChunkType.ContentBlockStop
                and current_event
                and current_event.type == EventType.ToolUse
                and isinstance(current_event.content, list)
                and current_event.content
            ):
                tool_use_content = current_event.content[-1]
                if isinstance(tool_use_content, ToolUseContent):
                    # Parse JSON input
                    if isinstance(tool_use_content.input, str):
                        try:
                            tool_use_content.input = json.loads(tool_use_content.input)
                        except json.JSONDecodeError:
                            self.agent.logger.logger.warning(
                                f"Invalid JSON in tool input: {tool_use_content.input}"
                            )
                            tool_use_content.input = {"INVALID_JSON": tool_use_content.input}
                    tool_uses.append(tool_use_content)
                yield current_event  # 只对工具调用输出最终事件
            # 对于文本和思考内容，不在 ContentBlockStop 时输出，避免重复

            if chunk_type == ChunkType.MessageDelta:
                stop_reason = chunk.delta.stop_reason
                usage = chunk.usage
                self.total_usage.merge(
                    Usage(
                        cache_creation_input_tokens=usage.cache_creation_input_tokens,
                        cache_read_input_tokens=usage.cache_read_input_tokens,
                        input_tokens=usage.input_tokens,
                        output_tokens=usage.output_tokens,
                    )
                )

                if stop_reason == StopReason.ToolUse:
                    yield current_event
                    # Handle tool calls
                    async for item in self._handle_tool_calls_stream(tool_uses):
                        yield item

                elif stop_reason in [StopReason.EndTurn, StopReason.MaxTokens]:
                    yield current_event

                elif stop_reason == StopReason.Refusal:
                    yield current_event
                    yield await self.create_event(
                        role=Role.Assistant,
                        event_type=EventType.Error,
                        content=TextContent(text="Model refused to generate response"),
                    )

            if chunk_type == ChunkType.MessageStop:
                yield current_event
                break

    async def _handle_tool_calls_stream(
        self, tool_uses: list[ToolUseContent]
    ) -> AsyncIterator[Event]:
        """Handle tool calls in streaming mode"""
        if not tool_uses:
            # 返回空的异步生成器而不是 None
            return
            yield  # 这行永远不会执行，但让函数成为生成器

        # Create tool result event
        tool_results = []

        for tool_use in tool_uses:
            # Map new tool names to old ones for compatibility
            tool_name = tool_use.name
            tool_params = tool_use.input if isinstance(tool_use.input, dict) else {}

            # Parameter mapping for compatibility
            if tool_name == "read_file":
                mapped_params = {
                    "file_path": tool_params.get("path", ""),
                    "start_line": tool_params.get("start_line"),
                    "end_line": tool_params.get("end_line"),
                }
            elif tool_name == "write_file":
                mapped_params = {
                    "file_path": tool_params.get("path", ""),
                    "content": tool_params.get("content", ""),
                }
            elif tool_name == "list_directory":
                mapped_params = {"dir_path": tool_params.get("path", "")}
            elif tool_name == "execute_command":
                mapped_params = tool_params  # No mapping needed
            elif tool_name == "sync_context":
                mapped_params = {"new_context_content": tool_params.get("new_context_content", "")}
            else:
                mapped_params = tool_params

            # Execute tool
            try:
                result = self.agent.execute_tool(tool_name, mapped_params)
                result_content = self._format_tool_result(result)
                tool_results.append(
                    ToolResultContent(tool_use_id=tool_use.id, content=result_content)
                )
            except Exception as e:
                import traceback
                error_msg = f"Tool execution error: {e!s}\n\n📋 详细堆栈信息：\n{traceback.format_exc()}"
                tool_results.append(
                    ToolResultContent(
                        tool_use_id=tool_use.id, content=error_msg
                    )
                )

        # Create and yield tool result event
        current_event = await self.create_event(
            role=Role.User, event_type=EventType.ToolResult, content=tool_results
        )
        yield current_event

        # Continue conversation
        async for item in self.invoke_stream():
            yield item

    def _format_tool_result(self, result: Any) -> str:
        """Format tool result for display"""
        if isinstance(result, dict):
            if "content" in result:
                return str(result["content"])
            elif "stdout" in result:
                # Command execution result
                output = f"Exit code: {result.get('returncode', 'N/A')}\n"
                if result.get("stdout"):
                    output += f"Output:\n{result['stdout']}"
                if result.get("stderr"):
                    output += f"\nError:\n{result['stderr']}"
                return output
            else:
                return json.dumps(result, ensure_ascii=False, indent=2)
        else:
            return str(result)
