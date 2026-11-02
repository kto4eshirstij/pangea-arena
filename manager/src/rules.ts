// Match request validation and mapping of Pangea rules to ioq3ded arguments.

export type Mode = "duel" | "ffa";
export type Arsenal = "full" | "rail" | "rocket" | "melee";

export interface Player {
  ticket: string;
  name?: string;
}

export interface Rules {
  fraglimit: number;
  timelimit: number;
  arsenal: Arsenal;
  instagib: boolean;
  powerups: boolean;
  items: boolean;
  warmup: number;
  bots: number;
}

export interface MatchRequest {
  match_id: string;
  mode: Mode;
  map: string;
  players: Player[];
  rules: Rules;
}

export const DEFAULT_RULES: Record<Mode, Rules> = {
  duel: { fraglimit: 10, timelimit: 10, arsenal: "full", instagib: false, powerups: true, items: true, warmup: 10, bots: 0 },
  ffa: { fraglimit: 20, timelimit: 12, arsenal: "full", instagib: false, powerups: true, items: true, warmup: 15, bots: 0 },
};

export const FFA_MAX_CLIENTS = 8;
export const DUEL_SPECTATORS = 2;
/** Names given to bots in FFA, in order. All exist in OpenArena's botfiles. */
export const BOT_NAMES = ["sarge", "grism", "kyonshi"];

const TICKET_RE = /^[A-Za-z0-9_-]{1,63}$/;
const ID_RE = /^[A-Za-z0-9_.-]{1,64}$/;

export class ValidationError extends Error {}

function int(v: unknown, name: string, min: number, max: number): number {
  if (typeof v !== "number" || !Number.isInteger(v) || v < min || v > max) {
    throw new ValidationError(`${name}: целое ${min}..${max}`);
  }
  return v;
}

function bool(v: unknown, name: string): boolean {
  if (typeof v !== "boolean") throw new ValidationError(`${name}: true/false`);
  return v;
}

/** Validates an untrusted POST /matches body. Missing rules take mode defaults. */
export function parseMatchRequest(body: unknown, allowedMaps: Record<Mode, string[]>): MatchRequest {
  if (!body || typeof body !== "object") throw new ValidationError("тело запроса — JSON-объект");
  const b = body as Record<string, unknown>;
  if (typeof b.match_id !== "string" || !ID_RE.test(b.match_id)) throw new ValidationError("match_id: [A-Za-z0-9_.-]{1,64}");
  if (b.mode !== "duel" && b.mode !== "ffa") throw new ValidationError("mode: duel | ffa");
  const mode = b.mode as Mode;
  if (typeof b.map !== "string" || !allowedMaps[mode].includes(b.map)) {
    throw new ValidationError(`map: одна из ${allowedMaps[mode].join(", ")}`);
  }
  if (!Array.isArray(b.players)) throw new ValidationError("players: массив");
  const players: Player[] = b.players.map((p, i) => {
    if (!p || typeof p !== "object") throw new ValidationError(`players[${i}]: объект`);
    const { ticket, name } = p as Record<string, unknown>;
    if (typeof ticket !== "string" || !TICKET_RE.test(ticket)) throw new ValidationError(`players[${i}].ticket: [A-Za-z0-9_-]{1,63}`);
    if (name !== undefined && typeof name !== "string") throw new ValidationError(`players[${i}].name: строка`);
    return { ticket, name: name as string | undefined };
  });
  if (new Set(players.map((p) => p.ticket)).size !== players.length) throw new ValidationError("players: билеты повторяются");

  const r = { ...DEFAULT_RULES[mode], ...((b.rules as object) ?? {}) } as Record<string, unknown>;
  const rules: Rules = {
    fraglimit: int(r.fraglimit, "rules.fraglimit", 1, 100),
    timelimit: int(r.timelimit, "rules.timelimit", 1, 60),
    arsenal: ((): Arsenal => {
      if (r.arsenal === "full" || r.arsenal === "rail" || r.arsenal === "rocket" || r.arsenal === "melee") return r.arsenal;
      throw new ValidationError("rules.arsenal: full | rail | rocket | melee");
    })(),
    instagib: bool(r.instagib, "rules.instagib"),
    powerups: bool(r.powerups, "rules.powerups"),
    items: bool(r.items, "rules.items"),
    warmup: int(r.warmup, "rules.warmup", 0, 60),
    bots: int(r.bots, "rules.bots", 0, 3),
  };

  if (mode === "duel") {
    if (players.length !== 2) throw new ValidationError("duel: ровно 2 игрока");
    if (rules.bots !== 0) throw new ValidationError("duel: боты не допускаются");
  } else {
    if (players.length < 2) throw new ValidationError("ffa: минимум 2 игрока");
    if (players.length + rules.bots > FFA_MAX_CLIENTS) throw new ValidationError(`ffa: игроков + ботов не больше ${FFA_MAX_CLIENTS}`);
  }
  return { match_id: b.match_id, mode, map: b.map, players, rules };
}

export function maxClients(req: MatchRequest): number {
  return req.mode === "duel" ? 2 + DUEL_SPECTATORS : Math.min(req.players.length + req.rules.bots, FFA_MAX_CLIENTS);
}

/** Warmup value used while waiting for everybody in FFA (re-set to rules.warmup at start). */
export const HOLD_WARMUP = 3600;

export interface ServerPaths {
  basepath: string;   // directory containing baseoa/
  homepath: string;   // per-match writable dir
  basegame: string;   // "baseoa"
}

export interface ServerLaunch {
  /** Command line: only startup cvars, then +exec and +map (ioq3 keeps at most 32 "+" commands). */
  args: string[];
  /** Contents of <homepath>/<basegame>/match.cfg with the match rules. */
  config: string;
}

/** ioq3ded command line + match.cfg for a match. */
export function serverLaunch(req: MatchRequest, port: number, paths: ServerPaths): ServerLaunch {
  const r = req.rules;
  const set = (k: string, v: string | number) => ["+set", k, String(v)];
  const cvars: [string, string | number][] = [
    ["sv_hostname", `pangea-${req.match_id}`],
    ["sv_pure", 0],
    ["sv_fps", 40],
    ["g_log", "games.log"],
    ["g_logsync", 1],
    ["g_gametype", req.mode === "duel" ? 1 : 0],
    ["sv_maxclients", maxClients(req)],
    ["fraglimit", r.fraglimit],
    ["timelimit", r.timelimit],
    ["g_doWarmup", 1],
    // FFA holds in warmup until every ticket is in (or the join timeout); see Match.begin
    ["g_warmup", req.mode === "ffa" ? HOLD_WARMUP : r.warmup],
    ["g_forcerespawn", 3],
    ["g_allowVote", 0],
    ["bot_enable", r.bots > 0 ? 1 : 0],
    ["g_pangea_tickets", req.players.map((p) => p.ticket).join(",")],
    ["g_pangea_arsenal", r.arsenal],
    ["g_pangea_instagib", r.instagib ? 1 : 0],
    ["g_pangea_powerups", r.powerups ? 1 : 0],
    ["g_pangea_items", r.items ? 1 : 0],
    ["g_pangea_bots", r.bots],
    ["g_pangea_autoexit", 1],
  ];
  const config = `// generated by pangea-arena-manager for match ${req.match_id}\n` +
    cvars.map(([k, v]) => `set ${k} "${v}"`).join("\n") + "\n";
  return {
    args: [
      ...set("dedicated", 1),
      ...set("net_ip", "127.0.0.1"),
      ...set("net_port", port),
      ...set("fs_basepath", paths.basepath),
      ...set("fs_homepath", paths.homepath),
      ...set("com_basegame", paths.basegame),
      "+exec", "match.cfg",
      "+map", req.map,
    ],
    config,
  };
}
