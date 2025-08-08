# 工具快速参考

## 📖 read_file
读取文件内容
```json
{
  "path": "/workspace/file.py",
  "start_line": 1,     // 可选
  "end_line": 50       // 可选
}
```

## 📝 write_file
写入文件（覆盖）
```json
{
  "path": "/workspace/file.py",
  "content": "file content here"
}
```

## 📁 list_directory
列出目录内容
```json
{
  "path": "/workspace"
}
```

## 💻 execute_command
执行命令
```json
{
  "command": "python main.py",
  "working_dir": "/workspace"  // 可选，默认 /workspace
}
```

## 🧠 sync_context
更新工作记忆
```json
{
  "new_context_content": "# Current Task\n...\n\n# Working Memory\n...\n\n# Active Observations\n...\n\n# Next Steps\n..."
}
```

## 常用命令示例
- `uv add package` - 安装 Python 包
- `uv run python script.py` - 运行 Python 脚本
- `git init` - 初始化 Git 仓库
- `curl -o file.txt URL` - 下载文件
- `grep -n "pattern" file` - 搜索文本

## 路径说明
- `/workspace/` - 工作目录（创建项目文件）
- `/storage/` - 存储目录（归档历史）
- `/` - Agent 根目录