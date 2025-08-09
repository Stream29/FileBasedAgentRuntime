# FileSystem-based Agent 项目状态

## 项目概述

FileSystem-based Agent 是一个创新的 AI Agent 开发框架，采用 **Runtime + State** 分离架构：

- **Runtime**：无状态的工具提供者（src/ 目录）
- **State**：Agent 的完整状态（agent_root/ 目录）

## 当前配置

Agent 当前配置用于 **Dify 工具插件开发**，具备：

### 可用资源
1. **参考文档** (`agent_root/storage/documents/plugins/`)
   - 插件开发快速入门
   - 模式定义和 API 文档
   - 最佳实践指南
   - 发布流程说明

2. **代码示例** (`agent_root/storage/few_shots/`)
   - Google Calendar 插件
   - HackerNews 插件
   - SQLite 插件
   - 工具使用示例

3. **工作空间** (`agent_root/workspace/`)
   - Agent 在此创建和开发新插件

### 当前任务
Agent 正在开发一个简单的计算器插件作为练习，已完成：
- ✅ 项目结构创建
- ✅ YAML 配置文件
- ⏳ Python 代码实现（进行中）

## 使用方法

### 启动 Agent
```bash
uv run python main.py
```

### 常用命令
- `status` - 查看当前状态
- `clear` - 清空对话历史
- `help` - 显示帮助信息
- `exit` - 退出程序

### 与 Agent 交互示例

1. **创建新插件**
   ```
   我需要开发一个天气查询的 Dify 工具插件
   ```

2. **修改现有代码**
   ```
   帮我优化 workspace 中的计算器插件，添加更多数学函数
   ```

3. **查看进度**
   ```
   总结一下当前的开发进度
   ```

## 项目特点

1. **完全透明**：所有 Agent 的思考和操作都保存为文件
2. **可迁移**：整个 agent_root 可以打包迁移
3. **可调试**：通过查看文件了解 Agent 的工作过程
4. **持久化**：Shell 会话保持状态，支持复杂操作

## 相关文档

- `README.md` - 项目介绍和快速开始
- `ARCHITECTURE.md` - 详细架构设计
- `DIFY_PLUGIN_DEVELOPMENT.md` - Dify 插件开发指南
- `mvp_plan.md` - 技术实现细节

## 注意事项

1. Agent 的所有操作都限制在 agent_root 目录内
2. 危险命令会被自动阻止
3. 定期使用 sync_context 保存进度
4. 交互式命令需要使用非交互参数

## 未来展望

- 支持更多类型的开发任务
- 多 Agent 协作能力
- 智能知识管理
- 自动化测试和部署