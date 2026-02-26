# icom-lan — Документация проекта

## Цель

Создать Python-библиотеку для прямого управления трансиверами Icom по LAN (UDP), без промежуточного ПО (wfview, RS-BA1, hamlib).

### Задачи
- Подключение к Icom по сети (аутентификация, keep-alive)
- Отправка/приём CI-V команд (частота, режим, мощность, метры)
- Приём/передача аудиопотока (Opus)
- Простой Pythonic API (sync + async)
- Поддержка IC-7610, IC-705, IC-7300, IC-9700

### Не-цели (пока)
- GUI
- Полная замена wfview
- Поддержка USB/serial (для этого есть hamlib)

## Архитектура

```
┌─────────────────────────────────────────────┐
│                 icom-lan                     │
│                                             │
│  ┌───────────┐  ┌──────────┐  ┌──────────┐ │
│  │ Transport │  │   CIV    │  │  Audio   │ │
│  │  (UDP)    │  │ Commands │  │ (Opus)   │ │
│  └─────┬─────┘  └────┬─────┘  └────┬─────┘ │
│        │             │             │        │
│  ┌─────┴─────────────┴─────────────┴─────┐  │
│  │         IcomRadio (public API)        │  │
│  └──────────────────┬────────────────────┘  │
│                     │                       │
│  ┌──────────────────┴────────────────────┐  │
│  │    rigctld TCP Server (:4532)         │  │
│  │    (Hamlib NET rigctl compatible)     │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
                     │ UDP
                     ▼
            ┌─────────────────┐
            │   Icom Radio    │
            │  192.168.x.x    │
            │  :50001 control │
            │  :50002 ci-v    │
            │  :50003 audio   │
            └─────────────────┘
```

## Протокол Icom LAN (по материалам wfview)

### Обзор
Icom использует проприетарный UDP-протокол для LAN-подключения. Не документирован официально. Полностью реверс-инжиниринг выполнен командой wfview.

### Порты
| Порт | Назначение |
|------|-----------|
| 50001 | Control — аутентификация, управление соединением |
| 50002 | CI-V Serial — проброс CI-V команд |
| 50003 | Audio — двунаправленный аудиопоток (Opus) |

### Фазы соединения
1. **Discovery** — опционально, поиск радио в сети
2. **Login** — отправка credentials (username/password)
3. **Auth** — получение токена/подтверждения
4. **Keep-alive** — периодический пинг (~500ms), иначе радио дропает соединение
5. **CI-V** — отправка/приём CI-V команд через UDP-обёртку
6. **Audio** — стриминг аудио (Opus кодек, 8/16/24 kHz)
7. **Disconnect** — корректное закрытие

### Структура пакета
Каждый UDP-пакет имеет заголовок фиксированного формата (см. `packettypes.h` в wfview):
- Длина пакета (2 байта, LE)
- Тип пакета (2 байта)
- Sequence number (2 байта)
- Sender ID (4 байта)
- Receiver ID (4 байта)
- Payload (переменная длина)

### Ключевые исходники wfview (reference)
| Файл | Строк | Описание |
|------|-------|----------|
| `include/packettypes.h` | 684 | Структуры пакетов, константы типов |
| `src/radio/icomudpbase.cpp` | 585 | Базовый UDP: подключение, keep-alive, retransmit |
| `src/radio/icomudphandler.cpp` | 690 | Основной хендлер: login, auth, маршрутизация |
| `src/radio/icomudpcivdata.cpp` | 248 | CI-V данные через UDP |
| `src/radio/icomudpaudio.cpp` | 303 | Аудио-стриминг |
| `src/radio/icomcommander.cpp` | 3533 | CI-V команды (частота, режим, метры и т.д.) |
| `src/rigcommander.cpp` | 256 | Высокоуровневый интерфейс к радио |
| **Итого** | **~6300** | |

## Этапы разработки

### Фаза 1 — Transport (MVP) ✅ COMPLETE
**Цель:** Установить UDP-соединение с радио, пройти аутентификацию, поддерживать keep-alive.

- [x] Разобрать формат пакетов из `packettypes.h`
- [x] Реализовать UDP transport (asyncio)
- [x] Discovery handshake (Are You There → I Am Here → Are You Ready)
- [x] Login + auth handshake
- [x] Token acknowledgement
- [x] Conninfo exchange (получить CI-V/audio ports)
- [x] Dual-port architecture (control port 50001 + CI-V port 50002)
- [x] Keep-alive loop (ping + retransmit)
- [x] Корректный disconnect
- [x] Тест: подключиться к IC-7610 на 192.168.55.40

**Результат:** `radio.connect()` / `radio.disconnect()` работают. ✅

### Фаза 2 — CI-V Commands ✅ COMPLETE
**Цель:** Отправлять и принимать CI-V команды через сетевое соединение.

- [x] Обёртка CI-V в UDP-пакеты (по `icomudpcivdata.cpp`)
- [x] Открытие CI-V data stream (OpenClose packet)
- [x] Фильтрация waterfall/echo packets
- [x] Базовые команды: get/set frequency, mode, power
- [x] Чтение метров: S-meter, SWR, ALC, power
- [x] PTT on/off
- [x] Тест: считать и установить частоту IC-7610

**Результат:** `radio.get_frequency()`, `radio.get_mode()`, `radio.get_s_meter()` работают. ✅

### Фаза 3 — Audio Streaming
**Цель:** Принимать и передавать аудио.

- [ ] Opus decode (приём аудио с радио)
- [ ] Opus encode (передача аудио на радио)
- [ ] Callback API для аудио
- [ ] Буферизация и управление потоком

**Результат:** `radio.audio.start_rx(callback)`, `radio.audio.tx(data)` работают.

### Фаза 4 — Polish & Publish
**Цель:** Готовая библиотека для PyPI.

- [ ] Sync + async API
- [ ] Autodiscovery радио в сети
- [ ] Поддержка нескольких моделей (IC-7610, IC-705, IC-7300, IC-9700)
- [ ] CLI-утилита (`icom-lan status`, `icom-lan freq 14074000`)
- [ ] Документация, примеры
- [ ] PyPI публикация

## Тестовое оборудование

- **Icom IC-7610** на `192.168.55.40`
- Порты: 50001 (control), 50002 (serial), 50003 (audio)
- Mac mini M4 Pro в той же LAN (`192.168.55.152`)

## Лицензионные заметки

- wfview: **GPLv3** — используем только как reference для понимания протокола
- Наш код: **MIT** — чистая независимая реализация, не copy-paste
- Не копируем код wfview, только изучаем формат пакетов и логику протокола
- Это легально: реверс-инжиниринг протокола для совместимости защищён законом (EU Directive 2009/24/EC, US DMCA interoperability exception)
