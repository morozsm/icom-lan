# icom-lan — High-Level Architecture

**Краткое описание:** Python библиотека + Web UI для управления трансиверами Icom через LAN (UDP) или USB serial.

---

## Уровни абстракции (снизу вверх)

```
┌─────────────────────────────────────────────────────────────┐
│                   Frontend (Web UI)                         │
│  Svelte 5 + TypeScript → HTTP poll /api/v1/state (200ms)   │
│  WebSocket для команд + scope data + audio stream           │
└─────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────┐
│              Web Server (src/icom_lan/web/)                 │
│  • HTTP API: /api/v1/info, /api/v1/state, /api/v1/capabilities
│  • WebSocket handlers: control, scope, audio                │
│  • RadioPoller: 200ms state polling                         │
│  • AudioBroadcaster: Opus → browser                         │
│  • DX Cluster client (telnet)                               │
└─────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────┐
│          Radio API Layer (src/icom_lan/radio.py)            │
│  IcomRadio (high-level async API)                           │
│  • get_frequency(), set_mode(), get_s_meter()               │
│  • Scope management (enable/disable/data callbacks)         │
│  • Audio RX/TX (start/stop/push)                            │
│  • Commander queue (serialized CI-V commands)               │
│  • State cache (TTL-based)                                  │
│  Implements: Radio protocol + AudioCapable + ScopeCapable   │
└─────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────┐
│       Backend Layer (LAN/USB Serial transport)              │
│  • LanBackend (UDP 50001/2/3): auth + CI-V + audio          │
│  • SerialBackend (USB): CI-V over serial + USB audio        │
│  Transport abstraction: send_civ() / recv_civ()             │
│  Connection FSM: IDLE → AUTH → PORTS_READY → READY          │
└─────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────┐
│    Command Layer (src/icom_lan/commands.py)                 │
│  • 134 CI-V command builders (get_freq, set_mode, etc)      │
│  • Command parsers (parse_frequency_response, etc)          │
│  • CommandMap: rig-specific overrides                       │
│  • Command29 wrapper для dual-receiver (IC-7610)            │
└─────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────┐
│   CI-V Protocol (src/icom_lan/civ.py)                       │
│  Binary framing: FE FE [to] [from] [cmd] [sub] [data] FD    │
│  BCD encoding (frequency), meter calibration                │
└─────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────┐
│  Rig Profiles (rigs/*.toml) → Data-Driven Config            │
│  • Capabilities (dual_rx, scope, nb, nr, etc)               │
│  • Modes (USB, LSB, CW, FM, AM, RTTY)                       │
│  • Filters (FIL1, FIL2, FIL3)                               │
│  • Band stack (160m-10m BSR codes)                          │
│  • Command overrides (IC-7300 vs IC-7610)                   │
│  • AGC labels (FAST/MID/SLOW vs 1/2/3)                      │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Flow: TOML → Web UI

### 1️⃣ **TOML файл** (`rigs/ic7610.toml`)

Декларативное описание возможностей радио:

```toml
[radio]
id = "icom_ic7610"
model = "IC-7610"
civ_addr = 0x98
receiver_count = 2
has_lan = true

[capabilities]
dual_rx = true
scope = true
nb = true
nr = true
digisel = true

[modes]
values = ["USB", "LSB", "CW", "AM", "FM", "RTTY"]

[filters]
values = ["FIL1", "FIL2", "FIL3"]

[commands]
get_s_meter_sql_status = [0x15, 0x01]  # Override IC-7610 command
```

**Зачем TOML?**
- Добавить новое радио = написать TOML файл (не нужен Python код)
- Централизация различий между моделями (IC-7610 vs IC-7300)
- Command overrides (разные wire bytes для одних и тех же функций)

---

### 2️⃣ **Rig Loader** (`src/icom_lan/rig_loader.py`)

Парсит TOML → валидирует → создаёт runtime объекты:

```python
from icom_lan.rig_loader import load_rig

rig = load_rig("rigs/ic7610.toml")
profile: RadioProfile = rig.to_profile()      # Runtime profile
cmd_map: CommandMap = rig.to_command_map()    # Command overrides
```

**Выходные объекты:**
- `RadioProfile` — capabilities, modes, filters, band stack, freq ranges
- `CommandMap` — словарь wire bytes для команд (используется в `commands.py`)

---

### 3️⃣ **Radio API** (`src/icom_lan/radio.py`)

Высокоуровневый async API:

```python
async with IcomRadio("192.168.1.100", username="u", password="p") as radio:
    freq = await radio.get_frequency()            # → commands.get_freq()
    await radio.set_mode("USB")                   # → commands.set_mode()
    s_meter = await radio.get_s_meter()           # → commands.get_s_meter()
```

**Под капотом:**
- `Commander` queue — сериализация CI-V команд (одна за раз)
- `StateCache` — TTL-кэш для снижения нагрузки на радио
- Retry logic + timeout handling
- Command29 routing для dual-receiver (MAIN/SUB)

**Scope API:**
```python
def on_scope_data(data: bytes):
    print(f"Spectrum frame: {len(data)} bytes")

await radio.enable_scope(on_scope_data)
```

**Audio API:**
```python
await radio.start_audio_rx()
audio_frame = await radio.recv_audio()  # Opus/PCM bytes
```

---

### 4️⃣ **Commands Layer** (`src/icom_lan/commands.py`)

**134 функции-builders** для CI-V команд:

```python
# Builder
frame = get_frequency(to_addr=0x98, from_addr=0xE0)
# → b'\xfe\xfe\x98\xe0\x03\xfd'

# Parser
freq_hz = parse_frequency_response(b'\x00\x40\x07\x14')
# → 14074000 (14.074 MHz, BCD encoded)
```

**Command Map routing:**
```python
# IC-7610 default
get_s_meter_sql_status(to_addr=0x98)
# → (0x15, 0x01)

# IC-7300 override (из TOML)
cmd_map = CommandMap({"get_s_meter_sql_status": (0x16, 0x43)})
get_s_meter_sql_status(to_addr=0x94, cmd_map=cmd_map)
# → (0x16, 0x43)  # Использован override
```

**Command29 wrapper** (dual-receiver):
```python
# Main receiver
get_frequency(receiver=RECEIVER_MAIN)  # → 0x07 0xD0 prefix

# Sub receiver
get_frequency(receiver=RECEIVER_SUB)   # → 0x07 0xD1 prefix
```

---

### 5️⃣ **Backend Layer** (Transport)

**LAN Backend** (`backends/icom7610/drivers/`):
- UDP port 50001 → control (auth, token renewal)
- UDP port 50002 → CI-V commands
- UDP port 50003 → audio (Opus/PCM)

**Serial Backend:**
- USB serial → CI-V commands (19200 baud)
- USB audio device → CoreAudio (macOS IORegistry matching)

**Connection FSM:**
```
IDLE → AUTH → TOKEN_RENEW → PORTS_READY → AUDIO_NEG → READY
```

---

### 6️⃣ **Web Server** (`src/icom_lan/web/server.py`)

**HTTP API:**
```
GET /api/v1/capabilities
  → {model, modes, filters, capabilities[], freq_ranges[]}

GET /api/v1/state
  → {main:{freq,mode,filter,meters}, sub:{...}, ptt, split, ...}
     124 полей, 200ms polling
```

**WebSocket channels:**
```
/api/v1/ws          → control commands (set freq/mode/power)
/api/v1/scope       → binary spectrum data (WebAssembly decoder)
/api/v1/audio       → Opus audio stream (RX/TX)
```

**RadioPoller** (`radio_poller.py`):
- 200ms таймер → `get_all_state()`
- Собирает 30+ команд (freq, mode, meters, toggles)
- Broadcast state → все подключенные WS клиенты

---

### 7️⃣ **Frontend** (`src/icom_lan/web/static/`)

**Svelte 5 + TypeScript**

**State sync:**
```typescript
// HTTP poll (200ms)
const state = await fetch('/api/v1/state').then(r => r.json());

// Derived UI state
$: freqMhz = state.main.freqHz / 1e6;
$: modeLabel = state.main.mode;
```

**Command dispatch:**
```typescript
// WebSocket send
ws.send(JSON.stringify({
  channel: 'control',
  command: 'set_frequency',
  args: { freq_hz: 14074000 }
}));
```

**Components:**
- `App.svelte` — root, desktop/mobile layout switch
- `Spectrum.svelte` — canvas rendering (WebAssembly decoder)
- `Waterfall.svelte` — canvas + DX spots overlay
- `ControlPanel.svelte` — sliders, toggles, buttons
- `MobileLayout.svelte` — touch-optimized

**State management:**
- Server state = single source of truth
- No Redux/Vuex — direct HTTP poll + WS commands
- Pending actions tracked locally for optimistic UI

---

## Ключевые паттерны

### 🔹 Data-driven rig profiles
- TOML файл = source of truth для нового радио
- Никаких hardcoded if/else в коде
- Command overrides через `CommandMap`

### 🔹 Protocol abstraction
- `Radio` protocol — backend-agnostic API
- `AudioCapable`, `ScopeCapable` — capability protocols
- LAN vs Serial — одинаковый high-level API

### 🔹 Commander queue
- Сериализованные CI-V команды (одна за раз)
- Retry + timeout + deduplication
- Pacing (1ms min gap between commands)

### 🔹 State polling (не push)
- Web UI делает GET /api/v1/state каждые 200ms
- Проще, чем WebSocket delta push
- Мобильная оптимизация отложена (Phase 3+)

### 🔹 Zero external dependencies
- Чистый Python stdlib (asyncio, socket, struct)
- Web UI = встроенный HTTP сервер (без Flask/FastAPI)
- WebSocket = RFC 6455 реализация (без библиотек)

---

## Примеры Flow

### 📡 **Set Frequency через Web UI**

```
Browser click "14.074" button
  ↓
WebSocket send: {command: "set_frequency", args: {freq_hz: 14074000}}
  ↓
ControlHandler.handle_set_frequency()
  ↓
radio.set_frequency(14074000)
  ↓
Commander queue: set_freq(14074000, cmd_map=profile.cmd_map)
  ↓
commands.set_frequency(14074000) → build CI-V frame
  ↓
Transport.send_civ(frame)
  ↓
UDP socket → radio IP:50002
  ↓
Radio executes, sends ACK
  ↓
Next poll (200ms): GET /api/v1/state
  ↓
Browser updates UI: freq = 14.074 MHz
```

### 📊 **Spectrum Data Flow**

```
radio.enable_scope(callback=on_scope_data)
  ↓
Send scope_on CI-V command (0x27 0x10 0x01)
  ↓
Radio starts streaming UDP packets (port 50002)
  ↓
_civ_rx.py: parse 0x27 0x14 frames
  ↓
Callback → ScopeHandler.on_scope_data()
  ↓
WebSocket broadcast → /api/v1/scope clients
  ↓
Browser: WebAssembly decoder → canvas render
```

### 🎛️ **TOML → Runtime**

```
rigs/ic7610.toml
  ↓
rig_loader.load_rig() → validate schema
  ↓
RigConfig dataclass
  ↓
RigConfig.to_profile() → RadioProfile
  ↓
RadioProfile passed to IcomRadio(profile=...)
  ↓
Used for:
  • Capability checks (if "scope" in profile.capabilities)
  • Mode/filter lists (frontend dropdown)
  • Command overrides (cmd_map in commands.py)
  • Band stack (BSR codes)
```

---

## Точки расширения

### ✅ Добавить новое радио
1. Создать `rigs/ic9700.toml` (скопировать шаблон)
2. Заполнить capabilities, modes, filters
3. Добавить command overrides (если нужны)
4. Готово — библиотека автоматически поддержит модель

### ✅ Добавить новую команду
1. Добавить builder в `commands.py`: `def get_new_feature()`
2. Добавить parser: `def parse_new_feature_response()`
3. Добавить метод в `IcomRadio`: `async def get_new_feature()`
4. Добавить в Web API handlers
5. Добавить UI компонент в Svelte

### ✅ Добавить новый transport
1. Реализовать `CivTransport` protocol
2. Добавить backend config (`WifiBackendConfig`)
3. Зарегистрировать в `create_radio()`

---

## Тестирование

- **3470 unit тестов** (5 минут runtime)
- **Mock radio classes** для integration tests (без hardware)
- **Command roundtrip tests** (builder → parser → validate)
- **Rig profile validation** (TOML schema checks)
- **Web API smoke tests** (HTTP endpoints)

---

## Документация

- `docs/guide/` — user guides (installation, quickstart, troubleshooting)
- `docs/plans/` — architecture decisions
- `docs/sessions/` — development session reports
- `README.md` — project overview + API examples
- `ARCHITECTURE.md` — (этот файл) high-level overview

---

**Итого:** TOML профили → rig_loader → Radio API → Commands layer → CI-V transport → Web Server → Frontend (Svelte). Каждый уровень независимый, с чёткими boundaries.
