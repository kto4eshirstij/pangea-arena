import { EventEmitter } from "node:events";
import { readFileSync } from "node:fs";
import { PassThrough } from "node:stream";
import { describe, expect, it } from "vitest";
import { Match, type Clock, type ChildLike, type MatchTimings } from "../src/match.js";
import { parseMatchRequest, serverLaunch, maxClients, translit, npcNames, botCommands, ValidationError, type MatchRequest } from "../src/rules.js";
import type { MatchResult } from "../src/logparse.js";

const MAPS = { duel: ["czest1tourney", "oa_dm7"], ffa: ["oa_dm4", "czest1dm"] };

class FakeClock implements Clock {
  t = 1_000_000;
  timers: { at: number; fn: () => void; id: number }[] = [];
  private n = 0;
  now() { return this.t; }
  setTimeout(fn: () => void, ms: number) { const id = ++this.n; this.timers.push({ at: this.t + ms, fn, id }); return id; }
  clearTimeout(h: unknown) { this.timers = this.timers.filter((x) => x.id !== h); }
  advance(ms: number) {
    const end = this.t + ms;
    for (;;) {
      this.timers.sort((a, b) => a.at - b.at);
      const next = this.timers[0];
      if (!next || next.at > end) break;
      this.timers.shift();
      this.t = next.at;
      next.fn();
    }
    this.t = end;
  }
}

class FakeServer extends EventEmitter implements ChildLike {
  stdout = new PassThrough();
  stdin = new PassThrough();
  commands: string[] = [];
  killed: string[] = [];
  constructor() {
    super();
    this.stdin.setEncoding("utf8");
    this.stdin.on("data", (d: string) => this.commands.push(...d.split("\n").filter(Boolean)));
  }
  kill(signal: NodeJS.Signals = "SIGTERM") { this.killed.push(signal); queueMicrotask(() => this.emit("exit", null, signal)); return true; }
  print(...lines: string[]) { this.stdout.write(lines.join("\n") + "\n"); }
  quit() { this.emit("exit", 0, null); }
}

const T: MatchTimings = { joinTimeoutMs: 180_000, reconnectGraceMs: 30_000, maxLifetimeMs: 3_600_000, exitKillMs: 15_000 };

function setup(body: object) {
  const req = parseMatchRequest(body, MAPS);
  const clock = new FakeClock();
  const srv = new FakeServer();
  const m = new Match(req, 27963, () => srv, T, clock);
  const done = new Promise<MatchResult>((r) => m.on("finished", r));
  m.start();
  return { req, clock, srv, m, done };
}
const tick = () => new Promise((r) => setTimeout(r, 5));

const duel = { match_id: "pvp-1", mode: "duel", map: "oa_dm7", players: [{ ticket: "aaa", name: "Арн" }, { ticket: "bbb", name: "Бер" }] };
const ffa = (n: number, rules: object = {}) => ({
  match_id: "pvp-2", mode: "ffa", map: "oa_dm4",
  players: Array.from({ length: n }, (_, i) => ({ ticket: `t${i + 1}` })), rules,
});

describe("rules", () => {
  it("fills mode defaults and maps them to ioq3ded args", () => {
    const req = parseMatchRequest(duel, MAPS);
    expect(req.rules).toMatchObject({ fraglimit: 10, timelimit: 10, warmup: 10, bots: 0, arsenal: "honor" });
    const { args, config } = serverLaunch(req, 27963, { basepath: "/c", homepath: "/h", basegame: "baseoa" });
    const a = args.join(" ");
    expect(a).toContain("+set net_port 27963");
    expect(a.endsWith("+exec match.cfg +map oa_dm7")).toBe(true);
    expect(args.filter((x) => x.startsWith("+")).length).toBeLessThanOrEqual(32);
    expect(config).toContain('set g_gametype "1"');
    expect(config).toContain('set sv_maxclients "4"');
    expect(config).toContain('set g_pangea_tickets "aaa,bbb"');
    expect(config).toContain('set g_warmup "10"');
    expect(config).toContain('set g_forcerespawn "3"');
    // a 0:0 at the timelimit ends as a draw after the overtime, not when the lifetime runs out
    expect(config).toContain('set g_pangea_overtime "120"');
  });

  it("ffa: defaults 20/12/15, maxclients = players + bots, held warmup", () => {
    const req = parseMatchRequest(ffa(3, { bots: 2, arsenal: "rail", instagib: true, powerups: false }), MAPS);
    expect(req.rules).toMatchObject({ fraglimit: 20, timelimit: 12, warmup: 15 });
    expect(maxClients(req)).toBe(5);
    const { config } = serverLaunch(req, 27960, { basepath: "/c", homepath: "/h", basegame: "baseoa" });
    expect(config).toContain('set g_gametype "0"');
    expect(config).toContain('set g_warmup "3600"');
    expect(config).toContain('set bot_enable "1"');
    expect(config).toContain('set g_pangea_arsenal "rail"\nset g_pangea_instagib "1"\nset g_pangea_powerups "0"');
  });

  it("rejects bad requests", () => {
    const bad = (b: object) => expect(() => parseMatchRequest(b, MAPS)).toThrow(ValidationError);
    bad({ ...duel, map: "q3dm17" });
    bad({ ...duel, players: [{ ticket: "a,b" }, { ticket: "c" }] });
    bad({ ...duel, players: [{ ticket: "a" }, { ticket: "a" }] });
    bad({ ...duel, players: [{ ticket: "a" }] });
    bad({ ...duel, rules: { bots: 1 } });
    bad(ffa(7, { bots: 2 }));
    bad({ ...duel, rules: { arsenal: "bfg" } });
    bad({ ...duel, match_id: "../x" });
  });
});

describe("duel life cycle", () => {
  it("normal finish by fraglimit, places from the scoreboard", async () => {
    const { clock, srv, done } = setup(duel);
    srv.print("InitGame: \\g_gametype\\1", "Pangea: ticket aaa client 0", "ClientConnect: 0", "ClientBegin: 0");
    srv.print("Pangea: ticket bbb client 1", "ClientConnect: 1", "ClientBegin: 1");
    await tick();
    clock.advance(10_000);
    srv.print("InitGame: \\g_gametype\\1");     // map_restart after warmup
    await tick();
    clock.advance(200_000);
    srv.print("Kill: 0 1 10: Arn killed Ber by MOD_RAILGUN", "Exit: Fraglimit hit.",
      "score: 10  ping: 40  client: 0 Arn", "score: 7  ping: 55  client: 1 Ber", "Pangea: quit");
    await tick();
    srv.quit();
    const r = await done;
    expect(r).toEqual({ match_id: "pvp-1", mode: "duel", reason: "fraglimit", duration_s: 200,
      places: [{ ticket: "aaa", score: 10, place: 1 }, { ticket: "bbb", score: 7, place: 2 }], left_early: [] });
  });

  it("no-show: the one who came wins after 3 minutes", async () => {
    const { clock, srv, done } = setup(duel);
    srv.print("InitGame: x", "Pangea: ticket bbb client 0", "ClientConnect: 0");
    await tick();
    clock.advance(180_000);
    const r = await done;
    expect(srv.killed).toContain("SIGTERM");
    expect(r.reason).toBe("no_show");
    expect(r.places).toEqual([{ ticket: "bbb", score: 0, place: 1 }, { ticket: "aaa", score: 0, place: 2 }]);
    expect(r.left_early).toEqual(["aaa"]);
  });

  it("no-show of both: no winner", async () => {
    const { clock, done } = setup(duel);
    clock.advance(180_000);
    const r = await done;
    expect(r.reason).toBe("no_show");
    expect(r.left_early).toEqual(["aaa", "bbb"]);
    expect(r.places.every((p) => p.place === 1)).toBe(true);
  });

  it("left early: forfeit after the reconnect grace, leaver is last", async () => {
    const { clock, srv, done } = setup(duel);
    srv.print("Pangea: ticket aaa client 0", "Pangea: ticket bbb client 1");
    await tick();
    clock.advance(60_000);
    srv.print("ClientDisconnect: 1");
    await tick();
    clock.advance(30_000);
    const r = await done;
    expect(r.reason).toBe("forfeit");
    expect(r.places).toEqual([{ ticket: "aaa", score: 0, place: 1 }, { ticket: "bbb", score: 0, place: 2 }]);
    expect(r.left_early).toEqual(["bbb"]);
  });

  it("reconnect within the grace keeps the match going", async () => {
    const { clock, srv, m } = setup(duel);
    srv.print("Pangea: ticket aaa client 0", "Pangea: ticket bbb client 1");
    await tick();
    srv.print("ClientDisconnect: 1");
    await tick();
    clock.advance(10_000);
    srv.print("Pangea: ticket bbb client 1");
    await tick();
    clock.advance(60_000);
    expect(m.state).toBe("running");
    expect(srv.killed).toEqual([]);
  });

  it("crash: process dies without Exit", async () => {
    const { srv, done } = setup(duel);
    srv.print("Pangea: ticket aaa client 0", "Pangea: ticket bbb client 1");
    await tick();
    srv.emit("exit", null, "SIGSEGV");
    const r = await done;
    expect(r.reason).toBe("crash");
    expect(r.places).toEqual([]);
  });

  it("cancel", async () => {
    const { m, done } = setup(duel);
    m.cancel();
    expect((await done).reason).toBe("cancelled");
  });
});

describe("closed arena tab", () => {
  it("kicks the client behind a closed WebSocket, and only it; not after the exit", async () => {
    const { srv, m } = setup(duel);
    srv.print("InitGame: x", "Pangea: ticket aaa client 0", "Pangea: addr client 0 127.0.0.1:40001",
      "Pangea: ticket bbb client 1", "Pangea: addr client 1 127.0.0.1:40002");
    await tick();
    m.peerClosed("127.0.0.1:49999");
    m.peerClosed("127.0.0.1:40002");
    expect(srv.commands).toEqual(["clientkick 1"]);
    // the kicked slot is gone: a second close of the same socket does nothing
    srv.print("ClientDisconnect: 1");
    await tick();
    m.peerClosed("127.0.0.1:40002");
    srv.print("Exit: Timelimit hit.");
    await tick();
    m.peerClosed("127.0.0.1:40001");
    expect(srv.commands).toEqual(["clientkick 1"]);
  });
});

describe("ffa life cycle", () => {
  it("waits for all tickets, then releases the warmup; adds bots", async () => {
    const { srv, m } = setup(ffa(3, { bots: 2 }));
    srv.print("InitGame: x");
    await tick();
    expect(srv.commands).toEqual(["addbot sarge 3", "addbot grism 3"]);
    srv.print("Pangea: ticket bot client 0", "Pangea: ticket bot client 1", "Pangea: ticket t1 client 2", "Pangea: ticket t2 client 3");
    await tick();
    expect(m.state).toBe("waiting");
    srv.print("Pangea: ticket t3 client 4");
    await tick();
    expect(m.state).toBe("running");
    expect(srv.commands.at(-1)).toBe("g_warmup 15");
  });

  it("starts on timeout with >= 2 players; absentees are left_early and last; bots are not placed", async () => {
    const { clock, srv, m, done } = setup(ffa(3, { bots: 1 }));
    srv.print("InitGame: x", "Pangea: ticket bot client 0", "Pangea: ticket t1 client 1", "Pangea: ticket t2 client 2");
    await tick();
    clock.advance(180_000);
    expect(m.state).toBe("running");
    srv.print("InitGame: x");
    await tick();
    clock.advance(300_000);
    srv.print("Exit: Timelimit hit.", "score: 9  ping: 0  client: 0 Sarge", "score: 5  ping: 30  client: 2 B",
      "score: 5  ping: 30  client: 1 A", "ClientDisconnect: 1", "Pangea: quit");
    await tick();
    srv.quit();
    const r = await done;
    expect(r.reason).toBe("timelimit");
    expect(r.duration_s).toBe(300);
    expect(r.places).toEqual([
      { ticket: "t2", score: 5, place: 1 }, { ticket: "t1", score: 5, place: 1 }, { ticket: "t3", score: 0, place: 3 }]);
    expect(r.left_early).toEqual(["t3"]);
  });

  it("no_show when fewer than 2 came", async () => {
    const { clock, srv, done } = setup(ffa(3));
    srv.print("Pangea: ticket t1 client 0");
    await tick();
    clock.advance(180_000);
    const r = await done;
    expect(r.reason).toBe("no_show");
    expect(r.places[0]).toEqual({ ticket: "t1", score: 0, place: 1 });
    expect(r.left_early).toEqual(["t2", "t3"]);
  });

  it("a player who leaves mid-match is left_early and last even with frags", async () => {
    const { srv, done } = setup(ffa(3));
    srv.print("Pangea: ticket t1 client 0", "Pangea: ticket t2 client 1", "Pangea: ticket t3 client 2", "InitGame: x");
    await tick();
    srv.print("ClientDisconnect: 2");
    srv.print("Exit: Fraglimit hit.", "score: 20  ping: 0  client: 0 A", "score: 3  ping: 0  client: 1 B", "Pangea: quit");
    await tick();
    srv.quit();
    const r = await done;
    expect(r.left_early).toEqual(["t3"]);
    expect(r.places.map((p) => [p.ticket, p.place])).toEqual([["t1", 1], ["t2", 2], ["t3", 3]]);
  });
});

describe("real ioq3ded logs (test/fixtures)", () => {
  const fixture = (n: string) => readFileSync(new URL(`./fixtures/${n}`, import.meta.url), "utf8");

  it("duel: fraglimit 3:0", async () => {
    const { srv, done } = setup({ ...duel, players: [{ ticket: "t1" }, { ticket: "t2" }] });
    srv.print(fixture("duel-bots.log"));
    await tick();
    srv.quit();
    const r = await done;
    expect(r.reason).toBe("fraglimit");
    expect(r.places).toEqual([{ ticket: "t1", score: 3, place: 1 }, { ticket: "t2", score: 0, place: 2 }]);
    expect(r.left_early).toEqual([]);
  });

  it("ffa: timelimit, ties share a place", async () => {
    const { srv, done, m } = setup(ffa(3));
    srv.print(fixture("ffa-bots.log"));
    await tick();
    expect(m.state).toBe("running");
    srv.quit();
    const r = await done;
    expect(r.reason).toBe("timelimit");
    expect(r.places).toEqual([
      { ticket: "t2", score: 1, place: 1 }, { ticket: "t1", score: 0, place: 2 }, { ticket: "t3", score: 0, place: 2 }]);
  });
});

// --- NPC fighters (Pangea part F4): named bots ---------------------------------

const ker = { npc: true, name: "Кер", bot: { model: "sarge", skill: 3 } };
const duelNpc = { match_id: "pvp-7", mode: "duel", map: "oa_dm7", players: [{ ticket: "t2", name: "Арн" }, ker] };

describe("npc: rules", () => {
  it("transliterates names for the engine fonts, unique", () => {
    expect(translit("Кер")).toBe("Ker");
    expect(translit("Щука Старый")).toBe("ShchukaStaryy");
    expect(translit("Ёж-17")).toBe("Ezh17");
    expect(translit("Очень Длинное Имя Наставника")).toHaveLength(15);
    expect(npcNames(["Кер", "Кер", "кер"])).toEqual(["Ker", "Ker2", "Ker3"]);
  });

  it("duel: one human + one npc is allowed; bot counts in g_pangea_bots, not in tickets", () => {
    const req = parseMatchRequest(duelNpc, MAPS);
    expect(req.players).toEqual([{ ticket: "t2", name: "Арн" }]);
    expect(req.npcs).toEqual([{ npc: true, name: "Кер", latin: "Ker", key: "npc:0", bot: { model: "sarge", skill: 3 } }]);
    const cfg = serverLaunch(req, 27990, { basepath: "/b", homepath: "/h", basegame: "baseoa" }).config;
    expect(cfg).toContain('set g_pangea_tickets "t2"');
    expect(cfg).toContain('set g_pangea_bots "1"');
    expect(cfg).toContain('set bot_enable "1"');
    expect(botCommands(req)).toEqual(["addbot sarge 3 free 0 Ker"]);
  });

  it("rejects: npc-only, three in a duel, unknown model, bad skill, too many in ffa", () => {
    const bad = (b: object) => expect(() => parseMatchRequest(b, MAPS)).toThrow(ValidationError);
    bad({ ...duelNpc, players: [ker, { ...ker, name: "Тур" }] });
    bad({ ...duelNpc, players: [{ ticket: "a" }, { ticket: "b" }, ker] });
    bad({ ...duelNpc, players: [{ ticket: "a" }, { ...ker, bot: { model: "doom" } }] });
    bad({ ...duelNpc, players: [{ ticket: "a" }, { ...ker, bot: { model: "sarge", skill: 9 } }] });
    bad({ ...ffa(5, { bots: 3 }), players: [...ffa(5).players, ker] });
  });

  it("ffa: npc entries add to rules.bots within 8 slots", () => {
    const req = parseMatchRequest({ ...ffa(2, { bots: 2 }), players: [...ffa(2).players, ker, { ...ker, name: "Тур", bot: { model: "grism", skill: 2 } }] }, MAPS);
    expect(maxClients(req)).toBe(6);
    expect(botCommands(req)).toEqual(["addbot sarge 3 free 0 Ker", "addbot grism 2 free 0 Tur", "addbot sarge 3", "addbot grism 3"]);
  });
});

describe("tier-0 arena (C6)", () => {
  const cfgOf = (req: MatchRequest) => serverLaunch(req, 27990, { basepath: "/b", homepath: "/h", basegame: "baseoa" }).config;

  it("defaults: honor in a duel, slaughter in ffa; the simulator arsenals still parse", () => {
    expect(parseMatchRequest(ffa(3), MAPS).rules.arsenal).toBe("slaughter");
    for (const a of ["full", "rail", "rocket", "melee", "honor", "slaughter"]) {
      expect(parseMatchRequest(ffa(3, { arsenal: a }), MAPS).rules.arsenal).toBe(a);
    }
  });

  it("passes the people of humans (by ticket) and npcs (by bot name) to g_pangea_races", () => {
    const req = parseMatchRequest({ ...duelNpc, players: [{ ticket: "t2", name: "Арн", race: "fey" }, { ...ker, race: "troll" }] }, MAPS);
    expect(req.players[0].race).toBe("fey");
    expect(req.npcs[0].race).toBe("troll");
    expect(cfgOf(req)).toContain('set g_pangea_races "t2=fey,Ker=troll"');
  });

  it("race is optional and must be lowercase latin", () => {
    expect(cfgOf(parseMatchRequest(ffa(3), MAPS))).toContain('set g_pangea_races ""');
    const bad = (b: object) => expect(() => parseMatchRequest(b, MAPS)).toThrow(ValidationError);
    bad({ ...ffa(2), players: [{ ticket: "a", race: "Тролль" }, { ticket: "b" }] });
    bad({ ...ffa(2), players: [{ ticket: "a", race: "x\"; quit" }, { ticket: "b" }] });
  });
});

describe("npc: life cycle", () => {
  it("adds the named bot after InitGame; the human alone starts the duel", async () => {
    const { srv, m } = setup(duelNpc);
    srv.print("InitGame: \\g_gametype\\1");
    await tick();
    expect(srv.commands).toEqual(["addbot sarge 3 free 0 Ker"]);
    srv.print("Pangea: ticket bot client 0", "ClientUserinfoChanged: 0 n\\Ker\\t\\0", "Pangea: ticket t2 client 1");
    await tick();
    expect(m.state).toBe("running");
  });

  it("real log: the npc wins 3:0 and is placed by name", async () => {
    const fixture = readFileSync(new URL("./fixtures/duel-npc.log", import.meta.url), "utf8");
    const { srv, done } = setup(duelNpc);
    srv.print(fixture);
    await tick();
    srv.quit();
    const r = await done;
    expect(r.reason).toBe("fraglimit");
    expect(r.places).toEqual([{ npc: true, name: "Кер", score: 3, place: 1 }, { ticket: "t2", score: 0, place: 2 }]);
    expect(r.npc_names).toEqual({ Ker: "Кер" });
  });

  it("human leaves: forfeit in favour of the npc", async () => {
    const { srv, clock, done } = setup(duelNpc);
    srv.print("InitGame:", "Pangea: ticket bot client 0", "ClientUserinfoChanged: 0 n\\Ker\\t\\0", "Pangea: ticket t2 client 1");
    await tick();
    srv.print("ClientDisconnect: 1");
    await tick();
    clock.advance(30_000);
    const r = await done;
    expect(r.reason).toBe("forfeit");
    expect(r.places).toEqual([{ npc: true, name: "Кер", score: 0, place: 1 }, { ticket: "t2", score: 0, place: 2 }]);
    expect(r.left_early).toEqual(["t2"]);
  });

  it("human never comes: no_show", async () => {
    const { clock, done } = setup(duelNpc);
    clock.advance(180_000);
    const r = await done;
    expect(r.reason).toBe("no_show");
    expect(r.left_early).toEqual(["t2"]);
  });

  it("ffa: npc bots are placed, plain bots are not", async () => {
    const { srv, done } = setup({ ...ffa(2, { bots: 1 }), players: [...ffa(2).players, ker] });
    srv.print("InitGame:", "Pangea: ticket t1 client 0", "Pangea: ticket t2 client 1",
      "Pangea: ticket bot client 2", "ClientUserinfoChanged: 2 n\\^1Ker^7\\t\\0",
      "Pangea: ticket bot client 3", "ClientUserinfoChanged: 3 n\\Sarge\\t\\0");
    await tick();
    srv.print("Exit: Fraglimit hit.", "score: 5  ping: 0  client: 2 ^1Ker^7", "score: 4  ping: 0  client: 3 Sarge",
      "score: 2  ping: 9  client: 0 Anna", "score: 1  ping: 9  client: 1 Bor");
    await tick();
    srv.quit();
    const r = await done;
    expect(r.places).toEqual([
      { npc: true, name: "Кер", score: 5, place: 1 }, { ticket: "t1", score: 2, place: 2 }, { ticket: "t2", score: 1, place: 3 }]);
  });
});
