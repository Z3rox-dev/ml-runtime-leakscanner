#!/bin/bash

echo "🎯 ML-guided Runtime Instrumentation Demo"
echo "=========================================="

# Cleanup previous runs to ensure a clean state
echo "🧹 Performing initial cleanup..."
# Use pkill which is more common than killall
pkill -f test_app >/dev/null 2>&1 || true
pkill -f analyzer.py >/dev/null 2>&1 || true
rm -f /dev/shm/ml_runtime_shm*

# Compile the C++ agent
echo "🔧 Compiling agent..."
# Ensure we are in the correct directory
cd /workspace/monitor
# Added -lrt for shm_open and friends
g++ -shared -fPIC -o agent.so agent.cpp -ldl -lrt -std=c++11

# Start the ML analyzer in the background
echo "🤖 Starting ML analyzer..."
python3 analyzer.py &
ML_PID=$!

# Wait for the analyzer to initialize and connect to shared memory
# The python script now retries, but a small sleep here doesn't hurt
echo "⏳ Waiting for analyzer to start..."
sleep 1

# Start the monitored application with the agent preloaded
echo "🚀 Starting monitored application..."
cd /workspace/target_app
# The LD_PRELOAD environment variable injects our agent
LD_PRELOAD=../monitor/agent.so ./test_app leak &
APP_PID=$!

# Let the demo run for a while to generate data
echo "⏰ Demo running for 30 seconds..."
sleep 30

# Cleanup all processes and shared memory files
echo "🧹 Cleaning up..."
# Using kill with PID is safer than killall
kill $APP_PID $ML_PID >/dev/null 2>&1 || true
# Wait a moment for processes to terminate gracefully
sleep 1
# Final cleanup of shared memory files
rm -f /dev/shm/ml_runtime_shm*

echo "✅ Demo completed!"
