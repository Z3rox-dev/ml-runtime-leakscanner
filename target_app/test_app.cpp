#include <iostream>
#include <chrono>
#include <thread>
#include <vector>
#include <cstdlib>
#include <cstring>
#include <unistd.h>

class BuggyApp {
private:
    std::vector<void*> leaked_memory;
    
public:
    // Pattern 1: Memory leak progressivo
    void memory_leak_pattern() {
        std::cout << "[MEMORY LEAK] Starting memory leak simulation..." << std::endl;
        
        for(int i = 0; i < 100; i++) {
            // Alloca memoria crescente
            size_t size = 1024 * (i + 1); // Da 1KB a 100KB
            void* ptr = malloc(size);
            
            if(ptr) {
                memset(ptr, 0xAA, size); // Riempi con pattern
                leaked_memory.push_back(ptr);
                std::cout << "Allocated " << size << " bytes (total allocations: " 
                         << leaked_memory.size() << ")" << std::endl;
            }
            
            std::this_thread::sleep_for(std::chrono::milliseconds(500));
        }
        
        std::cout << "Memory leak pattern completed. " << leaked_memory.size() 
                 << " allocations never freed!" << std::endl;
    }
    
    // Comportamento normale
    void normal_operations() {
        std::cout << "[NORMAL] Application starting normally..." << std::endl;
        
        for(int i = 0; i < 10; i++) {
            std::cout << "Normal operation " << (i + 1) << "/10" << std::endl;
            
            // Simula lavoro normale
            int* temp = new int[100];
            for(int j = 0; j < 100; j++) {
                temp[j] = j * j;
            }
            delete[] temp;
            
            std::this_thread::sleep_for(std::chrono::milliseconds(1000));
        }
        
        std::cout << "[NORMAL] Normal operations completed." << std::endl;
    }
    
    ~BuggyApp() {
        // Cleanup (anche se nella vita reale questi leak non vengono puliti)
        for(void* ptr : leaked_memory) {
            free(ptr);
        }
    }
};

int main(int argc, char* argv[]) {
    std::cout << "=== MEMORY LEAK TEST APPLICATION ===" << std::endl;
    std::cout << "PID: " << getpid() << std::endl;
    std::cout << "Usage: " << argv[0] << " [mode]" << std::endl;
    std::cout << "Modes: normal, leak, or no arguments for both" << std::endl;
    
    BuggyApp app;
    
    std::string mode = "both";
    if(argc > 1) {
        mode = argv[1];
    }
    
    if(mode == "normal" || mode == "both") {
        app.normal_operations();
    }
    
    if(mode == "leak" || mode == "both") {
        std::cout << "\n=== STARTING MEMORY LEAK PATTERN ===" << std::endl;
        app.memory_leak_pattern();
    }
    
    std::cout << "\n=== APPLICATION ENDING ===" << std::endl;
    return 0;
}