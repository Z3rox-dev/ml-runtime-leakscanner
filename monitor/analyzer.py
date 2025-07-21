#!/usr/bin/env python3
# simple_ml.py - Ultra simple ML per proof-of-concept

import json
import mmap
import struct
import time
import os
import sys

class SharedMemoryAnalyzer:
    def __init__(self):
        self.buffer_size = 1000
        # C++ struct: int32_t, uint64_t, uint64_t, int64_t, int32_t
        # Python format: < = little endian, no alignment (packed)
        # i (4), Q (8), Q (8), q (8), i (4) = 32 bytes total
        self.allocation_struct = struct.Struct('<iQQqi')
        self.header_struct = struct.Struct('<ii')         # write_index, read_index
        self.last_read_index = 0
        self.shm = None

    def connect_shared_memory(self, retries=10, delay=0.5):
        # Apre la shared memory creata dall'agent
        for i in range(retries):
            try:
                # The path in /dev/shm is correct for shm_open
                shm_fd = os.open("/dev/shm/ml_runtime_shm", os.O_RDWR)
                self.shm = mmap.mmap(shm_fd, 0)
                print("Connected to shared memory")
                sys.stdout.flush()
                return True
            except FileNotFoundError:
                if i < retries - 1:
                    # print(f"⏳ Shared memory not found, retrying in {delay}s... ({i+1}/{retries})")
                    time.sleep(delay)
                continue
            except Exception as e:
                print(f"Failed to connect to shared memory: {e}", file=sys.stderr)
                return False
        
        print(f"Failed to connect to shared memory after {retries} retries.", file=sys.stderr)
        return False

    def read_new_allocations(self):
        # Legge header (write_index, read_index)
        self.shm.seek(0)
        header_data = self.shm.read(self.header_struct.size)
        write_index, _ = self.header_struct.unpack(header_data)

        new_allocations = []

        # Legge solo i dati nuovi
        while self.last_read_index < write_index:
            # The C++ struct has the indexes *after* the buffer. The python code has them before.
            # I will stick to the user-provided python code. It's easier to change the C++ part.
            # I will assume the C++ part is now: { int write_index; int read_index; AllocationData allocations[1000]; }
            offset = self.header_struct.size + (self.last_read_index % self.buffer_size) * self.allocation_struct.size
            self.shm.seek(offset)
            data = self.shm.read(self.allocation_struct.size)

            if len(data) < self.allocation_struct.size:
                break # Avoid reading partial data

            malloc_count, size, total_bytes, timestamp, is_valid = self.allocation_struct.unpack(data)

            if is_valid:
                new_allocations.append({
                    'malloc_count': malloc_count,
                    'size': size,
                    'total': total_bytes,
                    'timestamp': timestamp
                })

            self.last_read_index += 1

        return new_allocations

    def predict_anomaly(self, size, total, malloc_count):
        # Stessa logica di prima
        if size > 30000 and total > 500000:
            return True, 0.9
        elif size > 20000 and total > 200000:
            return True, 0.7
        elif size > 15000 and total > 100000:
            return True, 0.5
        else:
            return False, 0.2

    def monitor_real_time(self):
        print(" Starting real-time monitoring...")
        sys.stdout.flush()

        while True:
            try:
                allocations = self.read_new_allocations()

                for data in allocations:
                    is_anomaly, confidence = self.predict_anomaly(
                        data['size'], data['total'], data['malloc_count']
                    )

                    if is_anomaly:
                        status = "🚨" if confidence > 0.7 else "⚠️"
                        print(f"{status} REAL-TIME ALERT #{data['malloc_count']}: "
                              f"{data['size']}B (total: {data['total']}B) "
                              f"-> ANOMALY (conf: {confidence:.1f})")
                        sys.stdout.flush()

                time.sleep(0.1)  # Check ogni 100ms
            except KeyboardInterrupt:
                print("\n Monitor stopped.")
                break
            except Exception as e:
                print(f"\nAn error occurred during monitoring: {e}", file=sys.stderr)
                break
        if self.shm:
            self.shm.close()


if __name__ == "__main__":
    analyzer = SharedMemoryAnalyzer()
    # Give the agent a moment to create the shared memory file
    # time.sleep(1) # Removed this, the connect method will now retry
    if analyzer.connect_shared_memory():
        analyzer.monitor_real_time()
    else:
        print("Cannot start - shared memory not available", file=sys.stderr)
        sys.exit(1)