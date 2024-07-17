.PHONY: main format

all: main format
	@echo "Done"

main: pipad.proto
	python -m grpc_tools.protoc -I. --python_out=. --pyi_out=. --grpc_python_out=. ./pipad.proto

format:
	black . --verbose