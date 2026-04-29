# `?ui=v1` Telemetry & Deprecation Audit

**Date:** 2026-04-23
**Issue:** [#1215](../../) — `feat(telemetry): audit ?ui=v1 usage before removal`
**Parent epic:** #874 — deprecate v1 UI (AppShell + `components/`)
**Scope:** research spike. No code changes.

---

## TL;DR

- **No telemetry exists.** No analytics SDK, no per-request access log, no usage counters. The single line that *could* surface `?ui=v1` is `logger.debug("request: %s %s …")` in `web/server.py:1325` — gated to DEBUG level, which is OFF by default.
- **`?ui=v1` is read in exactly one place:** `frontend/src/lib/stores/ui-version.svelte.ts:initUiVersion()`. It writes `'v1' | 'v2'` to localStorage and routes `App.svelte` between `<AppShell />` (v1) and `<RadioLayoutV2 />` (v2).
- **No prior deprecation notice has shipped.** v0.15.1 (2026-04-10) announced *"v2 is now default; use `?ui=v1` to opt back"* — that is a fallback, not a deprecation. v0.16–v0.19 ship no v1-related notice.
- **Recommendation:** drop `?ui=v1` outright in v0.20 alongside the v1 layout removal. The compatibility-window argument from epic #874 is moot once #1216 deletes `AppShell`. Add a one-line `console.warn` in the simplified `ui-version` shim (or in `App.svelte`) for users with bookmarked `?ui=v1` URLs.

---

## 1. Telemetry inventory

### Frontend (`frontend/src/`)

| Surface | Result |
|---|---|
| Analytics SDKs (PostHog, Plausible, GA, Mixpanel, Amplitude, Umami, Matomo, Fathom, Hotjar, Segment, Sentry) | **None.** Only transitive match is `workbox-google-analytics@7.4.0` inside `pnpm-lock.yaml` / `package-lock.json` — pulled in by Workbox (service-worker offline), unused at runtime. |
| Custom event sinks / `navigator.sendBeacon` / `fetch('/api/telemetry')` etc. | **None.** |
| `lib/utils/`, `lib/stores/` | No analytics module. |

### Server (`src/icom_lan/`)

| Surface | Result |
|---|---|
| Web framework | None — custom `asyncio.start_server` (`web/server.py:952`). No aiohttp, FastAPI, Starlette, Flask, hence no built-in `AccessLogger` middleware. |
| Per-request log line | One: `logger.debug("request: %s %s from %s:%s", method, _redact_token_in_path(path), peer[0], peer[1])` — `web/server.py:1325`. The `path` argument *does* include the query string (`_redact_token_in_path` only redacts `?token=`, leaves `?ui=v1` intact). |
| Effective level | **DEBUG, off by default.** `cli.py:2929-2933` configures the root logger at INFO unless `ICOM_DEBUG=1` is set. The default rotating file log at `logs/icom-lan.log` (`cli.py:2902-2923`) inherits that level. So `request:` lines are *not* persisted in production. |
| Audit log | `--audit-log PATH` exists for `serve` (rigctld) only — records CI-V commands, not HTTP requests. Irrelevant here. |

### Conclusion

There is no historical signal for `?ui=v1` usage and no infrastructure that *could* be queried retroactively. Adding it would require new instrumentation, which #1215 explicitly excludes ("Out of scope: adding new telemetry instrumentation").

---

## 2. `?ui=v1` URL handling — code path

```
URL ?ui=v1
  └─ frontend/src/App.svelte:30           initUiVersion() called in onMount
       └─ frontend/src/lib/stores/ui-version.svelte.ts:22-44
            ├─ URLSearchParams → 'v1' | 'v2' | null
            ├─ if param: setUiVersion(param) → localStorage write + state set
            ├─ else: read localStorage
            └─ else: default 'v2'
  └─ App.svelte:72   uiVersion = $derived(getUiVersion())
  └─ App.svelte:90-94
        {#if uiVersion === 'v2'}  <RadioLayoutV2 />
        {:else}                    <AppShell />          ← v1 path
```

Other consumer:

- `components-v2/layout/KeyboardHandler.svelte:65` — early-returns when `getUiVersion() !== 'v2'`. (Will go away with #1218.)

That is the entire surface. No other module reads `?ui=`.

---

## 3. Active users assessment

- **Project shape:** self-hosted local web UI for ham radios. Single-binary `icom-lan web` invoked on a LAN; the only "users" are the operator and (occasionally) other operators on the same LAN. No public deployment.
- **Distribution:** `pip install icom-lan` from PyPI; no central web entry point that could observe usage.
- **Default since 2026-04-10 (v0.15.1):** v2. Anyone installing v0.15.1+ fresh has never seen v1 unless they explicitly typed `?ui=v1`.
- **Persisted opt-in:** localStorage retains the v1 choice across sessions for users who actively flipped to v1 *before* v0.15.1, or who hit `?ui=v1` after.
- **Estimate:** unknown, almost certainly very low. The single confirmed user is the project author. There is no community signal in issues/PRs that anyone uses v1 deliberately.

---

## 4. Deprecation-notice status

Epic #874 explicitly requires:

> single release that adds the **deprecation notice** + `?ui=v1` fallback BEFORE the release that removes v1 code.

Audit of `CHANGELOG.md`:

- **v0.15.1 (2026-04-10):** announced *"Web UI v2 is now the default layout … switch manually with `?ui=v1` or `?ui=v2`."* This is an opt-in for v1, not a deprecation notice for v1.
- **v0.16.0 – v0.19.0:** no v1-related entries.
- **`[Unreleased]` (v0.20 candidate):** no v1-related entries yet.

**No deprecation notice has shipped.** The epic's own staging plan ("one release window") has not started.

---

## 5. Recommendation

**Drop the `?ui=v1` fallback in v0.20 together with the v1 layout removal (#1216 + #1217).**

Reasoning:

1. **Zero evidence of active use.** No telemetry to consult, no community signal, single-user project per author. Maintaining a fallback for an unmeasurable user base is speculative.
2. **The fallback becomes meaningless once #1216 deletes `AppShell`.** Even if `?ui=v1` is read, there is no v1 component to mount. Keeping the URL parameter alive only to be silently ignored is dead code with negative documentation value.
3. **The "one release window" is small in absolute terms.** v0.19 just shipped (2026-04-29). Forcing a v0.20-only deprecation window followed by v0.21 removal adds ~2 weeks for a benefit that cannot be measured. Not worth the coordination overhead.
4. **CHANGELOG announcement is sufficient.** The v0.20 release notes can call out the removal explicitly: "Removed: legacy v1 UI (`AppShell`, `components/layout/*`) and the `?ui=v1` URL fallback. v2 is the only UI." That is the realistic substitute for telemetry on a self-hosted tool.

### Alternative (lower confidence)

If the maintainer wants strict adherence to epic #874's compatibility-window language: keep `?ui=v1` as a **read-and-ignore** in v0.20 (one release), then strip in v0.21. This gives one full release where bookmarked URLs continue to load *something* (v2) without breaking. Cost: ~5 LOC (read param, log warn, ignore). I do not recommend this — see point 2.

---

## 6. Implications for #1217 (App.svelte unconditional `<RadioLayoutV2 />`)

#1217 should:

- **Mount `<RadioLayoutV2 />` unconditionally.** No `?ui=v1` escape hatch (no v1 to escape to).
- **Simplify `lib/stores/ui-version.svelte.ts` aggressively or delete it.** `KeyboardHandler.svelte:65` and any other `getUiVersion() !== 'v2'` guards (covered by #1218) become unreachable; remove them.
- **Optional one-line `console.warn`** in `App.svelte` `onMount` if `new URLSearchParams(window.location.search).get('ui') === 'v1'` — surfaces *why* the page didn't render v1 for users with stale bookmarks. Cost: 3 lines, no runtime impact, gone in v0.21.
- **Do not introduce a redirect** stripping `?ui=v1` from the URL. Unnecessary; it just gets ignored.

---

## 7. Acceptance checklist for #1215

- [x] Inventoried all telemetry / logging surfaces that could capture `?ui=v1`.
- [x] If data exists: report query results + sample size + time window. — N/A, no data.
- [x] If no data exists: explicitly document the gap and confirm time-based deprecation is the chosen path. — done above.
- [x] Markdown report committed.
- [x] `uv run pytest tests/ -q --tb=short` zero failures (no behavior change).
- [x] `uv run ruff check src/ tests/` zero violations (no behavior change).

---

## Appendix — file references

| File | Purpose |
|---|---|
| `frontend/src/lib/stores/ui-version.svelte.ts` | Reads `?ui=`, writes localStorage, exposes `getUiVersion()`. |
| `frontend/src/lib/stores/__tests__/ui-version.test.ts` | URL precedence, localStorage fallback, invalid-value handling. |
| `frontend/src/App.svelte:30, 72, 90-94` | Calls `initUiVersion()`, derives `uiVersion`, branches between `<RadioLayoutV2 />` and `<AppShell />`. |
| `frontend/src/components-v2/layout/KeyboardHandler.svelte:65` | v1 early-return guard. |
| `src/icom_lan/web/server.py:952, 1267-1307, 1325` | Custom asyncio HTTP server, request parser, single DEBUG-level access log line. |
| `src/icom_lan/cli.py:2867-2933` | Default INFO log level + rotating file log defaults. |
| `CHANGELOG.md:525-530` | v0.15.1 entry — v2 default + `?ui=v1` fallback announcement. |
