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
