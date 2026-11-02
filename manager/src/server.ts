// HTTP API of the match manager (127.0.0.1 only, X-Arena-Secret required).
//
//   POST /matches               -> 201 { port, ws_path, expires_at }
//   GET  /matches               -> debug list
//   POST /matches/<id>/cancel   -> 200 { ok: true }
//   GET  /health                -> 200 (no secret)

import { spawn } from "node:child_process";
import { timingSafeEqual } from "node:crypto";
import { mkdirSync, createWriteStream, writeFileSync } from "node:fs";
import { createServer, type IncomingMessage, type Server, type ServerResponse } from "node:http";
import { join } from "node:path";
import { Match, type ChildLike, type MatchTimings } from "./match.js";
import { Reporter } from "./reporter.js";
import { maxClients, parseMatchRequest, serverLaunch, ValidationError, type MatchRequest, type Mode } from "./rules.js";

export interface ManagerConfig {
  secret: string;
  ioq3ded: string;
  basepath: string;
  basegame: string;
  stateDir: string;
  minPort: number;
  maxPort: number;
  maps: Record<Mode, string[]>;
  maxMatches: number;
  /** Override for tests. */
  spawnServer?: (req: MatchRequest, port: number, args: string[]) => ChildLike;
  timings?: (req: MatchRequest) => MatchTimings;
  log?: (m: string) => void;
}

export class Manager {
  readonly matches = new Map<string, Match>();
  constructor(private cfg: ManagerConfig, private reporter: Reporter) {}

  private log(m: string): void {
    (this.cfg.log ?? ((s: string) => console.log(`[manager] ${s}`)))(m);
  }

  /** Running (not finished) match on a UDP port. */
  matchOnPort(port: number): Match | undefined {
    for (const m of this.matches.values()) if (m.port === port && m.state !== "finished") return m;
    return undefined;
  }

  private freePort(): number | null {
    for (let p = this.cfg.minPort; p <= this.cfg.maxPort; p++) if (!this.matchOnPort(p)) return p;
    return null;
  }

  private active(): number {
    return [...this.matches.values()].filter((m) => m.state !== "finished").length;
  }

  create(body: unknown): { status: number; json: unknown } {
    let req: MatchRequest;
    try {
      req = parseMatchRequest(body, this.cfg.maps);
    } catch (e) {
      if (e instanceof ValidationError) return { status: 400, json: { error: e.message } };
      throw e;
    }
    const existing = this.matches.get(req.match_id);
    if (existing && existing.state !== "finished") return { status: 409, json: { error: "матч уже идёт", port: existing.port } };
    if (this.active() >= this.cfg.maxMatches) return { status: 503, json: { error: "все арены заняты" } };
    const port = this.freePort();
    if (port === null) return { status: 503, json: { error: "нет свободного порта" } };

    const home = join(this.cfg.stateDir, "matches", req.match_id);
    mkdirSync(join(home, this.cfg.basegame), { recursive: true });
    const { args, config } = serverLaunch(req, port, { basepath: this.cfg.basepath, homepath: home, basegame: this.cfg.basegame });
    writeFileSync(join(home, this.cfg.basegame, "match.cfg"), config);
    const spawnServer = () => {
      if (this.cfg.spawnServer) return this.cfg.spawnServer(req, port, args);
      const child = spawn(this.cfg.ioq3ded, args, { stdio: ["pipe", "pipe", "pipe"] });
      const out = createWriteStream(join(home, "console.log"));
      child.stdout.pipe(out);
      child.stderr.pipe(out);
      return child as unknown as ChildLike;
    };
    const match = new Match(req, port, spawnServer, this.cfg.timings?.(req));
    match.on("log", (m: string) => this.log(`${req.match_id}: ${m}`));
    match.on("running", () => this.log(`${req.match_id}: all in, match running`));
    match.on("finished", (r) => {
      this.log(`${req.match_id}: finished ${JSON.stringify(r)}`);
      this.reporter.submit(r);
    });
    this.matches.set(req.match_id, match);
    match.start();
    this.log(`${req.match_id}: ${req.mode} on ${req.map}, port ${port}, ${req.players.length} players`);
    this.gc();
    return {
      status: 201,
      json: { port, ws_path: `/arena-ws/${port}`, expires_at: new Date(match.expiresAt).toISOString() },
    };
  }

  cancel(id: string): { status: number; json: unknown } {
    const m = this.matches.get(id);
    if (!m) return { status: 404, json: { error: "нет такого матча" } };
    if (m.state === "finished") return { status: 409, json: { error: "матч уже закончен", result: m.result } };
    m.cancel();
    return { status: 200, json: { ok: true } };
  }

  list() {
    return [...this.matches.values()].map((m) => m.summary());
  }

  /** Max WebSocket connections for a port: players (+ spectators in duel) + reconnect slack. */
  wsLimit(port: number): number | undefined {
    const m = this.matchOnPort(port);
    return m ? maxClients(m.req) + 2 : undefined;
  }

  /** Forget finished matches older than an hour. */
  private gc(): void {
    const cutoff = Date.now() - 3_600_000;
    for (const [id, m] of this.matches) if (m.state === "finished" && m.createdAt < cutoff) this.matches.delete(id);
  }

  stopAll(): void {
    for (const m of this.matches.values()) m.cancel();
  }
}

function secretOk(req: IncomingMessage, secret: string): boolean {
  const got = Buffer.from(String(req.headers["x-arena-secret"] ?? ""));
  const want = Buffer.from(secret);
  return got.length === want.length && timingSafeEqual(got, want);
}

async function readJson(req: IncomingMessage, limit = 64 * 1024): Promise<unknown> {
  let size = 0;
  const chunks: Buffer[] = [];
  for await (const c of req) {
    size += (c as Buffer).length;
    if (size > limit) throw new ValidationError("слишком большое тело");
    chunks.push(c as Buffer);
  }
  try {
    return JSON.parse(Buffer.concat(chunks).toString("utf8") || "null");
  } catch {
    throw new ValidationError("некорректный JSON");
  }
}

export function createApi(manager: Manager, secret: string): Server {
  return createServer(async (req: IncomingMessage, res: ServerResponse) => {
    const send = (status: number, json: unknown) => {
      res.writeHead(status, { "content-type": "application/json; charset=utf-8" });
      res.end(JSON.stringify(json));
    };
    try {
      const url = (req.url ?? "/").split("?")[0];
      if (req.method === "GET" && url === "/health") return send(200, { ok: true });
      if (!secretOk(req, secret)) return send(401, { error: "unauthorized" });
      if (req.method === "POST" && url === "/matches") {
        const r = manager.create(await readJson(req));
        return send(r.status, r.json);
      }
      if (req.method === "GET" && url === "/matches") return send(200, manager.list());
      const m = /^\/matches\/([^/]+)\/cancel$/.exec(url);
      if (req.method === "POST" && m) {
        const r = manager.cancel(decodeURIComponent(m[1]));
        return send(r.status, r.json);
      }
      return send(404, { error: "not found" });
    } catch (e) {
      if (e instanceof ValidationError) return send(400, { error: e.message });
      send(500, { error: (e as Error).message });
    }
  });
}
