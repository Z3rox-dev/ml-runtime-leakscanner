#!/bin/bash

# Script di setup per ML-guided Runtime Instrumentation
echo "=== ML-guided Runtime Instrumentation Setup ==="

# Crea struttura directory del progetto
mkdir -p monitor logs target_app

# Sposta test_app nella directory corretta
if [ -f test_app.cpp ]; then
    mv test_app.cpp target_app/
    echo "✅ Moved test_app.cpp to target_app/"
fi

# Crea file README per ogni directory
cat > target_app/README.md << 'EOF'
# Target Applications

Questa directory contiene le applicazioni di test che verranno monitorate.

## Files:
- `test_app.cpp` - Applicazione di test con pattern di bug simulati

## Usage:
```bash
# Compila
g++ -o test_app test_app.cpp -std=c++11 -pthread -g

# Esegui pattern specifico
./test_app 1  # Memory leak
./test_app 2  # Excessive recursion
./test_app 3  # Array bounds
./test_app 4  # CPU spinning
./test_app 0  # All patterns
```
EOF

cat > monitor/README.md << 'EOF'
# Monitor System

Directory per il sistema di monitoraggio e instrumentation.

## Planned Components:
- `agent.cpp` - Shared library per injection nel processo target
- `injector.cpp` - Tool per iniettare l'agent nei processi
- `analyzer.py` - Sistema di analisi e decision-making ML

## Architecture:
```
Target Process
    ↓ injection
[agent.so] ←→ [analyzer.py] ←→ [decision engine]
    ↓ monitoring
[stack traces + signals] → [logs/] → [ML model]
```
EOF

cat > logs/README.md << 'EOF'
# Logs Directory

Directory per output, logs e dati raccolti dal sistema di monitoraggio.

## Structure:
- `runtime_logs/` - Log real-time del comportamento applicazioni
- `stack_traces/` - Stack traces catturati durante anomalie
- `ml_data/` - Dataset per training modelli ML
- `analysis/` - Output analisi e report
EOF

# Crea sottodirectory per logs
mkdir -p logs/{runtime_logs,stack_traces,ml_data,analysis}

# Script rapido per Docker
cat > run_docker.sh << 'EOF'
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

EOF

chmod +x run_docker.sh

# Script per cleanup
cat > cleanup.sh << 'EOF'
#!/bin/bash

echo "🧹 Cleaning up development environment..."

# Stop e remove containers
docker compose down

# Rimuovi immagini (opzionale)
read -p "Remove Docker images too? [y/N]: " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker rmi ml-runtime-debug || true
fi

# Cleanup file compilati
make clean 2>/dev/null || true
rm -f target_app/test_app

echo "✅ Cleanup completed!"
EOF

chmod +x cleanup.sh

# Crea .gitignore
cat > .gitignore << 'EOF'
# Compiled binaries
*.o
*.so
*.a
test_app
target_app/test_app

# Logs and data
logs/runtime_logs/*
logs/stack_traces/*
logs/ml_data/*
logs/analysis/*

# Docker
.docker/

# IDE
.vscode/
.idea/

# Python
__pycache__/
*.pyc
*.pyo

# Temporary files
*.tmp
*.log
core
core.*
EOF

echo ""
echo "✅ Project structure created!"
echo ""
echo "📁 Directory structure:"
tree . 2>/dev/null || find . -type d | sed 's/^/  /'
echo ""
echo "🚀 Quick start:"
echo "  1. Run: ./run_docker.sh"
echo "  2. Inside container: make compile-target"
echo "  3. Test: ./target_app/test_app 1"
echo ""
echo "🧹 Cleanup: ./cleanup.sh"