# Dockerfile per l'ambiente di sviluppo del ML-guided runtime instrumentation
FROM ubuntu:22.04

# Evita prompt interattivi durante l'installazione
ENV DEBIAN_FRONTEND=noninteractive

# Installa dipendenze di base
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    gdb \
    cmake \
    make \
    git \
    vim \
    nano \
    python3 \
    python3-pip \
    python3-dev \
    strace \
    ltrace \
    valgrind \
    binutils \
    elfutils \
    libunwind-dev \
    libc6-dbg \
    pkg-config \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Installa librerie Python per ML
RUN pip3 install \
    numpy \
    pandas \
    scikit-learn \
    matplotlib \
    psutil \
    watchdog

# Crea directory di lavoro
WORKDIR /workspace

# Copia il progetto (verrà montato come volume)
COPY . .

# Compila l'app di test
RUN if [ -f test_app.cpp ]; then \
        g++ -o test_app test_app.cpp -std=c++11 -pthread -g; \
    fi

# Script di avvio per compilazione automatica
RUN echo '#!/bin/bash\n\
echo "=== ML-guided Runtime Instrumentation Development Environment ==="\n\
echo "Available tools:"\n\
echo "  - GCC/G++ compiler"\n\
echo "  - GDB debugger"\n\
echo "  - Valgrind memory analyzer"\n\
echo "  - Python3 with ML libraries"\n\
echo "  - strace/ltrace for system call tracing"\n\
echo ""\n\
echo "Quick start:"\n\
echo "  1. Compile buggy app: make compile-target"\n\
echo "  2. Run tests: make test"\n\
echo "  3. Develop monitor: cd monitor/"\n\
echo ""\n\
if [ -f /workspace/test_app ]; then\n\
    echo "Buggy app already compiled and ready!"\n\
else\n\
    echo "Compiling test_app..."\n\
    if [ -f /workspace/test_app.cpp ]; then\n\
        g++ -o /workspace/test_app /workspace/test_app.cpp -std=c++11 -pthread -g\n\
        echo "test app compiled successfully"\n\
    fi\n\
fi\n\
\n\
exec "$@"' > /usr/local/bin/entrypoint.sh && \
    chmod +x /usr/local/bin/entrypoint.sh

# Makefile per semplificare la compilazione
RUN echo 'CXX = g++\n\
CXXFLAGS = -std=c++11 -pthread -g -Wall\n\
\n\
# Target principale\n\
all: test_app\n\
\n\
# Compila app di test\n\
test_app: test_app.cpp\n\
\ttab$(CXX) $(CXXFLAGS) -o $@ $<\n\
\n\
# Compila monitor agent (quando sarà pronto)\n\
monitor: monitor/agent.cpp\n\
\ttab$(CXX) $(CXXFLAGS) -shared -fPIC -o monitor/agent.so monitor/agent.cpp\n\
\n\
# Test rapidi\n\
test: test_app\n\
\ttab@echo "Testing memory leak pattern..."\n\
\ttab./test_app 1 &\n\
\ttabsleep 10\n\
\ttabkillall test_app || true\n\
\n\
# Cleanup\n\
clean:\n\
\ttrm -f test_app monitor/*.so\n\
\n\
# Alias utili\n\
compile-target: test_app\n\
compile-monitor: monitor\n\
\n\
.PHONY: all test clean compile-target compile-monitor' | sed 's/tab/\t/g' > /workspace/Makefile

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["/bin/bash"]