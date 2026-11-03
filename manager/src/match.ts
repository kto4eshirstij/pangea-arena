// Life cycle of one match: one ioq3ded process, its log, and the final result.

import { EventEmitter } from "node:events";
import type { Readable, Writable } from "node:stream";
import { computePlaces, exitReason, MatchLog, parseLine, type ExitReason, type MatchResult, type LogEvent, type Place } from "./logparse.js";
import { botCommands, type MatchRequest } from "./rules.js";

export interface ChildLike extends EventEmitter {
  stdout: Readable | null;
  stderr?: Readable | null;
  stdin: Writable | null;
  kill(signal?: NodeJS.Signals): boolean;
  // emits "exit" (code, signal)
}

export interface MatchTimings {
  /** Everybody must connect within this time (duel: no-show; ffa: start with >= 2). */
  joinTimeoutMs: number;
  /** A duel player who dropped may reconnect within this time, else forfeit. */
  reconnectGraceMs: number;
  /** Hard cap on the whole process lifetime. */
  maxLifetimeMs: number;
  /** Time between "Exit:" and killing a server that did not quit by itself. */
  exitKillMs: number;
}

export const DEFAULT_TIMINGS = (req: MatchRequest): MatchTimings => ({
  joinTimeoutMs: 3 * 60_000,
  reconnectGraceMs: 30_000,
  maxLifetimeMs: (req.rules.timelimit + 3 + 2) * 60_000 + req.rules.warmup * 1000 + 60_000,
  exitKillMs: 15_000,
});

export type MatchState = "starting" | "waiting" | "running" | "finished";

export interface Clock {
  now(): number;
  setTimeout(fn: () => void, ms: number): unknown;
  clearTimeout(h: unknown): void;
}

export const realClock: Clock = {
  now: () => Date.now(),
  setTimeout: (fn, ms) => setTimeout(fn, ms),
  clearTimeout: (h) => clearTimeout(h as NodeJS.Timeout),
};

export class Match extends EventEmitter {
  readonly log: MatchLog;
  state: MatchState = "starting";
  readonly createdAt: number;
  startedAt: number | null = null;   // last InitGame while running (= after warmup map_restart)
  result: MatchResult | null = null;
  private child: ChildLike | null = null;
  private timers = new Map<string, unknown>();
  private bufs: Record<string, string> = { out: "", err: "" };
  private botsAdded = false;
  private killedFor: ExitReason | null = null;

  constructor(
    readonly req: MatchRequest,
    readonly port: number,
    private spawnServer: () => ChildLike,
    readonly timings: MatchTimings = DEFAULT_TIMINGS(req),
    private clock: Clock = realClock,
  ) {
    super();
    this.createdAt = clock.now();
    this.log = new MatchLog(new Map(req.npcs.map((n) => [n.latin.toLowerCase(), n.key])));
  }

  /** Tickets of the humans (NPC bots have none). */
  get tickets(): string[] {
    return this.req.players.map((p) => p.ticket);
  }

  /** Internal keys of the NPC bots ("npc:<i>"); they never leave early. */
  get npcKeys(): string[] {
    return this.req.npcs.map((n) => n.key);
  }

  get expiresAt(): number {
    return this.createdAt + this.timings.joinTimeoutMs;
  }

  start(): void {
    const child = this.spawnServer();
    this.child = child;
    this.state = "waiting";
    // ioq3ded prints its console to stderr (no tty) and some lines to stdout
    for (const [name, stream] of [["out", child.stdout], ["err", child.stderr]] as const) {
      stream?.setEncoding("utf8");
      stream?.on("data", (chunk: string) => this.onData(name, chunk));
    }
    child.on("exit", (code: number | null, signal: string | null) => this.onExit(code, signal));
    child.on("error", (e: Error) => { this.emit("log", `spawn error: ${e.message}`); this.onExit(null, "error"); });
    this.timer("join", this.timings.joinTimeoutMs, () => this.onJoinTimeout());
    this.timer("life", this.timings.maxLifetimeMs, () => this.kill("crash"));
  }

  cancel(): void {
    if (this.state === "finished") return;
    this.kill("cancelled");
  }

  /** Writes a console command to the server. */
  command(cmd: string): void {
    this.child?.stdin?.write(cmd + "\n");
  }

  // --- log handling -------------------------------------------------------

  private onData(stream: "out" | "err", chunk: string): void {
    this.bufs[stream] += chunk;
    let i: number;
    while ((i = this.bufs[stream].indexOf("\n")) >= 0) {
      const line = this.bufs[stream].slice(0, i);
      this.bufs[stream] = this.bufs[stream].slice(i + 1);
      this.emit("line", line);
      const ev = parseLine(line);
      if (ev) this.onEvent(ev);
    }
  }

  onEvent(ev: LogEvent): void {
    if (this.state === "finished") return;
    this.log.apply(ev);
    switch (ev.kind) {
      case "initgame":
        if (!this.botsAdded && (this.req.rules.bots > 0 || this.req.npcs.length > 0)) {
          this.botsAdded = true;
          for (const cmd of botCommands(this.req)) this.command(cmd);
        }
        if (this.state === "running") this.startedAt = this.clock.now();
        break;
      case "ticket":
        if (ev.ticket === "bot") break;
        this.clear(`grace:${ev.ticket}`);
        if (this.state === "waiting" && this.tickets.every((t) => this.log.present.has(t))) this.begin();
        break;
      case "disconnect":
        this.onHumanLeft();
        break;
      case "exit":
        this.clear("join");
        this.timer("exitkill", this.timings.exitKillMs, () => this.kill(null));
        break;
      case "quit":
        break;
    }
  }

  private onHumanLeft(): void {
    if (this.log.exitText !== null) return;
    for (const t of this.log.gone) {
      if (this.req.mode === "duel" && this.state === "running" && !this.timers.has(`grace:${t}`)) {
        this.timer(`grace:${t}`, this.timings.reconnectGraceMs, () => {
          if (this.log.gone.has(t)) this.kill("forfeit");
        });
      }
    }
    if (this.req.mode === "ffa" && this.state === "running" && this.log.present.size === 0) {
      this.kill("forfeit");
    }
  }

  private begin(): void {
    this.state = "running";
    this.startedAt = this.clock.now();
    this.clear("join");
    if (this.req.mode === "ffa") this.command(`g_warmup ${this.req.rules.warmup}`);
    this.emit("running");
  }

  private onJoinTimeout(): void {
    if (this.state !== "waiting") return;
    const present = this.tickets.filter((t) => this.log.present.has(t));
    if (this.req.mode === "ffa" && present.length >= 1 && present.length + this.req.npcs.length >= 2) {
      this.begin();
      return;
    }
    this.kill("no_show");
  }

  // --- end of match -------------------------------------------------------

  private kill(reason: ExitReason | null): void {
    if (this.state === "finished") return;
    if (reason) this.killedFor = reason;
    if (this.child) {
      this.child.kill("SIGTERM");
      this.timer("sigkill", 5_000, () => this.child?.kill("SIGKILL"));
    } else {
      this.onExit(null, "SIGTERM");
    }
  }

  private onExit(code: number | null, signal: string | null): void {
    if (this.state === "finished") return;
    for (const h of this.timers.values()) this.clock.clearTimeout(h);
    this.timers.clear();
    this.result = this.buildResult();
    this.state = "finished";
    this.emit("log", `server exited code=${code} signal=${signal} reason=${this.result.reason}`);
    this.emit("finished", this.result);
  }

  buildResult(): MatchResult {
    const L = this.log;
    const now = this.clock.now();
    const fromExit = L.exitText !== null ? exitReason(L.exitText) : null;
    // A real "Exit:" wins over our kill reason only if we did not end the match ourselves first.
    const reason: ExitReason = this.killedFor ?? fromExit ?? "crash";
    const neverCame = this.tickets.filter((t) => !L.seen.has(t));
    const leftEarly = this.tickets.filter((t) => neverCame.includes(t) || L.gone.has(t));

    let scores: { ticket: string; score: number }[] = [];
    if ((reason === "fraglimit" || reason === "timelimit") && L.scores.length) {
      scores = L.scores;
    } else if (reason === "no_show" || reason === "forfeit") {
      // whoever stayed wins (NPC bots always stay); ties share the place
      scores = this.tickets.filter((t) => L.present.has(t)).map((t) => ({ ticket: t, score: 0 }));
      if (scores.length || reason === "forfeit" || this.req.mode === "duel") {
        scores = scores.concat(this.npcKeys.map((k) => ({ ticket: k, score: 0 })));
      }
    }
    const raw = reason === "crash" || reason === "cancelled" ? [] : computePlaces(scores, [...this.tickets, ...this.npcKeys], leftEarly);
    const byKey = new Map(this.req.npcs.map((n) => [n.key, n]));
    const places: Place[] = raw.map((p) => {
      const n = p.ticket ? byKey.get(p.ticket) : undefined;
      return n ? { npc: true, name: n.name, score: p.score, place: p.place } : p;
    });
    return {
      match_id: this.req.match_id,
      mode: this.req.mode,
      reason,
      duration_s: Math.max(0, Math.round((now - (this.startedAt ?? this.createdAt)) / 1000)),
      places,
      left_early: leftEarly,
      ...(this.req.npcs.length ? { npc_names: Object.fromEntries(this.req.npcs.map((n) => [n.latin, n.name])) } : {}),
    };
  }

  // --- timers -------------------------------------------------------------

  private timer(name: string, ms: number, fn: () => void): void {
    this.clear(name);
    this.timers.set(name, this.clock.setTimeout(() => { this.timers.delete(name); fn(); }, ms));
  }

  private clear(name: string): void {
    const h = this.timers.get(name);
    if (h !== undefined) {
      this.clock.clearTimeout(h);
      this.timers.delete(name);
    }
  }

  summary() {
    return {
      match_id: this.req.match_id,
      mode: this.req.mode,
      map: this.req.map,
      port: this.port,
      state: this.state,
      created_at: new Date(this.createdAt).toISOString(),
      present: [...this.log.present],
      result: this.result,
    };
  }
}
