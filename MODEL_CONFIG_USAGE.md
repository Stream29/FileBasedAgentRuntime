# 模型配置使用说明

## 🎯 新功能：支持从环境变量配置模型

现在你可以通过环境变量 `ANTHROPIC_MODEL` 来选择不同的 Claude 模型了！

## 📋 可用模型

| 模型名称 | 特点 | 适用场景 |
|---------|------|---------|
| `claude-3-5-sonnet-20241022` | 默认，最强大 | 复杂任务、代码生成 |
| `claude-3-5-haiku-20241022` | 更快、更便宜 | 简单任务、快速响应 |
| `claude-3-opus-20240229` | 上一代，非常强大 | 需要稳定性 |
| `claude-3-haiku-20240307` | 上一代，快速 | 简单任务 |

## 🛠️ 使用方法

### 方法 1：通过 .env 文件（推荐）

1. 编辑 `.env` 文件：
```bash
ANTHROPIC_API_KEY=your_api_key_here
ANTHROPIC_MODEL=claude-3-5-haiku-20241022  # 使用更快的模型
```

2. 运行 Agent：
```bash
uv run python main.py
```

### 方法 2：通过环境变量

```bash
# 临时设置
export ANTHROPIC_MODEL=claude-3-5-haiku-20241022
uv run python main.py

# 或一行命令
ANTHROPIC_MODEL=claude-3-5-haiku-20241022 uv run python main.py
```

### 方法 3：查看当前使用的模型

```bash
# 在 Agent 交互中输入
status
# 会显示当前的配置信息
```

## 🔍 验证配置

要验证模型配置是否生效，可以：

1. 启动 Agent
2. 注意观察 Agent 的响应速度和质量
3. Haiku 模型会明显更快，但可能在复杂任务上不如 Sonnet

## 💡 使用建议

- **开发调试**：使用 `claude-3-5-haiku-20241022`，响应快，成本低
- **生产任务**：使用 `claude-3-5-sonnet-20241022`，能力最强
- **成本敏感**：使用 Haiku 系列模型
- **需要稳定性**：使用 Opus 或旧版 Haiku

## ⚠️ 注意事项

1. 模型名称必须完全匹配，包括日期后缀
2. 如果指定了不存在的模型，API 调用会失败
3. 不同模型的 token 限制和能力有所不同
4. 价格差异较大，请根据需求选择

## 📝 更新日志

- 2025-08-09：添加 `ANTHROPIC_MODEL` 环境变量支持
- 支持所有 Claude 3 系列模型
- 保持向后兼容，不设置时使用默认模型