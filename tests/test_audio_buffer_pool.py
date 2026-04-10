"""Tests for audio buffer pool — verify buffer reuse and pool mechanics."""

from __future__ import annotations

import threading
import time

from icom_lan._audio_buffer_pool import AudioBufferPool, ContextManagedBuffer


class TestAudioBufferPool:
    """Test buffer pool acquire/release mechanics."""

    def test_pool_initialization(self):
        """Pool should pre-allocate specified number of buffers."""
        pool = AudioBufferPool(buffer_size=1024, max_buffers=5)
        stats = pool.stats()

        assert stats["available"] == 5
        assert stats["in_use"] == 0
        assert stats["total_allocated"] == 5

    def test_acquire_buffer(self):
        """Acquiring a buffer should mark it as in-use."""
        pool = AudioBufferPool(buffer_size=512, max_buffers=3)
        buf = pool.acquire()

        assert isinstance(buf, bytearray)
        assert len(buf) == 512

        stats = pool.stats()
        assert stats["available"] == 2
        assert stats["in_use"] == 1

    def test_release_buffer(self):
        """Releasing a buffer should return it to available pool."""
        pool = AudioBufferPool(buffer_size=512, max_buffers=3)
        buf = pool.acquire()

        pool.release(buf)

        stats = pool.stats()
        assert stats["available"] == 3
        assert stats["in_use"] == 0

    def test_buffer_reuse(self):
        """Multiple acquire/release cycles should reuse buffers."""
        pool = AudioBufferPool(buffer_size=256, max_buffers=2)

        # Acquire first buffer
        buf1 = pool.acquire()
        buf1_id = id(buf1)

        # Release it
        pool.release(buf1)

        # Acquire again - should get the same buffer object
        buf2 = pool.acquire()
        buf2_id = id(buf2)

        assert buf1_id == buf2_id, "Buffers should be reused"

    def test_multiple_buffers(self):
        """Pool should handle multiple concurrent buffers."""
        pool = AudioBufferPool(buffer_size=1024, max_buffers=5)

        # Acquire multiple buffers
        buffers = [pool.acquire() for _ in range(5)]

        stats = pool.stats()
        assert stats["in_use"] == 5
        assert stats["available"] == 0

        # Release all
        for buf in buffers:
            pool.release(buf)

        stats = pool.stats()
        assert stats["in_use"] == 0
        assert stats["available"] == 5

    def test_buffer_ids_unique(self):
        """All pre-allocated buffers should be unique objects."""
        pool = AudioBufferPool(buffer_size=512, max_buffers=5)

        buffers = [pool.acquire() for _ in range(5)]
        buffer_ids = set(id(buf) for buf in buffers)

        assert len(buffer_ids) == 5, "All buffers should be unique objects"

        # Release all
        for buf in buffers:
            pool.release(buf)

    def test_exhaust_pool(self):
        """Exhausting the pool should allocate temporary buffers."""
        pool = AudioBufferPool(buffer_size=256, max_buffers=2)

        # Acquire all pre-allocated buffers
        _buf1 = pool.acquire()
        _buf2 = pool.acquire()

        # Next acquire should allocate temporary buffer
        buf3 = pool.acquire()

        assert isinstance(buf3, bytearray)

        # Releasing temporary buffer doesn't grow the pool
        pool.release(buf3)
        stats = pool.stats()
        assert stats["total_allocated"] == 2  # Still only 2 pre-allocated

    def test_concurrent_acquire_release(self):
        """Pool should be thread-safe under concurrent access."""
        pool = AudioBufferPool(buffer_size=512, max_buffers=10)
        acquired_buffers = []
        lock = threading.Lock()

        def acquire_release_cycle():
            for _ in range(100):
                buf = pool.acquire()
                with lock:
                    acquired_buffers.append(id(buf))
                time.sleep(0.001)  # Small delay to increase contention
                pool.release(buf)

        threads = [threading.Thread(target=acquire_release_cycle) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All cycles completed without deadlock
        assert len(acquired_buffers) == 300

    def test_buffer_size_variations(self):
        """Pool should support various buffer sizes."""
        sizes = [512, 1024, 2048, 4096]

        for size in sizes:
            pool = AudioBufferPool(buffer_size=size, max_buffers=2)
            buf = pool.acquire()
            assert len(buf) == size
            pool.release(buf)

    def test_stats_accuracy(self):
        """Stats should accurately reflect pool state."""
        pool = AudioBufferPool(buffer_size=256, max_buffers=5)

        # Initial state
        assert pool.stats()["available"] == 5
        assert pool.stats()["in_use"] == 0

        # After acquiring 3
        bufs = [pool.acquire() for _ in range(3)]
        assert pool.stats()["available"] == 2
        assert pool.stats()["in_use"] == 3

        # After releasing 1
        pool.release(bufs[0])
        assert pool.stats()["available"] == 3
        assert pool.stats()["in_use"] == 2

        # After releasing all
        for buf in bufs[1:]:
            pool.release(buf)
        assert pool.stats()["available"] == 5
        assert pool.stats()["in_use"] == 0

    def test_context_manager_acquisition(self):
        """Context manager should automatically release buffer."""
        pool = AudioBufferPool(buffer_size=512, max_buffers=3)

        with ContextManagedBuffer(pool) as buf:
            assert isinstance(buf, bytearray)
            stats = pool.stats()
            assert stats["in_use"] == 1

        # After context exit, buffer should be released
        stats = pool.stats()
        assert stats["in_use"] == 0
        assert stats["available"] == 3

    def test_buffer_clear_on_release(self):
        """Buffers should be cleared before reuse."""
        pool = AudioBufferPool(buffer_size=16, max_buffers=2)

        # Write data to buffer
        buf1 = pool.acquire()
        buf1[:] = b'\xFF' * 16

        # Release it
        pool.release(buf1)

        # Acquire again - should be cleared
        buf2 = pool.acquire()

        # First few bytes should be zeros (cleared)
        assert buf2[0:8] == b'\x00' * 8


class TestAudioBufferPoolPerformance:
    """Profile buffer pool performance."""

    def test_buffer_acquisition_throughput(self):
        """Measure buffer acquisition throughput."""
        pool = AudioBufferPool(buffer_size=1024, max_buffers=100)

        start = time.perf_counter()
        for _ in range(10000):
            buf = pool.acquire()
            pool.release(buf)
        elapsed_ms = (time.perf_counter() - start) * 1000

        ops_per_sec = 10000 / (elapsed_ms / 1000)
        print(f"  Buffer acquire/release throughput: {ops_per_sec:.0f} ops/sec")

        # Should be very fast (>50k ops/sec)
        assert ops_per_sec > 50_000

    def test_concurrent_throughput(self):
        """Measure throughput under concurrent access."""
        pool = AudioBufferPool(buffer_size=1024, max_buffers=50)
        op_count = [0]
        lock = threading.Lock()

        def worker():
            local_count = 0
            for _ in range(1000):
                buf = pool.acquire()
                local_count += 1
                pool.release(buf)
            with lock:
                op_count[0] += local_count

        threads = [threading.Thread(target=worker) for _ in range(5)]
        start = time.perf_counter()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        elapsed_ms = (time.perf_counter() - start) * 1000

        ops_per_sec = op_count[0] / (elapsed_ms / 1000)
        print(f"  Concurrent buffer throughput: {ops_per_sec:.0f} ops/sec")

        # Should maintain good throughput under concurrent access
        assert ops_per_sec > 30_000


class TestAudioFrameSizes:
    """Test buffer pool with realistic audio frame sizes."""

    def test_common_audio_frame_sizes(self):
        """Test buffer pool with common audio frame configurations."""
        configs = [
            # (sample_rate, channels, frame_ms, description)
            (16000, 1, 20, "16kHz mono 20ms"),
            (16000, 2, 20, "16kHz stereo 20ms"),
            (48000, 1, 20, "48kHz mono 20ms"),
            (48000, 2, 20, "48kHz stereo 20ms"),
        ]

        for sr, ch, frame_ms, desc in configs:
            # Calculate buffer size (PCM16 = 2 bytes per sample)
            samples_per_frame = (sr * frame_ms) // 1000
            buffer_size = samples_per_frame * ch * 2

            pool = AudioBufferPool(buffer_size=buffer_size, max_buffers=10)
            buf = pool.acquire()

            assert len(buf) == buffer_size, f"Size mismatch for {desc}"

            pool.release(buf)
            stats = pool.stats()
            assert stats["available"] == 10
