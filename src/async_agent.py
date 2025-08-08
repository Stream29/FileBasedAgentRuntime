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
        # Define our tools with their schemas
        tool_definitions = [
            {
                "name": "read_file",
                "description": (
                    "Read the contents of a file. Use agent-perspective paths "
                    "like /workspace/file.txt"
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": (
                                "The file path from agent's perspective (e.g., /workspace/file.txt)"
                            ),
                        },
                        "start_line": {
                            "type": "integer",
                            "description": "Start line number (1-indexed, optional)",
                        },
                        "end_line": {
                            "type": "integer",
                            "description": "End line number (inclusive, optional)",
                        },
                    },
                    "required": ["path"],
                },
            },
            {
                "name": "write_file",
                "description": "Write content to a file. Creates the file if it doesn't exist.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "The file path from agent's perspective",
                        },
                        "content": {"type": "string", "description": "The content to write"},
                    },
                    "required": ["path", "content"],
                },
            },
            {
                "name": "list_directory",
                "description": "List contents of a directory",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "The directory path from agent's perspective",
                        }
                    },
                    "required": ["path"],
                },
            },
            {
                "name": "execute_command",
                "description": "Execute a shell command",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The shell command to execute",
                        },
                        "working_dir": {
                            "type": "string",
                            "description": "Working directory (optional, defaults to /workspace)",
                        },
                    },
                    "required": ["command"],
                },
            },
            {
                "name": "sync_context",
                "description": (
                    "更新 context window 并清空临时对话历史。你需要全量生成新的 context 内容，"
                    "包括任务状态、工作记忆、观察结果等。"
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "new_context_content": {
                            "type": "string",
                            "description": (
                                "新的 context window 完整内容，应包含 Current Task、"
                                "Working Memory、Active Observations、Next Steps 等部分"
                            ),
                        }
                    },
                    "required": ["new_context_content"],
                },
            },
        ]

        return tool_definitions

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
        workspace_structure_path = self.agent.path_manager.agent_root / "workspace_structure.md"

        guideline = guideline_path.read_text(encoding="utf-8") if guideline_path.exists() else ""
        context = context_path.read_text(encoding="utf-8") if context_path.exists() else ""
        structure = (
            workspace_structure_path.read_text(encoding="utf-8")
            if workspace_structure_path.exists()
            else ""
        )

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
你可以使用以下工具来完成任务：
- read_file: 读取文件内容
- write_file: 写入或创建文件
- list_directory: 列出目录内容
- execute_command: 执行 shell 命令
- sync_context: 更新你的工作记忆（需要提供完整的新 context 内容）

# 重要提醒
1. 调用 sync_context 时，你需要全量生成新的 context window 内容
2. 包括 Current Task、Working Memory、Active Observations、Next Steps 等部分
3. 自己决定什么信息该保留（热数据）和什么该归档（冷数据）
4. 每 3-5 个操作后同步一次，保持 context 精简而完整

当需要使用工具时，请直接调用相应的工具。系统会自动处理工具调用和结果返回。
"""
        return system_prompt

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
                    current_event = await self.create_event(
                        role=Role.Assistant,
                        event_type=EventType.Message,
                        content=TextContent(text=content_block.text),
                    )
                    yield current_event

                elif content_block_type == ContentType.Thinking:
                    content_block: ThinkingBlock = chunk.content_block
                    current_event = await self.create_event(
                        role=Role.Assistant,
                        event_type=EventType.Thinking,
                        content=ThinkingContent(thinking=content_block.thinking),
                    )
                    yield current_event

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
                    yield current_event

            if chunk_type == ChunkType.ContentBlockDelta:
                content_block_type = chunk.delta.type

                if content_block_type == ContentDeltaType.Text:
                    delta: TextDelta = chunk.delta
                    if current_event and isinstance(current_event.content, TextContent):
                        current_event.content.text += delta.text
                        yield current_event

                elif content_block_type == ContentDeltaType.Thinking:
                    delta: ThinkingDelta = chunk.delta
                    if current_event and isinstance(current_event.content, ThinkingContent):
                        current_event.content.thinking += delta.thinking
                        yield current_event

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
                            yield current_event

            if chunk_type == ChunkType.ContentBlockStop:
                if (
                    current_event
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
                yield current_event

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
            return

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
                tool_results.append(
                    ToolResultContent(
                        tool_use_id=tool_use.id, content=f"Tool execution error: {e!s}"
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
