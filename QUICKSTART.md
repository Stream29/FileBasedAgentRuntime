# 快速开始指南

## 1. 安装和配置

```bash
# 克隆项目
git clone <repository-url>
cd FileSystemBasedAgent

# 安装 uv (如果还没有安装)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装依赖
uv sync

# 配置 API Key
cp .env.example .env
# 编辑 .env 文件，填入你的 Anthropic API Key
```

## 2. 启动交互式 Agent

```bash
uv run python -m src.main
```

## 3. 基本使用

### 创建文件
```
👤 You: 创建一个 Python 脚本，打印当前时间

🤖 Agent: [创建脚本并显示内容]
```

### 执行命令
```
👤 You: 运行刚才创建的脚本

🤖 Agent: [执行脚本并显示输出]
```

### 查看状态
```
👤 You: status

[显示当前 context 和对话历史]
```

### 清空历史
```
👤 You: clear

[清空对话历史，重置 context]
```

## 4. 特性说明

- **持久化记忆**: Agent 的记忆通过文件系统持久化，重启后仍然保留
- **智能归档**: 自动将历史对话归档到 `/storage/history/`
- **安全限制**: 所有操作限制在 `agent_root` 目录内
- **可观测性**: 所有操作都有详细日志记录在 `logs/` 目录

## 5. 演示脚本

不需要 API Key 的本地演示：
```bash
uv run python demo.py
```

这会展示 Agent 的文件操作能力，包括：
- 创建和修改文件
- 执行 shell 命令
- 管理 context window
- 归档历史记录

## 6. 故障排除

### API Key 错误
确保 `.env` 文件中的 `ANTHROPIC_API_KEY` 是有效的。

### 网络问题
如果使用代理或自定义端点，设置 `ANTHROPIC_API_BASE`：
```
ANTHROPIC_API_BASE=https://your-proxy.com
```

### 权限问题
确保项目目录有写入权限：
```bash
chmod -R 755 agent_root logs
```