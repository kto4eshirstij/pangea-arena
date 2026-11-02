// WebSocket -> UDP gateway for the Emscripten build of the Pangea Arena client.
//
// The Emscripten socket emulation (SOCKFS) sends every UDP datagram of the game
// as one binary WebSocket message, so the gateway maps frames to datagrams 1:1.
// Each WebSocket gets its own UDP socket towards 127.0.0.1:<udp_port>, so the
// game server sees every browser as a distinct ip:port peer.
//
// URL layout: ws://<listen>/<udp_port> (nginx publishes it as /arena-ws/<udp_port>).
// See docs/network.md for the details of the framing.

import { createSocket, type Socket } from "node:dgram";
import { createServer, type IncomingMessage, type Server } from "node:http";
import { WebSocketServer, type WebSocket, type RawData } from "ws";

export interface GatewayOptions {
  listenHost?: string;
  listenPort: number;
  udpHost?: string;
  /** Allowed UDP ports (inclusive). */
  minPort?: number;
  maxPort?: number;
  /** Max concurrent WebSockets per UDP port. */
  maxPerPort?: number;
  /** Idle timeout in ms (no traffic in either direction). */
  idleMs?: number;
  /** Optional extra check, e.g. "is there a running match on this port". */
  allowPort?: (port: number) => boolean;
  /** Overrides max connections per port (e.g. FFA with more players). */
  limitForPort?: (port: number) => number | undefined;
  log?: (msg: string) => void;
}

/** The SOCKFS "port" handshake: FF FF FF FF 'p' 'o' 'r' 't' hi lo. */
export function isPortHandshake(buf: Buffer): boolean {
  return (
    buf.length === 10 &&
    buf[0] === 0xff && buf[1] === 0xff && buf[2] === 0xff && buf[3] === 0xff &&
    buf[4] === 0x70 && buf[5] === 0x6f && buf[6] === 0x72 && buf[7] === 0x74
  );
}

export function parsePortFromPath(url: string | undefined): number | null {
  if (!url) return null;
  const path = url.split("?")[0];
  const m = /^\/(?:arena-ws\/)?(\d{1,5})\/?$/.exec(path);
  if (!m) return null;
  const port = Number(m[1]);
  return port > 0 && port < 65536 ? port : null;
}

function toBuffer(data: RawData): Buffer {
  if (Buffer.isBuffer(data)) return data;
  if (Array.isArray(data)) return Buffer.concat(data);
  return Buffer.from(data as ArrayBuffer);
}

export interface Gateway {
  server: Server;
  close(): Promise<void>;
  connections(port: number): number;
}

export function startGateway(opts: GatewayOptions): Promise<Gateway> {
  const {
    listenHost = "0.0.0.0",
    listenPort,
    udpHost = "127.0.0.1",
    minPort = 27960,
    maxPort = 27979,
    maxPerPort = 4,
    idleMs = 60_000,
    allowPort,
    limitForPort,
    log = (m: string) => console.log(`[gateway] ${m}`),
  } = opts;

  const perPort = new Map<number, Set<WebSocket>>();
  const server = createServer((_req, res) => {
    res.writeHead(426, { "content-type": "text/plain" });
    res.end("WebSocket only\n");
  });
  const wss = new WebSocketServer({ noServer: true, perMessageDeflate: false, maxPayload: 64 * 1024 });

  server.on("upgrade", (req: IncomingMessage, sock, head) => {
    const port = parsePortFromPath(req.url);
    const reject = (code: number, why: string) => {
      log(`reject ${req.socket.remoteAddress} ${req.url}: ${why}`);
      sock.write(`HTTP/1.1 ${code} ${why}\r\nConnection: close\r\n\r\n`);
      sock.destroy();
    };
    if (port === null || port < minPort || port > maxPort) return reject(404, "Bad port");
    if (allowPort && !allowPort(port)) return reject(404, "No match");
    const limit = limitForPort?.(port) ?? maxPerPort;
    if ((perPort.get(port)?.size ?? 0) >= limit) return reject(429, "Too many connections");
    wss.handleUpgrade(req, sock, head, (ws) => bridge(ws, port, req));
  });

  function bridge(ws: WebSocket, port: number, req: IncomingMessage) {
    const peer = (req.headers["x-forwarded-for"] as string | undefined)?.split(",")[0].trim() ||
      req.socket.remoteAddress || "?";
    let set = perPort.get(port);
    if (!set) perPort.set(port, (set = new Set()));
    set.add(ws);

    const udp: Socket = createSocket("udp4");
    let closed = false;
    let lastTraffic = Date.now();
    let toUdp = 0, toWs = 0;

    const close = (why: string) => {
      if (closed) return;
      closed = true;
      clearInterval(idleTimer);
      set!.delete(ws);
      if (set!.size === 0) perPort.delete(port);
      try { udp.close(); } catch { /* already closed */ }
      if (ws.readyState === ws.OPEN || ws.readyState === ws.CONNECTING) ws.close(1000, why.slice(0, 120));
      log(`close ${peer} -> :${port} (${why}) in=${toUdp} out=${toWs}`);
    };

    const idleTimer = setInterval(() => {
      if (Date.now() - lastTraffic > idleMs) close("idle");
    }, Math.min(idleMs, 5_000));

    udp.on("message", (msg) => {
      lastTraffic = Date.now();
      toWs++;
      if (ws.readyState === ws.OPEN) ws.send(msg, { binary: true });
    });
    udp.on("error", (e) => close(`udp error: ${e.message}`));
    let connected = false;
    const pending: Buffer[] = [];
    udp.connect(port, udpHost, () => {
      connected = true;
      log(`open ${peer} -> ${udpHost}:${port}`);
      for (const b of pending.splice(0)) udp.send(b);
    });

    ws.on("message", (data, isBinary) => {
      if (!isBinary) return;
      const buf = toBuffer(data);
      lastTraffic = Date.now();
      if (isPortHandshake(buf)) return; // SOCKFS bookkeeping, not game data
      toUdp++;
      if (!connected) { if (pending.length < 32) pending.push(buf); return; }
      udp.send(buf);
    });
    ws.on("close", () => close("ws closed"));
    ws.on("error", (e) => close(`ws error: ${e.message}`));
  }

  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(listenPort, listenHost, () => {
      log(`listening ws://${listenHost}:${listenPort}/<udp_port> -> udp ${udpHost}:${minPort}-${maxPort}`);
      resolve({
        server,
        connections: (port) => perPort.get(port)?.size ?? 0,
        close: () => new Promise<void>((res) => {
          for (const s of perPort.values()) for (const ws of s) ws.terminate();
          wss.close();
          server.close(() => res());
        }),
      });
    });
  });
}
