"""专门处理文件编辑的工具"""

from pathlib import Path
from typing import Any


class FileEditor:
    """处理文件创建和编辑操作"""

    def __init__(self, agent_root: Path, logger):
        """
        初始化文件编辑器

        Args:
            agent_root: Agent 的根目录
            logger: 日志记录器
        """
        self.agent_root = agent_root.resolve()
        self.logger = logger

    def edit_file(self, path: str, content: str) -> dict[str, Any]:
        """
        Replace the entire content of an existing file.

        Args:
            path: 文件路径（相对于 agent_root）
            content: 文件的完整新内容

        Returns:
            操作结果字典
        """
        try:
            # 解析文件路径
            file_path = Path(path) if path.startswith("/") else self.agent_root / path

            # 安全检查
            resolved_path = file_path.resolve()
            if not str(resolved_path).startswith(str(self.agent_root)):
                raise ValueError(f"Path {path} is outside agent_root")

            if not resolved_path.exists():
                raise FileNotFoundError(f"File {path} not found")

            if not resolved_path.is_file():
                raise ValueError(f"Path {path} is not a file")

            # 获取原文件信息（用于日志）
            original_size = resolved_path.stat().st_size
            with open(resolved_path, encoding="utf-8") as f:
                original_lines = len(f.readlines())

            # 写入新内容
            with open(resolved_path, "w", encoding="utf-8") as f:
                f.write(content)

            # 计算新文件信息
            new_size = resolved_path.stat().st_size
            new_lines = len(content.splitlines())

            # 记录操作
            result = {
                "success": True,
                "path": str(path),
                "original_lines": original_lines,
                "new_lines": new_lines,
                "size_change": new_size - original_size,
            }

            self.logger.log_operation(
                "edit_file",
                {
                    "path": str(path),
                    "resolved_path": str(resolved_path),
                },
                result,
            )

            return result

        except Exception as e:
            self.logger.log_operation(
                "edit_file",
                {"path": str(path)},
                None,
                str(e),
            )
            raise

    def create_file(self, path: str, content: str) -> dict[str, Any]:
        """
        创建新文件

        Args:
            path: 文件路径（相对于 agent_root）
            content: 文件内容

        Returns:
            操作结果字典
        """
        try:
            # 解析文件路径
            file_path = Path(path) if path.startswith("/") else self.agent_root / path

            # 安全检查
            resolved_path = file_path.resolve()
            if not str(resolved_path).startswith(str(self.agent_root)):
                raise ValueError(f"Path {path} is outside agent_root")

            # 检查文件是否已存在
            if resolved_path.exists():
                raise FileExistsError(f"File {path} already exists")

            # 创建父目录
            resolved_path.parent.mkdir(parents=True, exist_ok=True)

            # 写入文件
            with open(resolved_path, "w", encoding="utf-8") as f:
                f.write(content)

            # 记录操作
            result = {
                "success": True,
                "path": str(path),
                "size": len(content),
                "lines": content.count("\n") + (1 if content and not content.endswith("\n") else 0),
            }

            self.logger.log_operation(
                "create_file",
                {
                    "path": str(path),
                    "content_size": len(content),
                    "resolved_path": str(resolved_path),
                },
                result,
            )

            return result

        except Exception as e:
            self.logger.log_operation(
                "create_file", {"path": str(path)}, None, str(e)
            )
            raise
