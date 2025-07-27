# Environtment Variables
.PHONY: all build-server run-server clean-server

all : build

# Accumulated build for all the services
build : build-server

# Install server dependencies
deps-server:
	go mod tidy

# Build for server
build-server: deps-server
	go build -o bin/server cmd/server.go

# Run server by building binary
start-server: build-server
	./bin/server

# Run server without building binary
run-server:
	go run cmd/server.go

clean-server:
	rm -rf bin
