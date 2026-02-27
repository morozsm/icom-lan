# Strategy — Path to Platform

## Thesis

There is no standalone, embeddable, MIT-licensed library for Icom's LAN protocol. wfview is GPL (can't embed), RS-BA1 is closed/paid. We fill this gap. First mover wins.

## Competitive Moats

| Moat | Why it matters |
|------|---------------|
| **MIT license** | Any project can embed us. wfview (GPL) can't be embedded in closed-source or permissive projects |
| **Library-first** | wfview is an app. We're a building block. Every Icom LAN project will depend on us |
| **Multi-language** | Rust core → Python, JS, C, WASM. One protocol impl, every ecosystem |
| **Zero dependencies** | Easy to install, easy to audit, easy to embed |
| **Modern async** | asyncio/tokio, not callbacks-and-threads from 2005 |

## Anti-Moats (risks)

| Risk | Mitigation |
|------|-----------|
| Someone forks wfview as a library | GPL makes this painful for embedders; our MIT is strictly better |
| Icom opens their protocol | Good for us — validates the approach, expands the market |
| hamlib adds native LAN support | hamlib moves slowly (C, committee-driven); we move fast |
| Low adoption | Aggressive community outreach, killer demos |

## Velocity Plan (updated after v0.7.0)

### Done (all 32 issues closed, 1040 tests)

- [x] Phase 3: Opus audio RX/TX API (Python)
- [x] Phase 3b: High-level PCM API + CLI audio subcommands + auto-recovery
- [x] Phase 4: Polish + PyPI publish + GitHub releases (v0.7.0)
- [x] Phase 6: Spectrum/waterfall parsing + CLI capture + rendering
- [x] **Phase 7: Hamlib NET rigctld server** — drop-in replacement for `rigctld`
  - TCP server with multi-client, backpressure, caching
  - Golden protocol response suite (45 fixtures) + TCP wire tests
  - WSJT-X compat mode, DATA mode semantics, CI-V desync fix
  - 1040 tests, 0 regressions

### Next: v0.7.0 release + community launch

**Goal:** Ship v0.7.0, announce to community, start collecting feedback.

- [ ] Release v0.7.0 (version bump, CHANGELOG, PyPI)
- [ ] Reddit /r/amateurradio + /r/hamradio announcement
- [ ] QRZ.com forum post
- [ ] Enable GitHub Discussions

### After v0.7.0: client hardening + Web UI

- [ ] Test rigctld with WSJT-X, JS8Call, fldigi (real-world validation)
- [ ] Web backend bridge (safe API surface for freq/mode/meter/scope snapshot)
- [ ] Minimal UI: frequency, mode, S-meter, basic controls
- [ ] Scope snapshot panel (reuse existing `scope` pipeline)

### Parallel spike (optional)

**Goal:** Evaluate the cost of entry into Rust core (Phase 5.1) without migrating the entire project.

- [ ] Create minimal Rust transport prototype (connect + one CI-V command)
- [ ] Measure complexity/latency vs current Python implementation
- [ ] Decide go/no-go for full Rust migration

### Deferred (separate discussion)

- Community outreach/posts/channels
- Positioning/marketing tasks

## Community Building

### Where hams live

| Platform | Action | When |
|----------|--------|------|
| Reddit /r/amateurradio | "I built an open-source Python library for Icom LAN control" | Sprint 1 |
| Reddit /r/hamradio | Same | Sprint 1 |
| QRZ.com forums | Post in "Software" section | Sprint 1 |
| HackerNews | "Show HN: Control Icom radios from the browser" | Sprint 3 |
| YouTube | Waterfall demo video | Sprint 3 |
| Twitter/X | GIF of web waterfall | Sprint 3 |
| Ham radio clubs | Word of mouth, field day demos | Ongoing |
| GitHub Discussions | Enable for Q&A and feature requests | Sprint 1 |

### Content that converts

1. **GIF: terminal → radio frequency changes** — for Reddit (Sprint 1)
2. **Video: waterfall in browser, click-to-tune** — for YouTube/HN (Sprint 3)
3. **Blog post: "How Icom's LAN protocol works"** — SEO, establishes authority
4. **Comparison table: icom-lan vs wfview vs RS-BA1** — for README

### Metrics to track

- GitHub stars (vanity but visibility)
- PyPI downloads (actual usage)
- GitHub issues from non-us people (community health)
- Radio compatibility reports (coverage)

## Naming & Branding

**`icom-lan`** — short, descriptive, memorable. Perfect for a library.

If we grow into a full platform (web UI, waterfall), consider:
- **`icom-lan`** stays as the core library name
- Web UI could be **`icom-lan-web`** or a separate project name
- Don't over-brand early. Let the product speak.

## Future: Universal Radio Bridge (RPi)

**Idea:** Raspberry Pi appliance that connects to any transceiver via USB (serial CAT)
and exposes a unified network control interface — turning USB-only radios into
LAN-controllable ones.

**Why:**
- Most radios (Yaesu FTX-1, Xiegu X6200, Lab599 TX-500, IC-7300) only have USB/serial CAT
- IC-7610's LAN protocol is the exception, not the rule
- An RPi bridge would make `icom-lan`'s server layer (rigctld, future REST/WebSocket)
  available to *any* radio, not just Icom LAN models

**Architecture (conceptual):**
```
  Transceiver ──USB/Serial──▶ RPi Bridge ──LAN──▶ Clients (WSJT-X, Web UI, etc.)
                               │
                           RadioDriver (per-brand: CI-V, Yaesu CAT, Kenwood IF, Elecraft)
                               │
                           StateCache + Poller
                               │
                           rigctld / REST / WebSocket server
```

**When:** After v1.0 and proven stability with IC-7610. Extract `RadioDriver` Protocol
from real differences between at least 2 implementations (e.g., IC-7610 LAN + IC-7300 USB).

**Council verdict (2026-02-26, 5 models):** Don't abstract prematurely. StateCache + Poller
is already the right layer. Build the Protocol trait when the second radio driver exists,
not before. "Rule of Three" applies.

**Available hardware:** IC-7610 (LAN), IC-7300 (USB), Yaesu FTX-1 (USB),
Xiegu X6200 (USB), Lab599 TX-500 (USB).

## Long-term Vision

```
Year 1:  The go-to library for Icom LAN control
Year 2:  The platform (lib + CLI + web + audio)
Year 3:  Universal Radio Bridge (RPi) + multi-vendor drivers
         Extract RadioDriver Protocol from real implementations
```

---

*"Move fast. Ship often. Let the community tell you what's next."*

*Created: 2026-02-25*
*Last updated: 2026-02-26*
