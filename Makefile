all: clean lint build uninstall install test

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

.PHONY: test
test:
	pip install pytest
	pytest --ignore=data

lint:
	pip install flake8 black
	flake8 ./src --count --show-source --statistics
	black ./src --check --verbose
