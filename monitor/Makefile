CC = g++
CFLAGS = -std=c++17 -Wall -Wextra -O2 -g -fPIC
LDFLAGS = -shared -ldl -lpthread

# Targets
BASIC_AGENT = agent.so
ADVANCED_AGENT = advanced_agent.so

# Source files
BASIC_SRC = agent.cpp
ADVANCED_SRC = advanced_agent.cpp

# Default target
all: $(BASIC_AGENT) $(ADVANCED_AGENT)

# Basic agent (original malloc interceptor)
$(BASIC_AGENT): $(BASIC_SRC)
	@echo "🔨 Compiling basic agent..."
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $<
	@echo "✅ Basic agent compiled: $@"

# Advanced agent (O(1) leak detection)
$(ADVANCED_AGENT): $(ADVANCED_SRC)
	@echo "🔨 Compiling advanced agent..."
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $<
	@echo "✅ Advanced agent compiled: $@"

# Test compilation only (no linking)
test-compile: $(BASIC_SRC) $(ADVANCED_SRC)
	@echo "🧪 Testing compilation..."
	$(CC) $(CFLAGS) -c $(BASIC_SRC) -o basic_test.o
	$(CC) $(CFLAGS) -c $(ADVANCED_SRC) -o advanced_test.o
	@rm -f basic_test.o advanced_test.o
	@echo "✅ All sources compile successfully"

# Clean up
clean:
	@echo "🧹 Cleaning up..."
	rm -f $(BASIC_AGENT) $(ADVANCED_AGENT) *.o
	@echo "✅ Clean complete"

# Install (copy to system locations if needed)
install: $(BASIC_AGENT) $(ADVANCED_AGENT)
	@echo "📦 Installing agents..."
	@mkdir -p ./lib
	cp $(BASIC_AGENT) ./lib/
	cp $(ADVANCED_AGENT) ./lib/
	@echo "✅ Agents installed to ./lib/"

# Check shared memory
check-shm:
	@echo "🔍 Checking shared memory status..."
	@ls -la /dev/shm/ml_* 2>/dev/null || echo "No ML shared memory found"

# Clean shared memory
clean-shm:
	@echo "🧹 Cleaning shared memory..."
	@rm -f /dev/shm/ml_*
	@echo "✅ Shared memory cleaned"

# Demo targets
demo-basic: $(BASIC_AGENT)
	@echo "🎬 Running basic agent demo..."
	cd ../target_app && LD_PRELOAD=../monitor/$(BASIC_AGENT) ./test_app

demo-advanced: $(ADVANCED_AGENT)
	@echo "🎬 Running advanced agent demo..."
	cd ../target_app && LD_PRELOAD=../monitor/$(ADVANCED_AGENT) ./test_app

# Development helpers
rebuild: clean all

force: clean
	@$(MAKE) all

# Show build info
info:
	@echo "🛠️  BUILD INFORMATION"
	@echo "===================="
	@echo "Compiler: $(CC)"
	@echo "C++ Flags: $(CFLAGS)"
	@echo "Linker Flags: $(LDFLAGS)"
	@echo "Basic Agent: $(BASIC_AGENT)"
	@echo "Advanced Agent: $(ADVANCED_AGENT)"
	@echo ""
	@echo "📋 Available targets:"
	@echo "  all           - Build both agents"
	@echo "  basic         - Build basic agent only"
	@echo "  advanced      - Build advanced agent only"
	@echo "  test-compile  - Test compilation without linking"
	@echo "  clean         - Remove build artifacts"
	@echo "  install       - Install to ./lib/"
	@echo "  demo-basic    - Run basic agent demo"
	@echo "  demo-advanced - Run advanced agent demo"
	@echo "  check-shm     - Check shared memory status"
	@echo "  clean-shm     - Clean shared memory"

# Individual targets for convenience
basic: $(BASIC_AGENT)
advanced: $(ADVANCED_AGENT)

# Phony targets
.PHONY: all clean install demo-basic demo-advanced test-compile check-shm clean-shm rebuild force info basic advanced
