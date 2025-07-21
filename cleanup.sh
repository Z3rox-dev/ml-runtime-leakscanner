#!/bin/bash

echo "🧹 Cleaning up development environment..."

# Cleanup processes
pkill -f test_app >/dev/null 2>&1 || true
pkill -f analyzer.py >/dev/null 2>&1 || true

# Cleanup shared memory
rm -f /dev/shm/ml_runtime_shm*

# Cleanup file compilati
make clean 2>/dev/null || true
rm -f target_app/test_app

echo "✅ Cleanup completed!"
