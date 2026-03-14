# Epic #169: Frontend & API Audit — Priority Order

## 🔴 P0 (Critical - Start Here)
1. **#231** — bug: set_squelch command name mismatch (5 min fix)
2. **#232** — bug: set_att parameter mismatch (5 min fix)
3. **#241** — resilience: PTT button timeout protection (30 min)

## 🟠 P1 (High Priority - Do Next)
4. **#233** — bug: Waterfall double-rendering (1 hour)
5. **#234** — bug: WS command responses not handled (30 min)
6. **#236** — arch: Replace triple HTTP polling with WS state push (2-3 hours, BLOCKS #237)
7. **#237** — arch: Reduce WebSocket connections (1 hour, requires #236)
8. **#249** — arch: Eliminate hardcoded IC-7610 (capabilities-driven UI) (2 hours)
9. **#240** — resilience: XHR polling error backoff (1 hour)
10. **#242** — resilience: Stale state detection (30 min, requires #240)

## 🟡 P2 (Medium Priority)
11. **#235** — bug: BottomBar audioManager.onChange leak (15 min)
12. **#239** — bug: Optimistic update frequency snap (30 min)
13. **#238** — arch: Remove Connection:close (15 min)
14. **#243** — resilience: Coordinate Audio/Control WS state (1 hour, requires #236)
15. **#244** — resilience: App.svelte limit reload retries (15 min)
16. **#245** — improve: Set Vite build.target (5 min)
17. **#246** — improve: Pause RAF loop (30 min)
18. **#250** — improve: Wire up missing UI panels (3-4 hours, requires #249)

## 🔵 P3 (Low Priority - Nice to Have)
19. **#247** — improve: Add basic LAN authentication (2 hours)
20. **#248** — improve: State delta / ETag 304 (2 hours, requires #236)

---

## 🎯 Recommended Sprint 1 (Quick Wins)
**Goal:** Fix all P0 + easy P1 bugs (4-5 hours total)

1. #231 (5 min) — squelch name
2. #232 (5 min) — att param
3. #241 (30 min) — PTT timeout
4. #233 (1 hour) — waterfall double-render
5. #234 (30 min) — WS error handling
6. #240 (1 hour) — XHR backoff
7. #242 (30 min) — stale state
8. #235 (15 min) — listener leak
9. #239 (30 min) — freq snap

**Total:** ~4.5 hours, **9 issues closed**.

---

## 🎯 Sprint 2 (Architecture)
**Goal:** WS state push + capabilities-driven UI (5-6 hours)

1. #236 (2-3 hours) — WS state push
2. #237 (1 hour) — reduce WS conns
3. #249 (2 hours) — capabilities-driven UI
4. #243 (1 hour) — WS coordination

**Total:** ~6 hours, **4 issues closed**.

---

## 🎯 Sprint 3 (Improvements)
**Goal:** Remaining P2/P3 features

1. #238 (15 min) — Connection keepalive
2. #244 (15 min) — reload retries
3. #245 (5 min) — Vite target
4. #246 (30 min) — RAF pause
5. #250 (3-4 hours) — wire up panels
6. #247 (2 hours) — auth
7. #248 (2 hours) — state delta

**Total:** ~8 hours, **7 issues closed**.

---

## 📊 Summary
- **Sprint 1:** 9 issues, 4.5 hours (quick wins)
- **Sprint 2:** 4 issues, 6 hours (architecture)
- **Sprint 3:** 7 issues, 8 hours (polish)
- **Total:** 20 issues, ~18 hours

---

**Created:** 2026-03-13
**Epic:** #169
**Issues:** #231-#250
