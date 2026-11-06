# Обличие `siberian_core` — Вэр-Кирракс (Тёплые траппы), Сибирский кратон

Модель: **Nano Banana 2.1** (`nano_banana_2_1`), resolution 2k, aspect 1:1 для текстур, 4:3 для levelshot,
один seed на весь набор (стиль единый), thinking medium. Первую картинку (стена) потом подавать как
image reference остальным — так материалы «одной породы».

Ландшафт по лору (`pangea-rodiny-narodov.md`): базальтовые плато-траппы, горячие ключи и пар посреди
мерзлоты, гнездо красных драконорождённых; вокруг — холодная степь у края тайги. Палитра: чёрно-серый
базальт с бурыми окислами, тёплое оранжевое свечение в трещинах (жар из глубины), охристо-белые
минеральные натёки у источников, иней по кромкам, пар.

Общий хвост для всех текстур (STYLE):
`seamless tileable game texture, top-down orthographic, even diffuse lighting, no shadows cast by camera,
no vignette, no text, no watermark, photorealistic PBR albedo, 2k`

| Файл | Промпт |
|---|---|
| `wall_a.tga` | Columnar basalt wall, hexagonal prismatic columns packed tightly, dark charcoal-grey stone with faint brown oxide stains and frost rime along the edges, thin glowing orange heat cracks between some columns, cold volcanic plateau of Siberian traps, STYLE |
| `floor_a.tga` | Basalt flagstone floor of broken hexagonal column tops, dark grey polygonal slabs with ochre and white mineral sinter crust in the joints like a hot-spring terrace, thin steam condensation and frost at the edges, STYLE |
| `ceil_a.tga` | Rough basalt cave ceiling, dark grey volcanic rock with vesicular bubbles, soot streaks, small orange ember glow deep in a few cracks, STYLE |
| `trim_a.tga` | Horizontal band of ancient relic metal plating set into basalt, oxidized dark bronze with rust, a continuous engraved groove running along the middle filled with glowing orange ember light, small rune-like notches along the groove, STYLE |
| `lamp.tga` | Square relic lamp panel, dark bronze frame set into basalt, in the centre a glowing sun disc with twelve rays, orange-gold light, cracked enamel, frost on the frame corners, flat front view, no perspective, square composition, STYLE |
| `ring_floor.tga` | Circular dueling ring marked on a basalt floor: two concentric rings carved into dark grey hexagonal stone slabs and filled with ochre mineral pigment, scuffed centre, square composition, ring centred and touching the edges, STYLE |
| `sky.tga` (4:3 → будет cubemap-подложкой) | Cold sky over a volcanic trap plateau at low sun: pale orange sun near the horizon, long violet-grey clouds, columns of white steam rising from hot springs, distant dark basalt steps and a line of larch taiga, no ground in the lower third, painterly realism, wide panoramic |
| `clouds.tga` | Seamless tileable layer of thin high cirrus clouds and drifting steam wisps on pure black background, greyscale luminance only, soft edges, top-down, STYLE |
| `pad_base.tga` | Circular relic pad: a round bronze plate with concentric grooves inset in basalt, worn centre, square composition, pad touching the edges, STYLE |

Карты нормалей, спекуляр и свечение (`_n`, `_s`, `_g`) выводятся из этих картинок скриптом `texgen.py --from-art`
(высота из яркости + ручная маска свечения по оранжевому каналу).

## Levelshots (4:3, 2k, та же модель)

| Файл | Промпт |
|---|---|
| `levelshots/pangea_depth_siberian_core.jpg` | Interior of a two-level arena carved into columnar basalt, a stone staircase climbing to an upper ledge, glowing orange ember grooves along bronze trim bands, relic sun-disc lamps on the walls, steam drifting from floor vents, cold blue daylight from a doorway, no people, game level concept art, 4:3 |
| `levelshots/pangea_fronts_siberian_core.jpg` | Large open-air basalt courtyard between two fortified stone bases, a raised central plinth with a steaming hot spring, upper galleries along the sides, low orange sun and steam columns, frost on the stone, no people, game level concept art, wide shot, 4:3 |
| `levelshots/pangea_arena8_siberian_core.jpg` | Vast volcanic arena: a square basalt courtyard with a raised platform in the middle, four gateways to side halls, glowing ember lines in the floor joints, steam vents, pale cold sky with a low sun, no people, game level concept art, high viewpoint, 4:3 |

## Как сложить

```
content/pangea/skins/siberian_core/skin.yaml    # craton: siberian, niche: core, title_ru: "Вэр-Кирракс", hazards: [lava_vents], ambient 5
content/pangea/textures/pangea/siberian_core/   # файлы из таблицы + сгенерированные _n/_s/_g
content/pangea/scripts/pangea_siberian_core.shader   # копия relic-шейдера с заменой пути
```
Сборка: `tools\mapgen\build.ps1 -Archetype depth -Skin siberian_core` (и fronts, arena8).
