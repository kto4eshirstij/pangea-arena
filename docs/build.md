# Сборка Pangea Arena

Проверено на Ubuntu 24.04 (ноутбук-сервер), 2026-11-02. Root не нужен.

## Инструменты

```bash
uv tool install cmake && uv tool install ninja           # cmake 4.x, ninja → ~/.local/bin
git clone https://github.com/emscripten-core/emsdk.git ~/emsdk
~/emsdk/emsdk install latest && ~/emsdk/emsdk activate latest   # emcc 6.0.13 на момент проверки
source ~/emsdk/emsdk_env.sh
```
Клиент (SDL2) собирается только в веб-сборке — системный `libsdl2-dev` не нужен
(Emscripten приносит свой порт SDL2).

## Нативная сборка: сервер + QVM

```bash
cmake -S . -B build-native -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_CLIENT=OFF -DBUILD_SERVER=ON -DBUILD_GAME_QVMS=ON -DBUILD_GAME_LIBRARIES=OFF
cmake --build build-native -j"$(nproc)"
# build-native/Release/ioq3ded, build-native/Release/baseq3/vm/{cgame,qagame,ui}.qvm
```

## Веб-сборка клиента

```bash
source ~/emsdk/emsdk_env.sh
emcmake cmake -S . -B build-web -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build-web -j"$(nproc)"
# build-web/Release/: ioquake3.js, ioquake3.wasm, arena-boot.js, arena.html, baseq3/vm/*.qvm
```

**QVM в веб-сборке собираются** (`q3lcc`/`q3asm` собираются хостовым компилятором как внешний
проект) и побайтно совпадают с нативными — брать их из `build-native` не нужно.

## Временный контент OpenArena (из apt, без root)

```bash
mkdir -p ~/muddev/oa-debs && cd ~/muddev/oa-debs
apt-get download openarena-data openarena-088-data openarena-085-data \
  openarena-081-maps openarena-081-misc openarena-081-players openarena-081-textures
mkdir -p root && for d in *.deb; do dpkg-deb -x "$d" root; done
cp root/usr/share/games/openarena/baseoa/*.pk3 ~/muddev/pangea-arena/content/openarena/baseoa/
```
- `openarena-data` нужен ради `pak0.pk3` (в нём `default.cfg`, базовые модели, звуки, HUD).
  Его зависимость `openarena-081-players-mature` **не скачиваем и не распаковываем**.
- Паки — 8 файлов, ~380 МБ. В git не попадают.
- В `pak0.pk3`/`pak6-patch08x.pk3` лежат QVM OpenArena. Наши QVM кладём **россыпью** в
  `content/openarena/baseoa/vm/` — каталог в пути поиска стоит выше pk3, грузятся наши
  (в логе: `File "vm/qagame.qvm" found at ".../baseoa"`).

## Локальная проверка в браузере

```bash
tools/stage-web-openarena.sh          # симлинк baseoa + arena-config.json в build-web/Release
python3 -m http.server 8080 --bind 0.0.0.0 --directory build-web/Release
```
- Одиночная игра: `http://192.168.31.11:8080/arena.html?map=czest1tourney`
- По сети: см. `docs/network.md`.

Headless Chromium со SwiftShader для ioq3 не подходит: контекст WebGL теряется при повторной
инициализации рендера (загрузка карты). Картинку проверяем в настоящем браузере.
