#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <dlfcn.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <pthread.h>
#include <atomic>
#include <cstdint>

// ========================================
// ADVANCED AGENT WITH O(1) HEADER TRICK
// ========================================

// Metadata structure embedded in each allocation
struct AllocationMeta {
    uint32_t magic;          // Magic number for validation (0xDEADBEEF)
    size_t size;             // Original allocation size
    uint64_t alloc_time;     // Allocation timestamp (nanoseconds)
    uint64_t last_access;    // Last access timestamp
    uint32_t site_id;        // Call site identifier
    uint32_t thread_id;      // Thread that allocated
} __attribute__((packed));

// Event types for shared memory logging
enum EventType {
    EVENT_MALLOC = 1,
    EVENT_FREE = 2,
    EVENT_LEAK_DETECTED = 3,
    EVENT_ACCESS_PATTERN = 4
};

// Event structure for shared memory
struct LeakEvent {
    int32_t event_id;
    int32_t event_type;
    uint64_t timestamp;
    uint32_t thread_id;
    
    union {
        struct {
            void* address;
            size_t size;
            uint64_t staleness_ns;
            uint32_t site_id;
        } leak;
        
        struct {
            void* address;
            size_t size;
            uint64_t alloc_time;
            uint32_t site_id;
        } allocation;
    } data;
    
    int32_t is_valid;
} __attribute__((packed));

#define LEAK_BUFFER_SIZE 1000
struct LeakDetectionBuffer {
    volatile int write_index;
    volatile int read_index;
    volatile uint64_t total_allocations;
    volatile uint64_t total_frees;
    volatile uint64_t current_memory;
    volatile uint32_t leak_count;
    LeakEvent events[LEAK_BUFFER_SIZE];
} __attribute__((packed));

// Global state
static LeakDetectionBuffer* leak_buffer = nullptr;
static int shm_fd = -1;
static volatile uint32_t next_event_id = 1;
static std::atomic<int> event_counter{0};
static std::atomic<uint64_t> staleness_threshold_ns{3000000000ULL}; // 3 seconds for demo

// Function pointers to original functions
static void* (*real_malloc)(size_t) = nullptr;
static void (*real_free)(void*) = nullptr;
static void* (*real_realloc)(void*, size_t) = nullptr;
static void* (*real_calloc)(size_t, size_t) = nullptr;

// Statistics tracking
static std::atomic<uint64_t> total_allocations{0};
static std::atomic<uint64_t> total_frees{0};
static std::atomic<uint64_t> current_memory_usage{0};

// Magic number for header validation
#define ALLOC_MAGIC 0xDEADBEEF

// Simple active allocations tracking for leak detection
#define MAX_TRACKED_ALLOCS 10000
static struct {
    void* address;
    AllocationMeta* meta;
} active_allocs[MAX_TRACKED_ALLOCS];
static volatile int active_alloc_count = 0;

// Helper functions
static inline uint64_t get_timestamp_ns() {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec * 1000000000ULL + ts.tv_nsec;
}

static inline uint32_t get_thread_id() {
    return (uint32_t)pthread_self();
}

static inline uint32_t get_call_site_id() {
    // Simple hash of return address for call site identification
    void* caller = __builtin_return_address(0);
    return (uint32_t)((uintptr_t)caller >> 4) & 0xFFFF;
}

// Add allocation to tracking list
static void track_allocation(void* user_ptr, AllocationMeta* meta) {
    if (active_alloc_count < MAX_TRACKED_ALLOCS) {
        int index = active_alloc_count++;
        active_allocs[index].address = user_ptr;
        active_allocs[index].meta = meta;
    }
}

// Remove allocation from tracking list  
static void untrack_allocation(void* user_ptr) {
    for (int i = 0; i < active_alloc_count; i++) {
        if (active_allocs[i].address == user_ptr) {
            // Remove by swapping with last element
            active_allocs[i] = active_allocs[active_alloc_count - 1];
            active_alloc_count--;
            break;
        }
    }
}

// Write event to shared memory
static void write_leak_event(int event_type, void* data) {
    if (!leak_buffer) return;
    
    LeakEvent event = {};  // Zero-initialize all fields
    event.event_id = next_event_id++;
    event.event_type = event_type;
    event.timestamp = get_timestamp_ns();
    event.thread_id = static_cast<uint32_t>(pthread_self());
    event.is_valid = 1;
    
    // Copy event-specific data
    if (data) {
        memcpy(&event.data, data, sizeof(event.data));
    }
    
    // Write to circular buffer
    int slot = leak_buffer->write_index % LEAK_BUFFER_SIZE;
    leak_buffer->events[slot] = event;
    leak_buffer->write_index++;
}

// Validate allocation header
static inline bool is_valid_allocation(AllocationMeta* meta) {
    return meta && meta->magic == ALLOC_MAGIC;
}

// Get metadata from user pointer - O(1) operation!
static inline AllocationMeta* get_meta_from_user_ptr(void* user_ptr) {
    if (!user_ptr) return nullptr;
    return ((AllocationMeta*)user_ptr) - 1;
}

// Get user pointer from metadata
static inline void* get_user_ptr_from_meta(AllocationMeta* meta) {
    return (void*)(meta + 1);
}

// Update access time (called by memory access sampling)
extern "C" void update_allocation_access(void* addr) {
    if (!addr) return;
    
    AllocationMeta* meta = get_meta_from_user_ptr(addr);
    if (is_valid_allocation(meta)) {
        meta->last_access = get_timestamp_ns();
    }
}

// Check if allocation is potentially leaked
static bool is_potentially_leaked(AllocationMeta* meta) {
    if (!is_valid_allocation(meta)) return false;
    
    uint64_t now = get_timestamp_ns();
    uint64_t staleness = now - meta->last_access;
    
    return staleness > staleness_threshold_ns.load();
}

// Report potential leak
static void report_leak(AllocationMeta* meta, void* user_ptr) {
    uint64_t now = get_timestamp_ns();
    uint64_t staleness = now - meta->last_access;
    
    struct {
        void* address;
        size_t size;
        uint64_t staleness_ns;
        uint32_t site_id;
    } leak_data = {
        user_ptr,
        meta->size,
        staleness,
        meta->site_id
    };
    
    write_leak_event(EVENT_LEAK_DETECTED, &leak_data);
    
    leak_buffer->leak_count++;
    
    // Also log to stderr for immediate visibility
    fprintf(stderr, "[LEAK] %p: %zu bytes, stale for %.2fs, site_id=%u\n",
            user_ptr, meta->size, staleness / 1e9, meta->site_id);
}

// Advanced malloc with header trick
extern "C" void* malloc(size_t size) {
    if (!real_malloc) {
        real_malloc = (void*(*)(size_t))dlsym(RTLD_NEXT, "malloc");
    }
    
    if (size == 0) return nullptr;
    
    // Allocate extra space for metadata header
    size_t total_size = size + sizeof(AllocationMeta);
    void* real_ptr = real_malloc(total_size);
    
    if (!real_ptr) return nullptr;
    
    // Initialize metadata header
    AllocationMeta* meta = (AllocationMeta*)real_ptr;
    meta->magic = ALLOC_MAGIC;
    meta->size = size;
    meta->alloc_time = get_timestamp_ns();
    meta->last_access = meta->alloc_time;  // Initial access = allocation time
    meta->site_id = get_call_site_id();
    meta->thread_id = get_thread_id();
    
    // Calculate user pointer (after header)
    void* user_ptr = get_user_ptr_from_meta(meta);
    
    // Track this allocation for leak detection
    track_allocation(user_ptr, meta);
    
    // Update statistics
    total_allocations++;
    current_memory_usage += size;
    
    if (leak_buffer) {
        leak_buffer->total_allocations++;
        leak_buffer->current_memory += size;
        
        // Log allocation event
        struct {
            void* address;
            size_t size;
            uint64_t alloc_time;
            uint32_t site_id;
        } alloc_data = {user_ptr, size, meta->alloc_time, meta->site_id};
        
        write_leak_event(EVENT_MALLOC, &alloc_data);
    }
    
    return user_ptr;
}

// Advanced free with O(1) metadata lookup
extern "C" void free(void* ptr) {
    if (!real_free) {
        real_free = (void(*)(void*))dlsym(RTLD_NEXT, "free");
    }
    
    if (!ptr) return;
    
    // Get metadata using header trick - O(1)!
    AllocationMeta* meta = get_meta_from_user_ptr(ptr);
    
    if (!is_valid_allocation(meta)) {
        // Not our allocation or corrupted header
        real_free(ptr);
        return;
    }
    
    // Update statistics
    total_frees++;
    current_memory_usage -= meta->size;
    
    // Remove from tracking
    untrack_allocation(ptr);
    
    if (leak_buffer) {
        leak_buffer->total_frees++;
        leak_buffer->current_memory -= meta->size;
        
        // Log free event
        struct {
            void* address;
            size_t size;
            uint64_t alloc_time;
            uint32_t site_id;
        } free_data = {ptr, meta->size, meta->alloc_time, meta->site_id};
        
        write_leak_event(EVENT_FREE, &free_data);
    }
    
    // Clear magic to detect double-free
    meta->magic = 0;
    
    // Free the real pointer (including header)
    real_free((void*)meta);
}

// Realloc implementation
extern "C" void* realloc(void* ptr, size_t size) {
    if (!real_realloc) {
        real_realloc = (void*(*)(void*, size_t))dlsym(RTLD_NEXT, "realloc");
    }
    
    if (!ptr) return malloc(size);
    if (size == 0) {
        free(ptr);
        return nullptr;
    }
    
    // Get old metadata
    AllocationMeta* old_meta = get_meta_from_user_ptr(ptr);
    if (!is_valid_allocation(old_meta)) {
        // Not our allocation, pass through
        return real_realloc(ptr, size);
    }
    
    size_t old_size = old_meta->size;
    
    // Allocate new block
    void* new_ptr = malloc(size);
    if (!new_ptr) return nullptr;
    
    // Copy old data
    size_t copy_size = (size < old_size) ? size : old_size;
    memcpy(new_ptr, ptr, copy_size);
    
    // Free old block
    free(ptr);
    
    return new_ptr;
}

// Calloc implementation
extern "C" void* calloc(size_t nmemb, size_t size) {
    if (!real_calloc) {
        real_calloc = (void*(*)(size_t, size_t))dlsym(RTLD_NEXT, "calloc");
    }
    
    size_t total_size = nmemb * size;
    void* ptr = malloc(total_size);
    
    if (ptr) {
        memset(ptr, 0, total_size);
    }
    
    return ptr;
}

// Leak scanning thread function
static void* leak_scanner_thread(void* arg) {
    (void)arg;  // Unused
    
    while (true) {
        sleep(5);  // Scan every 5 seconds
        
        if (leak_buffer) {
            printf("[SCANNER] Active allocations: %lu, Total memory: %.2f MB\n",
                   leak_buffer->total_allocations - leak_buffer->total_frees,
                   leak_buffer->current_memory / (1024.0*1024.0));
            
            // Scan for potential leaks
            int leaks_found = 0;
            for (int i = 0; i < active_alloc_count; i++) {
                AllocationMeta* meta = active_allocs[i].meta;
                void* user_ptr = active_allocs[i].address;
                
                if (is_valid_allocation(meta) && is_potentially_leaked(meta)) {
                    report_leak(meta, user_ptr);
                    leaks_found++;
                }
            }
            
            if (leaks_found > 0) {
                printf("[SCANNER] 🔥 Found %d potential leaks!\n", leaks_found);
            }
        }
    }
    
    return nullptr;
}

// Set staleness threshold
extern "C" void set_staleness_threshold_seconds(double seconds) {
    staleness_threshold_ns.store((uint64_t)(seconds * 1e9));
    printf("[AGENT] Staleness threshold set to %.2f seconds\n", seconds);
}

// Get current statistics
extern "C" void get_allocation_stats(uint64_t* allocs, uint64_t* frees, uint64_t* current_mem) {
    if (allocs) *allocs = total_allocations.load();
    if (frees) *frees = total_frees.load();
    if (current_mem) *current_mem = current_memory_usage.load();
}

// Initialize advanced agent
__attribute__((constructor))
void advanced_agent_init() {
    printf("[ADVANCED AGENT] Initializing with O(1) leak detection...\n");
    
    // Initialize function pointers
    real_malloc = (void*(*)(size_t))dlsym(RTLD_NEXT, "malloc");
    real_free = (void(*)(void*))dlsym(RTLD_NEXT, "free");
    real_realloc = (void*(*)(void*, size_t))dlsym(RTLD_NEXT, "realloc");
    real_calloc = (void*(*)(size_t, size_t))dlsym(RTLD_NEXT, "calloc");
    
    // Create shared memory for leak detection
    shm_fd = shm_open("/ml_advanced_leak_detection", O_CREAT | O_RDWR, 0666);
    if (shm_fd != -1) {
        if (ftruncate(shm_fd, sizeof(LeakDetectionBuffer)) == -1) {
            perror("ftruncate");
            close(shm_fd);
            return;
        }
        leak_buffer = (LeakDetectionBuffer*)mmap(0, sizeof(LeakDetectionBuffer),
                                               PROT_READ | PROT_WRITE, MAP_SHARED, shm_fd, 0);
        
        if (leak_buffer != MAP_FAILED) {
            // Initialize the buffer properly
            leak_buffer->write_index = 0;
            leak_buffer->read_index = 0;
            leak_buffer->total_allocations = 0;
            leak_buffer->total_frees = 0;
            leak_buffer->current_memory = 0;
            leak_buffer->leak_count = 0;
            
            // Zero-initialize events array
            for (int i = 0; i < LEAK_BUFFER_SIZE; i++) {
                leak_buffer->events[i] = {};
            }
            printf("[ADVANCED AGENT] Shared memory created: %zu bytes\n", sizeof(LeakDetectionBuffer));
        } else {
            leak_buffer = nullptr;
        }
    }
    
    // Start leak scanner thread
    pthread_t scanner_thread;
    pthread_create(&scanner_thread, nullptr, leak_scanner_thread, nullptr);
    pthread_detach(scanner_thread);
    
    printf("[ADVANCED AGENT] Initialization complete!\n");
}

// Cleanup
__attribute__((destructor))
void advanced_agent_cleanup() {
    printf("[ADVANCED AGENT] Shutting down...\n");
    printf("Final stats: %lu allocations, %lu frees, %lu bytes current\n",
           total_allocations.load(), total_frees.load(), current_memory_usage.load());
    
    if (leak_buffer) {
        munmap(leak_buffer, sizeof(LeakDetectionBuffer));
        close(shm_fd);
        shm_unlink("/ml_advanced_leak_detection");
    }
}
