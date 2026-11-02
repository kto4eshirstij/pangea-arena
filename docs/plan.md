# Pangea Arena — дуэль 1 на 1 на базе ioquake3 в браузере. План работ

Дата: 2026-11-02. Основа: `github.com/ioquake/ioq3` (ветка `main`, последний коммит 2026-10-12,
лицензия GPLv2). Проверено по исходникам: в движке есть **официальная веб-сборка через Emscripten**
(`cmake/platforms/emscripten.cmake`, `code/web/client.html.in`, `code/web/client-config.json`),
есть режим **standalone-игры** (`BUILD_STANDALONE`, `cmake/identity.cmake`, `code/qcommon/q_shared.h`)
и **встроенный режим турнира 1 на 1** (`g_gametype 1`, GT_TOURNAMENT в `code/game/`).

Чего в ioq3 **нет** и что придётся делать самим:
1. Сетевой транспорт для браузера. Веб-сборка не трогает `net_ip.c` — она полагается на эмуляцию
   сокетов Emscripten: UDP-датаграммы уходят как бинарные WebSocket-кадры на `ws://host:port`.
   На сервере нужен **шлюз WebSocket→UDP** перед обычным нативным `ioq3ded`. Так устроены и
   QuakeJS, и современный Q3JS (`q3js.com`), и quake-kube.
2. Свой контент: pak-файлы Quake 3 использовать нельзя. На этапах 0–3 временно берём ассеты
   **OpenArena** (GPLv2), на этапе 4 заменяем на свои.
3. Привязка к Pangea: кто с кем дерётся, вход по билету, возврат результата в Evennia, правила
   дуэли чести (шрам, карма). Это пишем сами — в приватном репо, вне GPL-части.

---

## Архитектура

```
Браузер игрока                      Ноутбук (pangea.pp.ua, 217.77.223.72)
┌──────────────────────┐            ┌─────────────────────────────────────────────┐
│ React-клиент Pangea  │ wss /ws    │ Evennia (портал/сервер, Django)             │
│  вкладка «Арена»     │◄──────────►│   команда «арена», API /api/arena/*          │
│  ┌────────────────┐  │            │                     │ http 127.0.0.1:27950   │
│  │ ioquake3.wasm  │  │ wss        │ arena-manager (Node): матчи, билеты,         │
│  │ (ES-модуль)    │◄─┼───────────►│   WS→UDP шлюз, запуск ioq3ded на матч,       │
│  └────────────────┘  │ /arena-ws/ │   разбор лога, POST результата в Evennia     │
└──────────────────────┘            │                     │ udp 127.0.0.1:27960+N  │
                                    │ ioq3ded (native, standalone, g_gametype 1)   │
                                    └─────────────────────────────────────────────┘
```

Решения:
- **Два репозитория.** `kto4eshirstij/pangea-arena` — **публичный**, GPLv2: форк ioq3 + шлюз +
  менеджер матчей + исходники контента (map-файлы, текстуры, модели). `kto4eshirstij/pangea-mud` —
  приватный, как есть: команда «арена», Django-API, React-вкладка, nginx/systemd. Связь только по
  HTTP/WebSocket — GPL на приватную часть не распространяется.
- **Нативный `ioq3ded`**, не JS-сборка сервера (JS-сервер QuakeJS был в ~20 раз медленнее).
  Один процесс на один матч, `sv_maxclients 2`, живёт только пока идёт матч.
- **Наружу новых портов не открываем**: UDP-порты серверов слушают 127.0.0.1, шлюз
  проксируется nginx'ом по `wss://pangea.pp.ua/arena-ws/<port>` рядом с существующим `/ws`.
- Клиент встраивается в React как ES-модуль (сборка уже даёт `-sEXPORT_ES6`), отдельная вкладка
  интерфейса «Арена», полноэкранный canvas. Классический MUD-клиент не затрагивается.
- Паки раздаются как статика с хэшем в имени (`arena-<sha>.pk3`), кэш в браузере через IDBFS.

---

## Что менять в ioq3 (по файлам)

| Файл / область | Изменение | Этап |
|---|---|---|
| `cmake/identity.cmake` | PROJECT_NAME `pangea-arena`, SERVER_NAME `arena-ded`, CLIENT_NAME `arena`, BASEGAME `arena`, своя иконка, COPYRIGHT без id Software, PROTOCOL_HANDLER_SCHEME `pangea-arena` | 2 |
| `code/qcommon/q_shared.h` (блок `#ifdef STANDALONE`) | PRODUCT_NAME `Pangea Arena`, BASEGAME `arena`, HOMEPATH_NAME `PangeaArena`, GAMENAME_FOR_MASTER `pangea-arena` | 2 |
| `code/web/client.html.in` | заменить на минимальную страницу-обёртку для отладки; для продакшена React сам импортирует `arena.js` | 1, 3 |
| `code/web/client-config.json` | только наш `arena/arena-<sha>.pk3` + `vm/*.qvm`; секции baseq3/missionpack/demoq3/tademo убрать | 0, 4 |
| `cmake/platforms/emscripten.cmake` | добавить `-sWEBSOCKET_SUBPROTOCOL=binary`, `-lidbfs.js`, при необходимости `-sWEBSOCKET_URL`; `TOTAL_MEMORY` можно снизить до 128 МБ после замены контента | 1 |
| JS-обёртка (новый файл `web/arena-boot.js`) | `Module.websocket.url = (addr, port) => "wss://pangea.pp.ua/arena-ws/" + port`; монтирование IDBFS для кэша паков; передача аргументов `+connect`, `+set pangea_ticket`, `+set name`; пробрасывание событий «подключился/матч окончен» в React через `postMessage`/колбэк | 1, 3 |
| `code/game/g_client.c` (`ClientConnect`) | читать `pangea_ticket` из userinfo, сверять со списком в cvar `g_pangea_tickets` («t1,t2»), чужих отклонять; в лог `Pangea: ticket <t> -> client <n>`; запрет `callvote`, `team`-переходов, ботов | 2 |
| `code/game/g_main.c` (`LogExit`, `CheckExitRules`) | по окончании турнира писать в лог строку `Pangea: result <ticket_winner> <score_w>:<score_l> <reason>` и через `g_pangea_autoexit` завершать процесс (`quit`) | 2 |
| `code/game/bg_misc.c` (`bg_itemlist`) | названия оружия/предметов на русском под сеттинг (механика не меняется) | 4 |
| `code/cgame/cg_*.c`, `code/q3_ui/` | HUD-строки и меню: убрать Q3-брендинг, оставить минимум (подключение, табло, конец матча); меню «Multiplayer/Setup» не нужны — матч задаётся аргументами запуска | 4 |
| `code/game/ai_*.c`, `code/botlib/` | не собирать (`bot_enable 0`); на этапе 4 решить, выкидывать ли из сборки совсем | 4 |
| `code/client/cl_cin.c`, roq-ролики, `cl_keys` «~» | консоль игроку закрыть (`con_` cvar + `sv_pure 1`), ролики не нужны | 4 |
| `README.md`, `COPYING.txt` | README с упоминанием ioquake3 (как просит их README), ссылка на исходники в самом клиенте — обязательство GPL при раздаче wasm | 0 |

Пути ассетов в коде **не переименовываем**: cgame/ui ссылаются на `models/players/<model>/…`,
`sound/feedback/…`, `gfx/2d/…` и т.п. Дешевле положить **свои** файлы по тем же путям, чем править
сотни строк. Список обязательных путей получаем автоматически (этап 4.1).

---

## Этапы

### Этап 0. Форк, репозиторий, две сборки, OpenArena как временный контент (1–2 дня)

Цель: на ноутбуке собираются нативный сервер и веб-клиент, веб-клиент открывает карту OpenArena
локально (без сети) в браузере с Windows-компьютера.

```bash
# на ноутбуке
cd /home/gaskonec/muddev
git clone https://github.com/ioquake/ioq3.git pangea-arena && cd pangea-arena
git remote rename origin upstream
gh repo create kto4eshirstij/pangea-arena --public --source=. --remote=origin --push \
  --description "Pangea Arena: 1v1 duel client/server based on ioquake3 (GPLv2)"
git checkout -b develop

# зависимости
sudo apt-get install -y cmake build-essential libsdl2-dev python3 unzip
# Emscripten SDK
git clone https://github.com/emscripten-core/emsdk.git ~/emsdk
~/emsdk/emsdk install latest && ~/emsdk/emsdk activate latest
echo 'source ~/emsdk/emsdk_env.sh >/dev/null' >> ~/.bashrc && source ~/emsdk/emsdk_env.sh

# нативная сборка: сервер + QVM + инструменты q3lcc/q3asm
cmake -S . -B build-native -DCMAKE_BUILD_TYPE=Release -DBUILD_CLIENT=OFF -DBUILD_SERVER=ON \
  -DBUILD_GAME_QVMS=ON -DBUILD_GAME_LIBRARIES=OFF
cmake --build build-native -j"$(nproc)"

# веб-сборка клиента
emcmake cmake -S . -B build-web -DCMAKE_BUILD_TYPE=Release
cmake --build build-web -j"$(nproc)"
ls build-web/Release/   # ожидаем ioquake3.js, ioquake3.wasm, ioquake3.html, ioquake3-config.json
```

Задачи Claude Code на этапе:
1. ⛔ Проверить, собираются ли QVM в веб-сборке (q3lcc/q3asm — хост-инструменты). Если нет —
   брать `*.qvm` из `build-native` и класть рядом с паками; зафиксировать это в `docs/build.md`.
2. Скачать OpenArena 0.8.8 (`openarena.ws`, zip) во **временную** папку `content/openarena/`
   (в `.gitignore`), положить `baseoa/*.pk3` → `build-web/Release/baseq3/` (на этом этапе ещё
   под именем baseq3), поправить `client-config.json` под список pk3 OpenArena.
3. `python3 -m http.server 8080 --directory build-web/Release` → с Windows открыть
   `http://192.168.31.11:8080/ioquake3.html`, `\devmap oa_dm1` (или любая карта OA) — должно
   рендериться. Записать FPS и время загрузки.
4. README: кто мы, что это форк ioquake3, лицензия, как собрать. Коммит `arena: fork, build docs`.

### Этап 1. Сетевая связка: два браузера играют 1 на 1 по LAN (2–3 дня)

Цель: нативный `ioq3ded` на ноутбуке, шлюз WS→UDP, два браузера с Windows-компьютера (два
окна) подключаются и видят друг друга на карте.

1. `gateway/` (Node 20, TypeScript, пакет `ws`): слушает `ws://0.0.0.0:27961/<udp_port>`;
   каждый WS-клиент → свой UDP-сокет к `127.0.0.1:<udp_port>`; кадр WS ↔ датаграмма 1:1;
   таймаут простоя 60 с; лимит 2 соединения на порт (дуэль) + 2 запасных на реконнект.
2. ⛔ Выяснить точный формат эмуляции сокетов текущего Emscripten: подпротокол `binary`,
   нужен ли заголовок адреса в кадре (в старых версиях для UDP был), как задаётся
   `Module.websocket.url` функцией. Проверить на `emcc --version`, записать в `docs/network.md`.
3. Запуск сервера для теста:
   ```bash
   cd /home/gaskonec/muddev/pangea-arena
   ./build-native/Release/ioq3ded +set dedicated 1 +set net_ip 127.0.0.1 +set net_port 27960 \
     +set fs_basepath "$PWD/content/openarena" +set fs_game baseoa +set com_basegame baseoa \
     +set g_gametype 1 +set sv_maxclients 4 +set bot_enable 0 +set sv_pure 0 +map oa_dm1
   node gateway/dist/index.js --listen 27961 --udp-host 127.0.0.1
   ```
   В клиенте: `\connect 192.168.31.11:27960` (шлюз на том же номере порта, но TCP/WS —
   это самый простой вариант для эмуляции Emscripten; если URL задаётся функцией — порт шлюза
   любой).
4. Замерить пинг в игре (`\cg_lagometer 1`, `\cl_showping`), зафиксировать настройки:
   `sv_fps 40`, `snaps 40`, `cl_maxpackets 125`, `rate 90000`, `cl_timenudge 0`, `pmove_fixed 1`.
5. Коммит `arena: ws-udp gateway, LAN duel works`.

### Этап 2. Standalone-идентичность, билеты, менеджер матчей (3–5 дней)

1. Identity: `cmake/identity.cmake` + `q_shared.h` (таблица выше), `-DBUILD_STANDALONE=1` в обеих
   сборках; паки переезжают в каталог `arena/`. Убедиться, что `com_standalone` = 1 и никаких
   обращений к `authorize.quake3arena.com`/мастер-серверу (`sv_master1 ""`, `cl_motd 0`).
2. Игровой код: `g_pangea_tickets`, `pangea_ticket` в userinfo (клиент: `+set pangea_ticket X`
   с флагом userinfo — добавить cvar в `cl_main.c` как `CVAR_USERINFO`), отказ чужим
   («Это не ваша арена»), `g_pangea_autoexit 1` → после `Exit:` сервер пишет строку результата и
   выходит. Фиксированные правила дуэли: `fraglimit 10`, `timelimit 10`, `g_warmup 10`,
   `g_doWarmup 1`, `g_allowVote 0`, `g_forcerespawn 3`.
3. `manager/` (Node, тот же пакет, что и шлюз): HTTP на `127.0.0.1:27950`, только с заголовком
   `X-Arena-Secret` (общий секрет с Evennia в env):
   - `POST /matches {match_id, map, players:[{ticket,name,char_id},{…}], rules}` → выбирает
     свободный UDP-порт из пула 27960–27979, запускает `ioq3ded` с `+set g_pangea_tickets`,
     отвечает `{port, ws_url}`;
   - следит за stdout процесса: строки `Pangea: ticket…`/`Pangea: result…`, падения, зависший
     матч (нет подключения 3 мин → kill, результат `no_show`);
   - по завершении `POST <EVENNIA>/api/arena/result/` `{match_id, winner_ticket, score, reason,
     duration_s}` с HMAC-подписью; повтор с бэкоффом, если Evennia недоступна;
   - `GET /matches` — для отладки.
4. systemd-юнит `pangea-arena-manager.service` (User=gaskonec, Restart=always), менеджер сам
   поднимает шлюз. Логи в journald.
5. Тесты: `vitest` на разбор строк лога и жизненный цикл матча с фейковым `ioq3ded`
   (скрипт, печатающий ожидаемые строки). Коммит `arena: standalone identity, tickets, manager`.

### Этап 3. Интеграция с Pangea (≈ 1 неделя, приватный репо `pangea-mud`, ветка `feature/arena`)

1. Django-приложение `arena/`: модели `ArenaMatch` (id, вызвавший, принявший, карта, правила,
   билеты-хэши, статус, результат, created/started/finished), настройки `ARENA_MANAGER_URL`,
   `ARENA_SECRET` (в `secret_settings.py`).
2. Команда MUD «арена <персонаж>» → вызов; «арена принять» у второго → оба должны быть в одной
   комнате и в «одном времени» (проверка через `world/chrono`); создаётся матч, менеджеру
   уходит `POST /matches`, обоим клиентам OOB `arena_start {match_id, ws_url, port, ticket, name,
   paks:[…]}`; в классическом текстовом клиенте вместо OOB — строка со ссылкой
   `https://pangea.pp.ua/arena/<match_id>?t=<ticket>`.
3. React: вкладка/маршрут «Арена» — динамический `import('/static/arena/arena.js')`, canvas на
   весь игровой экран, кнопка «сдаться» (`\disconnect`), индикатор загрузки паков, возврат
   в MUD по окончании (событие из обёртки). Полноэкранный режим — тот же, что у 3D-сцены.
4. `POST /api/arena/result/` (HMAC, только с 127.0.0.1) → применяет правила **дуэли чести**:
   проигравшему памятный шрам (лицо/рука, как решено для дуэлей), запись в хронику обоих,
   изменение кармы персонажей, объявление в комнате. Смертей нет — это бой «в симуляторе».
   Нарративная рамка: реликт Потерянных времён, боевой симулятор, куда двое входят сознанием.
5. nginx: `location /arena-ws/` → `proxy_pass http://127.0.0.1:27961`, websocket-заголовки,
   `proxy_read_timeout 120s`; `location /static/arena/` — `immutable`-кэш для файлов с хэшем;
   `/api/arena/` под тот же `limit_req`, что и остальные API. `sudo -n nginx -t && sudo -n systemctl reload nginx`.
6. Проверка снаружи: два игрока из интернета (не из LAN), пинг, разрыв/реконнект, no-show,
   закрытие вкладки посреди матча.

### Этап 4. Свой контент и де-Quake-изация (2–4 недели, параллельно с художником)

1. **Список обязательных ассетов.** Запустить клиент и сервер с пустым паком и собрать все
   `WARNING: … not found` / `Couldn't load` в `content/required-assets.txt`; это и есть ТЗ на
   контент. Инструмент `tools/asset-audit.sh` в репо.
2. **Арена.** Одна карта 1 на 1 в стиле сеттинга (каменная чаша + «ржавый панк»: механизмы,
   решётки, реликтовые светильники). Редактор NetRadiant/TrenchBroom (формат `.map` Q3),
   компиляция `q3map2`; исходники `.map` в репо под GPL. Размер — как q3tourney2 (две-три
   комнаты, вертикальность, 1 мегахелс, 2 брони, телепорт).
3. **Модель игрока.** Конверсия «koi warrior» (GLB) в MD3 через Blender (экспортёр MD3), три
   части `head/upper/lower` + `animation.cfg` под анимации Q3 (можно упростить до одного
   набора). Если конверсия окажется тяжёлой — ⛔ сообщить, временно взять одну модель OpenArena.
4. **Оружие.** Механику оставляем (9 слотов, те же скорости/урон), меняем имена, модели,
   эффекты и звуки: клинок (gauntlet), самострел (machinegun), картечница (shotgun),
   метатель гранат, реликтовая ракетница, разрядник (lightning), рельсовый бур (railgun),
   плазмомёт, BFG → «сердце реликта». Имена вынести в один файл `arena/scripts/names.txt`
   или в `bg_misc.c`.
5. **HUD, шрифты, табло, диктор.** Шрифт — тот же, что в портале; диктор — записать свои фразы
   (можно через TTS) или убрать. Музыка — трек из набора Suno.
6. Удалить всё OpenArena из сборки, `content/openarena/` исчезает; `sv_pure 1`; проверить
   `asset-audit` — нулевой список недостающих файлов.
7. Юридическая гигиена: ни одной строки «Quake», «id Software», «Arena» как бренда в UI,
   названиях файлов и паках (grep по репо); в клиенте ссылка «Исходный код (GPLv2)» на репо.

### Этап 5. Доводка и запуск (≈ 1 неделя)

- Нагрузочная проверка: 4 матча одновременно на ноутбуке (CPU/RAM `ioq3ded` ≈ 1–2 % и ~30 МБ
  на матч; шлюз ≈ 30 КБ/с на игрока). Лимит одновременных матчей в менеджере.
- Разрыв соединения: пауза матча 30 с на реконнект (ioq3 `sv_reconnectlimit`), иначе техническое
  поражение.
- Античит: серверная авторитетность уже есть; `sv_pure 1`, запрет консоли игроку, лог
  аномальной точности в хронику — без автоматических санкций, для ручного разбора.
- Экспорт результата в «хронику» и «следы» персонажей; просмотр истории матчей на сайте.
- Документация в репо: `docs/build.md`, `docs/network.md`, `docs/content.md`, `docs/legal.md`.

---

## Оценка и риски

| Этап | Оценка | Главный риск |
|---|---|---|
| 0 | 1–2 дня | сборка QVM под Emscripten |
| 1 | 2–3 дня | формат эмуляции сокетов Emscripten (решаемо, есть три рабочих референса) |
| 2 | 3–5 дней | — |
| 3 | 1 неделя | синхронизация «одного времени» у двух игроков в модели хроно |
| 4 | 2–4 недели | конверсия GLB→MD3 и производство карты; это **контент**, не код |
| 5 | 1 неделя | — |

Играбельная дуэль на временном контенте — через **2–3 недели**; с собственным контентом —
**1,5–2,5 месяца**. Всё до этапа 4 делается на ноутбуке через Claude Code; этап 4 требует
Blender/редактор карт — на Windows-компьютере, с теми же файлами через репо.

## Что НЕ делаем

- Не трогаем Unity-клиент: он позже сможет подключаться к тем же `ioq3ded` напрямую по UDP
  (нативный ioq3-клиент как библиотека) или вообще не иметь арены — решим отдельно.
- Не реализуем арену на three.js — ioq3 даёт неткод, физику и предсказание бесплатно.
- Не делаем рейтинговую лигу. Командные режимы (TDM, CTF) есть в движке и заведены в каталог
  выключенными; боты — только как опция бойни.

## Изменения от 2026-11-02

- Добавлен режим **бойня** (deathmatch, `g_gametype 0`, 3–8 игроков) рядом с дуэлью.
- Матчи создаются не напрямую командой «арена», а через общую систему вызовов PvP
  (`world/pvp/`: «вызов» для 1 на 1, «клич» для бойни), где игроки выбирают режим и правила.
- Временный контент OpenArena берём из пакетов Ubuntu (`openarena-*-data`), без `players-mature`.
- Правила матча — cvar'ы `g_pangea_*` (арсенал, одним выстрелом, силы, предметы, боты, автовыход).
- Подробное задание: `pangea-pvp-challenges-task.md`.

---

## Запуск этапа 0 на ноутбуке

С Windows-компьютера (PowerShell), файл плана скачан в `Downloads`:
```powershell
scp $env:USERPROFILE\Downloads\pangea-arena-ioq3-plan.md gaskonec@192.168.31.11:/home/gaskonec/muddev/
ssh gaskonec@192.168.31.11
```
На ноутбуке:
```bash
cd /home/gaskonec/muddev
gh auth status || gh auth login
claude
```
Первое сообщение Claude Code:
```
Прочитай /home/gaskonec/muddev/pangea-arena-ioq3-plan.md и выполни «Этап 0» целиком: форк ioq3
в /home/gaskonec/muddev/pangea-arena, публичный репозиторий kto4eshirstij/pangea-arena, нативная
и веб-сборки, OpenArena как временный контент, проверка в браузере. План положи в репозиторий как
docs/plan.md. На каждом ⛔ останавливайся и спрашивай. В конце — сводка и команды для проверки
с Windows-компьютера.
```
