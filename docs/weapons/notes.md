# Оружие порога 0 — заметки разведки (W0)

Дата: 2026-11-04. Ветка `feature/weapons-tier0` (от `develop` @ 061f51f9, +1 коммит с документами).
Ветку `feature/npc-bots` не трогаем.

## Окружение

- Ubuntu 24.04.5 LTS, 8 ядер CPU, 5 ГБ RAM, GPU нет (nvidia-smi отсутствует) → запекание и рендер
  только CPU. Свободно 411 ГБ.
- `python3-pil` 10.2.0 — есть. `python3-numpy` — **нет**.
- Blender из apt (4.0.2) не ставили: `sudo` требует пароль из терминала. Выбран вариант 2 —
  официальный **Blender 4.2.23 LTS** с blender.org (sha256 сверен) в
  `~/opt/blender-4.2.23-linux-x64`, ссылка `~/opt/blender` → бинарь `~/opt/blender/blender`.
  Системные пакеты не менялись. Скрипты вызывают `${BLENDER:-$HOME/opt/blender/blender}`.
- Встроенный Python Blender: numpy 1.24.3 есть → системный `python3-numpy` не нужен.

## 1. Blender и Cycles CPU

- Версия: `Blender 4.2.23 LTS`, `bpy ok 4.2.23 LTS`.
- Cycles CPU headless — **работает**: куб с процедурным Noise, `bake(type='DIFFUSE')` 2,2 с,
  `bake(type='AO')` 2,6 с (32 сэмпла), сохранено `TARGA_RAW` → `Targa RGB 512×512×24`.
- При 5 ГБ RAM: запекание 512×512 по одной модели за раз, сэмплы 32–64 — должно уложиться.

## 2. MD3-писатель

- `pangea-glb2md3` (build.py, glb.py) на машине **не найден**: `find /home/gaskonec/muddev`
  по `build.py` в `*md3*` — пусто; найденные `glb.py` (`pangea/web/skins/glb.py`,
  `pangea-render/web/skins/glb.py`) — это разбор GLB для Django-сервиса скинов, к MD3 не относится.
  Поиск сигнатуры `IDP3` по `*.py/*.js/*.c` вне исходников движка — пусто.
- Решение: пишу MD3-писатель заново в `tools/md3/md3.py` (GPL, свой код, чистый Python + `struct`,
  без зависимостей). Формат — по `code/qcommon/qfiles.h` (`md3Header_t`, `md3Frame_t`, `md3Tag_t`,
  `md3Surface_t`, нормали lat/lng, XYZ ×64). Плюс читалка для самопроверки (round-trip тест).
  Если у тебя где-то есть старый glb2md3 (другая машина, Windows) — скажи, сравню.

## 3. Этап C6 способностей

- `code/game/bg_abilities.c` — **нет**; `docs/abilities-tier0.md` в репо тоже нет.
- Значит C6 не сделан → по W6 делаю только пак + `docs/weapons/README.md` с таблицей
  «приём → модель → поза рук»; подключение в cgame уйдёт в C6.
- Точки будущего подключения: `code/cgame/cg_weapons.c:668` (`handsModel`, `*_hand.md3`),
  `CG_AddViewWeapon` (`cg_weapons.c:1356`) — сюда процедурные замах/отдача.

## Прочее

- Каталог `tools/` сейчас: только `stage-web-openarena.sh`; `content/` — `build/`, `home/`,
  `openarena/`. Пак оружия соберу в `content/pangea/` → `content/build/arena-weapons-<sha8>.pk3`.
- В рабочей копии лежит неотслеживаемый `manager/` — не мой, не трогаю и не коммичу.
