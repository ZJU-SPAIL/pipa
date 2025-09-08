# PIPA Makefile
# This file defines build, installation, testing, and other tasks for the PIPA project

# Variable definitions
USER_BIN_DIR := $(HOME)/.local/bin
SCRIPT_DIR := ./script
PYTHON := python3
PIP := pip

# Main target that executes all phases in order
all: clean lint build uninstall install install-scripts test

# Build the Python package
build:
	@echo "[Build Phase] Starting to build PIPA package..."
	@$(PIP) install --upgrade build
	@$(PYTHON) -m build
	@echo "[Build Phase] PIPA package build completed!"

# Clean up build artifacts
clean:
	@echo "[Clean Phase] Cleaning up build directories..."
	@rm -rf dist
	@echo "[Clean Phase] Build directories cleaned!"

# Install the Python package
install:
	@echo "[Install Phase] Installing PIPA package..."
	@$(PIP) install dist/*.whl
	@echo "[Install Phase] PIPA package installation completed!"

# Uninstall the Python package
uninstall:
	@echo "[Uninstall Phase] Checking if PIPA package is installed..."
	@if $(PIP) freeze | grep -q pypipa; then \
		$(PIP) uninstall -y pypipa; \
		echo "[Uninstall Phase] PIPA package has been uninstalled!"; \
	else \
		echo "[Uninstall Phase] PIPA package is not installed, no need to uninstall."; \
	fi

# Install scripts to user's bin directory
install-scripts:
	@echo "[Script Installation Phase] Starting to install PIPA scripts..."
	@echo "[Script Installation Phase] Checking if user's bin directory exists..."
	@mkdir -p $(USER_BIN_DIR)
	@echo "[Script Installation Phase] User's bin directory: $(USER_BIN_DIR)"
	@echo "[Script Installation Phase] Copying script files..."
	@cp -f $(SCRIPT_DIR)/pipa-collect.sh $(USER_BIN_DIR)/pipa-collect
	@cp -f $(SCRIPT_DIR)/pipa-parse.sh $(USER_BIN_DIR)/pipa-parse
	@echo "[Script Installation Phase] Setting script execution permissions..."
	@chmod +x $(USER_BIN_DIR)/pipa-collect
	@chmod +x $(USER_BIN_DIR)/pipa-parse
	@echo "[Script Installation Phase] Script installation successful!"
	@echo "[Script Installation Phase] Please ensure $(USER_BIN_DIR) is in your PATH environment variable."
	@echo "[Script Installation Phase] You can check by executing 'echo $${PATH}'."
	@echo "[Script Installation Phase] If it's not in PATH, you can add it to your ~/.bashrc or ~/.zshrc file:"
	@echo "[Script Installation Phase] echo 'export PATH=$$PATH:$(USER_BIN_DIR)' >> ~/.bashrc && source ~/.bashrc"

# Test target (declared as phony target)
.PHONY: test
test:
	@echo "[Test Phase] Installing test dependencies..."
	@$(PIP) install --upgrade pytest
	@echo "[Test Phase] Running test suite..."
	@pytest --ignore=data -v
	@echo "[Test Phase] Testing completed!"

# Code quality check
lint:
	@echo "[Code Check Phase] Installing code checking tools..."
	@$(PIP) install --upgrade flake8 black
	@echo "[Code Check Phase] Running flake8 static analysis..."
	@flake8 ./src --count --show-source --statistics
	@echo "[Code Check Phase] Running black code style check..."
	@black ./src --check --verbose
	@echo "[Code Check Phase] Code quality check passed!"

# Help information
help:
	@echo "PIPA Build and Installation Tool"
	@echo "Available commands:" 
	@echo "  make all          - Execute complete build, installation and test process"
	@echo "  make build        - Build Python package"
	@echo "  make clean        - Clean up build artifacts"
	@echo "  make install      - Install Python package"
	@echo "  make uninstall    - Uninstall Python package"
	@echo "  make install-scripts - Install PIPA scripts to user's bin directory"
	@echo "  make test         - Run test suite"
	@echo "  make lint         - Perform code quality check"
	@echo "  make help         - Display this help information"