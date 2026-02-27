# Roadmap

## Completed ✅

### Audio API (issues #1-#10)
- [x] PCM transcoder layer
- [x] RX high-level API (`start_audio_rx_pcm`)
- [x] TX high-level API (`start_audio_tx_pcm`, `push_audio_tx_pcm`)
- [x] CLI audio subcommands (`rx`, `tx`, `loopback`)
- [x] E2E tests for PCM API and CLI
- [x] Runtime audio stats (`get_audio_stats`)
- [x] Auto-recover audio streams after reconnect (#7)
- [x] Capability negotiation UX + `icom-lan audio caps`
- [x] Task-oriented docs/recipes
- [x] API naming consistency + deprecation plan

### Hamlib NET rigctld (issues #16-#22, #27, #32)
- [x] TCP server skeleton (`asyncio.start_server`)
- [x] MVP command set (f/F/m/M/t/T/v/V/s/S/l/q + long-form)
- [x] Read-only safety mode (`--read-only`, RPRT -22)
- [x] Structured logging + guardrails (max clients, idle timeout, OOM guard)
- [x] Golden protocol response suite (45 fixtures)
- [x] TCP wire integration tests
- [x] WSJT-X/rigctl setup docs
- [x] `--wsjtx-compat` DATA mode pre-warm
- [x] DATA mode semantics fix (PKT*, RTTY/PKTRTTY)
- [x] CI-V desync fix + state cache + circuit breaker (#27)

## Next: v0.7.0 Release

### Release checklist
- [ ] Verify `ruff check` clean
- [ ] Verify `mkdocs build` clean
- [ ] Move CHANGELOG [Unreleased] → [0.7.0]
- [ ] Version bump: 0.6.6 → 0.7.0
- [ ] GitHub release + PyPI publish
- [ ] Community announcement (Reddit, QRZ)

## Future

### Client compatibility hardening
- [ ] Полный тест с WSJT-X (Hamlib NET rigctl, localhost:4532)
- [ ] Тест с JS8Call, fldigi
- [ ] Extended response protocol (per-session `extended_mode`)

### Features
- [ ] Web UI MVP (freq/mode/meter/scope snapshot)
- [ ] Async event/notification stream (S-meter polling, band changes)
- [ ] Mock Radio Server — UDP-эмулятор для CI интеграции
- [ ] Support for IC-705, IC-7300 (different CI-V, feature sets)

### Protocol completeness (rigctld)
- [ ] `\set_level` (RFPOWER)
- [ ] RIT/XIT (`J`/`Z`)
- [ ] Tuner control
- [ ] `\dump_state` protocol v1

### Long-term
- [ ] Universal Radio Bridge (RPi) — USB radios → LAN control
- [ ] Rust core prototype (performance spike)

---

*Updated: 2026-02-26*
