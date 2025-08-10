#!/usr/bin/env python3
"""代码质量检查脚本"""

import subprocess
import sys
from pathlib import Path

# 终端颜色
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"


def run_command(cmd: list[str], description: str) -> bool:
    """运行命令并返回是否成功"""
    print(f"\n{BOLD}🔍 {description}{RESET}")
    print(f"   命令: {' '.join(cmd)}")
    print("-" * 60)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"{GREEN}✅ 通过！{RESET}")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            print(f"{RED}❌ 失败！{RESET}")
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr)
            return False
    except Exception as e:
        print(f"{RED}❌ 错误: {e}{RESET}")
        return False


def main() -> None:
    """运行所有代码检查"""
    print(f"{BOLD}🚀 开始代码质量检查...{RESET}")

    # 检查是否在项目根目录
    if not Path("pyproject.toml").exists():
        print(f"{RED}错误: 请在项目根目录运行此脚本{RESET}")
        sys.exit(1)

    all_passed = True

    # 1. Ruff linting
    if not run_command(
        ["uv", "run", "ruff", "check", "src"],
        "Ruff 代码风格检查"
    ):
        all_passed = False
        print(f"{YELLOW}提示: 可以使用 'uv run ruff check src --fix' 自动修复部分问题{RESET}")

    # 2. Ruff formatting check
    if not run_command(
        ["uv", "run", "ruff", "format", "--check", "src"],
        "Ruff 代码格式检查"
    ):
        all_passed = False
        print(f"{YELLOW}提示: 可以使用 'uv run ruff format src' 自动格式化代码{RESET}")

    # 3. MyPy type checking
    if not run_command(
        ["uv", "run", "mypy", "src"],
        "MyPy 类型检查"
    ):
        all_passed = False
        print(f"{YELLOW}提示: 逐步添加类型注解可以提高代码质量{RESET}")

    # 4. 检查是否有未使用的导入
    if not run_command(
        ["uv", "run", "ruff", "check", "src", "--select", "F401"],
        "检查未使用的导入"
    ):
        all_passed = False

    # 总结
    print("\n" + "=" * 60)
    if all_passed:
        print(f"{GREEN}{BOLD}🎉 所有检查通过！{RESET}")
    else:
        print(f"{RED}{BOLD}⚠️  部分检查失败，请修复后再提交{RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
