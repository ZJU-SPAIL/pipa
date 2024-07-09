all: clean lint test build uninstall install

build:
	python -m build

clean:
	rm -rf dist

install:
	pip install dist/*.whl

uninstall:
	pip uninstall -y pypipa

.PHONY: test
test:
	pytest

lint:
	flake8 . --count --show-source --statistics
