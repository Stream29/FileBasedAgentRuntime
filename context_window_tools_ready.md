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

### 已知坑点
1. **dify plugin init必须加--quick**：否则会卡在交互

## 🛠️ 立即可用的代码片段

### 创建新插件
```bash
dify plugin init --quick --name [name] --author [author] --type tool
cd [name]
tree -a
```



## 📝 待填充信息模板

当用户提出需求后，立即收集以下信息：

### 实现进度跟踪
- [ ] 调用dify cli初始化插件
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

💭 记住：每个细节都要记录，每个错误都是经验，保持context完整性和丰富性！