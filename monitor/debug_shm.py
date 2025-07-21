#!/usr/bin/env python3
"""
Debug script to inspect shared memory content
"""

import struct
import mmap
import os

def inspect_shared_memory():
    try:
        shm_fd = os.open("/dev/shm/ml_advanced_leak_detection", os.O_RDONLY)
        shm = mmap.mmap(shm_fd, 0, access=mmap.ACCESS_READ)
        
        print("🔍 SHARED MEMORY INSPECTION")
        print("=" * 40)
        print(f"Total size: {len(shm)} bytes")
        print()
        
        # Read buffer header (6 values: write_index, read_index, total_allocs, total_frees, current_mem, leak_count)
        header_format = struct.Struct('<iiQQQI')
        header_data = shm.read(header_format.size)
        
        write_index, read_index, total_allocs, total_frees, current_mem, leak_count = \
            header_format.unpack(header_data)
        
        print(f"📊 BUFFER HEADER:")
        print(f"   Write index: {write_index}")
        print(f"   Read index: {read_index}")
        print(f"   Total allocations: {total_allocs}")
        print(f"   Total frees: {total_frees}")
        print(f"   Current memory: {current_mem}")
        print(f"   Leak count: {leak_count}")
        print()
        
        # Try to read a few events
        event_size = 64  # C++ struct with padding
        header_size = header_format.size
        
        print(f"🎯 EVENT INSPECTION:")
        print(f"   Header size: {header_size} bytes")
        print(f"   Event size: {event_size} bytes each")
        print(f"   Events start at offset: {header_size}")
        print()
        
        # Read first few event slots (only if we have some)
        max_events = min(10, write_index)
        if max_events > 0:
            print(f"   Reading first {max_events} events:")
            for i in range(max_events):
                offset = header_size + (i * event_size)
                shm.seek(offset)
                event_data = shm.read(event_size)
                
                if len(event_data) == event_size:
                    # Try to unpack: event_id(4), event_type(4), timestamp(8), thread_id(4)
                    try:
                        event_id, event_type, timestamp, thread_id = struct.unpack('<iIqI', event_data[:20])
                        is_valid = struct.unpack('<i', event_data[60:64])[0]  # Last 4 bytes
                        print(f"   Event {i}: ID={event_id}, Type={event_type}, ThreadID={thread_id}, Valid={is_valid}")
                    except Exception as e:
                        print(f"   Event {i}: Parse error: {e}")
                        print(f"             Raw: {event_data[:20].hex()}")
                else:
                    print(f"   Event {i}: Short read ({len(event_data)} bytes)")
        else:
            print("   No events to read yet")
        
        print()
        print(f"🔧 RAW HEADER BYTES:")
        shm.seek(0)
        header_bytes = shm.read(32)  # First 32 bytes
        print(f"   {header_bytes.hex()}")
        
        shm.close()
        os.close(shm_fd)
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    inspect_shared_memory()
