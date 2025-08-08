"""统一的工具注册和定义中心"""

from typing import Any


class ToolsRegistry:
    """工具注册中心，集中管理所有工具定义"""

    @staticmethod
    def get_all_tools() -> list[dict[str, Any]]:
        """获取所有工具定义"""
        return [
            {
                "name": "shell",
                "description": (
                    "Execute shell commands in a stateful session. "
                    "The session maintains state (current directory, environment variables, etc). "
                    "Common commands: ls, cat, grep, find, sed, awk, python, git, curl, etc."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Shell command to execute",
                        }
                    },
                    "required": ["command"],
                },
            },
            {
                "name": "edit_file",
                "description": (
                    "Edit specific lines in an existing file. "
                    "Useful for modifying parts of large files without rewriting everything."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path relative to agent_root",
                        },
                        "start_line": {
                            "type": "integer",
                            "description": "Starting line number (1-indexed)",
                        },
                        "end_line": {
                            "type": "integer",
                            "description": "Ending line number (inclusive)",
                        },
                        "new_content": {
                            "type": "string",
                            "description": "New content for the specified lines",
                        },
                    },
                    "required": ["path", "start_line", "end_line", "new_content"],
                },
            },
            {
                "name": "create_file",
                "description": (
                    "Create a new file with content. "
                    "Use this for creating files with large content that would be awkward with echo/cat."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path relative to agent_root",
                        },
                        "content": {
                            "type": "string",
                            "description": "Complete file content",
                        },
                    },
                    "required": ["path", "content"],
                },
            },
            {
                "name": "sync_context",
                "description": (
                    "Update your working memory (context window) and archive conversation history. "
                    "You need to provide the complete new context content including Current Task, "
                    "Working Memory, Active Observations, and Next Steps sections."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "new_context_content": {
                            "type": "string",
                            "description": (
                                "Complete new context window content. Should include sections: "
                                "Current Task, Working Memory, Active Observations, Next Steps"
                            ),
                        }
                    },
                    "required": ["new_context_content"],
                },
            },
        ]

    @staticmethod
    def get_tool_by_name(name: str) -> dict[str, Any] | None:
        """根据名称获取工具定义"""
        for tool in ToolsRegistry.get_all_tools():
            if tool["name"] == name:
                return tool
        return None

    @staticmethod
    def get_tool_names() -> list[str]:
        """获取所有工具名称"""
        return [tool["name"] for tool in ToolsRegistry.get_all_tools()]
