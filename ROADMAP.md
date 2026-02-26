# Roadmap

## Testing

- [ ] **Mock Radio Server** — UDP-сервер, эмулирующий протокол IC-7610 (discovery, auth, CI-V).
  Позволит покрыть интеграционными тестами `radio.py` connect/disconnect handshake,
  `transport.py` connect/discover, и `cli.py` discover (broadcast).
  Текущее покрытие: 88%. С mock-сервером — цель 95%+.

## Features

- [ ] Async event/notification stream (S-meter polling, band changes)
- [ ] Support for IC-705, IC-7300 (different CI-V addresses, feature sets)
- [ ] PyPI publication

## Hamlib NET rigctl compatibility (rigctld 1:1)

Цель: обеспечить совместимость с клиентами Hamlib/WSJT-X через TCP endpoint
`127.0.0.1:4532`, повторяя поведение `rigctld` на уровне протокола и кодов ответов.

### Phase 0 — RFC + protocol contract ✅

- [x] Контракт в `src/icom_lan/rigctld/contract.py`:
  - `RigctldCommand`, `RigctldResponse` dataclasses
  - `COMMAND_TABLE` с определениями всех команд
  - `HamlibError` enum (коды `-1..-22`)
  - `HAMLIB_MODE_MAP` / `CIV_TO_HAMLIB_MODE` маппинги
  - `RigctldConfig`, `ClientSession`
- [x] Read-only mode: deny set-команд с `RPRT -22` (`EACCESS`).

### Phase 1 — MVP command set ✅

- [x] TCP server на конфигурируемом host/port (`asyncio.start_server`)
- [x] Команды: `f/F`, `m/M`, `t/T`, `v/V`, `s/S`, `l` (STRENGTH/RFPOWER/SWR), `q`
- [x] Служебные: `\dump_state`, `\get_info`, `\chk_vfo`, `\get_powerstat`, `\dump_caps`
- [x] Long-form команды (`\get_freq`, `\set_freq`, etc.)
- [x] Формат ответов: `RPRT <code>\n` для set, value lines для get
- [x] `dump_state` в точном позиционном формате hamlib netrigctl.c (protocol v0)
- [x] Float frequency parsing (`F 7074000.000000`)

### Phase 2 — Safety + observability ✅

- [x] `--read-only` mode через CLI и RigctldConfig
- [x] Structured logging: client connect/disconnect/errors с peername
- [x] Max client limit (`--max-clients`)
- [x] Per-client idle timeout
- [x] Per-command timeout (`asyncio.wait_for`)
- [x] Frequency/mode cache с TTL (default 200ms) — защита от CI-V bus saturation
- [x] OOM guard: max line length 1024 bytes
- [x] TCP backpressure (`writer.drain()`)
- [x] CLI: `icom-lan serve --port 4532 --read-only --max-clients 10`

### Phase 3 — Client compatibility hardening (in progress)

- [x] Smoke-тест с `rigctl -m 2`: `f`, `F`, `m`, `M`, `l STRENGTH/RFPOWER/SWR` — OK
- [ ] Полный тест с WSJT-X (Hamlib NET rigctl, localhost:4532)
- [ ] Тест с JS8Call, fldigi
- [ ] Golden tests: Wireshark-дампы от реального rigctld vs наши ответы
- [ ] Extended response protocol (per-session `extended_mode`)
- [ ] Fallback policy для unsupported команд (`RPRT -4` / `RPRT -11`)

### Phase 4 — Protocol completeness (после Phase 3)

- [ ] `\set_level` (RFPOWER)
- [ ] RIT/XIT (`J`/`Z`)
- [ ] Tuner control
- [ ] `\dump_state` protocol v1 (key=value pairs, `done` terminator)
- [ ] Документировать compatibility matrix

### README / Docs updates ✅

- [x] README: CLI примеры для `icom-lan serve`
- [x] README: WSJT-X quick start (Rig: Hamlib NET rigctl, localhost:4532)
- [x] README: примеры `rigctl -m 2`
- [ ] Отдельный troubleshooting: port in use, unsupported command, read-only denied
