# Current Task
学习如何开发带 OAuth 认证的 Dify tool 插件

# Working Memory
1. **OAuth 插件核心架构**：
   - Provider 层：负责 OAuth 流程实现（授权、token 交换、刷新）
   - Tool 层：使用 OAuth token 调用 API
   - 配置层：manifest.yaml 定义插件元信息，provider.yaml 定义 OAuth 配置

2. **OAuth 配置结构（provider.yaml）**：
   ```yaml
   oauth_schema:
     client_schema:  # OAuth 客户端配置
       - name: client_id
         type: secret-input
         required: true
       - name: client_secret
         type: secret-input
         required: true
     credentials_schema:  # 用户凭据配置
       - name: access_token
         type: secret-input
       - name: refresh_token
         type: secret-input
   ```

3. **Provider 类必须实现的 OAuth 方法**：
   - `_oauth_get_authorization_url()`: 生成授权 URL
   - `_oauth_get_credentials()`: 用授权码交换 token
   - `_oauth_refresh_credentials()`: 刷新 access token
   - `_validate_credentials()`: 验证凭据有效性

4. **OAuth 流程实现要点**：
   - 使用 `secrets.token_urlsafe()` 生成 state 参数
   - 设置 `access_type=offline` 获取 refresh_token
   - 计算 token 过期时间 `expires_at`
   - 返回 `ToolOAuthCredentials` 对象

5. **Tool 中使用 OAuth**：
   - 通过 `self.runtime.credentials` 获取 access_token
   - 在 API 请求中使用 Bearer token：`Authorization: Bearer {access_token}`
   - 处理 401/403 错误（token 失效或权限不足）

6. **Google Calendar 插件示例架构**：
   ```
   google_calendar/
   ├── manifest.yaml         # 插件元信息
   ├── provider/
   │   ├── google_calendar.yaml  # OAuth 配置
   │   └── google_calendar.py    # OAuth 实现
   └── tools/
       ├── list_events.yaml      # 工具配置
       └── list_events.py        # 工具实现
   ```

# Active Observations
1. **Dify 插件开发模式**：
   - Tool Plugin 是最常见的插件类型，用于扩展应用能力
   - 一个 Provider 可包含多个 Tools
   - 支持多种认证方式：API Key、OAuth 2.0、自定义凭据

2. **OAuth 2.0 实现细节**：
   - **授权 URL 参数**：client_id, redirect_uri, scope, response_type=code, access_type=offline
   - **Token 交换**：POST 请求到 token_url，包含 client_id, client_secret, code, grant_type=authorization_code
   - **Token 刷新**：使用 refresh_token 获取新的 access_token
   - **错误处理**：处理 OAuth 错误、网络错误、API 限制

3. **插件权限系统**：
   - 需要在 manifest.yaml 中声明所需权限
   - 权限包括：tool, model, storage, endpoint 等
   - OAuth 插件通常需要 tool 权限和 storage 权限

4. **开发工具链**：
   - `dify plugin init --quick` 快速创建插件
   - Python 3.12+ 环境
   - 远程调试支持（通过 .env 配置）
   - `dify plugin package` 打包插件

# Knowledge
1. **Dify 插件系统核心概念**：
   - Tool Plugin：外部工具类型插件，增强应用能力
   - Provider：工具提供者，可包含多个具体工具
   - Tool：具体功能实现
   - Manifest：插件基本信息定义文件

2. **配置文件规范**：
   A. manifest.yaml 核心字段：
   - version：版本号（major.minor.patch）
   - type：插件类型（plugin/bundle）
   - author：作者信息
   - resource：资源限制配置
   - plugins：功能定义文件列表
   - meta：运行时配置
   - privacy：隐私政策文件

   B. provider.yaml 规范：
   - identity：提供者基本信息
   - credentials_for_provider：API Key 认证配置
   - oauth_schema：OAuth 认证配置
   - tools：包含的工具列表

   C. tool.yaml 规范：
   - identity：工具标识信息
   - description：工具描述
   - parameters：参数定义
   - 返回类型：text/links/images/files/json/variables

3. **OAuth 2.0 在 Dify 中的实现**：
   - 支持标准 OAuth 2.0 流程
   - 自动处理 token 刷新
   - 提供 ToolOAuthCredentials 封装
   - 支持自定义 scope 和权限

4. **错误处理模式**：
   - ToolProviderCredentialValidationError：凭据验证失败
   - ToolProviderOAuthError：OAuth 流程错误
   - 使用 try-except 捕获网络和 API 错误

# Next Steps
1. 基于学到的知识创建一个带 OAuth 认证的插件
2. 实现完整的 OAuth 流程（授权、token 交换、刷新）
3. 添加错误处理和日志记录
4. 测试插件的 OAuth 功能