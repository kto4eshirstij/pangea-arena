# Совместимость: игровой код ioq3 + паки OpenArena 0.8.8 (Ubuntu)

Проверено 2026-11-02 на нативном `ioq3ded` и в веб-клиенте (headless Chromium).

| Что | Итог |
|---|---|
| Наши `qagame/cgame/ui.qvm` поверх паков OA | Работает. В `pak0.pk3` и `pak6-patch08x.pk3` лежат свои QVM OpenArena — наши кладём россыпью в `baseoa/vm/`, каталог в пути поиска выше pk3 (`File "vm/qagame.qvm" found at ".../baseoa"`). |
| `default.cfg` | Есть только в `pak0.pk3` из пакета `openarena-data` (не входил в список A1). Без него `Couldn't load default.cfg` → фатально. Берём один этот pk3. |
| Модель по умолчанию `sarge` (`DEFAULT_MODEL`) | Есть в `pak0.pk3` (`models/players/sarge/`), боты используют `sarge/classic`. |
| Карты дуэли и бойни (7 шт.) | Грузятся, `.aas` есть у всех. Единственное предупреждение — `FinishSpawningItem: weapon_shotgun startsolid` на czest1tourney (дробовик в стене, безвредно). |
| Боты (`botfiles/` OpenArena + наш `qagame`) | Работают: `addbot` на oa_dm1/oa_dm4/czest1dm/aggressor — входят, бегают, убивают. Сами по себе бегают по карте долго — за 60 с на oa_dm4 могут не встретиться. |
| `com_gamename Quake3Arena`, протокол 71 | Пока не standalone — исправит этап 2 плана (identity). |
| Кириллица в движке | Шрифты Q3/OA без кириллицы: «Это не ваша арена» в консоли клиента выглядит как `.... .. ....`. Тексты для игрока показывает React-обёртка; движку — латиница или перевод на стороне обёртки. |
| Веб-клиент в headless Chromium | С ANGLE/GL-SwiftShader контекст теряется на загрузке карты; с Vulkan-SwiftShader всё рисуется (см. `docs/content.md`). |

## Выбранные карты (A1, решение владельца 2026-11-02)

| Режим | Карта | Название в OA | `.bsp` |
|---|---|---|---|
| дуэль | `czest1tourney` | The Space Spire | 1,8 МБ |
| дуэль | `pul1duel-oa` | Five Steps Ahead | 6,0 МБ |
| дуэль | `oa_dm7` | Outer Cistern | 1,6 МБ |
| дуэль | `am_lavaarena` | Lava Arena | 1,2 МБ |
| бойня | `oa_dm4` | The Bad Place | 2,2 МБ |
| бойня | `czest1dm` | Monastery | 3,5 МБ |
| бойня | `oa_dm1` | Think Twice Or Die | 1,4 МБ |

Временные имена в Pangea («Чаша I», «Чаша II», «Пыльный круг», «Ржавый двор», …) — в части B.

## Решено: «Bad clientNum on player entity» в бойне с ботами (2026-11-03)

Симптом: веб-клиент падал с `ERROR: Bad clientNum on player entity: ent 147 eType 1 clientNum 147`,
как только игрок оказывался не в слоте 0 (в бойне слоты 0–1 занимали боты). Зависело от сборки
`qagame.qvm`, а не от правил Pangea и не от ботов.

Причина — **устаревшие объектные файлы QVM**. Правила `q3lcc` в `cmake/utils/qvm_tools.cmake`
зависели только от своего `.c`, без заголовков. После правки `gclient_t` в `g_local.h`
пересобрались не все `.asm`, и в одном `qagame.qvm` оказались два размера структуры клиента:
`trap_LocateGameData` передавал движку то 840, то 776 байт. Для слота ≥ 1 движок читал
playerState по неверному смещению и отправлял клиенту чужую память (`clientNum 22`, потом `147`).
Клиент разбирал поток правильно (проверено `cl_shownet -2` против печати на сервере).

Исправления:
- `cmake/utils/qvm_tools.cmake`: каждый `.asm` зависит от всех заголовков игровых модулей
  (`game`, `cgame`, `q3_ui`, `ui`, `qcommon`, `botlib`, `renderercommon`);
- `code/server/sv_game.c`: если модуль в пределах карты сообщает разные размеры `gclient_t`
  или `gentity_t`, сервер падает с понятной ошибкой («rebuild the game module from clean»),
  а не шлёт мусор.

Проверено на чистой сборке: бойня на oa_dm4 с ботами, человек в слотах 1–3 — без ошибок (2 из 2);
полный стек через менеджер (2 браузера + 2 бота, rail + instagib, fraglimit 3) доигран,
результат доставлен. Боты (A5) работают: `rules.bots` 0–3.
