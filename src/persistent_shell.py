"""持久化 Shell 会话的实现，使用 pexpect 维持真正的 shell 进程"""

import asyncio
import contextlib
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, ClassVar

import pexpect


class PersistentShell:
    """使用 pexpect 维持的持久化 Shell 会话"""

    # 默认提示符模式
    PROMPT_PATTERNS: ClassVar[list[str]] = [
        r'\$ $',         # 普通用户 $
        r'# $',          # root 用户 #
        r'> $',          # 多行输入 >
        r'\]$ $',        # 自定义提示符结尾 ]$
        r'\]\$ $',       # 自定义提示符结尾 ]$
    ]

    # 交互式命令模式
    INTERACTIVE_PATTERNS: ClassVar[list[str]] = [
        r'[Pp]assword:',
        r'\(y/n\)',
        r'\(yes/no\)',
        r'Press any key',
        r'Are you sure',
        r'Do you want to continue',
    ]

    def __init__(self, working_dir: Path, logger=None, timeout: int = 30):
        self.working_dir = Path(working_dir).resolve()
        self.logger = logger
        self.shell: pexpect.spawn | None = None
        self.prompt_pattern: str = self.PROMPT_PATTERNS[0]  # 初始提示符
        self.timeout = timeout
        self._initialize_shell()

    def _initialize_shell(self):
        """初始化持久化的 shell 进程"""
        if self.shell and self.shell.isalive():
            self.shell.close()

        env = os.environ.copy()
        # 设置自定义提示符，便于准确识别命令结束
        env['PS1'] = '\\u@\\h:\\w\\]\\$ '
        env['PS2'] = '> '

        self.shell = pexpect.spawn(
            '/bin/bash',
            cwd=str(self.working_dir),
            env=env,
            encoding='utf-8',
            timeout=self.timeout
        )

        # 等待初始提示符
        try:
            index = self.shell.expect(self.PROMPT_PATTERNS, timeout=5)
            self.prompt_pattern = self.PROMPT_PATTERNS[index]
        except pexpect.TIMEOUT:
            # 如果没有匹配到提示符，使用默认的
            pass

        # 设置 AGENT_ROOT 环境变量
        self.shell.sendline(f'export AGENT_ROOT="{self.working_dir}"')
        self.shell.expect(self.prompt_pattern)

    def execute(self, command: str) -> dict[str, Any]:
        """执行命令并返回结果"""
        if not self.shell or not self.shell.isalive():
            self._initialize_shell()

        if self.logger:
            self.logger.logger.info(f"Executing: {command}")

        # 清理之前的缓冲区，忽略超时
        with contextlib.suppress(pexpect.TIMEOUT):
            self.shell.expect(pexpect.TIMEOUT, timeout=0.1)

        # 发送命令
        self.shell.sendline(command)

        output_lines = []
        command_echo_skipped = False

        while True:
            try:
                # 等待提示符或交互式提示
                index = self.shell.expect(
                    self.PROMPT_PATTERNS + self.INTERACTIVE_PATTERNS + ['\r\n', pexpect.TIMEOUT],
                    timeout=self.timeout
                )

                if index < len(self.PROMPT_PATTERNS):
                    # 找到提示符，命令执行完成
                    self.prompt_pattern = self.PROMPT_PATTERNS[index]
                    before = self.shell.before
                    if before:
                        lines = before.split('\n')
                        # 跳过命令回显
                        if not command_echo_skipped and lines and lines[0].strip() == command.strip():
                            lines = lines[1:]
                            command_echo_skipped = True
                        output_lines.extend(lines)
                    break

                elif index < len(self.PROMPT_PATTERNS) + len(self.INTERACTIVE_PATTERNS):
                    # 检测到交互式提示
                    pattern_index = index - len(self.PROMPT_PATTERNS)
                    pattern = self.INTERACTIVE_PATTERNS[pattern_index]
                    if self.logger:
                        self.logger.logger.warning(f"Interactive command detected: {pattern}. Sending Ctrl+C.")
                    self.shell.sendcontrol('c')  # 发送 Ctrl+C 取消
                    # 等待提示符
                    self.shell.expect(self.prompt_pattern)
                    return {
                        'stdout': '\n'.join(output_lines),
                        'stderr': f'Interactive command detected: {pattern}. Command cancelled.',
                        'exit_code': 130,  # Ctrl+C 的退出码
                        'cwd': str(self._get_current_dir())
                    }

                elif index == len(self.PROMPT_PATTERNS) + len(self.INTERACTIVE_PATTERNS):
                    # 新行
                    line = self.shell.before
                    if line:
                        # 跳过命令回显
                        if not command_echo_skipped and line.strip() == command.strip():
                            command_echo_skipped = True
                        else:
                            output_lines.append(line)

                else:
                    # 超时，继续等待或中断
                    if self.logger:
                        self.logger.logger.warning(f"Command still running after {self.timeout}s, waiting...")
                    continue

            except pexpect.TIMEOUT:
                # 真正超时，发送 Ctrl+C
                if self.logger:
                    self.logger.logger.error(f"Command timed out after {self.timeout}s. Sending Ctrl+C.")
                self.shell.sendcontrol('c')
                try:
                    self.shell.expect(self.prompt_pattern, timeout=5)
                except pexpect.TIMEOUT:
                    # 如果 Ctrl+C 也无效，重新初始化 shell
                    self._initialize_shell()
                return {
                    'stdout': '\n'.join(output_lines),
                    'stderr': 'Command timed out',
                    'exit_code': -1,
                    'cwd': str(self.working_dir)
                }
            except pexpect.EOF:
                # Shell 进程意外终止
                if self.logger:
                    self.logger.logger.error("Shell process terminated unexpectedly")
                self._initialize_shell()
                return {
                    'stdout': '\n'.join(output_lines),
                    'stderr': 'Shell process terminated',
                    'exit_code': -1,
                    'cwd': str(self.working_dir)
                }

        # 获取退出码
        self.shell.sendline('echo "EXIT_CODE:$?"')
        self.shell.expect(r'EXIT_CODE:(\d+)')
        exit_code = int(self.shell.match.group(1))
        self.shell.expect(self.prompt_pattern)

        # 清理输出中的 EXIT_CODE 行
        if output_lines and output_lines[-1].strip().startswith('EXIT_CODE:'):
            output_lines.pop()

        if self.logger:
            self.logger.logger.info(f"Command completed with exit code: {exit_code}")

        return {
            'stdout': '\n'.join(output_lines).strip(),
            'stderr': '',  # pexpect 不分离 stderr
            'exit_code': exit_code,
            'cwd': str(self._get_current_dir())
        }

    def _get_current_dir(self) -> Path:
        """获取当前工作目录"""
        self.shell.sendline('pwd')
        self.shell.expect(self.prompt_pattern)
        output = self.shell.before.strip().split('\n')
        # 跳过 pwd 命令本身，获取输出
        if len(output) > 1:
            return Path(output[1].strip())
        return self.working_dir

    def close(self) -> None:
        """关闭 shell 进程"""
        if self.shell and self.shell.isalive():
            self.shell.close()
        self.shell = None

    def __del__(self):
        """析构函数，确保清理资源"""
        self.close()


class AsyncPersistentShell:
    """异步版本的持久化 Shell"""

    def __init__(self, working_dir: Path, logger=None, timeout: int = 30):
        self.working_dir = Path(working_dir).resolve()
        self.logger = logger
        self.timeout = timeout
        self.persistent_shell = PersistentShell(working_dir, logger, timeout)
        self._executor = ThreadPoolExecutor(max_workers=1)  # 单线程执行器确保命令顺序

    async def execute(self, command: str) -> dict[str, Any]:
        """异步执行命令"""
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            self.persistent_shell.execute,
            command
        )
        return result

    def close(self) -> None:
        """关闭资源"""
        self.persistent_shell.close()
        self._executor.shutdown(wait=True)

    def __del__(self):
        """析构函数"""
        self.close()
