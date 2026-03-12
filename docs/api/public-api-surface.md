# Public API Surface

This page defines the **officially supported** public API of `icom_lan`. Use these exports for stable, documented behavior. Other symbols re-exported from `icom_lan` are available for advanced or legacy use but may have looser backward-compatibility guarantees.

## Supported exports (recommended)

### Radio connection and control

| Symbol | Description |
|--------|-------------|
| `create_radio` | Factory for backend-neutral radio instances (LAN or serial). **Preferred entry point.** |
| `Radio` | Protocol for radio control; use with `create_radio()` for type-safe, backend-agnostic code. |
| `IcomRadio` | Legacy LAN-specific class; use for direct IC-7610 LAN control or when migrating from older code. |
| `LanBackendConfig`, `SerialBackendConfig`, `BackendConfig` | Backend configuration for `create_radio()`. |
| `RadioState`, `ReceiverState`, `ScopeControlsState` | State types exposed by the radio. |
| `RadioProfile`, `get_radio_profile`, `resolve_radio_profile` | Model/profile resolution. |
| `RADIOS`, `RadioModel`, `get_civ_addr` | Radio model registry and CI-V address lookup. |

### Capability protocols (for type narrowing)

| Symbol | Description |
|--------|-------------|
| `AudioCapable` | Protocol for radios that support audio streaming. |
| `ScopeCapable` | Protocol for radios that support scope/waterfall. |
| `DualReceiverCapable` | Protocol for dual-receiver (MAIN/SUB) support. |
| `LevelsCapable` | Protocol for setting receiver levels: AF, RF gain, squelch. |
| `MetersCapable` | Protocol for read-only meters: S-meter, SWR, TX power. |
| `PowerControlCapable` | Protocol for power on/off and TX power level control. |
| `StateNotifyCapable` | Protocol for state-change and reconnect callbacks (server integration). |

**Note:** The core `Radio` protocol no longer includes meter, level, power, or state-notify methods; those live on the capability protocols above. Use `isinstance(radio, MetersCapable)` (etc.) before calling them.

### Exceptions

| Symbol | Description |
|--------|-------------|
| `IcomLanError` | Base exception. |
| `ConnectionError`, `AuthenticationError`, `CommandError`, `TimeoutError` | Connection and command errors. When catching timeouts, use `icom_lan.exceptions.TimeoutError` explicitly; distinguish from `asyncio.TimeoutError` if needed (see [exceptions](exceptions.md)). |
| `AudioError`, `AudioCodecBackendError`, `AudioFormatError`, `AudioTranscodeError` | Audio-related errors. |

### Sync wrapper and utilities

| Symbol | Description |
|--------|-------------|
| `icom_lan.sync.IcomRadio` | Synchronous wrapper; use `from icom_lan.sync import IcomRadio` for blocking API. |

### Common types

| Symbol | Description |
|--------|-------------|
| `__version__` | Package version string. |
| `PacketType`, `Mode`, `AudioCodec`, `CivFrame`, `PacketHeader` | Types used in API signatures. |
| `HEADER_SIZE`, `bcd_encode`, `bcd_decode`, `get_audio_capabilities` | Low-level helpers used by supported APIs. |

---

## Advanced / implementation detail

The following are re-exported for power users, scripts, or compatibility. Prefer the supported API above when possible.

- **Transport**: `IcomTransport`, `ConnectionState`, `RadioConnectionState` — connection lifecycle and state.
- **Protocol**: `parse_header`, `serialize_header`, `identify_packet_type` — packet parsing.
- **Auth**: `AuthResponse`, `StatusResponse`, `encode_credentials`, `build_login_packet`, `build_conninfo_packet`, `parse_auth_response`, `parse_status_response` — handshake building/parsing.
- **Commands**: Individual CI-V helpers (`get_frequency`, `set_frequency`, `get_mode`, `set_mode`, scope get/set, etc.), `build_civ_frame`, `parse_civ_frame`, `IC_7610_ADDR`, `CONTROLLER_ADDR`, `RECEIVER_MAIN`, `RECEIVER_SUB` — use when you need direct CI-V encoding or custom command flows.
- **Commander**: `IcomCommander`, `Priority` — command queue and priority (used internally by the radio).
- **Audio**: `AudioPacket`, `AudioState`, `AudioStats`, `AudioStream`, `JitterBuffer`, `AUDIO_HEADER_SIZE` — audio pipeline types.
- **Scope**: `ScopeAssembler`, `ScopeFrame` — scope assembly; scope rendering (`SCOPE_THEMES`, `amplitude_to_color`, `render_scope_image`, etc.) when Pillow is available.

When extending the library or writing integration code, prefer importing from the modules that define these symbols (e.g. `icom_lan.commands`, `icom_lan.transport`) rather than relying on `icom_lan` re-exports, so that future narrowing of the top-level `__all__` does not break your code.

---

## Summary

- **Use for new code**: `create_radio`, `Radio`, backend configs, capability protocols, exceptions, `RadioState`, profiles, and `sync.IcomRadio` for blocking use.
- **Use when needed**: Individual commands, transport, auth, and audio/scope types for custom pipelines or debugging.
- **Internal**: Modules and symbols whose names start with `_` (e.g. `_connection_state`, `_shared_state_runtime`) are not part of the public API and may change without notice.
