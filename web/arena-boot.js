// Pangea Arena boot wrapper for the Emscripten client (ES module).
//
//   import { bootArena } from './arena-boot.js';
//   const arena = await bootArena({
//     canvas, enginePath: '/static/arena/', dataPath: '/static/arena/',
//     configUrl: '/static/arena/arena-config.json', basegame: 'baseoa',
//     wsUrl: 'wss://pangea.pp.ua/arena-ws/27963',   // gateway URL for this match
//     connect: 'arena:27963', ticket: 'abc', name: 'Арн',
//     args: '+set cg_drawFPS 1',
//     onEvent: (e) => console.log(e),
//   });
//
// Events (onEvent), in load order:
//   {type:'engine', loaded, total}       bytes of ioquake3.wasm (total 0 = unknown)
//   {type:'pak', loaded, total}          bytes of all pak/QVM files of arena-config.json
//   {type:'progress', done, total, file} a pak file is written to MEMFS
//   {type:'ready'}                       runtime is up, the client starts connecting
//   {type:'arena-ready'}                 first snapshot of the match (CL_FirstSnapshot)
//   {type:'log', line, err?} · {type:'exit', code} · {type:'abort', what}
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

// fetch with byte progress: onBytes(delta, contentLength) per chunk; resolves to Uint8Array.
async function fetchBytes(url, onBytes) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url}: HTTP ${res.status}`);
  const total = Number(res.headers.get('Content-Length') || 0);
  onBytes(0, total);
  if (!res.body) {
    const buf = new Uint8Array(await res.arrayBuffer());
    onBytes(buf.byteLength, 0);
    return buf;
  }
  const reader = res.body.getReader();
  const chunks = [];
  let got = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value);
    got += value.byteLength;
    onBytes(value.byteLength, 0);
  }
  const out = new Uint8Array(got);
  let off = 0;
  for (const c of chunks) { out.set(c, off); off += c.byteLength; }
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

  const config = await fetch(configUrl).then((r) => (r.ok ? r.json() : {}));
  const dataURL = new URL(dataPath, location.href);
  const websocket = { url: wsUrl || 'ws://', subprotocol: 'binary' };

  const emit = (e) => { try { onEvent(e); } catch (err) { console.error(err); } };
  const engineURL = new URL(enginePath, location.href);

  // Engine: the wasm is fetched here (with progress) and handed over as wasmBinary.
  let wasmLoaded = 0, wasmTotal = 0;
  const [engine, wasmBinary] = await Promise.all([
    import(new URL(engineName + '.js', engineURL).href).then((m) => m.default),
    fetchBytes(new URL(engineName + '.wasm', engineURL), (delta, total) => {
      if (total) wasmTotal = total;
      wasmLoaded += delta;
      emit({ type: 'engine', loaded: wasmLoaded, total: wasmTotal });
    }),
  ]);

  const module = await engine({
    canvas,
    arguments: argv,
    websocket,
    wasmBinary: wasmBinary.buffer,
    locateFile: (file) => new URL(file, engineURL).href,
    print: (line) => { console.log(line); emit({ type: 'log', line }); },
    printErr: (line) => { console.warn(line); emit({ type: 'log', line, err: true }); },
    onExit: (code) => emit({ type: 'exit', code }),
    onAbort: (what) => emit({ type: 'abort', what: String(what) }),
    // called from CL_FirstSnapshot (code/client/cl_cgame.c) via EM_ASM
    onArenaReady: () => emit({ type: 'arena-ready' }),
    preRun: [async (m) => {
      m.addRunDependency('pangea-arena-fs');
      try {
        const files = (config[basegame] && config[basegame].files) || [];
        let done = 0, loaded = 0;
        // sizes from arena-config.json (tools/stage-web-slim.sh) give the total at once;
        // otherwise it grows as Content-Length headers arrive
        const known = files.every((f) => f.size > 0);
        let total = known ? files.reduce((a, f) => a + f.size, 0) : 0;
        emit({ type: 'pak', loaded, total });
        await Promise.all(files.map(async (file) => {
          let data;
          try {
            data = await fetchBytes(new URL(file.src, dataURL), (delta, len) => {
              if (len && !known) total += len;
              loaded += delta;
              emit({ type: 'pak', loaded, total });
            });
          } catch (err) {
            emit({ type: 'log', line: `missing ${file.src}: ${err.message}`, err: true });
            return;
          }
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
