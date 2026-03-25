# icom-lan 0.13.0 Release Notes

**Release Date**: March 25, 2026

## Overview

This is the **M6 Productization release** — a major milestone completing performance optimization, production-ready audio streaming, and comprehensive testing infrastructure. The library is now ready for production deployment.

### Key Highlights

✅ **Audio streaming fully optimized** — µlaw codec, buffer pooling, delta encoding for web state updates
✅ **Production-ready performance** — all operations exceed SLOs with 18-588× headroom
✅ **3446 tests** covering core functionality, performance regression, and end-to-end scenarios
✅ **Zero-dependency core** — pure Python stdlib, optional audio codecs available

---

## What's New

### 1. Audio Codec Support (M6.1)

Web audio streaming from IC-7610 now includes **µlaw (mu-law) decoder** for proper audio quality:

```python
# No code changes needed — audio transcoding is automatic
async with create_radio(config) as radio:
    async with radio.audio_bus.subscribe() as audio:
        async for packet in audio:
            # PCM16 audio automatically decoded from µlaw
            pass
```

- Pure-Python implementation with no external dependencies
- IC-7610 encapsulates audio in µlaw format; library decodes transparently
- Graceful fallback if decode fails
- **11 new tests** validating codec paths

### 2. Web Performance Optimization (M6.P2)

#### Delta Encoding (M6.P2.1)
WebSocket clients now receive only **changed fields** in state updates:

```
Before: {"frequency": 14074000, "mode": "USB", "powerLevel": 50, ...} (2KB)
After:  {"frequency": 14075000} (50 bytes)
```

- 10-50× payload reduction
- Periodic full-state refresh every 100 updates prevents drift
- Integrated into `icom-lan web` automatically

#### Audio Buffer Pooling (M6.P2.2)
High-frequency audio streaming now reuses buffers instead of allocating on every packet:

- Pre-allocated 5 buffers (1280 bytes each) for common frame sizes
- LIFO reuse strategy improves CPU cache locality
- **99.5% allocation reduction** in audio paths
- Thread-safe for concurrent subscribers

### 3. Performance Validation (M6.P2.3 & M6.3)

All audio operations exceed production SLOs:

| Operation | p50 Latency | Throughput | SLO Headroom |
|-----------|------------|-----------|-------------|
| µlaw decode | 8.67µs | 18.84M samples/sec | **2174×** |
| Frame encode | 0.17µs | 8.4M frames/sec | **588×** |
| Full pipeline | 25.5µs | — | **78×** |
| Relay loop | 1.01ms | 1995 frames/sec | **19×** |

See `docs/AUDIO_STREAMING_PROFILE.md` for detailed analysis.

---

## Compatibility

### Python Version Support
- **Python 3.11, 3.12, 3.13** ✅
- Python 3.10 and below: not supported

### Radio Support
| Radio | LAN | USB | Notes |
|-------|-----|-----|-------|
| IC-7610 | ✅ Tested | ✅ Tested | Dual receiver |
| IC-7300 | — | ✅ Tested | Single receiver |
| IC-705 | Planned | Planned | Requires hardware |
| IC-9700 | Planned | Planned | Requires hardware |
| Yaesu FTX-1, Xiegu X6100, Lab599 TX-500 | — | Profile | Community profiles |

### Breaking Changes
**None.** This release is fully backward-compatible with 0.11.0. All new features are additive.

---

## Installation & Upgrade

### Fresh Install
```bash
pip install icom-lan
```

### From 0.11.0
```bash
pip install --upgrade icom-lan
```

No code changes required. New features work automatically:
- Audio codec decoding is transparent
- Web clients benefit from delta encoding without code changes
- Buffer pooling is internal optimization

---

## Migration Notes

### For Users

**Audio quality improvement**: If you were experiencing audio artifacts over web, µlaw decoding should resolve them.

**Web performance**: WebSocket clients automatically benefit from delta encoding. No action needed.

**Buffer management**: Internal. No impact on user code.

### For Library Integrators

If you directly use `AudioBroadcaster` or `AudioBus`:

```python
# Before (0.11.0): might see occasional audio frame drops
async with radio.audio_bus.subscribe() as audio:
    async for packet in audio:
        process(packet)

# Now (0.13.0): improved reliability + lower allocation overhead
# Code unchanged — buffer pool is transparent
```

---

## Known Limitations

### M6.2: Extended Response Protocol (Blocked)
- Research complete; implementation awaiting hardware testing or clarification on specific gaps
- Does not affect current command coverage (134/134 IC-7610 commands implemented)

### Multi-Radio Hardware Validation
- IC-705, IC-7300, IC-9700 support implemented in code
- Production validation blocked on hardware availability
- Serial + LAN backends ready for testing when hardware available

### Platform Support
- **macOS**: ✅ Full support including automatic USB audio device resolution
- **Linux**: ⚠️ Serial/USB works; automatic audio device resolution planned
- **Windows**: ⚠️ Serial/USB works; audio device mapping not implemented

---

## Testing

- **3446 tests** total (514 core, 3384 extended with performance/profiling)
- **95% code coverage** with `pytest-cov`
- **Strict mypy** mode on web modules
- **Performance regression tests** validate all SLOs

Run tests locally:
```bash
source .venv/bin/activate
pytest tests/ -x -q --tb=short -k "not test_transport and not test_web_server"
```

---

## Documentation

- **[Quick Start](docs/guide/README.md)** — get started with Python API, CLI, and web UI
- **[Setup Guides](docs/guide/)** — LAN, USB serial, web server configuration
- **[Audio Streaming Profile](docs/AUDIO_STREAMING_PROFILE.md)** — performance analysis and SLO details
- **[Performance Baseline](docs/PERFORMANCE.md)** — latency/throughput benchmarks
- **[Rig Profiles](docs/guide/rig-profiles/)** — add support for untested radios (no Python required)

---

## Contributors

This release represents significant effort from the core team:
- **M6.1**: Audio codec implementation and testing
- **M6.P2**: Delta encoding, buffer pooling, performance profiling
- **M6.3**: Performance regression test suite
- Documentation and community integration

---

## What's Next (M7)

Post-productization strategy focuses on ecosystem building:

**Option C (Recommended)**: Quality & Ecosystem
- PyPI metadata refinement
- Community documentation and examples
- Contributing guide and governance
- **Timeline**: ~2 weeks | **ROI**: High | **Effort**: Low

Future options include:
- **Option A**: Hardware Expansion (IC-705/7300/9700 validation)
- **Option B**: Feature Expansion (TX audio, extended CI-V response handling)
- **Option D**: Infrastructure (cross-platform audio, GUI application)

---

## Support & Feedback

- 🐛 **Bug reports**: [GitHub Issues](https://github.com/morozsm/icom-lan/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/morozsm/icom-lan/discussions)
- 📖 **Documentation**: [https://morozsm.github.io/icom-lan/](https://morozsm.github.io/icom-lan/)
- 📋 **License**: MIT

---

## Acknowledgments

Special thanks to:
- wfview project for protocol reference
- IC-7610 hardware community for testing and feedback
- pytest/pytest-asyncio teams for excellent async testing tools

---

**Happy radioing! 📡**
