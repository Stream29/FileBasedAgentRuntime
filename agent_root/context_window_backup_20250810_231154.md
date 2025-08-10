# Current Task
重新开发 GitHub API 集成插件，遵循最佳实践，实现完整功能

## 当前进度
- ✅ 创建新插件项目 github_api
- ✅ 编写完整 README.md 文档
- ✅ 创建 PRIVACY.md 隐私政策
- ✅ 更新 guideline.md 添加插件开发规范
- ✅ 更新 manifest.yaml 配置
- ✅ 配置 provider/github_api.yaml（OAuth配置）
- ✅ 实现 provider/github_api.py（OAuth认证）
- ✅ 删除模板工具文件
- ✅ 创建 search_repositories 工具
- 🔄 需要创建其他3个工具
- ⏳ 测试插件功能

# Working Memory

## 项目状态
- 位置: workspace/github_api
- 已完成 OAuth 认证实现（provider 层）
- 已实现第一个工具 search_repositories

## 已完成的文件
1. **provider/github_api.yaml** (67行)
   - 完整的 OAuth 配置
   - 包含 client_id, client_secret 配置
   - 定义了4个工具的引用

2. **provider/github_api.py** (135行)
   - 实现了完整的 OAuth 流程
   - `_oauth_get_authorization_url`: 生成授权URL
   - `_oauth_get_credentials`: 代码换token
   - `_oauth_refresh_credentials`: GitHub token不过期
   - `_validate_credentials`: 验证token有效性

3. **tools/search_repositories.yaml** (107行)
   - 完整的参数定义（query, sort, order, per_page）
   - 多语言支持（en_US, zh_Hans, ja_JP, pt_BR）
   - 详细的参数说明和验证规则

4. **tools/search_repositories.py** (148行)
   - 完整的搜索实现
   - 错误处理（401, 403, 422等）
   - 同时返回文本和JSON格式结果
   - 处理GitHub API速率限制

## 需要创建的工具
1. ✅ tools/search_repositories.yaml + .py (已完成)
2. ⏳ tools/search_users.yaml + .py  
3. ⏳ tools/get_repository.yaml + .py
4. ⏳ tools/get_user.yaml + .py

## 实现经验总结
1. **参数验证**：
   - 始终验证必需参数
   - 对数值参数进行范围检查
   - 提供合理的默认值

2. **错误处理模式**：
   ```python
   if response.status_code == 401:
       yield self.create_text_message("Error: Invalid token")
       return
   elif response.status_code == 403:
       # 检查速率限制
       if response.headers.get("X-RateLimit-Remaining") == "0":
           yield self.create_text_message("Rate limit exceeded")
   ```

3. **返回格式**：
   - 文本消息：格式化的人类可读输出
   - JSON消息：结构化数据供程序使用

4. **GitHub API特点**：
   - 搜索API的参数：q, sort, order, per_page
   - 响应包含 total_count 和 items
   - 需要处理速率限制头部

## GitHub API 实现要点
1. **请求头**：
   ```python
   headers = {
       "Authorization": f"Bearer {access_token}",
       "Accept": "application/vnd.github.v3+json"
   }
   ```

2. **错误处理**：
   - 401: 未认证
   - 403: 权限不足或速率限制
   - 404: 资源不存在
   - 422: 参数错误

3. **API 端点**：
   - 搜索仓库: GET /search/repositories?q={query}
   - 搜索用户: GET /search/users?q={query}
   - 获取仓库: GET /repos/{owner}/{repo}
   - 获取用户: GET /users/{username}

# Active Observations

## 最新进展
- 成功删除了模板工具文件
- 创建了 search_repositories 工具的完整实现
- 工具包含详细的参数验证和错误处理
- 支持4种语言的国际化

## 从实践中学到的经验
1. **工具配置要点**：
   - form: llm 表示参数由AI推理
   - form: form 表示用户手动填写
   - select类型需要定义options
   - number类型可以设置min/max

2. **实现细节**：
   - GitHub搜索API不需要sort参数时传"best-match"会报错，需要传None
   - 需要过滤掉params中的None值
   - 速率限制信息在响应头的X-RateLimit-Remaining中

3. **返回格式最佳实践**：
   - 文本消息用Markdown格式化，便于阅读
   - JSON消息包含完整数据，便于程序处理
   - 提取关键字段，避免返回过多无用信息

## 下一步计划
1. 创建 search_users 工具
2. 创建 get_repository 工具
3. 创建 get_user 工具
4. 测试整个插件
5. 打包插件

# Knowledge

## Dify 插件系统核心知识
1. **插件生命周期**：初始化 → 认证 → 调用 → 返回结果
2. **权限系统**：tool、model、storage、endpoint 等权限需显式声明
3. **消息系统**：支持 text、json、link、image、blob、variable、log 等类型
4. **双向调用**：插件可反向调用 Dify 的 AI 模型、工具、知识库

## GitHub API 知识
1. **认证方式**：OAuth 2.0，使用 personal access token
2. **API 限制**：认证用户 5000 请求/小时，未认证 60 请求/小时
3. **搜索 API**：支持多种搜索类型和过滤器
4. **错误码**：401（未认证）、403（禁止）、404（不存在）、422（参数错误）

## Python 开发技巧
1. **Generator 模式**：使用 yield 返回多个消息
2. **类型注解**：使用 typing 模块提供类型提示
3. **异常处理**：使用 try-except 捕获所有可能的错误
4. **超时设置**：requests 调用设置 timeout 参数

## 工具实现模板
```python
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

class ToolName(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        # 1. 获取认证
        access_token = self.runtime.credentials.get("access_token")
        
        # 2. 参数验证
        param = tool_parameters.get("param")
        if not param:
            yield self.create_text_message("Error: param required")
            return
        
        # 3. API 调用
        try:
            response = requests.get(url, headers=headers, timeout=30)
            # 4. 返回结果
            yield self.create_text_message(text)
            yield self.create_json_message(data)
        except Exception as e:
            yield self.create_text_message(f"Error: {str(e)}")
```

# Next Steps
1. 创建 search_users 工具
2. 创建 get_repository 工具  
3. 创建 get_user 工具
4. 测试插件功能
5. 打包发布