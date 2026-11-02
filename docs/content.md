# Контент для браузера: тонкий пак (`tools/pk3slim.py`)

400 МБ OpenArena в браузер не отдаём. Пак собирается из того, что реально нужно картам и cgame/ui.

```bash
python3 -I tools/pk3slim.py \
  --maps czest1tourney,pul1duel-oa,oa_dm7,am_lavaarena,oa_dm4,czest1dm,oa_dm1 \
  --trace content/trace/*.log --report
# -> content/build/arena-oa-<sha8>.pk3, content/build/missing.txt
tools/stage-web-slim.sh        # -> build-web/Release/slim/, arena-config.json (по умолчанию в arena.html)
```

Что собирается:
1. карта: лампы шейдеров и туманов BSP, сущности (`model`, `model2`, `noise`, `music`), `.arena`;
2. шейдеры: `map`, `clampMap`, `animMap`, `skyParms` — по **всем** описаниям шейдера (в OA одно имя
   бывает в нескольких .shader); все `scripts/*.shader` целиком (текст, мало весит);
3. MD3 (шейдеры поверхностей), `*_default.skin`, `animation.cfg`; модели игроков sarge, grism, kyonshi;
4. строковые пути из `code/cgame`, `code/q3_ui`, `bg_misc.c`, с раскрытием `%s`/`%i`; к моделям оружия —
   `_flash/_barrel/_hand`; несколько мелких каталогов HUD целиком (`gfx/2d`, `sprites`, `sound/feedback`, …);
5. трасса: логи веб-клиента с `+set fs_debug 1` — строки `FS_FOpenFileRead: … (found in`,
   `could not find '…' in shader '…'` (берётся и файл, и шейдер целиком), `Failed to load sound`.

Не берём: `botfiles/` (боты живут на нативном сервере), `music/`, `video/`, `sound/teamplay/`, флаги CTF,
чужие карты.

Пути ищутся как в ioq3: поздний pk3 перекрывает ранний; `.tga`↔`.jpg`↔`.png`, `.wav`↔`.ogg`.

## Итог 2026-11-02

| Набор | Файлов | Пак |
|---|---|---|
| 7 карт (4 дуэльные + 3 бойни) | 1240 | **62,1 МБ** |
| 4 карты (czest1tourney, oa_dm7, oa_dm4, czest1dm) | ~1050 | **48,6 МБ** |

Трасса: каждая карта по 75 с в headless Chromium (Vulkan-SwiftShader), `content/trace/*.log`,
два прохода (`*.2.log` — после первого добора). После второго прохода на всех картах клиент входит
в игру только с тонким паком, недостающих файлов нет, кроме отсутствующих в самой OpenArena
(`sound/misc/windfly.wav`). `missing.txt` — в основном имена шейдеров из исходников моделей
(`d:/projects/...`), их перекрывают .skin.

Самое тяжёлое: модели игроков (12 МБ), `menu/art` (12 МБ, меню q3_ui — уйдёт при урезании UI на
этапе 4), оружие (10 МБ), `pul1duel-oa.bsp` (6 МБ). Следующий шаг по весу — общий пак + пак на карту,
чтобы браузер качал только карту своего матча.

## Headless-проверка

```bash
# Chromium (Playwright) с Vulkan-SwiftShader — так ioq3 рисует карту; с ANGLE/GL-SwiftShader
# контекст WebGL теряется на загрузке карты.
--use-angle=vulkan --use-vulkan=swiftshader --enable-features=Vulkan --enable-unsafe-swiftshader
```
