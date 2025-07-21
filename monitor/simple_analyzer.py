#!/usr/bin/env python3
"""
Simplified Advanced Analyzer - Focus on Working Demo
"""

import struct
import time
import mmap
import os
import sys
import signal

class SimpleAdvancedAnalyzer:
    def __init__(self):
        self.shm_fd = None
        self.shm = None
        self.running = True
        
        # Header struct: write_index(4), read_index(4), total_allocs(8), total_frees(8), current_mem(8), leak_count(4)
        self.header_struct = struct.Struct('<iiQQQI')
        
        # Stats for demo
        self.last_stats = None
        
    def connect_to_shared_memory(self, retries=5):
        """Connect to advanced agent's shared memory"""
        for attempt in range(retries):
            try:
                self.shm_fd = os.open("/dev/shm/ml_advanced_leak_detection", os.O_RDONLY)
                self.shm = mmap.mmap(self.shm_fd, 0, access=mmap.ACCESS_READ)
                print("✅ Connected to advanced leak detection shared memory")
                return True
            except FileNotFoundError:
                if attempt < retries - 1:
                    print(f"⏳ Waiting for advanced agent... (attempt {attempt + 1}/{retries})")
                    time.sleep(1)
                    continue
                else:
                    print("❌ Failed to connect to shared memory after all retries")
                    return False
            except Exception as e:
                print(f"❌ Error connecting to shared memory: {e}")
                return False
        return False
    
    def read_stats(self):
        """Read buffer statistics"""
        if not self.shm:
            return None
        
        try:
            self.shm.seek(0)
            header_data = self.shm.read(self.header_struct.size)
            
            if len(header_data) == self.header_struct.size:
                write_index, read_index, total_allocs, total_frees, current_mem, leak_count = \
                    self.header_struct.unpack(header_data)
                
                return {
                    'write_index': write_index,
                    'read_index': read_index,
                    'total_allocations': total_allocs,
                    'total_frees': total_frees,
                    'current_memory': current_mem,
                    'leak_count': leak_count,
                    'active_allocations': total_allocs - total_frees
                }
        except Exception as e:
            print(f"Error reading stats: {e}")
        
        return None
    
    def monitor_real_time(self):
        """Simple monitoring focusing on statistics"""
        print("🚀 Advanced leak detection monitoring started...")
        print("📊 Monitoring allocation statistics in real-time...")
        print()
        
        while self.running:
            try:
                stats = self.read_stats()
                
                if stats:
                    # Check if stats changed
                    if self.last_stats != stats:
                        self.print_stats_update(stats)
                        self.last_stats = stats.copy()
                    
                    # Check for potential issues
                    if stats['active_allocations'] > 50:
                        print(f"⚠️  HIGH ALLOCATION COUNT: {stats['active_allocations']} active allocations")
                    
                    if stats['current_memory'] > 1024 * 1024:  # > 1MB
                        memory_mb = stats['current_memory'] / (1024 * 1024)
                        print(f"⚠️  HIGH MEMORY USAGE: {memory_mb:.2f} MB")
                    
                    if stats['leak_count'] > 0:
                        print(f"🔥 LEAK DETECTED: {stats['leak_count']} potential leaks found!")
                
                time.sleep(0.5)  # Check every 500ms
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Error in monitoring loop: {e}")
                time.sleep(1)
    
    def print_stats_update(self, stats):
        """Print statistics update"""
        memory_kb = stats['current_memory'] / 1024
        
        print(f"📊 STATS UPDATE:")
        print(f"   Total allocations: {stats['total_allocations']}")
        print(f"   Total frees: {stats['total_frees']}")
        print(f"   Active allocations: {stats['active_allocations']}")
        print(f"   Current memory: {memory_kb:.1f} KB")
        print(f"   Events written: {stats['write_index']}")
        
        if stats['leak_count'] > 0:
            print(f"   🔥 Leaks detected: {stats['leak_count']}")
        
        print()
    
    def cleanup(self):
        """Clean up resources"""
        self.running = False
        if self.shm:
            self.shm.close()
        if self.shm_fd:
            os.close(self.shm_fd)

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print("\n🛑 Shutdown signal received...")
    sys.exit(0)

def main():
    """Main function"""
    print("🧠 SIMPLIFIED ADVANCED MEMORY ANALYZER")
    print("=====================================")
    print()
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    analyzer = SimpleAdvancedAnalyzer()
    
    try:
        # Connect to shared memory
        if not analyzer.connect_to_shared_memory():
            print("Failed to connect to advanced agent. Make sure it's running.")
            return 1
        
        # Start monitoring
        analyzer.monitor_real_time()
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        return 1
    finally:
        analyzer.cleanup()
        print("🏁 Analyzer shutdown complete")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
