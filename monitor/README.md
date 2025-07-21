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
