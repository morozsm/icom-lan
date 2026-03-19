# icom-lan Debug Logs

This directory contains debug logs when running `icom-lan` in development mode.

## Usage

### Quick Start (Development Server)

```bash
./run-dev.sh
```

This starts the web server with:
- `ICOM_DEBUG=1` — enables DEBUG level logging
- Logs to `logs/icom-lan.log` (console + file)
- Radio: `192.168.55.40` (override with `ICOM_HOST=...`)
- Web UI: `http://0.0.0.0:8080` (override with `WEB_PORT=...`)

### Manual Control

```bash
# Enable debug logging (logs to logs/icom-lan.log by default)
ICOM_DEBUG=1 uv run icom-lan web --host 0.0.0.0 --port 8080

# Custom log file
ICOM_DEBUG=1 ICOM_LOG_FILE=/tmp/my-debug.log uv run icom-lan web

# Console only (no file)
ICOM_DEBUG=1 ICOM_LOG_FILE= uv run icom-lan web
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ICOM_DEBUG` | `0` | Set to `1` to enable DEBUG level logging + file output |
| `ICOM_LOG_FILE` | `logs/icom-lan.log` | Path to log file (auto-created in DEBUG mode) |
| `ICOM_HOST` | `192.168.55.40` | Radio IP address |
| `ICOM_USER` | `moroz` | Radio login username |
| `ICOM_PASS` | — | Radio password |

## Log Format

**Console (DEBUG mode):**
```
19:41:47 icom_lan.discovery INFO discover_lan_radios: found 192.168.55.40
```

**File:**
```
2026-03-19 19:41:47 icom_lan.discovery [INFO] discover_lan_radios: found 192.168.55.40
```

## Troubleshooting

**Server crashed?** Check `logs/icom-lan.log` for the last exception traceback.

**No log file created?** Verify `ICOM_DEBUG=1` is set before running.

**Logs too large?** Rotate manually:
```bash
mv logs/icom-lan.log logs/icom-lan.log.old
```

## .gitignore

The `logs/` directory is excluded from git (see `.gitignore`).
