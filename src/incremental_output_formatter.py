"""增量输出格式化器 - 只输出新增内容，避免重复"""

import json
from typing import Any, Dict, Set, Optional
from collections import defaultdict


class IncrementalOutputFormatter:
    """格式化 Agent 的输出，确保只显示增量内容"""
    
    def __init__(self):
        # 记录已经显示过的内容，避免重复
        self.shown_tool_calls: Set[str] = set()
        self.shown_results: Set[str] = set()
        self.last_sync_context: Optional[str] = None
        self.sync_context_count = 0
        self.file_operations: Dict[str, int] = defaultdict(int)
        
    def format_tool_call(self, tool_name: str, tool_input: Dict[str, Any]) -> Optional[str]:
        """格式化工具调用输出 - 只显示新的调用"""
        
        # 确保 tool_input 是字典类型
        if not isinstance(tool_input, dict):
            tool_input = {"input": str(tool_input)}
        
        # 为工具调用生成唯一标识
        tool_call_id = f"{tool_name}:{json.dumps(tool_input, sort_keys=True)}"
        
        # sync_context 特殊处理 - 只在内容真正变化时显示
        if tool_name == "sync_context":
            new_context = tool_input.get("new_context_content", "")
            if new_context == self.last_sync_context:
                # 内容没变，不显示
                return None
            self.last_sync_context = new_context
            self.sync_context_count += 1
            # 只显示简短信息
            lines = new_context.count('\n')
            return f"\n📝 更新 Context ({lines} 行, 第 {self.sync_context_count} 次更新)"
            
        # 检查是否已经显示过相同的调用
        if tool_call_id in self.shown_tool_calls:
            # 对于某些工具，即使参数相同也可能需要重复执行
            if tool_name in ["shell", "execute_command"]:
                # Shell 命令可能需要重复执行，但标记重复
                return f"\n🔁 重复执行: {self._format_single_tool_call(tool_name, tool_input)}"
            else:
                # 其他工具完全相同的调用不显示
                return None
                
        # 记录这次调用
        self.shown_tool_calls.add(tool_call_id)
        
        return f"\n{self._format_single_tool_call(tool_name, tool_input)}"
        
    def _format_single_tool_call(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """格式化单个工具调用"""
        if tool_name == "shell":
            cmd = tool_input.get("command", "")
            return f"🔧 执行命令: {cmd}"
            
        elif tool_name in ["read_file", "write_file", "edit_file", "create_file"]:
            path = tool_input.get("path", tool_input.get("file_path", tool_input.get("target_file", "")))
            self.file_operations[path] += 1
            op_count = self.file_operations[path]
            
            # 标记是第几次操作这个文件
            count_str = f" (第 {op_count} 次)" if op_count > 1 else ""
            
            if tool_name == "read_file":
                lines = tool_input.get("start_line", "?") 
                end = tool_input.get("end_line", tool_input.get("end_line_one_indexed_inclusive", "?"))
                return f"📖 读取文件: {path} [行 {lines}-{end}]{count_str}"
            elif tool_name == "edit_file":
                lines = tool_input.get("start_line", "?")
                end = tool_input.get("end_line", "?")
                return f"✏️ 编辑文件: {path} [行 {lines}-{end}]{count_str}"
            else:
                return f"📄 {tool_name}: {path}{count_str}"
                
        else:
            # 其他工具显示完整参数
            params_str = json.dumps(tool_input, ensure_ascii=False, indent=2)
            return f"⚙️ 调用工具: {tool_name}\n参数:\n{params_str}"
            
    def format_tool_result(self, tool_id: str, result: Any) -> Optional[str]:
        """格式化工具结果输出 - 智能处理避免冗余"""
        content_str = str(result)
        
        # 为结果生成标识（截取前100字符作为特征）
        result_signature = content_str[:100]
        
        # sync_context 结果特殊处理
        if "sync_context" in content_str or ("status" in content_str and "Context 已更新" in content_str):
            try:
                result_dict = json.loads(content_str) if isinstance(content_str, str) else result
                if result_dict.get("status") == "success":
                    archive = result_dict.get("archive_path", "")
                    message = result_dict.get("message", "")
                    if "清空了" in message:
                        cleared = message.split("清空了")[-1].split("条")[0].strip()
                    else:
                        cleared = ""
                    
                    if archive:
                        return f"\n✅ Context 已更新，归档到: {archive}"
                    elif cleared and cleared.isdigit():
                        return f"\n✅ Context 已更新，清空了 {cleared} 条历史"
                    else:
                        return f"\n✅ Context 已更新"
            except:
                pass
                
        # 命令执行结果
        elif "exit_code" in content_str and "stdout" in content_str:
            try:
                result_dict = json.loads(content_str) if isinstance(content_str, str) else result
                exit_code = result_dict.get("exit_code", "N/A")
                stdout = result_dict.get("stdout", "").strip()
                stderr = result_dict.get("stderr", "").strip()
                
                # 构建输出
                output_parts = [f"\n{'✅' if exit_code == 0 else '❌'} 命令完成 (退出码: {exit_code})"]
                
                # 显示输出（如果有）
                if stdout:
                    # 对于长输出，显示前10行和后5行
                    lines = stdout.split('\n')
                    if len(lines) > 20:
                        shown = lines[:10] + ["... (省略 {} 行) ...".format(len(lines) - 15)] + lines[-5:]
                        stdout = '\n'.join(shown)
                    # 添加缩进使输出更清晰
                    indented_output = '\n'.join('   ' + line for line in stdout.split('\n'))
                    output_parts.append(f"输出:\n{indented_output}")
                    
                if stderr and exit_code != 0:
                    output_parts.append(f"错误:\n{stderr}")
                    
                return '\n'.join(output_parts)
            except:
                pass
                
        # 检查是否已经显示过类似结果
        if result_signature in self.shown_results:
            return None  # 避免重复显示相同结果
            
        self.shown_results.add(result_signature)
        
        # 文件内容结果
        if isinstance(result, dict) and "content" in result:
            content = result["content"]
            lines = content.split('\n') if isinstance(content, str) else []
            return f"\n✅ 读取到 {len(lines)} 行内容"
        elif isinstance(content_str, str) and len(content_str) > 500:
            # 长文本只显示摘要
            lines = content_str.split('\n')
            if len(lines) > 10:
                return f"\n✅ 读取到 {len(lines)} 行内容"
            else:
                return f"\n✅ 读取到 {len(content_str)} 字符"
        else:
            # 简短结果直接显示
            if len(content_str) < 100:
                return f"\n✅ {content_str}"
            else:
                # 其他较长结果做截断
                return f"\n✅ {content_str[:100]}..."
            
    def format_thinking(self, thinking: str) -> Optional[str]:
        """格式化思考过程 - 完整显示"""
        return f"\n💭 思考: {thinking}"
        
    def format_error(self, error: str) -> str:
        """格式化错误输出"""
        return f"\n❌ 错误: {error}"
        
    def reset_for_new_conversation(self):
        """为新对话重置状态"""
        self.shown_tool_calls.clear()
        self.shown_results.clear()
        self.last_sync_context = None
        self.sync_context_count = 0
        self.file_operations.clear()