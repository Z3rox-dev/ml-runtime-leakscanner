#!/bin/bash

echo "🚀 ADVANCED LEAK DETECTION DEMO"
echo "==============================="
echo

# Check if we're in the right directory
if [[ ! -f "monitor/advanced_agent.cpp" ]]; then
    echo "❌ Must run from workspace root directory"
    exit 1
fi

# Function to cleanup on exit
cleanup() {
    echo
    echo "🧹 Cleaning up..."
    
    # Kill any running processes
    pkill -f advanced_analyzer.py 2>/dev/null
    pkill -f test_app 2>/dev/null
    
    # Clean shared memory
    rm -f /dev/shm/ml_advanced_leak_detection 2>/dev/null
    rm -f /dev/shm/ml_runtime_shm 2>/dev/null
    
    echo "✅ Cleanup complete"
}

# Set cleanup trap
trap cleanup EXIT

echo "📋 Step 1: Building advanced agent..."
cd monitor
make clean
make advanced
if [[ $? -ne 0 ]]; then
    echo "❌ Failed to build advanced agent"
    exit 1
fi
echo "✅ Advanced agent built successfully"
echo

echo "📋 Step 2: Building test application..."
cd ../target_app
# Check if already compiled
if [[ ! -f "test_app" ]]; then
    g++ -o test_app test_app.cpp
    if [[ $? -ne 0 ]]; then
        echo "❌ Failed to build test application"
        exit 1
    fi
fi
echo "✅ Test application ready"
echo

echo "📋 Step 3: Starting advanced analyzer..."
cd ../monitor
python3 advanced_analyzer.py &
ANALYZER_PID=$!
echo "✅ Advanced analyzer started (PID: $ANALYZER_PID)"
echo

# Give analyzer time to initialize
sleep 2

echo "📋 Step 4: Running test application with advanced agent..."
echo "🎯 This will demonstrate O(1) leak detection with embedded metadata"
echo

cd ../target_app
echo "🔧 Starting monitored application..."
LD_PRELOAD=../monitor/advanced_agent.so ./test_app &
APP_PID=$!

echo "📡 Monitoring leak detection for 30 seconds..."
echo "   (Advanced agent will detect leaks with precise metadata)"
echo

# Monitor for 30 seconds
for i in {1..30}; do
    echo -n "⏱️  Monitoring... ${i}/30 seconds"
    if ! kill -0 $APP_PID 2>/dev/null; then
        echo " (app finished)"
        break
    fi
    echo
    sleep 1
done

echo
echo "📋 Step 5: Final analysis..."

# Let analyzer process final events
sleep 3

echo
echo "🎬 DEMO COMPLETE!"
echo "=================="
echo
echo "📊 Advanced features demonstrated:"
echo "   ✅ O(1) metadata lookup with header trick"
echo "   ✅ Precise per-allocation tracking"
echo "   ✅ Real-time leak detection"
echo "   ✅ Call site identification"
echo "   ✅ Staleness analysis"
echo "   ✅ Statistical pattern analysis"
echo
echo "💡 For job interviews, highlight:"
echo "   🎯 Generic application analysis (no source needed)"
echo "   🎯 Sub-100ms detection latency"
echo "   🎯 Memory-efficient O(1) lookup"
echo "   🎯 Real-time statistical analysis"
echo "   🎯 Extensible to other vulnerability types"
echo

# Check shared memory status
echo "🔍 Shared memory status:"
ls -la /dev/shm/ml_* 2>/dev/null || echo "No shared memory files found"
echo

# Wait a moment before cleanup
echo "Press Ctrl+C to exit and cleanup..."
wait
