#!/usr/bin/env python3
"""
工具使用示例 - 展示 FileSystem-based Agent 如何使用各种工具

这个脚本模拟了 Agent 使用工具的典型场景
"""

# 注意：这些不是真实的 Python 函数调用，而是展示 Agent 如何调用工具的示例

# 示例 1: 创建一个简单的 Python 项目
# =====================================

# 1.1 首先列出当前目录，了解环境
list_directory({"path": "/workspace"})
# 返回: [{"name": ".gitkeep", "type": "file", "size": 0}]

# 1.2 创建项目主文件
write_file({
    "path": "/workspace/hello_world.py",
    "content": """#!/usr/bin/env python3
'''一个简单的 Hello World 程序'''

def greet(name='World'):
    return f'Hello, {name}!'

if __name__ == '__main__':
    print(greet())
    print(greet('FileSystem Agent'))
"""
})
# 返回: {"path": "/workspace/hello_world.py", "size": 197, "lines": 10}

# 1.3 执行脚本查看效果
execute_command({
    "command": "python hello_world.py",
    "working_dir": "/workspace"
})
# 返回: {
#   "stdout": "Hello, World!\nHello, FileSystem Agent!\n",
#   "stderr": "",
#   "returncode": 0,
#   "success": true
# }

# 示例 2: 处理依赖和包管理
# ========================

# 2.1 创建一个需要外部依赖的项目
write_file({
    "path": "/workspace/web_app.py",
    "content": """from flask import Flask, jsonify
import requests

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({'message': 'Hello from Flask!'})

@app.route('/quote')
def get_quote():
    # 获取随机引言
    response = requests.get('https://api.quotable.io/random')
    return response.json()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
"""
})

# 2.2 安装依赖
execute_command({
    "command": "uv add flask requests",
    "working_dir": "/workspace"
})

# 2.3 运行应用（注意：这会启动服务器，实际使用时可能需要后台运行）
execute_command({
    "command": "uv run python web_app.py",
    "working_dir": "/workspace"
})

# 示例 3: 文件读取和分析
# ======================

# 3.1 读取文件查看内容
read_file({
    "path": "/workspace/web_app.py",
    "start_line": 10,
    "end_line": 15
})
# 返回文件的第 10-15 行内容

# 3.2 搜索特定内容
execute_command({
    "command": "grep -n 'Flask' /workspace/web_app.py"
})

# 示例 4: 同步工作记忆
# ====================

# 4.1 在完成一系列操作后，更新 context
sync_context({
    "new_context_content": """# Current Task
创建了一个 Flask Web 应用示例

# Working Memory
- 创建了 hello_world.py - 简单的问候程序
- 创建了 web_app.py - Flask Web 应用
- 安装了依赖：flask, requests
- 应用包含两个路由：/ 和 /quote

# Active Observations
- hello_world.py 执行成功
- Flask 应用需要的依赖已安装
- 应用设置在 5000 端口运行

# Next Steps
- 添加错误处理
- 创建配置文件
- 添加单元测试
"""
})

# 示例 5: 创建项目结构
# ====================

# 5.1 创建多级目录结构
write_file({
    "path": "/workspace/my_project/__init__.py",
    "content": "# My Project Package"
})

write_file({
    "path": "/workspace/my_project/utils/helpers.py",
    "content": """def format_date(date_obj):
    '''格式化日期'''
    return date_obj.strftime('%Y-%m-%d')
"""
})

# 5.2 查看创建的结构
list_directory({"path": "/workspace/my_project"})

# 示例 6: 错误处理
# ================

# 6.1 尝试读取不存在的文件
try:
    read_file({"path": "/workspace/nonexistent.py"})
except FileNotFoundError:
    # Agent 会收到错误信息，然后可以处理
    print("文件不存在，创建它...")
    write_file({
        "path": "/workspace/nonexistent.py",
        "content": "# 新创建的文件"
    })

# 示例 7: 使用 Git
# ================

# 7.1 初始化 Git 仓库
execute_command({
    "command": "git init",
    "working_dir": "/workspace"
})

# 7.2 添加文件并提交
execute_command({
    "command": "git add . && git commit -m 'Initial commit'",
    "working_dir": "/workspace"
})

# 示例 8: 下载和处理外部资源
# ==========================

# 8.1 下载文件
execute_command({
    "command": "curl -o data.json https://api.github.com/repos/python/cpython",
    "working_dir": "/workspace"
})

# 8.2 处理下载的数据
read_file({"path": "/workspace/data.json"})

# 提示和最佳实践
# ==============

"""
1. 路径使用：
   - 始终使用 Agent 视角的路径（/workspace/, /storage/ 等）
   - 系统会自动映射到实际路径

2. 错误处理：
   - 工具调用可能失败，检查返回的错误信息
   - execute_command 检查 returncode 和 stderr

3. 性能考虑：
   - 大文件使用 read_file 的行范围功能
   - 避免在循环中频繁调用 sync_context

4. 命令执行：
   - 使用 working_dir 参数避免频繁 cd
   - 长时间运行的命令考虑后台执行

5. 记忆管理：
   - 定期调用 sync_context 保存进展
   - 保持 context 精简，归档详细信息
"""