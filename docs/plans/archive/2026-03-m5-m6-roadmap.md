# M5/M6 Roadmap — Multi-Radio Expansion & Productization

**Status:** Draft for CEO review
**Created:** 2026-03-22
**Context:** Post-M4 (IC-7610 parity complete), planning next phases

---

## Executive Summary

With M3 (IC-7610 USB backend) complete and M4 (IC-7610 command parity) at 100%, `icom-lan` has achieved **complete IC-7610 coverage** across LAN and serial backends. The library is production-ready for IC-7610 users.

**Next strategic phases:**

- **M5 (Multi-Radio Expansion)** — Extend proven architecture to popular Icom models (IC-705, IC-7300, IC-9700)
- **M6 (Productization)** — Polish, performance, deployment patterns, documentation, community growth

**Timeline estimate:** M5 (6-8 weeks) + M6 (4-6 weeks) = ~3 months total, assuming continuation of current development velocity.

**Key dependencies:**
- M5 requires M4 completion (cross-surface exposure of advanced features)
- M6 benefits from M5 multi-radio test matrix but can run in parallel for non-radio-specific work

---

## Phase M5 — Multi-Radio Expansion

### Goals

1. **Extend backend architecture to 3 additional popular models:**
   - IC-705 (portable HF/VHF/UHF transceiver) — most requested community model
   - IC-7300 (HF base station) — entry-level HF, large user base
   - IC-9700 (VHF/UHF/SHF all-mode) — satellite/VHF enthusiast favorite

2. **Unify model-specific capabilities** via `RadioProfile` system (already scaffolded in M2)

3. **Enable runtime auto-detection** for model selection (LAN: from conninfo; serial: from `get_id`)

4. **Maintain backward compatibility** — existing IC-7610 API/CLI/Web code works unchanged

### Success Criteria

- ✅ All 4 models (IC-7610/IC-705/IC-7300/IC-9700) pass core integration suite (connect, CI-V, audio, scope)
- ✅ CLI `--model` flag + auto-detection work for all models
- ✅ Web UI detects model and adapts control visibility (no IC-7300 scope controls, etc.)
- ✅ Profile system documents capabilities per model (docs/radios/)
- ✅ PyPI package works across all 4 models with single `pip install icom-lan`

### Task Breakdown

#### M5.1 — IC-705 Backend (Portable HF/VHF/UHF)

**Why IC-705 first?** Most-requested model in GitHub issues/discussions. Portable use case (field ops, POTA/SOTA) is distinct from IC-7610 base station.

| Task | Effort | Notes |
|------|--------|-------|
| Research IC-705 CI-V command set vs IC-7610 | 2d | Use wfview parity, Icom CI-V docs |
| Create `IC705Profile` with capabilities | 1d | Likely subset of IC-7610 (single receiver, no dual scope) |
| Implement IC-705 LAN backend | 3d | Port differences, smaller conninfo, different model ID |
| Implement IC-705 serial backend | 3d | USB CI-V + audio device handling (same pattern as 7610) |
| Audio capability matrix (LAN Opus support?) | 1d | Verify IC-705 audio codec support |
| Scope/waterfall support (single receiver) | 2d | IC-705 has spectrum scope, verify cmd 0x27 format |
| Integration tests with real IC-705 | 3d | Requires hardware loan or community tester |
| CLI/Web smoke tests | 1d | Verify auto-detect, control visibility |
| **Total** | **16d (~3 weeks)** | |

**Hardware dependency:** Need access to IC-705 (borrow, buy used ~$1000, or remote test with community member).

#### M5.2 — IC-7300 Backend (Entry-Level HF)

**Why IC-7300?** Largest user base for Icom HF (most affordable HF SDR transceiver). No second receiver, no dual scope.

| Task | Effort | Notes |
|------|--------|-------|
| Research IC-7300 CI-V differences | 2d | Older firmware, some commands may differ |
| Create `IC7300Profile` | 1d | Single receiver, standard HF modes |
| Implement IC-7300 LAN backend | 3d | Verify LAN protocol compatibility (should be similar to IC-7610) |
| Implement IC-7300 serial backend | 3d | USB CI-V + audio |
| Scope support (single receiver, center-mode only?) | 2d | IC-7300 has spectrum scope but fewer modes than IC-7610 |
| Audio capability matrix | 1d | Verify codec support |
| Integration tests with real IC-7300 | 3d | Requires hardware access |
| CLI/Web smoke tests | 1d | |
| **Total** | **16d (~3 weeks)** | |

**Hardware dependency:** Need access to IC-7300 (more common, ~$1100 new, ~$800 used).

#### M5.3 — IC-9700 Backend (VHF/UHF/SHF All-Mode)

**Why IC-9700?** Covers VHF/UHF/SHF (satellite ops, VHF contesting). Different band plan, different modes (includes D-STAR).

| Task | Effort | Notes |
|------|--------|-------|
| Research IC-9700 CI-V differences | 2d | Satellite mode, D-STAR, different bands |
| Create `IC9700Profile` | 1d | Dual receiver (like IC-7610), different band edges |
| Implement IC-9700 LAN backend | 3d | Should be similar to IC-7610 protocol-wise |
| Implement IC-9700 serial backend | 3d | USB CI-V + audio |
| Scope support (dual receiver, satellite mode) | 3d | Verify scope behavior on VHF/UHF bands |
| D-STAR mode handling (if applicable) | 2d | May need special mode enum, test with D-STAR enabled |
| Integration tests with real IC-9700 | 3d | Requires hardware access or remote tester |
| CLI/Web smoke tests | 1d | |
| **Total** | **18d (~3.5 weeks)** | |

**Hardware dependency:** Need access to IC-9700 (~$1500 new, ~$1200 used). Community member with satellite station?

#### M5.4 — Unified Model Selection & Auto-Detection

| Task | Effort | Notes |
|------|--------|-------|
| Enhance `RadioProfile` system | 2d | Document model-specific capabilities in profiles |
| CLI `--model` flag + auto-detect logic | 2d | Fallback: auto-detect from radio ID, else use `--model` |
| Web UI model detection + control hiding | 2d | Don't show dual scope controls for IC-7300/IC-705 |
| Backend factory enhancements | 1d | Route to correct backend based on model |
| Profile documentation in docs/radios/ | 2d | Per-model capability matrix |
| **Total** | **9d (~2 weeks)** | |

#### M5.5 — Multi-Model Testing & Regression

| Task | Effort | Notes |
|------|--------|-------|
| Expand integration matrix for 4 models | 3d | Parametrize tests by model |
| Multi-model CI strategy (mock vs real) | 2d | Real tests require hardware, mocks for CI |
| Golden fixture expansion (per model) | 2d | Capture model-specific CI-V responses |
| Regression gate for all models | 2d | Ensure IC-7610 coverage doesn't regress |
| **Total** | **9d (~2 weeks)** | |

### Total M5 Effort

| Milestone | Effort |
|-----------|--------|
| M5.1 IC-705 | 16d (~3 weeks) |
| M5.2 IC-7300 | 16d (~3 weeks) |
| M5.3 IC-9700 | 18d (~3.5 weeks) |
| M5.4 Unified Selection | 9d (~2 weeks) |
| M5.5 Multi-Model Testing | 9d (~2 weeks) |
| **Total** | **68d (~13.5 weeks or 3+ months)** |

**Note:** Sequential hardware access would extend this. Parallel work (e.g., IC-705 integration while IC-7300 profile dev) could reduce calendar time.

### Dependencies & Sequencing

1. **M4 completion** — Finish cross-surface exposure (#138) before M5 starts
2. **Hardware access** — Critical path bottleneck. Options:
   - Buy used radios (~$3000 total for 3 radios)
   - Borrow from community (ham radio clubs, online forums)
   - Remote test access (TeamViewer / remote desktop with volunteer)
3. **Profile system** — Already scaffolded in M2, needs expansion
4. **Backward compat** — IC-7610 tests must remain green throughout M5

### Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| **Hardware access delays** | High | High | Prioritize IC-705 (most requested), use community testers |
| **Protocol differences** | Medium | Medium | IC-705/7300/9700 use same base protocol, differences should be minor |
| **Audio codec variance** | Low | Medium | Some models may not support Opus; fallback to PCM |
| **Scope format changes** | Medium | Low | cmd 0x27 format may vary; study wfview per-model parsing |
| **D-STAR complexity (IC-9700)** | Low | Low | D-STAR is radio-internal, likely no library impact |
| **Regression in IC-7610** | Low | High | Maintain strict regression gate; run full IC-7610 suite on every change |

---

## Phase M6 — Productization

### Goals

1. **Performance optimization** — Profile and optimize critical paths (latency, CPU, memory)
2. **Production deployment patterns** — Document systemd, Docker, monitoring best practices
3. **Web UI polish** — Mobile responsiveness, accessibility (a11y), PWA installability
4. **Documentation expansion** — Tutorials, troubleshooting, API examples, video guides
5. **Community engagement** — Discord/forum, contributor guide, roadmap transparency
6. **PyPI optimization** — Reduce install time, optional dependencies, wheel size

### Success Criteria

- ✅ Latency benchmarks published (audio RTT, CI-V command latency, scope frame rate)
- ✅ Docker image + docker-compose.yml for one-command deployment
- ✅ systemd unit file for Linux server deployment
- ✅ Web UI passes WCAG 2.1 AA accessibility audit
- ✅ Web UI installable as PWA (offline-capable for cached assets)
- ✅ Contributor guide (CONTRIBUTING.md) with dev setup, testing, PR workflow
- ✅ Video tutorials (YouTube) for setup and common use cases
- ✅ Discord server or GitHub Discussions active with community Q&A
- ✅ PyPI install time <30s on common platforms

### Task Breakdown

#### M6.1 — Performance Profiling & Optimization

| Task | Effort | Notes |
|------|--------|-------|
| Audio latency benchmark (LAN vs serial) | 2d | Measure RX/TX round-trip time, compare to wfview/RS-BA1 |
| CI-V command latency profile | 1d | Measure get_frequency(), set_mode(), etc. |
| Scope frame rate optimization | 2d | Reduce CPU usage for waterfall rendering |
| Memory profiling (long-running sessions) | 2d | Check for leaks in audio/scope buffers |
| CPU profiling (hot paths) | 2d | Identify bottlenecks in protocol/transport layers |
| Optimize imports (lazy loading) | 1d | Reduce startup time |
| Async task profiling (task count, backpressure) | 2d | Ensure no task leaks or runaway loops |
| Document performance characteristics | 1d | Publish benchmarks in docs/performance.md |
| **Total** | **13d (~2.5 weeks)** | |

#### M6.2 — Production Deployment Patterns

| Task | Effort | Notes |
|------|--------|-------|
| Docker image (slim Python + icom-lan) | 2d | Multi-stage build, <200MB image size |
| docker-compose.yml (web + rigctld services) | 1d | One-command deployment |
| systemd unit file + install script | 2d | Auto-restart, logging, user guide |
| Monitoring / metrics (Prometheus exporter?) | 3d | Expose uptime, command counts, audio stats |
| Logging best practices guide | 1d | Structured logging, log levels, rotation |
| Production checklist (security, firewall, TLS) | 2d | Document network security for web UI |
| Kubernetes manifest (optional) | 2d | For k8s users (lower priority) |
| **Total** | **13d (~2.5 weeks)** | |

#### M6.3 — Web UI Polish

| Task | Effort | Notes |
|------|--------|-------|
| Mobile responsiveness audit (phone/tablet) | 2d | Test on iOS Safari, Android Chrome |
| Accessibility audit (WCAG 2.1 AA) | 3d | Keyboard navigation, ARIA labels, screen reader testing |
| PWA manifest + service worker | 2d | Installable, offline-capable for cached assets |
| Touch gestures for waterfall (pinch-zoom, pan) | 3d | Improve mobile UX |
| Dark/light theme polish | 1d | Already implemented, refine color palette |
| Loading states & error boundaries | 2d | Better UX for network failures |
| WebSocket reconnect UX | 1d | Auto-reconnect with toast notifications (already works, polish) |
| **Total** | **14d (~3 weeks)** | |

#### M6.4 — Documentation Expansion

| Task | Effort | Notes |
|------|--------|-------|
| Quickstart video (5-min YouTube) | 2d | Setup, connect, basic operation |
| Troubleshooting guide expansion | 2d | Common issues, debug logs, FAQ |
| API examples (10+ code snippets) | 3d | Frequency scanning, memory recall, CW keyer, etc. |
| CLI cookbook (common workflows) | 2d | rigctld setup, audio loopback, etc. |
| Architecture deep-dive (internals docs) | 3d | For contributors, protocol details |
| CONTRIBUTING.md | 1d | Dev setup, testing, PR workflow, code style |
| Release process documentation | 1d | For maintainers (PyPI publish, changelogs) |
| **Total** | **14d (~3 weeks)** | |

#### M6.5 — Community Engagement

| Task | Effort | Notes |
|------|--------|-------|
| Discord server setup | 1d | Channels: #general, #support, #dev, #announcements |
| GitHub Discussions activation | 1d | Q&A, feature requests, show-and-tell |
| Roadmap transparency (public M5/M6 issues) | 1d | GitHub project board with progress |
| Community call for testers (IC-705/7300/9700) | 1d | Reddit, QRZ, eHam forums |
| Contributor recognition (CONTRIBUTORS.md) | 1d | Credit community contributions |
| Social media presence (Twitter/Mastodon) | Ongoing | Project announcements, milestone releases |
| **Total** | **6d (~1 week)** | |

#### M6.6 — PyPI Optimization

| Task | Effort | Notes |
|------|--------|-------|
| Dependency audit (remove unused deps) | 1d | Minimize install size |
| Optional dependencies (serial, audio, web) | 2d | `pip install icom-lan[serial,web]` for extras |
| Wheel size optimization | 1d | Ensure no unnecessary files in wheel |
| Install time benchmark (Linux/macOS/Windows) | 1d | Target <30s on common platforms |
| Pre-built binary wheels for common platforms | 2d | manylinux, macOS arm64/x86_64, Windows |
| **Total** | **7d (~1.5 weeks)** | |

### Total M6 Effort

| Milestone | Effort |
|-----------|--------|
| M6.1 Performance | 13d (~2.5 weeks) |
| M6.2 Deployment | 13d (~2.5 weeks) |
| M6.3 Web UI Polish | 14d (~3 weeks) |
| M6.4 Documentation | 14d (~3 weeks) |
| M6.5 Community | 6d (~1 week) |
| M6.6 PyPI Optimization | 7d (~1.5 weeks) |
| **Total** | **67d (~13.5 weeks or 3+ months)** |

**Note:** M6 work can largely run in parallel with M5 (except M6.1 multi-model performance comparison needs M5 completion).

### Dependencies & Sequencing

1. **M4 completion** — Cross-surface exposure should be done before heavy docs/polish work
2. **M5 optional** — Most M6 work (except multi-model performance) can start before M5
3. **Community testers** — M6.5 benefits from M5 multi-model support (more testers with different radios)
4. **Web UI stability** — M6.3 assumes current web UI is feature-complete (Phase 7.3 done)

### Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| **Performance regressions** | Low | Medium | Maintain benchmark suite, run on every PR |
| **Accessibility gaps** | Medium | Low | Hire a11y consultant or use community testers |
| **Documentation drift** | High | Medium | Automate API doc generation (Sphinx), link examples to tests |
| **Community silence** | Medium | Low | Seed Discord with initial content, be responsive |
| **Docker image size bloat** | Low | Low | Multi-stage builds, alpine base, prune dependencies |
| **PyPI install failures** | Medium | High | Test on fresh VMs for each platform before release |

---

## Sequencing Strategy

### Option A: Sequential (M5 → M6)

**Timeline:** 6-7 months total
**Pros:** Clear focus, easier testing, less context switching
**Cons:** Longer time to community features, delayed user feedback on multi-radio

```
┌──────────────┬──────────────┐
│      M5      │      M6      │
│  (3 months)  │  (3 months)  │
└──────────────┴──────────────┘
```

### Option B: Parallel (M5 + M6 overlapped)

**Timeline:** 4-5 months total
**Pros:** Faster to market, community engagement starts sooner
**Cons:** Higher context switching, potential resource conflicts

```
┌──────────────────────────────┐
│             M5               │
│         (3 months)           │
└──────────────────────────────┘
         ┌──────────────────────┐
         │         M6           │
         │     (3 months)       │
         └──────────────────────┘
```

**Recommended:** Start M6.4 (docs), M6.5 (community), M6.6 (PyPI) early while M5.1-M5.3 run. Hold M6.1 (multi-model performance) until M5 completes.

### Option C: Staggered (IC-705 first, then parallel)

**Timeline:** 5-6 months total
**Pros:** Early IC-705 release builds momentum, validates multi-model approach
**Cons:** Slightly longer calendar time

```
┌─────────┬────────────────────┐
│ M5.1    │ M5.2/M5.3 parallel │
│ IC-705  │ (IC-7300 + IC-9700)│
│(3 weeks)│   (6-8 weeks)      │
└─────────┴────────────────────┘
              ┌────────────────┐
              │       M6       │
              │  (3 months)    │
              └────────────────┘
```

**Recommendation for CEO:** **Option C (Staggered)** — ship IC-705 support early to validate architecture and build community momentum, then parallelize IC-7300/IC-9700 with M6 work.

---

## Success Metrics

### M5 Success Metrics
- 4 models fully supported (IC-7610, IC-705, IC-7300, IC-9700)
- 100% of IC-7610 integration tests pass for all 4 models (where hardware capabilities allow)
- GitHub issues/requests for IC-705/7300/9700 support resolved
- PyPI downloads increase (more radio models = larger user base)

### M6 Success Metrics
- Docker deployment guide followed by 10+ community members
- Web UI accessibility score >90 (Lighthouse)
- Discord server reaches 50+ members within 1 month of launch
- 5+ external contributors (non-maintainer PRs merged)
- PyPI install time <30s on all platforms
- Performance benchmarks documented and published

---

## Resource Requirements

### Hardware
- IC-705 (~$1000 used) — **Priority 1**
- IC-7300 (~$800 used) — **Priority 2**
- IC-9700 (~$1200 used) — **Priority 3**
- **Alternative:** Remote test access via community volunteers (TeamViewer, AnyDesk)

### Development Time
- M5: ~13.5 weeks full-time (or 6 months part-time)
- M6: ~13.5 weeks full-time (or 6 months part-time)
- **Staggered (Option C):** ~5-6 months calendar time with parallel work

### Community Support
- Beta testers for IC-705/7300/9700 (10+ volunteers)
- Accessibility tester for WCAG audit (1-2 volunteers)
- Documentation reviewers (3-5 technical writers / ham ops)

---

## Open Questions for CEO Review

1. **Hardware procurement strategy?** Buy used radios vs rely on community remote access?
2. **Sequencing preference?** Sequential (A), Parallel (B), or Staggered (C)?
3. **Budget for M6 tools?** E.g., Docker registry ($5/mo), YouTube channel (free), accessibility tools ($0-500)
4. **Community platform preference?** Discord (most ham radio activity) vs GitHub Discussions (lower friction)?
5. **M5 model priority?** IC-705 first (most requested), IC-7300 (largest base), or IC-9700 (satellite niche)?
6. **Release cadence during M5?** Incremental releases (v0.12 IC-705, v0.13 IC-7300) or bundled (v1.0 all 4 models)?

---

## Conclusion

M5 and M6 represent the transition from **single-radio library** (IC-7610 focus) to **multi-radio platform** (community-driven, production-ready). The work is substantial but well-scoped:

- **M5 expands market reach** (4x radio models → 4x potential users)
- **M6 lowers adoption friction** (better docs, easier deployment, community support)

With disciplined execution and community engagement, `icom-lan` can become the **de facto open-source library** for Icom transceiver control, competing with (and surpassing) wfview and RS-BA1 in usability, features, and ecosystem reach.

**Recommended next step:** CEO approval → Create detailed GitHub issues for M5.1 (IC-705) → Begin community outreach for IC-705 hardware access → Kick off M6.4 (docs) and M6.5 (community) in parallel.

---

**Author:** CEO Agent
**Review Status:** Awaiting CEO approval
**Next Review:** After M4.138 completion
