"""状态化的 Shell 会话管理"""

import re
from pathlib import Path
from typing import ClassVar

from .persistent_shell import AsyncPersistentShell, PersistentShell


class StatefulShell:
    """维持状态的 Shell 会话，支持 cd、环境变量等状态保持"""

    # 危险命令模式
    DANGEROUS_PATTERNS: ClassVar[list[str]] = [
        r"\brm\s+-rf\s+/",  # rm -rf /
        r"\bdd\s+if=/dev/(zero|random)",  # dd 危险操作
        r"\bmkfs\b",  # 格式化
        r":\(\)\s*{\s*:\|:&\s*};:",  # Fork bomb
        r"\bsudo\b",  # sudo 命令
        r"\bsu\b",  # su 命令
        r"\bchmod\s+777\s+/",  # 危险权限修改
        r"\b(shutdown|reboot|halt|poweroff)\b",  # 系统控制
        r"\b(kill|killall)\s+-9\s+\d+",  # 强制终止进程
    ]

    def __init__(self, agent_root: Path, logger):
        """
        初始化状态化 Shell

        Args:
            agent_root: Agent 的根目录
            logger: 日志记录器
        """
        self.agent_root = agent_root.resolve()
        self.logger = logger

        # 初始化持久化 Shell
        self.async_persistent_shell = AsyncPersistentShell(self.agent_root, logger)
        self.persistent_shell = PersistentShell(self.agent_root, logger)

        # 当前目录（用于安全检查）
        self.current_dir = self.agent_root

        # 编译危险命令正则
        self.dangerous_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.DANGEROUS_PATTERNS]

    async def execute(self, command: str) -> dict[str, any]:
        """
        执行命令并返回结果

        Args:
            command: 要执行的命令

        Returns:
            包含 stdout, stderr, exit_code, cwd 的字典
        """
        # 安全检查
        safety_check = self._check_command_safety(command)
        if not safety_check[0]:
            return {
                "stdout": "",
                "stderr": f"Command blocked: {safety_check[1]}",
                "exit_code": 1,
                "cwd": str(self.agent_root),
            }

        # 使用持久化 Shell 执行命令
        try:
            result = await self.async_persistent_shell.execute(command)

            # 记录操作
            self.logger.log_operation(
                "shell",
                {
                    "command": command,
                    "cwd": result.get("cwd", str(self.agent_root)),
                },
                {
                    "exit_code": result.get("exit_code", -1),
                    "stdout_size": len(result.get("stdout", "")),
                    "stderr_size": len(result.get("stderr", "")),
                },
            )

            # 更新当前目录（用于安全检查）
            if result.get("cwd"):
                self.current_dir = Path(result["cwd"])

            return result

        except Exception as e:
            self.logger.log_operation("shell", {"command": command}, None, str(e))
            return {
                "stdout": "",
                "stderr": f"Error executing command: {e}",
                "exit_code": -1,
                "cwd": str(self.agent_root),
            }



    def _check_command_safety(self, command: str) -> tuple[bool, str | None]:
        """
        检查命令是否安全

        Returns:
            (是否安全, 错误信息)
        """
        # 检查危险命令
        for regex in self.dangerous_regex:
            if regex.search(command):
                return False, "Dangerous command pattern detected"

        # 检查路径逃逸
        # 简单检查，提取可能的路径参数
        tokens = command.split()
        for _, token in enumerate(tokens):
            # 跳过选项
            if token.startswith("-"):
                continue

            # 检查绝对路径
            if token.startswith("/") and not token.startswith(str(self.agent_root)):
                # 排除一些安全的系统路径
                safe_prefixes = ["/usr/bin", "/usr/local/bin", "/bin", "/tmp", "/dev/null"]
                if not any(token.startswith(prefix) for prefix in safe_prefixes):
                    return False, f"Path outside agent_root: {token}"

            # 检查相对路径中的 ..
            if ".." in token:
                try:
                    # 尝试解析路径
                    potential_path = self.current_dir / token
                    resolved = potential_path.resolve()
                    if not str(resolved).startswith(str(self.agent_root)):
                        return False, f"Path traversal outside agent_root: {token}"
                except Exception:
                    # 不是有效路径，可能是参数，继续
                    pass

        return True, None

    def get_state(self) -> dict[str, any]:
        """获取当前 shell 状态"""
        return {
            "cwd": str(self.current_dir),
            "agent_root": str(self.agent_root),
        }

    def execute_sync(self, command: str) -> dict[str, any]:
        """同步执行命令（用于非异步环境）"""
        # 安全检查
        safety_check = self._check_command_safety(command)
        if not safety_check[0]:
            return {
                "stdout": "",
                "stderr": f"Command blocked: {safety_check[1]}",
                "exit_code": 1,
                "cwd": str(self.agent_root),
            }

        # 使用持久化 Shell 执行命令
        try:
            result = self.persistent_shell.execute(command)

            # 记录操作
            self.logger.log_operation(
                "shell",
                {
                    "command": command,
                    "cwd": result.get("cwd", str(self.agent_root)),
                },
                {
                    "exit_code": result.get("exit_code", -1),
                    "stdout_size": len(result.get("stdout", "")),
                    "stderr_size": len(result.get("stderr", "")),
                },
            )

            # 更新当前目录（用于安全检查）
            if result.get("cwd"):
                self.current_dir = Path(result["cwd"])

            return result

        except Exception as e:
            self.logger.log_operation("shell", {"command": command}, None, str(e))
            return {
                "stdout": "",
                "stderr": f"Error executing command: {e}",
                "exit_code": -1,
                "cwd": str(self.current_dir),
            }
