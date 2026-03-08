# UI Architecture Research — Desktop + Mobile

**Date:** 2026-03-07
**Author:** Жора
**Status:** Draft / Research

## Проблема

Текущий UI — **2731 строк в одном `index.html`**: 165 функций, 42 event handler'а, ~100KB. HTML + CSS + JS в одном файле. Это работало для MVP, но дальше масштабировать невозможно:

- Нет компонентной архитектуры — каждая новая фича = ещё 50-100 строк в один файл
- Нет переиспользования — VFO display, meters, spectrum дублируют логику
- Mobile layout потребует значительного рефакторинга CSS и JS
- Нет type safety — plain JS, баги находятся только в runtime
- Нет тестов для UI-логики

## Конкуренты: как устроены radio web UI

### OpenWebRX+ (Python + vanilla JS)
- **Архитектура:** Python backend, vanilla JS frontend, WebSocket
- **UI:** Один большой JS файл с Canvas waterfall
- **Плюсы:** Самый популярный open-source web SDR, хороший waterfall
- **Минусы:** Монолитный JS, сложно расширять, нет мобильной адаптации из коробки
- **Масштаб:** ~15K строк JS

### Web Radio Control (webradiocontrol.tech)
- **Архитектура:** Коммерческий, закрытый исходник
- **UI:** Чистый, минималистичный, responsive
- **Фичи:** Spectrum + waterfall, VFO dial для touch, multi-user, reservation system
- **Заметки:** Лучший UX среди ham radio web UI. Референс для дизайна

### Universal HamRadio Remote HTML5 (F4HTB)
- **Архитектура:** Python + HTML5/JS
- **UI:** Функциональный, но визуально устарел
- **Плюсы:** Open source, работает с любым hamlib-совместимым радио
- **Минусы:** Дизайн ~2020, не responsive

### SparkSDR
- **Архитектура:** Cross-platform (Electron/native)
- **UI:** Нативный look, waterfall, multi-receiver
- **Заметки:** Не web-based в первую очередь, но есть API

### wfview (Qt/C++)
- **Архитектура:** Qt desktop app, не web
- **UI:** Desktop-only, полный контроль IC-7610
- **Заметки:** Референс по функциональности, но не по web UI

## Варианты фреймворка

### Вариант A: Vanilla JS (улучшенный)

Оставить текущий подход, но разбить на модули через ES modules.

```
static/
├── index.html          (shell, CSS)
├── js/
│   ├── app.js          (entry point)
│   ├── vfo.js          (VFO display + control)
│   ├── spectrum.js     (spectrum + waterfall Canvas)
│   ├── meters.js       (S-meter, SWR, power)
│   ├── controls.js     (band, mode, filter selectors)
│   ├── audio.js        (WebSocket audio, mic)
│   ├── dx-cluster.js   (DX spot overlay)
│   ├── toast.js        (notification system)
│   └── ws.js           (WebSocket connection manager)
```

| Плюс | Минус |
|------|-------|
| Нет build step | Нет реактивности — ручной DOM manipulation |
| Нулевые зависимости | Нет type safety |
| Текущий код переносится почти as-is | Компонентная модель — самодельная |
| Один файл bundle возможен через concat | Растёт в спагетти с масштабом |
| **Self-hosted, zero CDN** | |

**Effort:** M (2-3 дня). Рефакторинг, не переписывание.

### Вариант B: Svelte 5

Компиляторный фреймворк. Пишешь компоненты → компилируется в чистый JS. Нет runtime (как React/Vue).

```
frontend/
├── src/
│   ├── App.svelte          (root layout)
│   ├── components/
│   │   ├── VfoDisplay.svelte
│   │   ├── Spectrum.svelte
│   │   ├── Waterfall.svelte
│   │   ├── SMeter.svelte
│   │   ├── BandSelector.svelte
│   │   ├── ModeSelector.svelte
│   │   ├── PttButton.svelte
│   │   ├── DxCluster.svelte
│   │   └── Toast.svelte
│   ├── stores/
│   │   ├── radio.ts        (reactive state)
│   │   └── websocket.ts    (WS connection)
│   └── lib/
│       ├── spectrum-renderer.ts
│       └── audio-engine.ts
├── package.json
├── vite.config.ts
└── tsconfig.json
```

| Плюс | Минус |
|------|-------|
| Compile-time → маленький bundle (~15-30KB) | Build step (npm/pnpm) |
| TypeScript из коробки | Новый язык/фреймворк для контрибьюторов |
| Реактивный state без boilerplate | Node.js зависимость для разработки |
| Scoped CSS в каждом компоненте | Spectrum/waterfall всё равно Canvas (переносится) |
| Идеален для embedded/dashboard | |
| **Ближе к vanilla JS** чем React | |

**Bundle size:** ~20KB gzip (Svelte) vs ~45KB (React) vs ~30KB (Vue)

**Effort:** L (5-7 дней). Полное переписывание, но с чёткой структурой.

### Вариант C: React + TypeScript

Самый популярный фреймворк, огромная экосистема.

| Плюс | Минус |
|------|-------|
| Огромная экосистема | Тяжёлый runtime (~45KB min) |
| Много UI библиотек (Radix, shadcn) | Virtual DOM overhead |
| TypeScript нативно | Boilerplate (hooks, useEffect, memo) |
| Легко найти разработчиков | Overkill для embedded UI |

**Effort:** L (5-7 дней).

### Вариант D: Preact + HTM (компромисс)

Preact = React API, но 3KB. HTM = JSX без build step.

```html
<script type="module">
  import { h, render } from 'https://esm.sh/preact';
  import { useState } from 'https://esm.sh/preact/hooks';
  import htm from 'https://esm.sh/htm';
  const html = htm.bind(h);
  
  function VfoDisplay({ freq, mode }) {
    return html`<div class="vfo">${freq} ${mode}</div>`;
  }
</script>
```

| Плюс | Минус |
|------|-------|
| 3KB runtime | Маленькая экосистема |
| React-совместимый API | Меньше инструментов |
| Можно без build step (ESM) | Нет scoped CSS |
| TypeScript опционально | HTM синтаксис менее удобен чем JSX |

**Effort:** M (3-4 дня).

## Рекомендация

### Ближайший шаг: Вариант A (Vanilla JS модули)

**Почему:**
1. **Нулевой risk** — нет новых зависимостей, build tools, CDN
2. **Быстрый** — 2-3 дня на рефакторинг
3. **Обратно совместимо** — тот же HTML, тот же server, `python -m icom_lan` просто работает
4. **Self-contained** — один Python пакет, без `npm install`
5. **Mobile layout** можно добавить media queries без фреймворка

**План:**
1. Разбить `index.html` на ES-модули (`<script type="module">`)
2. Каждый модуль — один UI concern (VFO, spectrum, meters, controls, audio, WS)
3. Shared state через простой EventBus или pub/sub
4. CSS остаётся в `index.html` (или выносится в `styles.css`)
5. Добавить responsive media queries для `<768px`

### Следующий этап (если vanilla станет тесно): Вариант B (Svelte)

**Когда переходить:**
- Если UI вырастет до 5000+ строк
- Если нужны сложные интерактивные компоненты (settings panel, memory manager)
- Если появятся внешние контрибьюторы, которым нужен type safety

**Как мигрировать:**
- Canvas-рендеринг (spectrum, waterfall) переносится 1:1 — это чистый JS
- WS-логика переносится в Svelte store
- Каждая JS-функция → Svelte компонент
- Build: `vite build` → single `bundle.js` → встраивается в Python пакет

## Mobile UI

Независимо от фреймворка, мобильный UI требует:

### Обязательно (Phase 1)
- [ ] Responsive CSS (`@media (max-width: 768px)`)
- [ ] Touch-friendly кнопки (min 44x44px tap targets)
- [ ] Stacked layout (вертикальный)
- [ ] Compact VFO display
- [ ] Спектр/waterfall ~30% экрана с fullscreen toggle
- [ ] Grouped dropdowns (BAND, MODE, FILTER, FEATURES)
- [ ] Fixed bottom bar (audio toggle + PTT)

### Желательно (Phase 2)
- [ ] Swipe-to-tune на VFO display
- [ ] Tap-to-tune на waterfall
- [ ] Hold-to-talk PTT
- [ ] PWA manifest + icons
- [ ] Service Worker для offline shell
- [ ] Haptic feedback (navigator.vibrate)

### Desktop улучшения
- [ ] Resizable panels (spectrum vs controls)
- [ ] Keyboard shortcuts (freq input, band switching)
- [ ] Dark/light theme toggle
- [ ] Multi-VFO view (MAIN + SUB side-by-side)
- [ ] Settings panel (audio, connection, display preferences)

## Файловая структура после рефакторинга (Вариант A)

```
src/icom_lan/web/static/
├── index.html              # Shell: HTML structure + CSS
├── js/
│   ├── main.js             # Entry: init, WS connect, state
│   ├── ws-client.js        # WebSocket manager + reconnect
│   ├── state.js            # Reactive state store (EventBus)
│   ├── vfo.js              # VFO display, frequency formatting
│   ├── spectrum.js         # Spectrum canvas renderer
│   ├── waterfall.js        # Waterfall canvas renderer
│   ├── meters.js           # S-meter, SWR, power bars
│   ├── controls.js         # Band/mode/filter/feature selectors
│   ├── audio.js            # Audio worklet, mic, PTT
│   ├── dx-cluster.js       # DX spot overlay + list
│   ├── toast.js            # Notification toasts
│   └── utils.js            # Helpers (BCD, formatting)
├── css/
│   ├── base.css            # Colors, typography, reset
│   ├── layout.css          # Grid/flex layout
│   ├── components.css      # Per-component styles
│   └── mobile.css          # @media <768px overrides
└── icons/                  # PWA icons (Phase 2)
```

## Effort Estimate

| Task | Effort | Depends on |
|------|--------|-----------|
| Split index.html → ES modules | 3-4 дня | — |
| Responsive CSS (mobile layout) | 2-3 дня | Split |
| Touch interactions (swipe, tap-to-tune) | 2-3 дня | Mobile CSS |
| PWA manifest + Service Worker | 0.5 дня | Mobile CSS |
| Desktop improvements (resize, shortcuts) | 2-3 дня | Split |
| **Total Phase 1 (basic mobile)** | **~8-10 дней** | |
| Svelte migration (Phase 2, optional) | 5-7 дней | Phase 1 complete |

## Решение

Предложение: начать с **Вариант A** (модульный vanilla JS) + responsive CSS. Это даёт:
- Работающий mobile UI за ~1 неделю
- Чистую кодовую базу для будущего рефакторинга
- Zero новых зависимостей
- Возможность мигрировать на Svelte потом, если понадобится

Svelte оставляем как запасной план на случай, если UI вырастет до уровня, где vanilla JS станет неуправляемым.
