# Менеджер матчей (`manager/`)

Node 20+ / TypeScript. Один процесс: HTTP API, шлюз WS→UDP (`gateway/`) и по одному `ioq3ded` на матч.

```bash
cd gateway && npm ci && npx tsc -p . && cd ../manager && npm ci && npx tsc -p . && npx vitest run
ARENA_SECRET=... ARENA_RESULT_URL=http://127.0.0.1:4001/api/pvp/arena-result/ node dist/index.js
```

## Переменные окружения

| Переменная | По умолчанию | |
|---|---|---|
| `ARENA_SECRET` | — (обязательна, ≥16 символов) | заголовок `X-Arena-Secret` для API; ключ HMAC результата |
| `ARENA_RESULT_URL` | пусто — только журнал | куда POST'ить результат (Evennia) |
| `ARENA_RESULT_SECRET` | = `ARENA_SECRET` | отдельный ключ HMAC, если нужен |
| `ARENA_LISTEN` | `127.0.0.1:27950` | API |
| `ARENA_GATEWAY_LISTEN` | `127.0.0.1:27961` | шлюз; nginx: `/arena-ws/` → сюда. Для LAN-теста `0.0.0.0:27961` |
| `ARENA_PORTS` | `27960-27979` | UDP-порты матчей (слушают 127.0.0.1) |
| `ARENA_MAX_MATCHES` | `4` | одновременных матчей |
| `ARENA_IOQ3DED` | `build-native/Release/ioq3ded` | |
| `ARENA_BASEPATH` / `ARENA_BASEGAME` | `content/openarena` / `baseoa` | |
| `ARENA_MAPS_DUEL` | `czest1tourney,pul1duel-oa,oa_dm7,am_lavaarena` | белый список карт |
| `ARENA_MAPS_FFA` | `oa_dm4,czest1dm,oa_dm1` | |
| `ARENA_STATE_DIR` | `manager/state` | `matches/<id>/` (homepath, `match.cfg`, `console.log`, `games.log`), `results.jsonl` |

## API

```http
POST /matches                      (X-Arena-Secret)
{ "match_id": "pvp-123", "mode": "duel" | "ffa", "map": "oa_dm7",
  "players": [{"ticket": "…", "name": "Арн"}, …],
  "rules": { "fraglimit": 10, "timelimit": 10, "arsenal": "full", "instagib": false,
             "powerups": true, "items": true, "warmup": 10, "bots": 0 } }
→ 201 { "port": 27963, "ws_path": "/arena-ws/27963", "expires_at": "…" }
→ 400 { "error": "…" }   неверный запрос (карта не из списка, билет не [A-Za-z0-9_-]{1,63}, …)
→ 409 матч с таким id уже идёт · 503 все арены заняты / нет порта · 401 нет секрета

GET  /matches                      отладка: состояние, кто на арене, результат
POST /matches/<id>/cancel          → результат с reason=cancelled
GET  /health                       без секрета
```
Правила по умолчанию: дуэль 10/10, разминка 10; бойня 20/12, разминка 15. В `rules` можно
передать только часть полей. Дуэль — ровно 2 участника (люди и NPC), без безымянных ботов; бойня —
от 2 участников, участников + `rules.bots` ≤ 8. Хотя бы один участник — человек.

**NPC-бойцы Пангеи** (часть F4) — именованные боты, запись без билета:
```json
"players": [{"ticket": "…", "name": "Арн"},
            {"npc": true, "name": "Кер", "bot": {"model": "sarge", "skill": 3}}]
```
- `model` — только `sarge | grism | kyonshi` (их модели есть в тонком паке браузера), `skill` 1–5.
- Имя в игре — транслит (`Кер` → `Ker`, `Щука Старый` → `ShchukaStaryy`, ≤ 15 знаков, повтор
  получает цифру: `Ker2`): шрифты движка без кириллицы.
- `g_pangea_tickets` — только билеты людей; `g_pangea_bots` = число NPC + `rules.bots`.

`expires_at` — до этого момента все билеты должны войти (3 мин).

## Результат

`POST $ARENA_RESULT_URL`, заголовок `X-Arena-Signature: hex(HMAC-SHA256(тело, ключ))`:
```json
{ "match_id": "pvp-123", "mode": "duel", "reason": "fraglimit",
  "duration_s": 431,
  "places": [{"ticket": "…", "score": 10, "place": 1}, {"ticket": "…", "score": 7, "place": 2}],
  "left_early": [] }
```
С NPC в `places` есть строки без билета: `{"npc": true, "name": "Кер", "score": 3, "place": 1}`, а в
итоге — таблица имён `"npc_names": {"Ker": "Кер"}`. NPC никогда не попадает в `left_early`.

| `reason` | Когда | `places` |
|---|---|---|
| `fraglimit`, `timelimit` | `Exit:` в логе сервера | по табло; ушедшие и не пришедшие — последние |
| `no_show` | дуэль: не пришёл за 3 мин; бойня: за 3 мин пришло < 2 | пришедшие — 1-е место, остальные — последние |
| `forfeit` | **новое**: дуэль — соперник вышел и не вернулся за 30 с; бойня — вышли все | оставшиеся — 1-е, ушедшие — последние |
| `crash` | сервер умер без `Exit:` или превысил срок жизни | пусто |
| `cancelled` | `POST /matches/<id>/cancel` или остановка менеджера | пусто |

- Равный счёт — одно место. Безымянные боты (`rules.bots`) в `places` не попадают; NPC-боты
  попадают — их строка `score:` сопоставляется по имени (цветовые коды `^N` отбрасываются; запасной
  источник имени — `ClientUserinfoChanged`).
- Дуэль с NPC: человек не пришёл — `no_show` (NPC на 1-м месте, человек в `left_early`; Пангея
  такой матч не засчитывает — не пришёл ни один человек); человек вышел и не вернулся — `forfeit`
  в пользу NPC.
- `duration_s` — от конца разминки (map_restart) до конца матча.
- Доставка: 2xx — готово; 4xx (кроме 408/429) — Pangea отказала, не повторяем; иначе повтор
  5 с, 10 с, 20 с … (не чаще раза в 5 мин) в течение часа. Журнал — `state/results.jsonl`,
  после перезапуска менеджер досылает недоставленное.

## Как устроен матч

- Командная строка `ioq3ded` — только стартовые cvar'ы, `+exec match.cfg`, `+map`: движок
  принимает не больше 32 команд `+…`, лишние молча отбрасывает (так терялся `+map`).
  Все правила — в `state/matches/<id>/baseoa/match.cfg`.
- Консоль `ioq3ded` без tty пишет в **stderr** — менеджер читает оба потока.
- Бойня: сервер стартует с `g_warmup 3600` (держит разминку); когда вошли все билеты или прошло
  3 мин и вошло ≥ 2 — менеджер пишет в консоль `g_warmup <warmup>`, отсчёт начинается заново.
- Боты: после первого `InitGame` менеджер пишет `addbot <model> <skill> free 0 <латинское имя>`
  для каждого NPC, затем `addbot sarge|grism|kyonshi 3` для безымянных ботов бойни.

## systemd

`manager/systemd/pangea-arena-manager.service`, переменные — в `manager/arena.env` (не в git):
```bash
sudo cp manager/systemd/pangea-arena-manager.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now pangea-arena-manager
journalctl -u pangea-arena-manager -f
```
