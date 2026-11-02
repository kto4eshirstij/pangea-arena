# Что взято, откуда, под какой лицензией

| Что | Откуда | Лицензия | Как используем |
|---|---|---|---|
| Движок: рендер, физика `bg_pmove`, неткод, предсказание, сервер | `github.com/ioquake/ioq3` | GPLv2 | основа форка (этот репозиторий) |
| Игровые режимы `GT_FFA`, `GT_TOURNAMENT`, `GT_TEAM`, `GT_CTF`, … | `code/game/bg_public.h` | GPLv2 | дуэль и бойня включены, остальное выключено |
| Оружие, предметы, тайминги, разминка, лимиты, лог матча | `code/game/g_*.c` | GPLv2 | итог матча разбирается из лога |
| Боты и навигация (`botlib`, AAS) | `code/botlib`, `code/game/ai_*.c` | GPLv2 | опция «боты» для бойни, по умолчанию 0 |
| Меню, HUD, табло | `code/q3_ui`, `code/cgame` | GPLv2 | урезаем, брендинг убираем |
| Веб-сборка (Emscripten, ES-модуль, WebGL) | `cmake/platforms/emscripten.cmake` | GPLv2 | клиент в React |
| Шлюз WebSocket→UDP, менеджер матчей | `gateway/`, `manager/` (наши) | GPLv2+ | |
| **Временный** контент: карты, модели, текстуры, звуки | OpenArena 0.8.8 из Ubuntu: `openarena-data` (только `pak0.pk3`), `openarena-088-data`, `openarena-085-data`, `openarena-081-{maps,misc,players,textures}` — сборки «+dfsg»/«split», очищенные Debian | GPLv2+ (тексты: `openarena-copyright.txt`) | до замены своим контентом; в git не хранится |
| Редактор и компилятор карт | NetRadiant-custom + `q3map2` | GPL | свои арены (на Windows) |

## Обязательство GPL

При раздаче `ioquake3.wasm`/`.js` и QVM клиент показывает ссылку «Исходный код (GPLv2)» на этот
репозиторий (`web/arena.html`; в React-вкладке — то же). Раздаваемые pk3 OpenArena — GPLv2+,
их источник — пакеты Ubuntu, указанные выше.

## Запрещено (в репозитории и в раздаче)

- pak-файлы Quake III Arena и Team Arena (в т.ч. демо `demoq3`, `tademo`), `q3ded`, `quake3.x86`,
  `Q3A_EULA`, любые репозитории с ними (например, `nrempel/q3-server`);
- демо-контент QuakeJS, код Q3JS (проприетарный);
- пакет `openarena-081-players-mature` и `pak2-players-mature.pk3`;
- названия Quake / id Software / «Arena» как бренд в интерфейсе, голос диктора и звуки Q3.

Проверка перед каждым push (должно быть пусто):
```bash
git ls-files | grep -iE 'pak[0-9]\.pk3|q3ded|quake3\.x86|Q3A_EULA'
```
