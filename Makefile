.PHONY: help install install-dev proto check clean lint format typecheck test ci build verify-package publish docs-install docs-build docs-serve generate-cards

# Default target
help:
	@echo "Available targets:"
	@echo "  install      - Install package in production mode"
	@echo "  install-dev  - Install package in development mode"
	@echo "  proto        - Generate protobuf code"
	@echo "  clean        - Clean build artifacts and caches"
	@echo "  lint         - Run linting (ruff)"
	@echo "  format       - Format code (black, ruff)"
	@echo "  typecheck    - Run type checking (mypy)"
	@echo "  test         - Run tests"
	@echo "  check        - Check project code health"
	@echo "  ci           - Run CI pipeline (install-dev, proto, lint, test)"
	@echo "  build        - Build package and check"
	@echo "  verify-package - Verify built package integrity"
	@echo "  publish      - Publish package to PyPI"
	@echo "  docs-install - Install documentation dependencies"
	@echo "  docs-build   - Build documentation"
	@echo "  docs-serve   - Serve documentation locally"
	@echo "  generate-cards - Generate agent cards from all prompts in agents/prompts/"

# Python and venv setup
PYTHON := python3
VENV := .venv
VENV_PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

# Create virtual environment if it doesn't exist
$(VENV):
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --timeout 300 --upgrade pip setuptools wheel

check: $(VENV) proto lint typecheck format test

# Install package in production mode
install: $(VENV)
	$(PIP) install .

# Install package in development mode with all dependencies
install-dev: $(VENV)
	# Install core dependencies first to avoid timeout
	$(PIP) install --timeout 300 --retries 3 "pydantic>=2.5.0" "python-dotenv>=1.0.0" "httpx>=0.25.0" "aiohttp>=3.9.0"
	$(PIP) install --timeout 300 --retries 3 "rich>=13.0.0" "rich-click>=1.6.0" "click>=8.0.0" "uvicorn>=0.24.0"
	# Install complex dependencies separately
	$(PIP) install --timeout 600 --retries 3 "pydantic-ai>=0.0.10"
	$(PIP) install --timeout 300 --retries 3 "fasta2a>=0.0.1" "protoc-gen-validate>=1.2.0" "a2a-registry==0.1.4" "duckduckgo-search>=8.1.0"
	# Install dev dependencies
	$(PIP) install --timeout 300 --retries 3 "pytest>=7.4.0" "pytest-asyncio>=0.21.0" "pytest-cov>=4.1.0"
	$(PIP) install --timeout 300 --retries 3 "black>=23.0.0" "ruff>=0.1.0" "mypy>=1.6.0" "build>=1.0.0"
	# Install package in development mode
	$(PIP) install --timeout 300 --retries 3 -e . --no-deps
	$(PIP) install --timeout 300 --retries 3 --force-reinstall protobuf==5.29.5 grpcio grpcio-tools googleapis-common-protos
	$(PIP) install --timeout 300 --retries 3 twine

# Generate protobuf code
proto: install-dev
	$(VENV_PYTHON) scripts/generate_proto.py

# Clean build artifacts and caches
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf src/mantis.egg-info/
	rm -rf src/mantis/proto/*.py
	rm -rf src/mantis/proto/*.pyi
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

# Linting
lint: install-dev
	$(VENV)/bin/ruff check src/ scripts/

# Type checking
typecheck: install-dev
	$(VENV)/bin/mypy src/ scripts/ --check-untyped-defs --exclude="src/mantis/proto/*_pb2.py|src/mantis/proto/*_pb2_grpc.py"

# Formatting
format: install-dev
	$(VENV)/bin/black src/ scripts/ --exclude="src/mantis/proto/.*_pb2.*\.py$$"
	$(VENV)/bin/ruff format src/ scripts/

# Run tests
test: install-dev proto
	$(VENV)/bin/pytest tests/ -v

# CI pipeline - what GitHub Actions runs
ci: install-dev proto lint typecheck test

# Build package and check
build: install-dev proto
	$(VENV)/bin/python -m build
	$(VENV)/bin/python -m twine check dist/*

# Verify built package integrity
verify-package: build
	$(VENV)/bin/python -m twine check dist/* --strict

# Publish package to PyPI
publish: verify-package
	$(VENV)/bin/python -m twine upload dist/*

# Documentation targets (placeholder for now)
docs-install: install-dev
	$(PIP) install mkdocs mkdocs-material mkdocstrings mkdocstrings-python

docs-build: docs-install
	$(VENV)/bin/mkdocs build --config-file mkdocs.yml --site-dir docs-site

docs-serve: docs-install
	$(VENV)/bin/mkdocs serve --config-file mkdocs.yml

# Generate agent cards from all prompts using dependency-based regeneration
generate-cards:
	@echo "Generating agent cards from agents/prompts/ to agents/cards/..."
	@find agents/prompts -name "*.md" -type f | while read prompt_file; do \
		rel_path=$$(echo "$$prompt_file" | sed 's|agents/prompts/||'); \
		output_file="agents/cards/$$(echo "$$rel_path" | sed 's|\.md$$|.json|')"; \
		$(MAKE) "$$output_file"; \
	done
	@echo "Agent card generation complete!"

# Pattern rule for generating individual agent cards with dependency checking
agents/cards/%.json: agents/prompts/%.md
	@echo "Generating: $@ from $<"
	@mkdir -p $(dir $@)
	@if PYTHONPATH=src $(VENV_PYTHON) -m mantis agent generate --model claude-opus-4-0 --input "$<" --output "$@"; then \
		echo "✅ Generated: $@"; \
	else \
		echo "❌ Failed to generate: $@"; \
		exit 1; \
	fi
