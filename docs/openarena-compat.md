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
| Веб-клиент в headless SwiftShader | Меню и сеть работают, но при загрузке карты WebGL-контекст теряется (`CONTEXT_LOST_WEBGL` на второй `R_Init`). Особенность стенда, не клиента; картинка — проверка в настоящем браузере. |

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
