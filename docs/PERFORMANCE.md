# Performance Analysis & Optimization (M6.3)

## Baseline Metrics (2026-03-23)

### Test Suite Performance
- **Unit tests (test_commands, test_civ, test_radio)**: 514 tests in 1.88s (3.6ms per test)
- **Full test suite**: 3384 tests in ~79s (23ms per test)
- **Slowest tests**:
  - `test_multiple_timeouts_followed_by_success`: 0.21s (timeout simulation)
  - `test_deadline_timeout_does_not_always_send_three_attempts`: 0.20s (timeout simulation)
  - `test_timeout_does_not_affect_subsequent_command`: 0.10s (timeout simulation)

### Key Observations
1. **Unit tests are fast** — 514 tests in <2s, 3.6ms median
2. **Slow tests are mostly timeout/stress simulations** — intentionally slow for testing robustness
3. **No obvious performance bottlenecks** in regular command path
4. **Test collection overhead** is minimal

## Potential Optimization Areas

### 1. CI-V Command Parsing
- **Current**: Sequential parsing of CI-V responses in `commands.py`
- **Opportunity**: Lazy evaluation of rarely-used fields
- **Impact**: Small (most operations are fast enough)
- **Effort**: Medium (refactoring required)

### 2. RadioPoller Efficiency
- **Current**: TOML-based command map lookup per poll cycle
- **Opportunity**: Cache compiled command sequence after first poll
- **Impact**: Medium (reduces TOML parsing overhead)
- **Effort**: Low (simple caching)

### 3. Audio Buffer Management
- **Current**: Dynamic allocation in audio streams
- **Opportunity**: Pre-allocate buffers for common sizes (16kHz, 20ms frames)
- **Impact**: Small (buffer allocation not a bottleneck)
- **Effort**: Low (simple pool implementation)

### 4. Web State Synchronization
- **Current**: Full state object serialization per update
- **Opportunity**: Delta encoding for incremental state updates
- **Impact**: Medium (reduces network payload)
- **Effort**: Medium (requires protocol change)

### 5. Test Parallelization
- **Current**: Sequential test execution
- **Opportunity**: Use pytest-xdist for parallel test runs
- **Impact**: High (3-4x speedup on multi-core)
- **Effort**: Low (pytest plugin)

## Completed Optimizations (M4-M5)

- ✅ Data-driven poller (TOML CommandMap) — reduced hardcoded command lists
- ✅ Plain CI-V fallback — eliminated receiver selector overhead for single-receiver radios
- ✅ Optimistic state updates — UI feedback without waiting for CI-V ACK
- ✅ Command deduplication in commander queue — reduced redundant transmissions

## Recommendations

### Priority 1 (High ROI, Low Effort)
- [ ] Cache compiled poller command sequences (reduces TOML parsing per cycle)
- [ ] Add performance regression tests
- [ ] Profile CI-V command pipeline latency

### Priority 2 (Medium ROI, Medium Effort)
- [ ] Implement delta encoding for web state updates
- [ ] Add audio buffer pooling
- [ ] Profile web audio streaming performance

### Priority 3 (Low ROI, High Effort)
- [ ] Refactor CI-V parsing for lazy evaluation
- [ ] Optimize command matrix lookups

### Not Viable
- ❌ pytest-xdist for parallel testing — incompatible with asyncio test mode
  - All radio tests use asyncio; xdist requires isolation that breaks shared fixtures
  - Test suite already fast (79s total); further optimization has diminishing returns

## Testing Performance

### Next Steps
1. Cache compiled poller command sequences (quick win)
2. Add latency regression tests for key operations
3. Profile real-time operations (audio streaming, scope updates)
4. Establish latency SLOs for user-facing operations (get_frequency, set_mode, etc.)

---

**Generated**: 2026-03-23
**Status**: Analysis complete, optimization roadmap established
**Next**: Implement Priority 1 items (pytest-xdist, poller caching)
