# Context Window - Tools插件开发专用

## 🚀 准备状态：已就绪，等待用户需求

### 开发环境检查 ✅
- [x] Dify CLI工具已安装
- [x] Python ≥ 3.12 环境就绪
- [x] 工作目录：agent_root/workspace/
- [x] 参考文档已加载到storage/documents/
- [x] 示例代码已准备在storage/few_shots/

### 我掌握的核心知识

#### 1. Tools插件文件结构
```
plugin_name/
├── manifest.yaml          # 必需：插件元信息
├── main.py               # 必需：固定入口（from dify_plugin import Plugin）
├── requirements.txt      # Python依赖
├── README.md            # 使用说明
├── PRIVACY.md           # 隐私政策（发布必需）
├── _assets/             
│   └── icon.svg         # 插件图标
├── provider/            
│   ├── provider_name.yaml  # 必需：provider配置
│   └── provider_name.py    # OAuth必需：认证实现
└── tools/               
    ├── tool1.yaml       # 必需：工具配置
    ├── tool1.py         # 必需：工具实现
    └── ...
```

#### 2. 认证方式决策树
```
需要用户特定数据？
  ├─ 是 → OAuth 2.0（复杂但安全）
  └─ 否 → API Key（简单直接）
          ├─ 有免费tier → 告知限制
          └─ 纯付费 → 说明定价
```

#### 3. 常用API模式库

##### 3.1 REST API调用模板
```python
headers = {"Authorization": f"Bearer {api_key}"}
response = requests.get(url, headers=headers, timeout=30)
response.raise_for_status()
data = response.json()
```

##### 3.2 错误处理标准
- 401: 认证失败 → "请检查API密钥"
- 403: 权限不足 → "需要更高权限"
- 404: 资源不存在 → "未找到指定资源"
- 429: 速率限制 → 检查X-RateLimit头
- 500+: 服务器错误 → "服务暂时不可用"

##### 3.3 参数验证模板
```python
# 必需参数
if not param:
    yield self.create_text_message("Error: param is required")
    return

# 数值范围
if not (1 <= value <= 100):
    yield self.create_text_message("Error: value must be between 1-100")
    return
```

## 📚 已收集的API信息库

### 常用API速查
1. **OpenAI**: Bearer token认证，有速率限制
2. **Google APIs**: OAuth 2.0，scope很重要
3. **GitHub**: token不过期，设置expires_at=-1
4. **Slack**: OAuth，需要特定scope
5. **AWS**: 签名认证，较复杂

### 已知坑点
1. **dify plugin init必须加--quick**：否则会卡在交互
2. **GitHub搜索API**：sort参数不传而不是"best-match"
3. **中文支持**：确保response.encoding='utf-8'
4. **OAuth state**：用secrets.token_urlsafe(16)生成

### 🚨 Dify YAML配置详细规定

#### 1. provider.yaml 关键细节

##### 1.1 字段顺序灵活但要完整
```yaml
# extra字段位置灵活（可在开头或结尾）
extra:
  python:
    source: provider/provider_name.py  # 必须指向.py文件

identity:
  name: provider_name  # 必须与文件名前缀一致
  author: your_name
  label:  # 多语言必需，至少要有en_US
    en_US: Display Name
    zh_Hans: 显示名称  # ⚠️ 是zh_Hans不是zh_CN！
    ja_JP: 表示名     # ⚠️ 是ja_JP不是ja_Jp！
    pt_BR: Nome
```

##### 1.2 认证方式严格区分
```yaml
# 方式1：API Key认证 - 使用credentials_for_provider
credentials_for_provider:
  api_key:
    type: secret-input  # 敏感信息必须用secret-input
    required: true
    label:
      en_US: API Key
    help:  # 可选，提供获取凭据的指导
      en_US: Get your API key from dashboard
      zh_Hans: 从控制台获取API密钥
    url: https://example.com/api-keys  # help的链接
    
# 方式2：OAuth认证 - 使用oauth_schema
oauth_schema:
  client_schema:  # 应用级配置（客户端ID/密钥）
    - name: client_id
      type: secret-input
      required: true
  credentials_schema:  # 用户级凭据（token）
    - name: access_token
      type: secret-input
    - name: refresh_token  
      type: secret-input
```

##### 1.3 tools列表格式
```yaml
tools:  # 必须是YAML列表格式
  - tools/tool1.yaml  # ⚠️ 注意前面的"- "
  - tools/tool2.yaml  # 路径相对于插件根目录
# ❌ 错误：tools: tools/tool1.yaml
```

#### 2. tool.yaml 完整配置

##### 2.1 必需字段结构
```yaml
identity:
  name: tool_name  # 工具标识名
  author: author_name
  label:
    en_US: Tool Display Name
    zh_Hans: 工具显示名称

description:
  human:  # 给用户看的友好描述
    en_US: User-friendly description
    zh_Hans: 用户友好的描述
  llm: Precise description for AI. Explain when to use this tool.  # 给AI看的精确描述

parameters:  # 参数列表
  - name: param_name
    type: string  # 9种类型之一（见下表）
    required: true
    form: llm  # ⚠️ 99%情况用llm（AI推理）
    label:
      en_US: Parameter Label
    llm_description: Detailed info for AI to understand this parameter
    # 其他可选字段见下文

extra:  # ⚠️ 每个tool文件都需要！
  python:
    source: tools/tool_name.py
```

##### 2.2 参数类型完整列表
| type值 | 说明 | 使用场景 |
|--------|------|----------|
| string | 字符串 | 普通文本输入 |
| number | 数字 | 数值输入（可设min/max） |
| boolean | 布尔值 | 是/否选择 |
| select | 下拉选择 | 需要options字段 |
| secret-input | 加密输入 | API密钥等敏感信息 |
| file | 单文件 | 文件上传 |
| files | 多文件 | 批量文件上传 |
| model-selector | 模型选择 | 选择AI模型 |
| app-selector | 应用选择 | 选择Dify应用 |

##### 2.3 form字段说明
```yaml
form: llm    # AI推理参数（最常用）
# form: form  # 用户预设参数（少用）

# 在Agent应用中：
# - llm: 参数由AI推理得出
# - form: 参数可以预设使用

# 在Workflow应用中：
# - 两种都需要前端填写
# - llm参数会作为工具节点的输入变量
```

##### 2.4 完整参数配置示例
```yaml
parameters:
  - name: query
    type: string
    required: true
    form: llm
    label:
      en_US: Search Query
      zh_Hans: 搜索关键词
    human_description:  # 前端显示的说明
      en_US: Keywords to search
      zh_Hans: 要搜索的关键词
    llm_description: Search keywords, be specific  # AI理解的说明
    placeholder:  # 仅当form:form且type是string/number/secret-input时有效
      en_US: Enter keywords...
    
  - name: limit
    type: number
    required: false
    form: llm
    default: 10
    min: 1        # 数字类型专用
    max: 100      # 有min/max时会显示滑块
    label:
      en_US: Result Limit
      
  - name: sort_by
    type: select
    required: false
    form: llm
    default: relevance
    options:      # select类型必需
      - value: relevance
        label:
          en_US: Relevance
          zh_Hans: 相关性
      - value: date
        label:
          en_US: Date
          zh_Hans: 日期
```

##### 2.5 输出变量定义（可选）
```yaml
output_schema:  # 定义工具输出的变量结构
  type: object
  properties:
    results:
      type: array
      items:
        type: object
        properties:
          title:
            type: string
          url:
            type: string
    total_count:
      type: number
```

#### 3. manifest.yaml 易错配置

##### 3.1 版本字段出现两次
```yaml
version: 0.1.0  # 插件版本（顶层）
# ...其他配置...
meta:
  version: 0.0.1  # ⚠️ manifest格式版本，固定0.0.1
```

##### 3.2 plugins配置指向
```yaml
plugins:
  tools:  # ⚠️ 指向provider yaml，不是tool yaml！
    - provider/provider_name.yaml
  # models:
  #   - provider/model_provider.yaml
  # endpoints:
  #   - provider/endpoint_provider.yaml
```

##### 3.3 时间格式和其他细节
```yaml
created_at: '2024-08-07T08:03:44.658609186Z'  # RFC3339格式，注意引号
type: plugin  # 固定值
meta:
  runner:
    language: python
    version: '3.12'  # ⚠️ 现在支持3.12了
    entrypoint: main  # Python固定为main
```

#### 4. 通用配置规则

##### 4.1 国际化语言代码（IETF BCP 47）
- ✅ `en_US`（不是en或en-US）
- ✅ `zh_Hans`（不是zh_CN或zh）  
- ✅ `ja_JP`（不是ja_Jp或ja）
- ✅ `pt_BR`（巴西葡萄牙语）

##### 4.2 provider配置type完整列表
| type值 | 说明 | 使用场景 |
|--------|------|----------|
| secret-input | 加密输入 | API密钥、密码、token |
| text-input | 明文输入 | 普通文本、路径 |
| select | 下拉框 | 预定义选项 |
| boolean | 开关 | 是/否选择 |
| model-selector | 模型选择器 | 选择AI模型（可设scope） |
| app-selector | 应用选择器 | 选择Dify应用 |
| tool-selector | 工具选择器 | 选择工具 |
| dataset-selector | 数据集选择器 | （待定） |

##### 4.3 路径规则
- 所有路径都相对于插件根目录
- 使用正斜杠`/`（不是反斜杠）
- 不需要`./`前缀
- 多媒体文件放在`_assets/`目录

#### 5. 快速检查清单

写完配置后逐项检查：
- [ ] provider.yaml的`extra.python.source`路径正确？
- [ ] 每个tool.yaml都有`extra.python.source`？
- [ ] 所有`label`至少有`en_US`？
- [ ] 语言代码拼写正确？（zh_Hans、ja_JP）
- [ ] manifest的`plugins.tools`指向provider.yaml而非tool yaml？
- [ ] tools列表每项前都有`- `（横杠加空格）？
- [ ] 参数的`form`字段是"llm"（除非真需要预设）？
- [ ] select类型参数有`options`字段？
- [ ] number类型参数设置了合理的min/max？
- [ ] 敏感信息使用`secret-input`而非`text-input`？

#### 6. 常见错误示例

```yaml
# ❌ 错误：中文语言代码
zh_CN: 中文名称  # 应该是zh_Hans

# ❌ 错误：日文语言代码  
ja_Jp: 日本語  # 应该是ja_JP（P大写）

# ❌ 错误：tools不是列表
tools: tools/tool.yaml  # 应该是 - tools/tool.yaml

# ❌ 错误：manifest指向错误
plugins:
  tools:
    - tools/search.yaml  # 应该指向provider yaml

# ❌ 错误：普通文本用了加密类型
database_path:
  type: secret-input  # 路径应该用text-input
```

## 🛠️ 立即可用的代码片段

### 创建新插件
```bash
dify plugin init --quick --name [name] --author [author] --type tool
cd [name]
tree -a
```

### 快速测试
```bash
python -m py_compile provider/*.py tools/*.py
dify plugin package ./
```

### OAuth实现骨架
```python
class Provider(ToolProvider):
    def _oauth_get_authorization_url(self, redirect_uri: str, 
                                   system_credentials: Mapping[str, Any]) -> str:
        params = {
            "client_id": system_credentials["client_id"],
            "redirect_uri": redirect_uri,
            "scope": self._OAUTH_SCOPE,
            "response_type": "code",
            "state": secrets.token_urlsafe(16)
        }
        return f"{self._AUTH_URL}?{urllib.parse.urlencode(params)}"
```

## 📝 待填充信息模板

当用户提出需求后，立即收集以下信息：

### API调研清单
- [ ] API文档URL：
- [ ] 认证方式：
- [ ] 速率限制：
- [ ] 价格/免费tier：
- [ ] SDK可用性：
- [ ] 特殊要求：

### 功能需求清单
- [ ] 核心功能列表：
- [ ] 用户使用场景：
- [ ] 输入参数类型：
- [ ] 输出数据格式：
- [ ] 错误处理需求：

### 实现进度跟踪
- [ ] Provider配置
- [ ] OAuth实现（如需要）
- [ ] Tool 1: [名称]
- [ ] Tool 2: [名称]
- [ ] Tool 3: [名称]
- [ ] 测试通过
- [ ] 打包完成

## 💡 开发策略

1. **快速原型**：先实现一个最简单的工具，验证连通性
2. **增量开发**：每个工具独立实现和测试
3. **错误优先**：先处理各种错误情况，再优化正常流程
4. **信息收集**：遇到任何有用信息立即记录到这里

## 🎯 当前状态

**等待用户输入具体需求...**

准备好了，请告诉我：
1. 你想集成什么服务/API？
2. 需要实现哪些功能？
3. 有什么特殊要求吗？

---

> 💭 记住：每个细节都要记录，每个错误都是经验，保持context完整性！