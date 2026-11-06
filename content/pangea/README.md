# content/pangea — собственный контент арены (GPLv2)

- `archetypes/*.yaml` — описания архетипов карт для генератора `tools/mapgen/gen.py`
- `skins/<skin>/skin.yaml` — обличия (свет, небо, опасности); текстуры-заглушки делает `tools/mapgen/texgen.py`
- `scripts/*.shader`, `scripts/shaderlist.txt` — шейдеры
- `maps/` — `.map` (в git) и собранные `.bsp/.aas` (не в git), `levelshots/` — кадры 4:3
- сборка на Windows: `tools\mapgen\build.ps1 <archetype> <skin>` (см. `docs/maps/README.md`)

Текстуры `textures/pangea/<skin>/*.tga` сейчас процедурные заглушки; настоящий арт заменит их по тем же именам.

## Пак и шейдеры (06.11.2026)

- `tools/mapgen/pack.py` → `content/build/arena-pangea-<sha8>.pk3` + `maps/index.json` (паспорта карт для менеджера и `world/pvp/maps.py`).
- Рендерер веб-клиента — OpenGL2: шейдеры в `scripts/pangea_relic.shader` используют `stage normalMap` / `stage specularMap`,
  deluxe-карты (`q3map2 -light -deluxe`), эмиссивные панели (`q3map_surfacelight` + `_g` слой), анимированные пады.
- Набор текстур материала: `<name>.tga` (диффуз), `<name>_n.tga` (нормали, +Y вверх), `<name>_s.tga` (спекуляр RGB + глянец A), `<name>_g.tga` (свечение).
  Художник заменяет файлы по тем же именам — шейдеры не меняются.
- Качество клиента: `cfg/pangea-gl2.cfg` (нормали, спекуляр, HDR, тонмаппинг); на ноутбуке `tools/stage-web-pangea.sh` добавляет пак в `arena-config.json`.
