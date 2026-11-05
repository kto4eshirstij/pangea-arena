# Pangea Arena — бриф для задания C6 «способности порога 0 в игре»

Дата: 2026-11-05. Кому: Claude на ПК владельца (автор `pangea-arena-abilities-tier0.md` и
`pangea-arena-weapons-concepts.md`). От: Claude Code на ноутбуке (сервер, где живёт арена).

## Что нужно от тебя

Написать **задание для Claude Code на ноутбуке**: `pangea-arena-abilities-c6-task.md` в том же
формате, что `pangea-arena-weapons-models-task.md`. Нужны этапы с номерами, проверка на каждом,
стопы ⛔ там, где решает владелец, и в конце раздел «Как запустить» со `scp` и первым сообщением.
Цель — чтобы в браузерной арене вместо оружия OpenArena (рейлган, ракетница…) были приёмы порога 0
из слотов 1–7 (а если влезет, то и 8–9) с новыми моделями, руками и росписью.

Задание по способностям `pangea-arena-abilities-tier0.md` есть только у тебя, на ноутбуке его нет.
**Приложи его к заданию**, либо положи в `docs/abilities-tier0.md` и упомяни в «Как запустить».
Механику (урон, перезарядки, дальность, что разрешено в каком режиме) бери оттуда. Чего там нет,
предложи сам и пометь ⛔ на решение владельца.

## Что уже сделано (факты, проверено 2026-11-05)

**Репозиторий** `~/muddev/pangea-arena` — форк ioquake3 (GPLv2), GitHub
`kto4eshirstij/pangea-arena`. Клиент — ioq3, собранный emscripten в WebAssembly, работает в
браузере (iframe из MUD). Игровая логика — QVM (`qagame`, `cgame`, `ui`), данные — OpenArena.

**Ветки:**
- `feature/npc-bots` (223e4120) — **живая**, её код сейчас крутится на сервере: правила Пангеи,
  NPC-боты, ничья по таймлимиту, кик при закрытой вкладке.
- `feature/weapons-tier0` (8a485b47, на GitHub) — поверх `feature/npc-bots`, этапы W0–W6 модели оружия.
  Рабочая копия — `~/muddev/pangea-arena-weapons`.
- C6 надо делать в новой ветке от `feature/weapons-tier0` (например `feature/abilities-c6`),
  **в отдельной worktree, не в `~/muddev/pangea-arena`**: живая копия должна оставаться на живой ветке.

**Пак моделей готов** (`content/build/arena-weapons-7d7107d3.pk3`, 14 МБ, свой код и ассеты, без
OpenArena). Собирается `bash tools/weapons/build_all.sh` (Blender 4.2 headless, ~2 мин). Полная
раскладка, теги, бюджеты и таблица «приём → модель → поза рук» — в `docs/weapons/README.md`. Кратко:

| id | что | теги |
|---|---|---|
| `fists` | без геометрии, обмотки = поверхность `wraps` рук | `tag_weapon`, `tag_flash` |
| `club`, `spear`, `sling`, `bow`, `torch` | палица, копьё, праща, лук, факел (+`flame`) | `tag_weapon`, `tag_flash` |
| `atlatl` | копьеметалка, левая рука | `tag_weapon_l` |
| `shield` | щит, левое предплечье | `tag_weapon` |
| `proj_stone1..4`, `proj_arrow`, `proj_arrow_fire`, `proj_bola`, `proj_brand`, `proj_boulder`, `proj_spear` | снаряды | — / `tag_flash` |
| `item_quiver`, `item_stones` | пикапы | — |

- Модели **статичные, 1 кадр**. Замах, удар, натяжение и отдачу должен делать cgame процедурно.
- Руки от 1-го лица: `models/hands/<small|medium|large>/<pose>.md3`, позы `fist club spear
  spear_atlatl sling bow torch shield rite`. У поз есть теги `tag_weapon`/`tag_weapon_l`/`tag_flash(_l)`
  в пространстве вида (глаз в 0,0,0, взгляд +X, fov 90). Кожа — `models/hands/skin/<race>.skin`
  (13 народов), обмотки кулаков — `<race>_fists1..4.skin`.
- Комплекция по народу: `small` — гном, полурослик, гоблин, фей; `medium` — человек, эльф, дварф,
  орк, драконорождённый, тифлинг, фелар; `large` — голиаф, тролль.
- Роспись: `<id>_paint1..4.skin`, правило `paint = (clientNum % 4) + 1`.
- Шейдеры пламени — `scripts/pangea_weapons.shader`.

**Чего нет:**
- `code/game/bg_abilities.c` и любой код способностей — **нет**. Оружие в игре — стандартные 10
  оружий Q3/OpenArena.
- Звуков (~25 по концептам) — **нет**, ни одного. Их нужно либо сделать в задании (процедурно,
  своя лицензия), либо явно отложить.
- Пак оружия игрокам **не раздаётся**: веб-клиент грузит только `slim/arena-oa-c828a9e0.pk3` и три
  QVM по списку `build-web/Release/arena-config.json`.
- **Народ игрока до арены не доходит.** MUD (`~/muddev/pangea`, `world/pvp/`) шлёт менеджеру
  только `ticket`, `name`, для NPC — `bot{model, skill}`. Для рук по народу нужно протащить
  `race` по цепочке: MUD → менеджер (`manager/src/rules.ts`, `parseMatchRequest`) → `match.cfg`/
  userinfo → qagame → configstring → cgame.

## Код, к которому подключаться

- Правила Пангеи — `code/game/g_pangea.c` + объявления в `code/game/g_local.h:956–984`. Cvars
  `g_pangea_tickets`, `g_pangea_arsenal` (сейчас `full | rail | rocket | melee`),
  `g_pangea_instagib`, `g_pangea_powerups`, `g_pangea_items`, `g_pangea_bots`,
  `g_pangea_autoexit`, `g_pangea_overtime`. Хуки: `Pangea_GiveArsenal`, `Pangea_ItemAllowed`,
  `Pangea_ModifyDamage`, `Pangea_BlockCommand`, `Pangea_RunFrame`.
- Вид от 1-го лица: `code/cgame/cg_weapons.c` — `CG_RegisterWeapon` (стр. 606), `handsModel` из
  `*_hand.md3` (стр. 667), `CG_AddViewWeapon` (стр. 1356), сборка руки (стр. 1432).
- Предметы на карте: `bg_itemlist` в `code/game/bg_misc.c`.
- Менеджер матчей (Node/TS): `manager/src/` (`rules.ts`, `match.ts`, `server.ts`), тесты
  `manager/test/`. Режимы сейчас `duel | ffa`. В MUD в каталоге есть ещё зарезервированные
  `tdm | ctf` (`world/pvp/modes.py`).
- Сборка веба: `tools/stage-web-slim.sh`, `build-web/Release/`.

## Ограничения и грабли (обязательно перенеси в задание)

1. **После любой правки заголовков игры (`g_local.h`, `bg_public.h`…) — чистая пересборка QVM.**
   Зависимости asm от заголовков исправлены в cf7ace9d, но проверка размера `gclient_t`
   (`SV_LocateGameData`) должна остаться зелёной. Старый баг: «Bad clientNum on player entity».
2. **Сетевой протокол.** Новые поля в `playerState_t`/`entityState_t` трогать с осторожностью. Лучше
   кодировать приём в существующих полях (`weapon`, `generic1`, `eFlags`…) или в configstrings.
   Клиент и сервер всегда одной сборки, но демо и совместимость с OpenArena не нужны.
3. Ботам с патронами −1 AI считает оружие пустым (поэтому arsenal выдаёт 99). Новые приёмы с
   перезарядкой должны работать и для ботов (NPC Кер, Бранн). Либо описать, как боты их используют,
   либо ограничить ботов кулаками/копьём.
4. ioq3 держит максимум 32 «+»-команды в командной строке: менеджер пишет `match.cfg` + `+exec`.
5. Консоль `ioq3ded` пишет в stderr. Менеджер парсит лог (`manager/src/logparse.ts`): новые строки
   лога не должны ломать разбор результатов (`ExitReason`: `fraglimit | timelimit | no_show | forfeit | crash | cancelled`; ничья — timelimit при равном счёте).
6. **Выкатка**: живой менеджер работает из `~/muddev/pangea-arena/manager/dist`, QVM живого сервера
   лежат в `content/openarena/baseoa/vm/`. Задание должно кончаться стопом ⛔ «выкатить?». Сама
   выкатка: merge в `feature/npc-bots` (или новую живую ветку), сборка, копирование QVM и паков,
   новая строка пака в `arena-config.json`. Перезапуск сервиса делает **владелец**:
   `sudo systemctl restart pangea-arena-manager`, sudo у Claude нет.
7. Проверка в браузере без GPU: headless Chromium рисует ioq3 только с `--use-angle=vulkan
   --use-vulkan=swiftshader --enable-features=Vulkan`. Готовый рецепт стенда (порты 27850/27861/
   27990, свой basepath, python http.server на `build-web/Release`, playwright
   `arena.html?connect&ws&ticket`) уже применялся. Попроси в задании скриншоты в `docs/abilities/check/`.
8. Никогда `pkill -f <шаблон>`, который встречается в той же bash-команде: убивает оболочку.
9. Пак оружия уже 14 МБ, а качается в браузер. Если добавятся звуки — указать бюджет размера и
   формат (ogg/wav 22 кГц mono).

## Что задание должно решить (вопросы для ⛔ владельцу)

1. Как приёмы ложатся на управление Q3. Слоты 1–7 = клавиши оружия 1–7? Вторичные приёмы
   (подсечка, навесной выстрел, бросок копья, «раздуть пламя», блок) — на `+button`/альт-атаку?
2. Что из арсенала доступно в каждом режиме: дуэль чести (без огня) и бойня (всё; бола и оглушение
   только здесь). Новые значения `g_pangea_arsenal`?
3. Остаются ли старые оружия OpenArena как отдельный режим «симулятор» или убираются совсем.
4. Подбор брошенного копья и головни, пятно огня, колчан и голыши как пикапы — что из этого в
   первую поставку, что потом.
5. Обряды (слот 8) и наследия рас (слот 9) — в этом же задании или отдельным C7.
6. Звуки: делать сейчас (процедурно) или временно взять из OpenArena (GPL — можно, но это «чужие» звуки).

## Предлагаемая разбивка (поправь по abilities-tier0)

- **C6.0** разведка: прочитать код из раздела выше, отчёт `docs/abilities/notes.md`, ⛔.
- **C6.1** общая таблица приёмов в `bg_` (shared game/cgame): id, слот, примитив (melee дуга /
  снаряд / область / бафф), урон, перезарядка, дальность, флаги режимов. Юнит-проверка таблицы.
- **C6.2** сервер: выдача арсенала по режиму, обработка приёмов (melee-трассы, снаряды из моделей
  `proj_*`), урон через `Pangea_ModifyDamage`, боты.
- **C6.3** протаскивание народа: MUD → менеджер → userinfo → configstring; тест менеджера.
- **C6.4** cgame: регистрация моделей и скинов, руки по комплекции и коже, роспись, процедурные
  замах/удар/натяжение в `CG_AddViewWeapon`, вид у противника (мир), HUD-иконки.
- **C6.5** эффекты: пламя и свет факела, пыль, искра «сим-поля», кольцо взрывного прыжка; звуки по решению ⛔6.
- **C6.6** сборка веба: пак в `arena-config.json`, размер, проверка в headless-браузере, дуэль и
  бойня с ботами, 3 народа разных комплекций, скриншоты, ⛔.
- **C6.7** документация, push, ⛔ на выкатку (см. грабли 6).

## Как владелец передаст результат на ноутбук

Готовое задание (и `abilities-tier0`) владелец кладёт так (PowerShell):
```powershell
scp $env:USERPROFILE\Downloads\pangea-arena-abilities-c6-task.md $env:USERPROFILE\Downloads\pangea-arena-abilities-tier0.md gaskonec@192.168.31.11:/home/gaskonec/muddev/pangea-arena-weapons/docs/
```
Дальше на ноутбуке `cd ~/muddev/pangea-arena-weapons && claude` и первое сообщение из твоего
раздела «Как запустить».
