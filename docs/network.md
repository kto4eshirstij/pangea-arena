# Сеть браузерного клиента

## Как Emscripten эмулирует UDP (emcc 6.0.13, `src/lib/libsockfs.js`)

- ioq3 в веб-сборке использует обычный `net_ip.c` (BSD-сокеты); Emscripten подменяет их SOCKFS.
- Каждый адрес назначения (`addr:port`), на который клиент делает `sendto`, получает **свой
  WebSocket**. URL берётся из `Module.websocket.url` **в момент подключения**:
  - если это ровно `ws://` или `wss://` — дописывается `addr:port/`;
  - иначе используется как есть (полный URL). Функцию вместо строки SOCKFS не принимает,
    но объект `Module.websocket` можно менять во время работы — обёртка так и делает.
- Подпротокол — `binary` (по умолчанию; в сборку добавлен явный `-sWEBSOCKET_SUBPROTOCOL=binary`).
- **Кадр = датаграмма 1:1**, без заголовка адреса.
- Если UDP-сокет был `bind`-нут (ioq3 всегда биндит `net_port`), первым кадром уходит служебное
  сообщение `FF FF FF FF 'p' 'o' 'r' 't' <port_hi> <port_lo>` (10 байт). Шлюз его отбрасывает.
- Ответы сервера приписываются адресу, к которому клиент подключался, — для ioq3 это выглядит как
  обычный UDP-обмен с `addr:port`.
- `bind` в браузере не поднимает сервер (EOPNOTSUPP глушится). `SO_BROADCAST` не поддерживается —
  в консоли безвредное `WARNING: NET_IPSocket: setsockopt SO_BROADCAST`.

Следствие: любая отправка клиента на «чужой» адрес (MOTD, авторизация, мастер-сервер) откроет
ещё один WebSocket на тот же URL матча. Поэтому `cl_motd 0`; авторизацию и мастер выключит
standalone-сборка (этап 2).

## Шлюз `gateway/`

```bash
cd gateway && npm ci && npx tsc -p . && npx vitest run
node dist/index.js --listen 27961 --host 0.0.0.0 --udp-host 127.0.0.1 --min 27960 --max 27979
```
- `ws://<host>:27961/<udp_port>` (и `/arena-ws/<udp_port>` — тот же маршрут за nginx).
- На каждый WebSocket — свой UDP-сокет к `127.0.0.1:<udp_port>`, сервер видит каждого игрока
  как отдельный `ip:port`.
- Порты только из диапазона; лимит соединений на порт (по умолчанию 4); простой 60 с — закрытие.
- `startGateway({allowPort, limitForPort})` — хуки для менеджера матчей.

## Проверка по LAN

```bash
./build-native/Release/ioq3ded +set dedicated 1 +set net_ip 127.0.0.1 +set net_port 27960 \
  +set fs_basepath "$PWD/content/openarena" +set fs_homepath "$PWD/content/home" \
  +set com_basegame baseoa +set fs_game baseoa +set g_gametype 1 +set sv_maxclients 4 \
  +set bot_enable 0 +set sv_pure 0 +map czest1tourney
node gateway/dist/index.js --listen 27961 --host 0.0.0.0
```
Браузер: `http://192.168.31.11:8080/arena.html?connect=192.168.31.11:27960&name=Арн`
(страница сама строит `ws://192.168.31.11:27961/27960`; иначе — параметр `ws=`).

Проверено 2026-11-02 headless: клиент прошёл challenge/connect, сервер — `ClientConnect: 0`,
`Arn connected`, клиент получил gamestate (1128 датаграмм). Игра и пинг — проверка с Windows.

Рекомендуемые настройки для замера: `sv_fps 40`, `snaps 40`, `cl_maxpackets 125`, `rate 90000`,
`cl_timenudge 0`, `pmove_fixed 1`, `cg_lagometer 1`.
