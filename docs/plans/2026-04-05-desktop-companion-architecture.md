# Desktop Companion Architecture (dual-mode remote access)

**Date:** 2026-04-05  
**Status:** Accepted architectural direction  
**Scope:** Remote access, desktop integration, RC-28, local audio bridge, WSJTX interoperability

## Summary

`icom-lan` will keep its current **remote-first web/server architecture** as the primary open-core experience.

A separate **optional desktop companion** will be introduced for desktop-only integrations that do not fit a browser-first model:
- RC-28 / local hardware controllers
- local virtual audio devices
- WSJTX / desktop digital-mode interoperability
- desktop-specific UX and OS integration

The desktop companion will be developed in a **separate closed-source repository** (currently referred to as `icom-lan-pro`, exact repo name to verify).

This is a **dual-mode architecture**:

1. **Direct remote web mode** — browser connects directly to the remote `icom-lan` server
2. **Desktop companion mode** — local companion proxies the remote server to `localhost` and adds desktop integrations

## Decision

### Keep the remote web server

The remote `icom-lan` web server remains a first-class product surface.

It is required for:
- mobile/phone access
- tablet/browser-only access
- zero-install remote operation
- simple remote control from any browser

The companion must **not** replace or deprecate direct remote web access.

### Add an optional desktop companion

The companion is a **desktop-only edge adapter / local gateway**, not a second radio server.

It will:
- connect to a remote `icom-lan` server over an encrypted channel
- expose a local `localhost` entrypoint for browser-based desktop use
- proxy web assets / API / websocket streams from the remote server
- provide local integrations that are not practical from the browser

### Keep the companion closed-source and in a separate repository

The companion should live in a separate private/closed repository (`icom-lan-pro`, exact name to verify), not in the main `icom-lan` repository.

## Why this decision makes sense

### 1. Browser-only is insufficient for desktop radio workflows

A browser-first approach is still correct for mobile and casual remote access, but it is the wrong foundation for:
- RC-28 integration
- local HID/USB controller support
- local virtual audio devices
- direct WSJTX/JTDX/Fldigi interoperability
- desktop-grade system integration

Even where WebHID/WebUSB/Web MIDI exist, they are inconsistent across browsers and operating systems and create fragile permission-dependent UX.

### 2. Companion solves desktop problems without weakening mobile

With a dual-mode design:
- **phones** use the remote server directly
- **desktops/laptops** can optionally use the companion

That means mobile does not depend on a local service, and desktop gets the features a browser cannot provide well.

### 3. Closed companion is a good boundary

The companion is likely to contain high-friction platform-specific glue:
- HID/RC-28 integration
- audio-device management
- installers / updater logic
- platform-specific background service behavior
- proxy/tunnel/session glue

That code is support-heavy and product-specific. Keeping it separate and closed allows faster iteration without polluting the open-core repository.

### 4. Open server + public API remains the source of truth

The remote `icom-lan` server remains the authoritative system for:
- radio state
- protocol/backends
- web UI contract
- authentication/authorization behavior
- capabilities and events

The companion must be an adapter layer, not a second source of truth.

## Non-goals

The companion is **not** intended to:
- duplicate radio state machine logic locally
- become a forked second implementation of `icom-lan`
- replace direct remote web access
- support phones/mobile OSes as a local service
- require hidden/private server behavior unavailable to normal clients

## Architecture

## Mode A — Direct Remote Web

Used by:
- phones
- tablets
- zero-install remote access
- browser-only environments

Flow:

`Browser -> HTTPS/WSS -> remote icom-lan server -> radio`

Benefits:
- no local install
- first-class mobile support
- simplest access path

Limitations:
- no RC-28
- no local audio devices
- limited desktop interoperability

## Mode B — Desktop Companion / Local Proxy

Used by:
- desktop/laptop users
- RC-28 users
- WSJTX/JTDX/Fldigi users
- users who need local audio bridge devices or desktop-native integrations

Flow:

`Desktop browser / desktop apps -> localhost companion -> encrypted tunnel -> remote icom-lan server -> radio`

The companion provides:
- local HTTP proxy for the web UI
- API/WebSocket proxying
- local hardware-controller integration
- local virtual audio-device integration
- desktop-specific helper services

## Boundary: what stays open vs closed

### Open (`icom-lan` repo)

- remote server
- radio backends
- web UI
- public API contracts
- event model
- capability model
- documented transport expectations
- browser/mobile direct access

### Closed companion repo (`icom-lan-pro`)

- desktop proxy service
- RC-28 / HID / local controller adapters
- local audio-device integration and packaging
- desktop-only UX
- installer/update/distribution logic
- power-user integrations for local desktop workflows

## Hard architectural constraints

### 1. Public APIs only

The companion must consume **documented public APIs/contracts**.

It must not depend on:
- hidden endpoints
- private companion-only wire behavior
- undocumented server state assumptions
- server hacks unavailable to first-class web clients

### 2. One source of truth

The remote server remains the authoritative source of state.

The companion may cache or proxy, but it must not become a second state authority.

### 3. Companion-only features must be clearly namespaced

If the companion needs local-only APIs, they should be clearly separated from remote-server APIs.

Recommended split:
- `/api/v1/...` — server-compatible public API
- `/api/local/v1/...` — companion-local desktop integrations

This avoids ambiguity between direct mode and companion mode.

### 4. Mobile remains first-class without companion

Everything needed for mobile/browser remote operation must continue to work without any companion present.

## Transport direction

Initial assumption:
- use encrypted HTTPS/WSS-based communication between companion and remote server
- use reconnect-friendly token-based auth/session model

Why:
- works cleanly through NAT/reverse proxy setups
- fits current browser/web transport model
- avoids inventing a second premature transport stack

Future alternatives (not MVP):
- QUIC
- gRPC streams
- mTLS device identity

## Audio direction

For MVP, the companion should initially reuse the existing remote audio/control model where practical, then adapt it into local desktop-facing devices.

That means:
- receive remote audio stream
- expose it locally to desktop workflows
- send local TX audio back over the encrypted tunnel

The platform-specific local audio-device strategy will likely differ per OS and should be abstracted inside the companion.

## Multi-platform assumptions

The companion is explicitly **desktop-only** and should target:
- macOS
- Windows
- Linux

Mobile platforms are not a target for the companion.

### Implication

- mobile = direct remote web
- desktop = either direct remote web or optional companion mode

## Risks and tradeoffs

### Risk: two access modes diverge

If direct remote web and companion mode see different behavior, the product becomes confusing.

Mitigation:
- maintain one public API contract
- use companion as a proxy/adapter, not a forked API surface
- isolate local-only desktop APIs under a clearly separate namespace

### Risk: platform-specific audio complexity

Audio-device plumbing varies heavily across macOS/Windows/Linux.

Mitigation:
- keep platform audio abstraction entirely inside the companion
- do not let OS-specific audio assumptions leak into open-core server APIs

### Risk: support burden

Desktop glue code tends to generate operational complexity.

Mitigation:
- keep it in the separate companion repo
- version and ship it independently
- keep the open server repo focused on portable core logic

## MVP roadmap

### MVP 1 — Local proxy companion

- authenticate to remote `icom-lan`
- expose a localhost browser entrypoint
- proxy remote web/API/websocket traffic
- establish encrypted tunnel foundation

### MVP 2 — RC-28 / local controller integration

- detect RC-28 / supported local controllers
- translate local device input into semantic tuning/PTT actions
- send those actions to the remote server

### MVP 3 — Local audio bridge / desktop interoperability

- expose local RX/TX audio path for desktop software
- support WSJTX-style local integration
- keep remote server as audio source of truth

### MVP 4 — Optional desktop polish

- installer/autostart
- tray/menu-bar integration
- reconnect/status UX
- optional local notifications

## Practical implication for issue #315

Issue #315 should not be treated as a browser-only `WebUSB/WebHID/MIDI` feature.

The correct long-term framing is broader:
- desktop companion / local controller integration for remote radios
- local desktop interoperability layer

That may justify either:
- rewriting/reframing #315, or
- creating a new companion epic and downgrading #315 to an optional experimental browser path

## Accepted decisions

1. Keep direct remote web access as a first-class product path
2. Add an optional desktop companion for desktop-specific integrations
3. Develop the companion in a separate closed-source repository (`icom-lan-pro`, exact repo name to verify)
4. Keep the remote server and protocol surface open and documented
5. Require companion/server interaction to use public APIs/contracts only
6. Treat mobile as direct-remote only; companion is desktop-only

## Next steps

1. Verify the exact private repository name for the companion
2. Open an architecture/epic issue for the companion layer
3. Define companion/server public API boundary explicitly
4. Decompose MVP into:
   - local proxy/tunnel
   - controller integration
   - local audio bridge
   - desktop packaging
5. Save this decision in project memory / RAG for future planning and cross-session continuity
