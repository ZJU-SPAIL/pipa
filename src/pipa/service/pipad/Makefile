.PHONY: main

main: pipad.proto
	python -m grpc_tools.protoc -I. --python_out=. --pyi_out=. --grpc_python_out=. ./pipad.proto