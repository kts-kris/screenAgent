# 屏幕AI助手 (Screen AI Agent)

一个强大的屏幕AI助手，通过图像识别技术读取屏幕内容，并使用大语言模型理解和执行用户指令。

## ✨ 主要功能

- 🖼️ **智能屏幕截图** - 高性能屏幕捕获，支持全屏、区域、窗口截图
- 👁️ **OCR文字识别** - 基于Tesseract的高精度文字识别，支持中英文
- 🧠 **多LLM支持** - 支持Ollama（本地）、OpenAI GPT、Anthropic Claude
- ⚡ **自动化操作** - 点击、输入、滚动、拖拽等屏幕自动化操作
- 💬 **自然语言处理** - 智能解析自然语言指令并执行
- 🛡️ **安全防护** - 完整的安全检查和权限管理系统
- 🎨 **美观界面** - 基于Rich的现代化CLI交互界面

## 🚀 快速开始

### 系统要求

- macOS 10.15+ (支持其他系统的截图功能)
- Python 3.8+
- Tesseract OCR

### 安装依赖

1. **安装Python依赖**
```bash
pip install -r requirements.txt
```

2. **安装Tesseract (macOS)**
```bash
# 使用Homebrew
brew install tesseract

# 安装中文语言包
brew install tesseract-lang
```

3. **配置macOS权限**
- 系统偏好设置 > 安全性与隐私 > 隐私 > 屏幕录制 → 添加终端/Python
- 系统偏好设置 > 安全性与隐私 > 隐私 > 辅助功能 → 添加终端/Python

### 基本使用

1. **启动交互模式**
```bash
python main.py --interactive
```

2. **执行单个指令**
```bash
python main.py "点击登录按钮"
python main.py "输入'用户名'"
python main.py "向下滚动3次"
```

3. **查看系统状态**
```bash
python main.py status
```

## 📖 使用指南

### 支持的指令类型

#### 点击操作
```
点击登录按钮
点击确定
点击坐标(100, 200)
click on submit button
```

#### 文本输入
```
输入'hello world'
输入密码
type 'username'
填写'邮箱地址'
```

#### 滚动操作
```
向下滚动
向上滚动5次
scroll down
左滑
```

#### 按键操作
```
按回车键
按空格键
press enter
键盘按Tab
```

#### 拖拽操作
```
拖拽文件到回收站
drag from (100,100) to (200,200)
```

#### 其他操作
```
截图
等待3秒
查找'确定按钮'
```

### 配置管理

#### 查看配置
```bash
python main.py config --show
```

#### 编辑配置
```bash
python main.py config --edit
```

#### 重置配置
```bash
python main.py config --reset
```

### LLM提供商配置

#### Ollama (推荐用于开发)
```yaml
llm:
  default_provider: "ollama"
  providers:
    ollama:
      base_url: "http://localhost:11434"
      model: "auto"  # 自动选择可用模型
```

#### OpenAI
```yaml
llm:
  providers:
    openai:
      api_key: ""  # 设置环境变量 OPENAI_API_KEY
      model: "gpt-4o"
```

#### Anthropic Claude
```yaml
llm:
  providers:
    anthropic:
      api_key: ""  # 设置环境变量 ANTHROPIC_API_KEY
      model: "claude-3-5-sonnet-20241022"
```

## 🏗️ 项目架构

```
screen-ai-agent/
├── src/
│   ├── capture/         # 屏幕截图模块
│   ├── vision/          # OCR和图像处理
│   ├── ai/             # LLM接口管理
│   │   └── providers/   # 各LLM提供商
│   ├── executor/        # 指令解析和执行
│   ├── ui/             # 用户界面
│   ├── security/       # 安全和权限管理
│   └── config/         # 配置管理
├── tests/              # 测试文件
├── config.yaml         # 配置文件
├── requirements.txt    # Python依赖
└── main.py            # 入口文件
```

## ⚙️ 高级功能

### 性能优化

- **缓存机制** - 图像处理结果缓存，避免重复计算
- **并行处理** - 多线程OCR处理，提升大图像识别速度
- **智能策略** - 根据图像大小自动选择最佳处理方式
- **批量操作** - 支持批量指令执行

### 安全特性

- **操作白名单** - 只允许安全的操作类型
- **内容过滤** - 过滤危险关键词和敏感信息
- **频率限制** - 防止恶意高频操作
- **权限检查** - 完整的macOS权限管理
- **审计日志** - 记录所有操作用于安全审计

### 错误处理

- **优雅降级** - LLM不可用时自动切换到传统解析
- **重试机制** - 网络错误自动重试
- **详细日志** - 完整的错误信息和堆栈跟踪

## 🧪 开发和测试

### 运行测试
```bash
python main.py test
```

### 性能基准测试
```bash
python -c "
from src.executor import InstructionProcessor
from src.config import ConfigManager
import asyncio

config = ConfigManager().load_config()
processor = InstructionProcessor(config.model_dump())

# 测试截图性能
screenshot = processor.screen_capture.capture_full_screen()
print(f'截图尺寸: {screenshot.size}')

# 测试OCR性能
result = processor.ocr_engine.benchmark_performance(screenshot)
print('OCR性能测试结果:')
for mode, stats in result.items():
    print(f'{mode}: {stats[\"average_time\"]:.2f}s')
"
```

### 调试模式
```bash
python main.py --verbose "你的指令"
```

## 🔧 故障排除

### 常见问题

1. **权限问题**
   - 确保已授予屏幕录制和辅助功能权限
   - 重启终端或应用程序

2. **OCR识别率低**
   - 检查Tesseract是否正确安装
   - 尝试安装更多语言包
   - 调整图像预处理参数

3. **LLM连接失败**
   - 检查网络连接
   - 验证API密钥配置
   - 确认服务商配额

4. **Ollama模型问题**
   ```bash
   # 查看可用模型
   ollama list
   
   # 下载推荐模型
   ollama pull llama3.2
   ollama pull qwen2.5
   ```

### 日志查看
```bash
# 查看审计日志
ls logs/
cat logs/audit_$(date +%Y%m%d).jsonl

# 查看会话日志
cat logs/session_*.jsonl
```

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) - 开源OCR引擎
- [PyAutoGUI](https://github.com/asweigart/pyautogui) - Python自动化库
- [Rich](https://github.com/Textualize/rich) - 终端美化库
- [Ollama](https://ollama.ai/) - 本地LLM运行环境

## 📞 支持

如果您遇到问题或有功能建议，请：

1. 查看 [FAQ](docs/FAQ.md)
2. 搜索 [Issues](https://github.com/your-repo/screen-ai-agent/issues)
3. 创建新的 Issue

---

**免责声明**: 本工具仅用于合法的自动化操作。请遵守相关法律法规，不要用于恶意用途。