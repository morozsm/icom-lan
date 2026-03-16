# Rig Loader

TOML rig file loading, validation, and runtime object construction.

Module: `icom_lan.rig_loader`

```python
from icom_lan.rig_loader import load_rig, discover_rigs, RigConfig, RigLoadError
```

## Functions

### `load_rig()`

```python
def load_rig(path: Path) -> RigConfig
```

Load and validate a single TOML rig file.

**Args:**

- `path` — `Path` to the `.toml` file.

**Returns:** Parsed and validated `RigConfig`.

**Raises:** `RigLoadError` if the file is missing, cannot be parsed as TOML, or
fails schema validation (missing sections, unknown capability, invalid VFO scheme, etc.).

**Example:**

```python
from pathlib import Path
from icom_lan.rig_loader import load_rig

cfg = load_rig(Path("rigs/ic7610.toml"))
print(cfg.model)          # "IC-7610"
print(cfg.civ_addr)       # 0x98
print(cfg.receiver_count) # 2
print(cfg.vfo_scheme)     # "main_sub"
```

---

### `discover_rigs()`

```python
def discover_rigs(directory: Path) -> dict[str, RigConfig]
```

Discover and load all rig TOML files in a directory.

Files whose names start with `_` are skipped (e.g. `_schema.md`, `_template.toml`).

**Returns:** Dict mapping model name → `RigConfig`, sorted by filename.

**Example:**

```python
from pathlib import Path
from icom_lan.rig_loader import discover_rigs

rigs = discover_rigs(Path("rigs/"))
for model, cfg in rigs.items():
    print(f"{model}: {cfg.civ_addr:#04x}, receivers={cfg.receiver_count}")
# IC-7300: 0x94, receivers=1
# IC-7610: 0x98, receivers=2
```

---

## Classes

### `RigConfig`

```python
@dataclass(frozen=True, slots=True)
class RigConfig:
    id: str
    model: str
    civ_addr: int
    receiver_count: int
    has_lan: bool
    has_wifi: bool
    capabilities: tuple[str, ...]
    modes: tuple[str, ...]
    filters: tuple[str, ...]
    vfo_scheme: str                          # "ab" | "main_sub"
    vfo_main_select: tuple[int, ...] | None
    vfo_sub_select: tuple[int, ...] | None
    vfo_swap: tuple[int, ...] | None
    freq_ranges: tuple[dict, ...]
    commands: dict[str, tuple[int, ...]]
    cmd29_routes: tuple[tuple[int, int | None], ...]
    spectrum: dict[str, int] | None
```

Frozen dataclass. All values are immutable after construction.

#### `.to_profile()` → `RadioProfile`

Build a `RadioProfile` from this config for use in command routing and capability guards.

```python
cfg = load_rig(Path("rigs/ic7300.toml"))
profile = cfg.to_profile()

profile.receiver_count          # 1
profile.vfo_scheme              # "ab"
profile.supports_capability("digisel")  # False — IC-7300 lacks DIGI-SEL
```

#### `.to_command_map()` → `CommandMap`

Build a `CommandMap` from this config's commands (base commands + overrides merged).

```python
cfg = load_rig(Path("rigs/ic7610.toml"))
cmd_map = cfg.to_command_map()

cmd_map.get("get_af_level")  # (0x14, 0x01)
cmd_map.get("scope_on")      # (0x27, 0x10)
len(cmd_map)                 # ~150 commands
```

---

### `CommandMap`

```python
class CommandMap:
    def __init__(self, commands: dict[str, tuple[int, ...]]) -> None: ...
```

Immutable lookup mapping command names to CI-V wire byte tuples.
See [`docs/api/commands.md`](commands.md) for usage with command builder functions.

#### `.get(name)` → `tuple[int, ...]`

Return wire bytes for `name`. **Raises** `KeyError` with a helpful message listing
available commands if `name` is not found.

```python
cm.get("get_af_level")   # (0x14, 0x01)
cm.get("nonexistent")    # KeyError: Unknown command 'nonexistent'. Available: ...
```

#### `.has(name)` → `bool`

Check whether `name` is a known command.

```python
cm.has("digisel")  # True (IC-7610), False (IC-7300)
```

#### `len(cm)` and `iter(cm)`

```python
len(cm)         # number of commands
list(cm)        # sorted list of command names
```

---

### `RigLoadError`

```python
class RigLoadError(Exception): ...
```

Raised by `load_rig()` when the rig file is invalid. The message includes the filename
and the specific field or section that failed validation.

```python
from icom_lan.rig_loader import load_rig, RigLoadError

try:
    cfg = load_rig(Path("rigs/bad.toml"))
except RigLoadError as e:
    print(e)
# bad.toml: missing required section [capabilities]
```

---

## Validation Rules

`load_rig()` enforces the following:

| Check | Error |
|-------|-------|
| File exists | `file not found: <path>` |
| Valid TOML syntax | `failed to parse TOML: <detail>` |
| Required sections present | `missing required section [<section>]` |
| All `[radio]` fields present | `missing required field [radio].<field>` |
| `civ_addr` in 0x00–0xFF | `[radio].civ_addr = X out of range` |
| `[capabilities].features` non-empty | `[capabilities].features must not be empty` |
| All capability strings known | `unknown capability 'xyz'. Known: [...]` |
| `[vfo].scheme` is `"ab"` or `"main_sub"` | `[vfo].scheme must be one of ...` |
| `[modes].list` non-empty | `[modes].list must not be empty` |
| `[filters].list` non-empty | `[filters].list must not be empty` |

Unknown sections or extra fields are silently ignored (forward-compatible).

---

## See Also

- [`rigs/_schema.md`](../../rigs/_schema.md) — complete TOML schema reference
- [`docs/guide/rig-profiles.md`](../guide/rig-profiles.md) — guide for adding new radios
- [`docs/api/commands.md`](commands.md) — using `CommandMap` with command functions
