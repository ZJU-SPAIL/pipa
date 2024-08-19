all: clean lint build uninstall install test

build:
	python -m build

clean:
	rm -rf dist
	rm -rf htmlcov

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
	pip install pytest coverage coverage-badge
	coverage run -m pytest --ignore=data
	coverage report
	coverage html
	coverage-badge -o ./asset/coverage.svg

lint:
	pip install flake8 black
	flake8 ./src --count --show-source --statistics
	black ./src --check --verbose
