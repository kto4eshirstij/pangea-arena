# Оружие порога «Пещера» — модели, руки, пак

Первая low-poly версия, собранная скриптами Blender (headless, Cycles CPU). Концепты —
`docs/pangea-arena-weapons-concepts.md`, задание — `docs/pangea-arena-weapons-models-task.md`,
разведка окружения — `docs/weapons/notes.md`. Все исходники под GPLv2+, в паке нет ни одного
ассета OpenArena/Quake.

## Пересборка

```bash
cd /home/gaskonec/muddev/pangea-arena
bash tools/weapons/build_all.sh        # ~2 мин на 8 ядрах CPU
unzip -l content/build/arena-weapons-*.pk3 | tail -3
# листы предпросмотра (рендер из готовых MD3/TGA/.skin, ~10 мин):
~/opt/blender/blender -b --python-exit-code 1 -P tools/weapons/preview.py -- content/pangea content/build/weapons-preview-tiles
python3 tools/weapons/sheets.py content/build/weapons-preview-tiles docs/weapons/preview
```

Blender: `$BLENDER` или `~/opt/blender/blender` (официальный 4.2 LTS, см. notes.md).
Генерируемое (`content/pangea/models|icons`, `scripts/pangea_weapons.shader`, `content/build/`)
в git не хранится: всё воспроизводится из скриптов. Пак детерминированный:
`arena-weapons-<sha8>.pk3`, sha8 — первые 8 hex sha256 содержимого.

| Шаг | Где |
|---|---|
| Примитивы, материалы, роспись, запекание | `tools/weapons/lib/` (`geo`, `materials`, `ochre`, `bake`, `tga`) |
| Модели оружия/снарядов/пикапов | `tools/weapons/models/<id>.py` → `build()` |
| Руки: комплекции, позы, кожа | `tools/weapons/hands/` (`poses.py` — таблицы, `hands.py`, `skins.py`) |
| MD3 | `tools/md3/md3.py` (писатель + читалка, `test_md3.py`), `tools/weapons/export.py` |
| Этапы сборки | `tools/weapons/run.py` → `stages.py`; `pack.py` — шейдеры, аудит, zip |
| Быстрый просмотр по ходу работы | `run.py -- look <dir> [ids]`, `run.py -- hands_look <dir> [build] [poses]` |

## Раскладка пака

```
models/weapons2/<id>/<id>.md3              мир + вид от 1-го лица, хват в начале координат
models/weapons2/<id>/<id>_hand.md3         только tag_weapon: где оружие в позе рук medium
models/weapons2/<id>/<id>.tga              база (без росписи); _paint1..4.tga — росписи
models/weapons2/<id>/<id>_paint1..4.skin   подмена текстуры поверхности <id>
models/weapons2/torch/flame1..8.tga        кадры пламени (animMap 15)
models/weapons2/fists/fists_paint1..4.*    роспись обмоток (поверхность wraps рук)
models/hands/<build>/<pose>.md3            small|medium|large × 9 поз
models/hands/skin/<race>.tga|.skin         13 народов; <race>_fists1..4.skin = кожа + роспись обмоток
models/hands/wraps.tga                     обмотки, одна текстура на всех
models/projectiles/<id>.md3|.tga           снаряды и пикапы
icons/iconw_<id>.tga                       64×64, светлая охра на прозрачном
scripts/pangea_weapons.shader              пламя, тлеющие угли (факел, головня, огненная стрела)
```

## Модели, теги, бюджеты

Оси как в Q3: +X вперёд, +Z вверх, +Y влево; 1 ед. ≈ 1 дюйм (человек 56 ед.). Одна поверхность
на модель с именем `<id>` (плюс `flame` у факела и огненной стрелы). Модели статичные, 1 кадр:
замах, удар, натяжение — процедурно в cgame.

| id | Что | Треуг. (бюджет) | Теги |
|---|---|---|---|
| `fists` | без геометрии, обмотки — поверхность `wraps` рук | 0 | `tag_weapon`, `tag_flash` |
| `club` | ясеневая рукоять 28 ед. (≈70 см, «в руку»), голыш в расщепе, крест сухожилия, смола, темляк | 468 (500) | `tag_weapon`, `tag_flash` у навершия |
| `spear` | древко 70 ед., кремнёвый лист, мех и перья, обожжённая пятка | 274 (450) | `tag_weapon`, `tag_flash` у острия |
| `atlatl` | дощечка с крючком, рукоять «голова зверя» | 112 (200) | `tag_weapon_l` |
| `sling` | два шнура, кармашек с дырочками и голышом, петля, кисточка | 241 (300) | `tag_weapon`, `tag_flash` у кармашка |
| `bow` | тисовый лук 58 ед., рукоять, роговые накладки, тетива | 302 (600) | `tag_weapon`, `tag_flash` на тетиве |
| `torch` | палка, береста и пакля, обугленный верх; `flame` — 2 плоскости | 224 (350) | `tag_weapon`, `tag_flash` в пламени |
| `shield` | ивовый обод Ø24, шкура, костяной умбон, 2 ремня | 392 (500) | `tag_weapon` (левое предплечье по оси Y) |
| `proj_stone1..4` | голыши, 4 формы и оттенка | 64 (80) | — |
| `proj_arrow`, `proj_arrow_fire` | тростник, кремень, 3 пера; у огненной пакля + `flame` | 92 / 112 (120) | `tag_flash` |
| `proj_bola` | 3 мешочка на ремнях звездой | 150 (200) | — |
| `proj_brand` | головня, тлеющий конец | 80 (150) | `tag_flash` |
| `proj_boulder` | валун голиафа | 90 (150) | — |
| `item_quiver` | берестяной колчан, мех, 5 оперений | 149 (300) | — |
| `item_stones` | 6 голышей | 216 (300) | — |
| `proj_spear` | = `spear.md3` | — | — |

Руки: ≤ 900 треуг. на пару (348 на кисть, обмотки +44 на кисть). Поверхности: `hands` (правая),
`hands_l` (левая), `wraps` (только поза `fist`); каждая ≤ 999 вершин.

## Руки от 1-го лица

Комплекции и народы (`poses.py`, `RACE_BUILD`): `small` — гном, полурослик, гоблин, фей;
`medium` — человек, эльф, дварф, орк, драконорождённый, тифлинг, фелар; `large` — голиаф, тролль.
У всех комплекций и поз одна топология, поэтому одна текстура кожи на народ подходит ко всем.

Каждая поза — MD3 в пространстве вида (глаз в 0,0,0, взгляд +X, fov 90) с тегами, куда ставить
предмет: `tag_weapon` (правая рука), `tag_weapon_l` (левая), `tag_flash`/`tag_flash_l` (кулаки,
ладони обряда). В позе `bow` `tag_weapon` — центр стрелы на тетиве.

| Приём (категория) | Модель | Поза рук | Предмет на тегах |
|---|---|---|---|
| Тело: удары, пинок, подсечка, удар головой | `fists` | `fist` | — (обмотки — `wraps`) |
| Палица: размах, удар сверху, толчок древком | `club` | `club` | `tag_weapon` ← `club` |
| Копьё: укол, бросок | `spear` | `spear` | `tag_weapon` ← `spear` |
| Копьеметалка | `spear` + `atlatl` | `spear_atlatl` | `tag_weapon` ← `spear`, `tag_weapon_l` ← `atlatl` |
| Камень / праща / бола | `sling`, `proj_stone*`, `proj_bola` | `sling` | `tag_weapon` ← `sling`, `tag_weapon_l` ← голыш |
| Лук, навесной, огненная стрела | `bow`, `proj_arrow(_fire)` | `bow` | `tag_weapon_l` ← `bow`, `tag_weapon` ← стрела |
| Факел, бросок головни, «раздуть пламя» | `torch`, `proj_brand` | `torch` | `tag_weapon` ← `torch` |
| Щит, блок, взрывной прыжок «удар о землю» | `shield` | `shield` | `tag_weapon_l` ← `shield` |
| Обряды (слот 8) | — | `rite` | эффект между ладонями у `tag_flash` |

## Роспись охрой

4 варианта на оружие (`<id>_paintN`): 1 полосы, 2 точки, 3 ладонь, 4 зигзаг; красная охра
`#b5532a`, жёлтая `#c99a3a`, сажа `#1e1a17`. В игре: `paint = (clientNum % 4) + 1`, стабильно на
матч. База `<id>.tga` без росписи — запасной вариант. Где рисовать, задаёт «холст» материала
(`paint={...}` в `models/<id>.py`: ось, центр, размер, форма shaft|disc).

## Палитра

Тёплая гамма Пангеи: охра, кость, тёмное дерево; кремень серо-коричневый с голубоватым сколом.
Иконки — светлая охра `#e2b674` с тёмным контуром `#5a2e14`. Кожа народов — `hands/skins.py`.

## Как заменить модель работой художника

Положить файл по тому же пути и сохранить контракт:
1. Те же имена поверхностей (`<id>`, `flame`; у рук `hands`, `hands_l`, `wraps`), иначе не сработают
   `.skin` росписи и кожи.
2. Те же теги и их смысл: хват в начале координат, `tag_flash` в точке вылета/вспышки, у поз рук —
   `tag_weapon`/`tag_weapon_l` в точке хвата.
3. Оси и масштаб как выше; ≤ 999 вершин и ≤ 1999 треуг. на поверхность; бюджеты из таблицы.
4. Текстуры TGA 512×512 (снаряды 128–256, кожа 256×512), росписи — отдельными `_paintN.tga`
   с той же UV-развёрткой.
Скриптовую модель при этом достаточно не запускать: убрать id из `models/__init__.py`.

## Отличия от задания

- Палица: в таблице W2 указано «рукоять 70 ед.», но концепт говорит «длиной в руку». 70 ед. ≈ 1,8 м,
  поэтому сделано 28 ед. ≈ 70 см (похоже, в таблице имелись в виду сантиметры).
- Руки поз — отдельные поверхности `hands`/`hands_l`: две кисти вместе дают > 999 вершин.
- `.skin` для рук: `<race>.skin` и `<race>_fists1..4.skin` (кожа + роспись обмоток одним скином —
  у сущности в Q3 только один customSkin).
- Нормали MD3 квантуются как `byte·2π/256` — ровно как декодирует `tr_model.c`.
