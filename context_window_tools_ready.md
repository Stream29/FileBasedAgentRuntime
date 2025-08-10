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