#include <stdio.h>
#include <stdlib.h>
#include <dlfcn.h>
#include <unistd.h>
#include <time.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <cstdint> // Use fixed-size integers for cross-language compatibility

// Data structure for shared memory using fixed-size types
struct AllocationData {
    int32_t malloc_count;
    uint64_t size;
    uint64_t total_bytes;
    int64_t timestamp;
    int32_t is_valid;  // 0=empty, 1=valid data
} __attribute__((packed));

#define BUFFER_SIZE 1000
struct SharedBuffer {
    // Moved indexes to the top to match Python analyzer's expectation
    volatile int write_index;
    volatile int read_index;
    AllocationData allocations[BUFFER_SIZE];
} __attribute__((packed));

// Global variables
static void* (*real_malloc)(size_t) = NULL;
static int malloc_count = 0;
static size_t total_bytes_allocated = 0;
static SharedBuffer* shared_buffer = NULL;
static int shm_fd = -1;

void write_to_shared_memory(int count, size_t size, size_t total) {
    if (shared_buffer == NULL) return;

    // Get the index for the new data.
    int next_slot = shared_buffer->write_index % BUFFER_SIZE;

    // Prepare the data packet first.
    AllocationData data = {count, size, total, time(NULL), 1};

    // Write the complete data structure to the buffer.
    shared_buffer->allocations[next_slot] = data;

    // Insert a full memory barrier. This is the critical step.
    // It ensures that all the writes to the `data` structure above are
    // fully completed and visible to other processes *before* the write
    // index is incremented below. This prevents the Python analyzer
    // from reading a partially-written record.
    __sync_synchronize();

    // Now, atomically increment the write index to "publish" the new data.
    shared_buffer->write_index++;
}

__attribute__((constructor))
void agent_start() {
    real_malloc = (void* (*)(size_t))dlsym(RTLD_NEXT, "malloc");

    // Create and map shared memory
    shm_fd = shm_open("/ml_runtime_shm", O_CREAT | O_RDWR, 0666);
    if (shm_fd != -1) {
        ftruncate(shm_fd, sizeof(SharedBuffer));
        shared_buffer = (SharedBuffer*)mmap(0, sizeof(SharedBuffer),
                                           PROT_READ | PROT_WRITE, MAP_SHARED, shm_fd, 0);
        if (shared_buffer != MAP_FAILED) {
            // Initialize buffer - this will now correctly zero everything,
            // including the indexes at the start.
            memset(shared_buffer, 0, sizeof(SharedBuffer));
        } else {
            shared_buffer = NULL;
        }
    }
}

__attribute__((destructor))
void agent_stop() {
    if (shared_buffer != NULL) {
        munmap(shared_buffer, sizeof(SharedBuffer));
        close(shm_fd);
        shm_unlink("/ml_runtime_shm");
    }
}

extern "C" void* malloc(size_t size) {
    // Ottieni la malloc originale
    if (!real_malloc) {
        real_malloc = (void*(*)(size_t))dlsym(RTLD_NEXT, "malloc");
    }
    
    // Chiama la malloc originale
    void* ptr = real_malloc(size);
    
    // Conta e stampa direttamente su stdout (niente file)
    if (ptr) {
        malloc_count++;
        total_bytes_allocated += size;

        // Write to shared memory instead of file
        write_to_shared_memory(malloc_count, size, total_bytes_allocated);
    }
    
    return ptr;
}
