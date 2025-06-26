.PHONY: help install install-dev test test-verbose lint format clean run status config build docs

# 默认目标
help:
	@echo "可用的命令:"
	@echo "  install      - 安装生产依赖"
	@echo "  install-dev  - 安装开发依赖"
	@echo "  test         - 运行测试"
	@echo "  test-verbose - 运行详细测试"
	@echo "  lint         - 代码检查"
	@echo "  format       - 代码格式化"
	@echo "  clean        - 清理临时文件"
	@echo "  run          - 启动交互模式"
	@echo "  status       - 显示系统状态"
	@echo "  config       - 显示配置"
	@echo "  build        - 构建分发包"
	@echo "  docs         - 生成文档"

# 安装依赖
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt
	pip install -e ".[dev]"

# 测试
test:
	python -m pytest tests/ -v

test-verbose:
	python -m pytest tests/ -v -s --tb=long

test-coverage:
	python -m pytest tests/ --cov=src --cov-report=html --cov-report=term

# 代码质量
lint:
	flake8 src/ tests/ main.py
	mypy src/ main.py

format:
	black src/ tests/ main.py
	isort src/ tests/ main.py

# 清理
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/ .coverage htmlcov/ .pytest_cache/ .mypy_cache/
	rm -rf logs/*.log
	rm -rf screenshots/*.png

# 运行应用
run:
	python main.py --interactive

run-help:
	python main.py --help

status:
	python main.py status

config:
	python main.py config --show

# 开发工具
dev-setup:
	@echo "设置开发环境..."
	make install-dev
	@echo "检查系统依赖..."
	@which tesseract > /dev/null || echo "警告: 未找到tesseract，请运行 'brew install tesseract'"
	@which ollama > /dev/null || echo "提示: 可选安装ollama用于本地LLM"

# 构建和分发
build:
	python setup.py sdist bdist_wheel

build-clean:
	make clean
	make build

# 文档
docs:
	@echo "生成API文档..."
	@mkdir -p docs/api
	python -c "import src; help(src)" > docs/api/overview.txt

# 安全检查
security-check:
	bandit -r src/
	safety check

# 性能测试
benchmark:
	python main.py test

# 完整的CI流程
ci: lint test security-check
	@echo "✅ CI检查通过"

# 发布前检查
pre-release: clean ci build
	@echo "✅ 发布前检查通过"

# 快速开始
quickstart:
	@echo "🚀 屏幕AI助手快速开始"
	@echo "1. 安装依赖..."
	make install
	@echo "2. 检查系统状态..."
	python main.py status
	@echo "3. 启动交互模式..."
	python main.py --interactive

# Docker相关 (可选)
docker-build:
	docker build -t screen-ai-agent .

docker-run:
	docker run -it --rm screen-ai-agent

# 环境检查
check-env:
	@echo "检查Python环境..."
	@python --version
	@echo "检查依赖..."
	@pip list | grep -E "(pillow|pytesseract|pyautogui|rich|typer)"
	@echo "检查Tesseract..."
	@tesseract --version || echo "❌ Tesseract未安装"
	@echo "检查Ollama..."
	@ollama --version || echo "⚠️ Ollama未安装（可选）"

# 权限检查 (macOS)
check-permissions:
	@echo "检查macOS权限..."
	python -c "
from src.security import PermissionManager; 
pm = PermissionManager(); 
status = pm.get_all_permissions_status();
for ptype, pstatus in status.items():
    print(f'{ptype.value}: {"✅" if pstatus.granted else "❌"} {pstatus.description}')
"

# 示例运行
examples:
	@echo "运行示例命令..."
	python main.py "截图"
	python main.py "点击坐标(100, 100)" --no-screenshot
	python main.py screenshot --ocr

# 日志查看
logs:
	@echo "最近的日志文件:"
	@ls -la logs/ 2>/dev/null || echo "暂无日志文件"

logs-tail:
	@tail -f logs/audit_$$(date +%Y%m%d).jsonl 2>/dev/null || echo "暂无今日日志"

# 配置管理
config-edit:
	python main.py config --edit

config-reset:
	python main.py config --reset

# 调试模式
debug:
	python main.py --verbose --interactive

# 安装脚本
install-script:
	@echo "创建安装脚本..."
	@cat > install.sh << 'EOF'
#!/bin/bash
echo "🚀 安装屏幕AI助手"
echo "=================="

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 需要Python 3.8+"
    exit 1
fi

# 检查pip
if ! command -v pip3 &> /dev/null; then
    echo "❌ 需要pip"
    exit 1
fi

# 安装依赖
echo "📦 安装Python依赖..."
pip3 install -r requirements.txt

# 检查Tesseract
if ! command -v tesseract &> /dev/null; then
    echo "⚠️ 未找到Tesseract OCR"
    echo "请运行: brew install tesseract"
fi

echo "✅ 安装完成!"
echo "运行 'make quickstart' 开始使用"
EOF
	@chmod +x install.sh
	@echo "安装脚本已创建: install.sh"