#!/bin/bash

echo "🐳 Starting ML-guided Runtime Instrumentation environment..."

# Build container se non esiste
if [[ "$(docker images -q ml-runtime-debug 2> /dev/null)" == "" ]]; then
    echo "📦 Building Docker image..."
    docker compose build
fi

# Avvia ambiente di sviluppo
echo "🚀 Starting development environment..."
docker compose up -d

# Entra nel container
echo "🔧 Entering development container..."
docker compose exec ml-runtime-debug bash

