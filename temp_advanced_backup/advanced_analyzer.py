#!/usr/bin/env python3
"""
Advanced Memory Leak Analyzer with O(1) Detection
=================================================

Reads from advanced agent's shared memory and provides:
- Real-time leak detection
- Statistical analysis
- Pattern recognition
- Advanced alerting
"""

import struct
import time
import mmap
import os
import json
import signal
import sys
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict, deque
import threading

@dataclass
class LeakEvent:
    event_id: int
    event_type: int
    timestamp: int  # nanoseconds
    thread_id: int
    data: Dict
    is_valid: int

@dataclass
class AllocationInfo:
    address: int
    size: int
    alloc_time: int
    site_id: int
    thread_id: int

@dataclass
class LeakInfo:
    address: int
    size: int
    staleness_ns: int
    site_id: int

class AdvancedLeakAnalyzer:
    def __init__(self):
        self.shm_fd = None
        self.shm = None
        self.running = True
        
        # Event type constants
        self.EVENT_MALLOC = 1
        self.EVENT_FREE = 2
        self.EVENT_LEAK_DETECTED = 3
        self.EVENT_ACCESS_PATTERN = 4
        
        # Statistics
        self.stats = {
            'events_processed': 0,
            'leaks_detected': 0,
            'total_allocations': 0,
            'total_frees': 0,
            'peak_memory': 0,
            'current_memory': 0
        }
        
        # Active allocations tracking
        self.active_allocations: Dict[int, AllocationInfo] = {}
        self.leak_history: List[LeakInfo] = []
        
        # Pattern analysis
        self.allocation_patterns = defaultdict(list)
        self.site_stats = defaultdict(lambda: {'count': 0, 'total_size': 0, 'leaks': 0})
        
        # Thresholds
        self.staleness_threshold_seconds = 30.0
        self.large_allocation_threshold = 1024 * 1024  # 1MB
        
        # Struct formats for binary data  
        self.buffer_header_struct = struct.Struct('<iiQQQI')  # buffer metadata (36 bytes)
        
        # For LeakEvent: need to match C++ exactly
        # C++ struct has: event_id(4), event_type(4), timestamp(8), thread_id(4), data(32), is_valid(4) = 56 bytes + padding
        self.event_struct = struct.Struct('<iIqI32sI')  # Total should be 56 bytes
        
    def connect_to_shared_memory(self, retries=10, delay=0.5):
        """Connect to advanced agent's shared memory"""
        for attempt in range(retries):
            try:
                self.shm_fd = os.open("/dev/shm/ml_advanced_leak_detection", os.O_RDWR)
                self.shm = mmap.mmap(self.shm_fd, 0)
                print("✅ Connected to advanced leak detection shared memory")
                return True
            except FileNotFoundError:
                if attempt < retries - 1:
                    print(f"⏳ Waiting for advanced agent... (attempt {attempt + 1}/{retries})")
                    time.sleep(delay)
                    continue
                else:
                    print("❌ Failed to connect to shared memory after all retries")
                    return False
            except Exception as e:
                print(f"❌ Error connecting to shared memory: {e}")
                return False
        
        return False
    
    def read_buffer_header(self) -> Tuple[int, int, int, int, int, int]:
        """Read shared buffer metadata"""
        if not self.shm:
            return 0, 0, 0, 0, 0, 0
        
        self.shm.seek(0)
        header_data = self.shm.read(self.buffer_header_struct.size)
        
        if len(header_data) != self.buffer_header_struct.size:
            return 0, 0, 0, 0, 0, 0
        
        write_index, read_index, total_allocs, total_frees, current_mem, leak_count = \
            self.buffer_header_struct.unpack(header_data)
        
        return write_index, read_index, total_allocs, total_frees, current_mem, leak_count
    
    def read_leak_event(self, slot_index: int) -> Optional[LeakEvent]:
        """Read a single leak event from shared memory"""
        if not self.shm:
            return None
        
        # Calculate offset for this event slot
        header_size = self.buffer_header_struct.size  # 36 bytes
        event_size = self.event_struct.size  # Should be 56 bytes
        offset = header_size + (slot_index * event_size)
        
        try:
            self.shm.seek(offset)
            event_data = self.shm.read(event_size)
            
            if len(event_data) != event_size:
                return None
            
            # Unpack the full event (64 bytes)
            event_id, event_type, timestamp, thread_id, data_bytes, is_valid = \
                self.event_struct.unpack(event_data)
            
            if not is_valid:
                return None
            
            # Unpack event data based on type
            if event_type == self.EVENT_MALLOC or event_type == self.EVENT_FREE:
                address, size, alloc_time, site_id = struct.unpack('<QqQI', data_bytes[:24])
                data = {
                    'address': address,
                    'size': size,
                    'alloc_time': alloc_time,
                    'site_id': site_id
                }
            elif event_type == self.EVENT_LEAK_DETECTED:
                address, size, staleness_ns, site_id = struct.unpack('<QqQI', data_bytes[:24])
                data = {
                    'address': address,
                    'size': size,
                    'staleness_ns': staleness_ns,
                    'site_id': site_id
                }
            else:
                data = {}
            
            return LeakEvent(
                event_id=event_id,
                event_type=event_type,
                timestamp=timestamp,
                thread_id=thread_id,
                data=data,
                is_valid=is_valid
            )
            
        except Exception as e:
            print(f"Error reading event at slot {slot_index}: {e}")
            return None
    
    def process_malloc_event(self, event: LeakEvent):
        """Process malloc event"""
        data = event.data
        allocation = AllocationInfo(
            address=data['address'],
            size=data['size'],
            alloc_time=data['alloc_time'],
            site_id=data['site_id'],
            thread_id=event.thread_id
        )
        
        self.active_allocations[data['address']] = allocation
        self.stats['total_allocations'] += 1
        self.stats['current_memory'] += data['size']
        
        # Update peak memory
        if self.stats['current_memory'] > self.stats['peak_memory']:
            self.stats['peak_memory'] = self.stats['current_memory']
        
        # Track allocation patterns by site
        site_id = data['site_id']
        self.site_stats[site_id]['count'] += 1
        self.site_stats[site_id]['total_size'] += data['size']
        
        # Alert for large allocations
        if data['size'] > self.large_allocation_threshold:
            print(f"🚨 LARGE ALLOCATION: {data['size']} bytes at site {site_id:04x}")
    
    def process_free_event(self, event: LeakEvent):
        """Process free event"""
        data = event.data
        address = data['address']
        
        if address in self.active_allocations:
            alloc_info = self.active_allocations[address]
            self.stats['current_memory'] -= alloc_info.size
            del self.active_allocations[address]
        
        self.stats['total_frees'] += 1
    
    def process_leak_event(self, event: LeakEvent):
        """Process leak detection event"""
        data = event.data
        leak = LeakInfo(
            address=data['address'],
            size=data['size'],
            staleness_ns=data['staleness_ns'],
            site_id=data['site_id']
        )
        
        self.leak_history.append(leak)
        self.stats['leaks_detected'] += 1
        
        # Update site leak statistics
        self.site_stats[data['site_id']]['leaks'] += 1
        
        # Generate detailed alert
        staleness_seconds = data['staleness_ns'] / 1e9
        size_mb = data['size'] / (1024 * 1024)
        
        print(f"🔥 MEMORY LEAK DETECTED:")
        print(f"   Address: 0x{data['address']:x}")
        print(f"   Size: {data['size']} bytes ({size_mb:.2f} MB)")
        print(f"   Stale for: {staleness_seconds:.2f} seconds")
        print(f"   Call site: 0x{data['site_id']:04x}")
        print(f"   Leak #{self.stats['leaks_detected']}")
        print()
    
    def analyze_allocation_patterns(self):
        """Analyze allocation patterns and detect suspicious behavior"""
        if len(self.active_allocations) == 0:
            return
        
        # Find top call sites by allocation count
        top_sites = sorted(self.site_stats.items(), 
                          key=lambda x: x[1]['count'], reverse=True)[:5]
        
        print(f"📊 TOP ALLOCATION SITES:")
        for site_id, stats in top_sites:
            leak_ratio = stats['leaks'] / stats['count'] if stats['count'] > 0 else 0
            avg_size = stats['total_size'] / stats['count'] if stats['count'] > 0 else 0
            
            print(f"   Site 0x{site_id:04x}: {stats['count']} allocs, "
                  f"avg {avg_size:.0f}B, {stats['leaks']} leaks ({leak_ratio:.1%})")
        print()
    
    def generate_summary_report(self):
        """Generate comprehensive summary report"""
        current_leaks = len(self.active_allocations)
        memory_mb = self.stats['current_memory'] / (1024 * 1024)
        peak_mb = self.stats['peak_memory'] / (1024 * 1024)
        
        print(f"📋 ADVANCED LEAK DETECTION SUMMARY:")
        print(f"   📊 Events processed: {self.stats['events_processed']}")
        print(f"   🔢 Total allocations: {self.stats['total_allocations']}")
        print(f"   🔢 Total frees: {self.stats['total_frees']}")
        print(f"   💾 Current memory: {memory_mb:.2f} MB")
        print(f"   📈 Peak memory: {peak_mb:.2f} MB")
        print(f"   🔥 Leaks detected: {self.stats['leaks_detected']}")
        print(f"   ⚠️  Active allocations: {current_leaks}")
        print()
    
    def monitor_real_time(self):
        """Main monitoring loop"""
        last_read_index = 0
        last_stats_time = time.time()
        
        print("🚀 Advanced leak detection monitoring started...")
        print(f"📡 Staleness threshold: {self.staleness_threshold_seconds} seconds")
        print(f"📡 Large allocation threshold: {self.large_allocation_threshold} bytes")
        print()
        
        while self.running:
            try:
                # Read buffer metadata
                write_index, read_index, total_allocs, total_frees, current_mem, leak_count = \
                    self.read_buffer_header()
                
                # Process new events
                while last_read_index != write_index:
                    slot_index = last_read_index % 1000  # LEAK_BUFFER_SIZE
                    event = self.read_leak_event(slot_index)
                    
                    if event:
                        self.stats['events_processed'] += 1
                        
                        if event.event_type == self.EVENT_MALLOC:
                            self.process_malloc_event(event)
                        elif event.event_type == self.EVENT_FREE:
                            self.process_free_event(event)
                        elif event.event_type == self.EVENT_LEAK_DETECTED:
                            self.process_leak_event(event)
                    
                    last_read_index += 1
                
                # Periodic analysis and reporting
                current_time = time.time()
                if current_time - last_stats_time > 10.0:  # Every 10 seconds
                    self.analyze_allocation_patterns()
                    self.generate_summary_report()
                    last_stats_time = current_time
                
                time.sleep(0.1)  # 100ms polling interval
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Error in monitoring loop: {e}")
                time.sleep(1)
    
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
    print("🧠 ADVANCED MEMORY LEAK ANALYZER")
    print("================================")
    print()
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    analyzer = AdvancedLeakAnalyzer()
    
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
        print("🏁 Advanced analyzer shutdown complete")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
