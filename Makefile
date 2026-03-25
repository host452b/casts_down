.PHONY: help install dev build wheel clean release test lint

help:
	@echo "Casts Down - Podcast Downloader & Transcriber"
	@echo ""
	@echo "Commands:"
	@echo "  make install    - Install dependencies"
	@echo "  make dev        - Install with dev dependencies"
	@echo "  make test       - Run test suite"
	@echo "  make lint       - Check code compiles"
	@echo "  make build      - Build .pyz executable (zipapp, <1s)"
	@echo "  make wheel      - Build wheel for pip distribution"
	@echo "  make clean      - Clean build artifacts"
	@echo "  make release    - Clean + build release"
	@echo ""

install:
	@echo "Installing dependencies..."
	pip install -e .
	@echo "Done"

dev:
	@echo "Installing with dev dependencies..."
	pip install -e ".[dev]"
	@echo "Done"

test:
	@echo "Running tests..."
	pytest tests/ -v
	@echo "Done"

lint:
	@echo "Checking compilation..."
	python -m py_compile casts_down/__init__.py
	python -m py_compile casts_down/cli.py
	python -m py_compile casts_down/downloaders/base.py
	python -m py_compile casts_down/downloaders/podcast.py
	python -m py_compile casts_down/downloaders/xiaoyuzhou.py
	python -m py_compile casts_down/transcribe/__init__.py
	python -m py_compile casts_down/transcribe/engine.py
	python -m py_compile casts_down/transcribe/formatter.py
	python -m py_compile casts_down/transcribe/installer.py
	@echo "All files compile OK"

build:
	@echo "Building .pyz executable..."
	python build_exe.py
	@echo "Done"

wheel:
	@echo "Building wheel..."
	python build_exe.py --mode pip
	@echo "Done"

clean:
	@echo "Cleaning build artifacts..."
	python build_exe.py --clean
	rm -rf __pycache__ *.pyc .pytest_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@echo "Done"

release: clean build
	@echo "Release ready — check release/ directory"
