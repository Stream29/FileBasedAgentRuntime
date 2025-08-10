# Prompt文件更新说明 - 2024-08-10

## 更新概述

本次更新将Agent的prompt文件专门优化为Tools插件开发专用版本，强调实用性和信息完整性。

## 主要变更

### 1. guideline.md 更新
- **原文件**：已备份为 `guideline_backup_[timestamp].md`
- **新文件**：专注于Tools插件开发的详细指南
- **核心改进**：
  - 明确文件位置：第一行说明位于 `{agent_root}/guideline.md`
  - 删除了完整的开发流程（用户已简化）
  - 强调信息收集的完整性
  - 保留了Context管理要求

### 2. context_window_main.md 更新
- **原文件**：已备份为 `context_window_backup_[timestamp].md`  
- **新文件**：预置了Tools插件开发的基础知识
- **核心改进**：
  - 简化了模板内容（用户已精简）
  - 保留了文件结构说明
  - 强调信息完整性和丰富性

### 3. 保留的参考文件
- `guideline_tools_plugin_focused.md` - 完整版guideline（供参考）
- `context_window_tools_ready.md` - 完整版context模板（供参考）
- `prompt_improvement_plan_tools_focused.md` - 改进方案说明

### 4. 已删除的文件
- `guideline_v2_example.md` - 通用版本guideline
- `context_window_template.md` - 通用版本context模板
- `prompt_improvement_plan.md` - 通用版本改进方案

## 使用说明

1. **Agent将使用更新后的文件**：
   - `agent_root/guideline.md` - 行为准则
   - `agent_root/context_window_main.md` - 工作记忆

2. **备份文件位置**：
   - `agent_root/guideline_backup_*.md`
   - `agent_root/context_window_backup_*.md`

3. **恢复原版本**：
   ```bash
   cd agent_root
   cp guideline_backup_*.md guideline.md
   cp context_window_backup_*.md context_window_main.md
   ```

## 核心理念

本次更新的核心理念是：
- **专注性**：只做Tools插件开发
- **实用性**：功能实现优先于代码质量
- **完整性**：宁可信息冗余，不可遗漏重要信息
- **快速交付**：2小时内产出可用插件

## 后续建议

1. 在实际使用中验证效果
2. 根据Agent反馈持续优化
3. 积累成功案例到guideline中
4. 定期清理过时信息

## 更新记录

### 2024-08-10 23:50
- 添加了 **Dify YAML配置详细规定** 章节到context_window_main.md
- 包含了provider.yaml、tool.yaml、manifest.yaml的详细配置规范
- 基于官方文档验证，修正了语言代码（ja_JP）等细节
- 提供了完整的参数类型列表和常见错误示例
- 新增了432行context内容，帮助Agent避免YAML配置错误

---

更新人：用户与AI协作
更新时间：2024-08-10