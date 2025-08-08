"""Entity classes for agent system."""

import json
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Role(str, Enum):
    """Message role"""

    User = "user"
    Assistant = "assistant"
    System = "system"

    def __str__(self) -> str:
        return self.value


class EventType(str, Enum):
    """Event type"""

    Message = "message"
    ToolUse = "tool_use"
    ToolResult = "tool_result"
    Thinking = "thinking"
    Error = "error"

    def __str__(self) -> str:
        return self.value


class ContentType(str, Enum):
    """Content block type"""

    Text = "text"
    Thinking = "thinking"
    ToolUse = "tool_use"
    ToolResult = "tool_result"

    def __str__(self) -> str:
        return self.value


class ContentDeltaType(str, Enum):
    """Message content delta type"""

    Text = "text_delta"
    InputJson = "input_json_delta"
    Thinking = "thinking_delta"


class StopReason(str, Enum):
    """Stop reason"""

    EndTurn = "end_turn"
    MaxTokens = "max_tokens"
    StopSequence = "stop_sequence"
    ToolUse = "tool_use"
    PauseTurn = "pause_turn"
    Refusal = "refusal"


class Usage(BaseModel):
    """Token usage statistics"""

    cache_creation_input_tokens: int | None = Field(
        default=0, description="Cache creation input tokens"
    )
    cache_read_input_tokens: int | None = Field(default=0, description="Cache read input tokens")
    input_tokens: int | None = Field(default=0, description="Input tokens")
    output_tokens: int | None = Field(default=0, description="Output tokens")

    def merge(self, other: "Usage") -> "Usage":
        """Merge two usage statistics"""
        if other.cache_creation_input_tokens is not None:
            self.cache_creation_input_tokens = (
                self.cache_creation_input_tokens or 0
            ) + other.cache_creation_input_tokens
        if other.cache_read_input_tokens is not None:
            self.cache_read_input_tokens = (
                self.cache_read_input_tokens or 0
            ) + other.cache_read_input_tokens
        if other.input_tokens is not None:
            self.input_tokens = (self.input_tokens or 0) + other.input_tokens
        if other.output_tokens is not None:
            self.output_tokens = (self.output_tokens or 0) + other.output_tokens
        return self

    @property
    def total_tokens(self) -> int:
        """Calculate total tokens"""
        return (self.input_tokens or 0) + (self.output_tokens or 0)


class ContentBlock(BaseModel):
    """Base content block"""

    type: ContentType = Field(description="The type of the content block")


class TextContent(ContentBlock):
    """Text content block"""

    type: ContentType = ContentType.Text
    text: str = Field(description="The text content")


class ThinkingContent(ContentBlock):
    """Thinking content block"""

    type: ContentType = ContentType.Thinking
    thinking: str = Field(description="The thinking content")
    signature: str = Field(default="", description="The signature of the thinking block")


class ToolUseContent(ContentBlock):
    """Tool use content block"""

    type: ContentType = ContentType.ToolUse
    id: str = Field(description="The id of the tool call")
    name: str = Field(description="The name of the tool")
    input: str | dict[str, Any] = Field(default="", description="The input parameters")


class ToolResultContent(ContentBlock):
    """Tool result content block"""

    type: ContentType = ContentType.ToolResult
    tool_use_id: str = Field(description="The id of the tool use")
    content: str | dict[str, Any] | list[str | dict[str, Any]] = Field(
        default="", description="The result content"
    )


class Event(BaseModel):
    """Event representing a message or action"""

    id: int | None = Field(default=None, description="Event id")
    role: Role = Field(description="The role of the event")
    type: EventType = Field(description="The type of the event")
    created_at: datetime = Field(default_factory=datetime.now, description="Created timestamp")
    content: (
        TextContent | list[ThinkingContent | ToolUseContent | ToolResultContent | TextContent]
    ) = Field(description="The content of the event")

    def tail(self) -> ContentBlock | None:
        """Get the last content block"""
        if isinstance(self.content, list):
            return self.content[-1] if self.content else None
        return self.content

    def transform_api(self) -> dict[str, Any]:
        """Convert event to Claude API message format"""

        # Handle content conversion
        if isinstance(self.content, ContentBlock):
            # Single content block
            content = [self.content.model_dump()]
        else:
            # List of content blocks
            content = []
            for item in self.content:
                item_dict = item.model_dump()

                # Ensure tool use inputs are always dictionaries for the API
                if (
                    item_dict.get("type") == "tool_use"
                    and "input" in item_dict
                    and isinstance(item_dict["input"], str)
                ):
                    try:
                        item_dict["input"] = json.loads(item_dict["input"])
                    except json.JSONDecodeError:
                        # If it's not valid JSON, wrap it in a dict
                        item_dict["input"] = {"text": item_dict["input"]}

                content.append(item_dict)

        return {"role": str(self.role), "content": content}
