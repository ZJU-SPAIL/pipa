all: clean lint build uninstall install install-scripts test

build:
	pip install build
	python -m build

clean:
	rm -rf dist

install:
	pip install dist/*.whl

uninstall:
	@if pip freeze | grep -q pypipa; then \
		pip uninstall -y pypipa; \
	else \
		echo "pypipa not installed."; \
	fi

install-scripts:
	@echo "Installing PIPA scripts..."
	@# Create user's bin directory if it doesn't exist
	@mkdir -p $(HOME)/.local/bin
	@# Copy scripts to user's bin directory
	@cp -f ./script/pipa-collect.sh $(HOME)/.local/bin/pipa-collect
	@cp -f ./script/pipa-parse.sh $(HOME)/.local/bin/pipa-parse
	@# Make sure scripts are executable
	@chmod +x $(HOME)/.local/bin/pipa-collect
	@chmod +x $(HOME)/.local/bin/pipa-parse
	@echo "Scripts installed successfully to $(HOME)/.local/bin"
	@echo "Please ensure $(HOME)/.local/bin is in your PATH"

.PHONY: test
test:
	pip install pytest
	pytest --ignore=data

lint:
	pip install flake8 black
	flake8 ./src --count --show-source --statistics
	black ./src --check --verbose