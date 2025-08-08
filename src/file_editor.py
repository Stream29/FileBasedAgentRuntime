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

    def edit_file(
        self, path: str, start_line: int, end_line: int, new_content: str
    ) -> dict[str, Any]:
        """
        编辑文件的指定行

        Args:
            path: 文件路径（相对于 agent_root）
            start_line: 起始行号（1-indexed）
            end_line: 结束行号（包含）
            new_content: 新内容

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

            # 读取文件
            with open(resolved_path, encoding="utf-8") as f:
                lines = f.readlines()

            # 验证行号
            total_lines = len(lines)
            if start_line < 1 or start_line > total_lines:
                raise ValueError(
                    f"start_line {start_line} out of range (file has {total_lines} lines)"
                )
            if end_line < start_line:
                raise ValueError("end_line must be >= start_line")
            if end_line > total_lines:
                raise ValueError(
                    f"end_line {end_line} out of range (file has {total_lines} lines)"
                )

            # 准备新内容
            new_lines = new_content.split("\n")
            # 确保每行都有换行符（除了可能的最后一行）
            for i in range(len(new_lines) - 1):
                if not new_lines[i].endswith("\n"):
                    new_lines[i] += "\n"
            # 最后一行的处理
            if new_lines and not new_content.endswith("\n"):
                # 如果原内容没有以换行结尾，最后一行也不加
                pass
            elif new_lines:
                # 如果原内容以换行结尾，最后一行也加上
                new_lines[-1] += "\n"

            # 构建新文件内容
            result_lines = lines[: start_line - 1] + new_lines + lines[end_line:]

            # 写回文件
            with open(resolved_path, "w", encoding="utf-8") as f:
                f.writelines(result_lines)

            # 记录操作
            result = {
                "success": True,
                "path": str(path),
                "lines_replaced": end_line - start_line + 1,
                "new_lines": len(new_lines),
                "total_lines": len(result_lines),
            }

            self.logger.log_operation(
                "edit_file",
                {
                    "path": str(path),
                    "start_line": start_line,
                    "end_line": end_line,
                    "resolved_path": str(resolved_path),
                },
                result,
            )

            return result

        except Exception as e:
            self.logger.log_operation(
                "edit_file",
                {"path": str(path), "start_line": start_line, "end_line": end_line},
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
