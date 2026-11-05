# content/pangea — собственный контент арены (GPLv2)

- `archetypes/*.yaml` — описания архетипов карт для генератора `tools/mapgen/gen.py`
- `skins/<skin>/skin.yaml` — обличия (свет, небо, опасности); текстуры-заглушки делает `tools/mapgen/texgen.py`
- `scripts/*.shader`, `scripts/shaderlist.txt` — шейдеры
- `maps/` — `.map` (в git) и собранные `.bsp/.aas` (не в git), `levelshots/` — кадры 4:3
- сборка на Windows: `tools\mapgen\build.ps1 <archetype> <skin>` (см. `docs/maps/README.md`)

Текстуры `textures/pangea/<skin>/*.tga` сейчас процедурные заглушки; настоящий арт заменит их по тем же именам.
