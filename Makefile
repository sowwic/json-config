SHELL := /bin/bash

APP_NAME = json-config
DIST_DIR = dist
BUILD_DIR = build
MKDOCS_SITE_DIR = site
TEST_OUTPUT_DIR = .test_output


# Colors
BLUE := \033[34m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
MAGENTA := \033[35m
CYAN := \033[36m
RESET := \033[0m

# Banner helper
define banner
	@printf "$(CYAN)==>$(RESET) $(1)\n"
endef

.PHONY: help 
help: ## Show this help message
	@echo "Available make targets:"
	@echo ""
	@grep -E '^[a-zA-Z0-9_-]+:.*?##' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS=":.*?##"}; {printf "  %-15s %s\n", $$1, $$2}'
	@echo ""

.PHONY: clean
clean: ## Remove build artifacts, cache, and temporary files
	$(call banner, Cleaning project...)
	@rm -rf .pytest_cache
	@rm -rf .ruff_cache
	@rm -rf __pycache__
	@rm -rf .coverage
	@rm -rf src/**/__pycache__
	@rm -rf tests/**/__pycache__
	@rm -rf $(BUILD_DIR)
	@rm -rf $(DIST_DIR)
	@rm -rf $(TEST_OUTPUT_DIR)
	@rm -rf $(MKDOCS_SITE_DIR)
	@printf "$(GREEN)Clean up complete.$(RESET)\n"

.PHONY: lint
lint: ## Run the Ruff linter on source and test files
	$(call banner, Running Ruff linter...)
	@uv run ruff check src tests || true

.PHONY: lint-fix
lint-fix: ## Runs the Ruff linter on source and test files and applies fixes
	$(call banner, Running Ruff linter...)
	@uv run ruff check --fix src tests || true

.PHONY: format
format: ## Run the Ruff formatter on source and test files
	$(call banner, Running Ruff formatter...)
	@uv run ruff format src tests

.PHONY: pytest
pytest: ## Run pytest on tests directory
	$(call banner, Running pytest...)
	
	@uv run pytest tests
	
	
.PHONY: pytest-pdb
pytest-pdb: ## Run pytest with pdb on failure
	$(call banner, Cleaning pytest output dir...)
	@rm -rf $(TEST_OUTPUT_DIR)
	$(call banner, Running pytest with pdb...)
	
	@uv run pytest -vvv --pdb --log-cli-level=DEBUG tests
	
	
.PHONY: mkdocs
mkdocs:  ## Run MkDocs development server
	$(call banner, Building MkDocs documentation...)
	@uv run mkdocs serve
.PHONY: check
check: lint pytest ## Run all checks (linting and testing)


.PHONY: build
build: ## Build the application using uv
	$(call banner, Building $(APP_NAME)...)
	@uv build


