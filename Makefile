.PHONY: help install run test lint clean venv

.DEFAULT_GOAL := help
VENV_DIR ?= .venv

# 自动检测 Python 3.10+，优先用用户指定的
PYTHON3 ?= $(shell \
	for p in python3 python3.13 python3.12 python3.11 python3.10; do \
		command -v $$p >/dev/null 2>&1 && $$p -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" 2>/dev/null && echo $$p && break; \
	done)

PYTHON := $(VENV_DIR)/bin/python
PIP := $(VENV_DIR)/bin/pip

help: ## 显示帮助信息
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

venv: ## 创建虚拟环境
	@test -d $(VENV_DIR) || $(PYTHON3) -m venv $(VENV_DIR)
	@$(PIP) install --upgrade pip -q
	@echo "虚拟环境已就绪: $(VENV_DIR)"

install: venv ## 安装依赖
	$(PIP) install -r requirements.txt

run: install ## 启动程序
	$(PYTHON) main.py

test: install ## 运行测试
	$(PYTHON) -m unittest discover -s tests -v

lint: install ## 代码检查
	$(PYTHON) -m flake8 core ui main.py --max-line-length=120 --ignore=E501,W503

clean: ## 清理缓存和虚拟环境
	rm -rf $(VENV_DIR) __pycache__ .pytest_cache htmlcov .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
