.PHONY: help install check format lint type test run clean

# 默认目标
help:
	@echo "可用的命令："
	@echo "  make install  - 安装依赖"
	@echo "  make check    - 运行所有代码检查"
	@echo "  make format   - 自动格式化代码"
	@echo "  make lint     - 运行 linting 检查"
	@echo "  make type     - 运行类型检查"
	@echo "  make test     - 运行测试"
	@echo "  make run      - 运行 Agent"
	@echo "  make clean    - 清理临时文件"

# 安装依赖
install:
	uv sync

# 运行所有检查
check:
	@python check.py

# 自动格式化代码
format:
	uv run ruff format src
	uv run ruff check src --fix

# 只运行 linting
lint:
	uv run ruff check src

# 只运行类型检查
type:
	uv run mypy src

# 运行测试
test:
	uv run pytest tests/ -v

# 运行 Agent
run:
	uv run python -m src.main

# 清理临时文件
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +