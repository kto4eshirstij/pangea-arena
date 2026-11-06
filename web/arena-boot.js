// Pangea Arena boot wrapper for the Emscripten client (ES module).
//
//   import { bootArena } from './arena-boot.js';
//   const arena = await bootArena({
//     canvas, enginePath: '/static/arena/', dataPath: '/static/arena/',
//     configUrl: '/static/arena/arena-config.json', basegame: 'baseoa',
//     wsUrl: 'wss://pangea.pp.ua/arena-ws/27963',   // gateway URL for this match
//     connect: 'arena:27963', ticket: 'abc', name: 'Арн',
//     args: '+set cg_drawFPS 1',
//     onEvent: (e) => console.log(e),                // {type:'log'|'exit'|'ready'|'progress', ...}
//   });
//
// Emscripten's SOCKFS sends every UDP datagram as one binary WebSocket message to
// Module.websocket.url (read at connect time), so one URL per match is enough:
// the gateway maps /<udp_port> to 127.0.0.1:<udp_port>. See docs/network.md.

const DEFAULT_ARGS = [
  '+set', 'sv_pure', '0',
  '+set', 'net_enabled', '1',       // IPv4 only, emulated over WebSocket
  '+set', 'r_mode', '-2',           // canvas size
  '+set', 'cl_motd', '0',           // no MOTD request to the internet
  '+set', 'com_introplayed', '1',
  '+set', 'bot_enable', '0',       // local devmap only; the slim pak has no botfiles
];

function splitArgs(s) {
  if (!s) return [];
  const out = [];
  const re = /"([^"]*)"|(\S+)/g;
  let m;
  while ((m = re.exec(s))) out.push(m[1] !== undefined ? m[1] : m[2]);
  return out;
}

export async function bootArena(opts) {
  const {
    canvas,
    enginePath = './',
    dataPath = './',
    configUrl = enginePath + 'arena-config.json',
    engineName = 'ioquake3',
    basegame = 'baseoa',
    wsUrl,
    connect,
    ticket,
    name,
    map,
    args = '',
    onEvent = () => {},
  } = opts;

  const argv = [...DEFAULT_ARGS, '+set', 'com_basegame', basegame, '+set', 'fs_game', ''];
  if (name) argv.push('+set', 'name', name);
  if (ticket) argv.push('+set', 'pangea_ticket', ticket);
  argv.push(...splitArgs(args));
  if (map) argv.push('+devmap', map);
  else if (connect) argv.push('+connect', connect);

  const config = await fetch(configUrl, { cache: 'no-store' }).then((r) => (r.ok ? r.json() : {}));
  const dataURL = new URL(dataPath, location.href);
  const websocket = { url: wsUrl || 'ws://', subprotocol: 'binary' };

  const engine = (await import(new URL(engineName + '.js', new URL(enginePath, location.href)).href)).default;
  const emit = (e) => { try { onEvent(e); } catch (err) { console.error(err); } };

  const module = await engine({
    canvas,
    arguments: argv,
    websocket,
    locateFile: (file) => new URL(file, new URL(enginePath, location.href)).href,
    print: (line) => { console.log(line); emit({ type: 'log', line }); },
    printErr: (line) => { console.warn(line); emit({ type: 'log', line, err: true }); },
    onExit: (code) => emit({ type: 'exit', code }),
    preRun: [async (m) => {
      m.addRunDependency('pangea-arena-fs');
      try {
        const files = (config[basegame] && config[basegame].files) || [];
        let done = 0;
        await Promise.all(files.map(async (file) => {
          const res = await fetch(new URL(file.src, dataURL), { cache: 'no-store' });
          if (!res.ok) { emit({ type: 'log', line: `missing ${file.src}`, err: true }); return; }
          const data = new Uint8Array(await res.arrayBuffer());
          m.FS.mkdirTree(file.dst);
          m.FS.writeFile(`${file.dst}/${file.src.match(/[^/]+$/)[0]}`, data);
          emit({ type: 'progress', done: ++done, total: files.length, file: file.src });
        }));
      } finally {
        m.removeRunDependency('pangea-arena-fs');
      }
    }],
  });
  emit({ type: 'ready' });

  return {
    module,
    /** Change the gateway URL before the next connect. */
    setWebSocketUrl(url) { websocket.url = url; },
  };
}
