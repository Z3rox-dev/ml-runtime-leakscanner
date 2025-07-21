#!/usr/bin/env python3
import os
import mmap
import struct
import time

def test_shared_memory():
    try:
        print("🔍 Testing shared memory connection...")
        
        # Try to open shared memory
        shm_fd = os.open("/dev/shm/ml_advanced_leak_detection", os.O_RDONLY)
        shm = mmap.mmap(shm_fd, 0, access=mmap.ACCESS_READ)
        
        print(f"✅ Connected! Size: {len(shm)} bytes")
        
        # Read header
        header_struct = struct.Struct('<iiQQQI')
        header_data = shm.read(header_struct.size)
        
        write_index, read_index, total_allocs, total_frees, current_mem, leak_count = \
            header_struct.unpack(header_data)
        
        print(f"📊 CURRENT STATS:")
        print(f"   Write index: {write_index}")
        print(f"   Total allocations: {total_allocs}")
        print(f"   Total frees: {total_frees}")
        print(f"   Active allocations: {total_allocs - total_frees}")
        print(f"   Current memory: {current_mem} bytes ({current_mem/1024:.1f} KB)")
        print(f"   Leak count: {leak_count}")
        
        shm.close()
        os.close(shm_fd)
        
        return True
        
    except FileNotFoundError:
        print("❌ Shared memory not found. Make sure advanced agent is running.")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_shared_memory()
