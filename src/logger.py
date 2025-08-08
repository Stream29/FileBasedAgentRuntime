"""Operation logging system for observability."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class OperationLogger:
    """记录所有 Agent 操作，确保可观测性"""
    
    def __init__(self, log_dir: Path):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 操作日志文件（JSONL 格式）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.operation_log = self.log_dir / f"operations_{timestamp}.jsonl"
        
        # 配置标准日志
        self.logger = logging.getLogger('FileSystemAgent')
        self.logger.setLevel(logging.INFO)
        
        # 避免重复添加 handler
        if not self.logger.handlers:
            # 文件处理器
            file_handler = logging.FileHandler(self.log_dir / 'agent.log', encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            
            # 控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            # 设置格式
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            # 添加处理器
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
        
    def log_operation(self, operation_type: str, params: Dict[str, Any], 
                     result: Any = None, error: Optional[str] = None):
        """记录一次操作"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'operation': operation_type,
            'params': params,
            'result': self._serialize_result(result),
            'error': error,
            'success': error is None
        }
        
        # 写入 JSONL
        with open(self.operation_log, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
            
        # 同时记录到标准日志
        if error:
            self.logger.error(f"{operation_type} failed: {error}")
        else:
            self.logger.info(f"{operation_type} completed")
            
    def _serialize_result(self, result: Any) -> Any:
        """序列化结果，处理不可JSON序列化的对象"""
        if result is None:
            return None
        elif isinstance(result, (str, int, float, bool, list, dict)):
            return result
        elif isinstance(result, Path):
            return str(result)
        else:
            return str(result)