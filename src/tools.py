"""Observable tools for the agent."""

import subprocess
import shlex
from pathlib import Path
from typing import Optional, List, Dict, Any

from .logger import OperationLogger
from .path_manager import PathManager


class ObservableTools:
    """提供基础工具，所有操作都被记录"""
    
    def __init__(self, logger: OperationLogger, path_manager: PathManager):
        self.logger = logger
        self.path_manager = path_manager
        
    def read_file(self, file_path: str, 
                  start_line: Optional[int] = None,
                  end_line: Optional[int] = None) -> str:
        """读取文件内容"""
        try:
            resolved_path = self.path_manager.resolve_agent_path(file_path)
            
            with open(resolved_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # 处理行范围
            if start_line is not None and end_line is not None:
                # 转换为 0-indexed
                start_idx = max(0, start_line - 1)
                end_idx = min(len(lines), end_line)
                result = ''.join(lines[start_idx:end_idx])
            else:
                result = ''.join(lines)
                
            self.logger.log_operation('read_file', {
                'file_path': file_path,
                'start_line': start_line,
                'end_line': end_line,
                'resolved_path': str(resolved_path),
                'size': len(result)
            }, f"Read {len(result)} characters")
            
            return result
            
        except Exception as e:
            self.logger.log_operation('read_file', 
                                    {'file_path': file_path}, 
                                    None, str(e))
            raise
            
    def write_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """写入文件（覆盖）"""
        try:
            resolved_path = self.path_manager.resolve_agent_path(file_path)
            
            # 确保父目录存在
            resolved_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入文件
            with open(resolved_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            result = {
                'path': file_path,
                'size': len(content),
                'lines': content.count('\n') + 1 if content else 0
            }
            
            self.logger.log_operation('write_file', {
                'file_path': file_path,
                'content_size': len(content),
                'resolved_path': str(resolved_path)
            }, result)
            
            return result
            
        except Exception as e:
            self.logger.log_operation('write_file',
                                    {'file_path': file_path},
                                    None, str(e))
            raise
            
    def list_directory(self, dir_path: str) -> List[Dict[str, Any]]:
        """列出目录内容"""
        try:
            resolved_path = self.path_manager.resolve_agent_path(dir_path)
            
            if not resolved_path.exists():
                raise FileNotFoundError(f"{dir_path} does not exist")
                
            if not resolved_path.is_dir():
                raise NotADirectoryError(f"{dir_path} is not a directory")
                
            items = []
            for item in sorted(resolved_path.iterdir()):
                item_info = {
                    'name': item.name,
                    'type': 'directory' if item.is_dir() else 'file',
                    'size': item.stat().st_size if item.is_file() else None
                }
                
                # 对于目录，计算子项数量
                if item.is_dir():
                    try:
                        item_info['items'] = len(list(item.iterdir()))
                    except:
                        item_info['items'] = 0
                        
                items.append(item_info)
                
            self.logger.log_operation('list_directory', {
                'dir_path': dir_path,
                'resolved_path': str(resolved_path)
            }, f"Found {len(items)} items")
            
            return items
            
        except Exception as e:
            self.logger.log_operation('list_directory',
                                    {'dir_path': dir_path},
                                    None, str(e))
            raise
            
    def execute_command(self, command: str, 
                       working_dir: Optional[str] = None) -> Dict[str, Any]:
        """执行 shell 命令"""
        try:
            # 解析工作目录
            if working_dir:
                cwd = self.path_manager.resolve_agent_path(working_dir)
            else:
                cwd = self.path_manager.workspace
                
            self.logger.logger.info(f"Executing: {command}")
            self.logger.logger.info(f"Working dir: {cwd}")
            
            # 执行命令
            result = subprocess.run(
                command,
                shell=True,  # 使用 shell 以支持管道等功能
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            output = {
                'command': command,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode,
                'success': result.returncode == 0
            }
            
            self.logger.log_operation('execute_command', {
                'command': command,
                'working_dir': working_dir,
                'cwd': str(cwd)
            }, {
                # 只记录部分输出避免日志过大
                'stdout_preview': result.stdout[:500] if result.stdout else '',
                'stderr_preview': result.stderr[:500] if result.stderr else '',
                'returncode': result.returncode
            })
            
            return output
            
        except subprocess.TimeoutExpired:
            error = "Command timed out after 5 minutes"
            self.logger.log_operation('execute_command',
                                    {'command': command},
                                    None, error)
            raise TimeoutError(error)
        except Exception as e:
            self.logger.log_operation('execute_command',
                                    {'command': command},
                                    None, str(e))
            raise