// Match request validation and mapping of Pangea rules to ioq3ded arguments.

export type Mode = "duel" | "ffa";
/**
 * full | rail | rocket | melee — «симулятор», the stock OpenArena weapons;
 * honor | slaughter — tier-0 abilities (code/game/bg_pangea.h): дуэль чести (no fire) / бойня (everything).
 */
export type Arsenal = "full" | "rail" | "rocket" | "melee" | "honor" | "slaughter";
export const ARSENALS: Arsenal[] = ["full", "rail", "rocket", "melee", "honor", "slaughter"];

export interface Player {
  ticket: string;
  name?: string;
  /** People of the character (arena hand skins), e.g. "human", "troll", "fey". */
  race?: string;
  /** Faith (rites, slot 8): "sun" | "moon"; none = «Очаг». */
  faith?: string;
}

/** A Pangea NPC fighter: an ioq3 bot under the NPC's (transliterated) name. */
export interface NpcPlayer {
  npc: true;
  name: string;          // as in Pangea (Cyrillic)
  latin: string;         // in-game name: the engine fonts have no Cyrillic
  key: string;           // internal id in places ("npc:<i>")
  bot: { model: string; skill: number };
  race?: string;
  faith?: string;
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
  npcs: NpcPlayer[];
  rules: Rules;
}

export const DEFAULT_RULES: Record<Mode, Rules> = {
  duel: { fraglimit: 10, timelimit: 10, arsenal: "honor", instagib: false, powerups: true, items: true, warmup: 10, bots: 0 },
  ffa: { fraglimit: 20, timelimit: 12, arsenal: "slaughter", instagib: false, powerups: true, items: true, warmup: 15, bots: 0 },
};

export const FFA_MAX_CLIENTS = 8;
export const DUEL_SPECTATORS = 2;
/** Names given to bots in FFA, in order. All exist in OpenArena's botfiles. */
export const BOT_NAMES = ["sarge", "grism", "kyonshi"];

const TICKET_RE = /^[A-Za-z0-9_-]{1,63}$/;
/** A people key: lowercase latin, as in the arena's hand skins. */
const RACE_RE = /^[a-z_]{1,20}$/;

const FAITHS = ["sun", "moon"];

function faith(v: unknown, where: string): string | undefined {
  if (v === undefined || v === null || v === "") return undefined;
  if (typeof v !== "string" || !FAITHS.includes(v)) throw new ValidationError(`${where}.faith: ${FAITHS.join(" | ")}`);
  return v;
}

function race(v: unknown, where: string): string | undefined {
  if (v === undefined || v === null || v === "") return undefined;
  if (typeof v !== "string" || !RACE_RE.test(v)) throw new ValidationError(`${where}.race: [a-z_]{1,20}`);
  return v;
}
/** Longest in-game name of an NPC bot. */
export const NPC_NAME_MAX = 15;

const TRANSLIT: Record<string, string> = {
  а: "a", б: "b", в: "v", г: "g", д: "d", е: "e", ё: "e", ж: "zh", з: "z", и: "i", й: "y", к: "k", л: "l",
  м: "m", н: "n", о: "o", п: "p", р: "r", с: "s", т: "t", у: "u", ф: "f", х: "kh", ц: "ts", ч: "ch", ш: "sh",
  щ: "shch", ъ: "", ы: "y", ь: "", э: "e", ю: "yu", я: "ya",
};

/** "Кер Старый" -> "KerStaryy": Latin letters and digits only, capitalised words, <= NPC_NAME_MAX. */
export function translit(name: string): string {
  const words = name.split(/\s+/).map((w) => {
    let out = "";
    for (const ch of w) {
      const low = ch.toLowerCase();
      const t = TRANSLIT[low] ?? (/[a-z0-9]/i.test(ch) ? low : "");
      out += t;
    }
    return out.charAt(0).toUpperCase() + out.slice(1);
  });
  return (words.join("") || "Npc").slice(0, NPC_NAME_MAX);
}

/** Unique Latin names: a repeat gets a digit ("Ker", "Ker2"). */
export function npcNames(names: string[]): string[] {
  const used = new Set<string>();
  return names.map((n) => {
    const base = translit(n);
    let out = base;
    for (let i = 2; used.has(out.toLowerCase()); i++) out = base.slice(0, NPC_NAME_MAX - String(i).length) + i;
    used.add(out.toLowerCase());
    return out;
  });
}
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
  const players: Player[] = [];
  const npcRaw: { name: string; bot: { model: string; skill: number }; race?: string; faith?: string }[] = [];
  b.players.forEach((p, i) => {
    if (!p || typeof p !== "object") throw new ValidationError(`players[${i}]: объект`);
    const { ticket, name, npc, bot } = p as Record<string, unknown>;
    const r = race((p as Record<string, unknown>).race, `players[${i}]`);
    const f = faith((p as Record<string, unknown>).faith, `players[${i}]`);
    const kin = { ...(r ? { race: r } : {}), ...(f ? { faith: f } : {}) };
    if (npc === true) {
      if (typeof name !== "string" || !name.trim() || name.length > 64) throw new ValidationError(`players[${i}].name: имя NPC`);
      const bb = (bot ?? {}) as Record<string, unknown>;
      const model = bb.model ?? BOT_NAMES[0];
      if (typeof model !== "string" || !BOT_NAMES.includes(model)) throw new ValidationError(`players[${i}].bot.model: одна из ${BOT_NAMES.join(", ")}`);
      const skill = int(bb.skill ?? 3, `players[${i}].bot.skill`, 1, 5);
      npcRaw.push({ name: name.trim(), bot: { model, skill }, ...kin });
      return;
    }
    if (npc !== undefined) throw new ValidationError(`players[${i}].npc: true`);
    if (typeof ticket !== "string" || !TICKET_RE.test(ticket)) throw new ValidationError(`players[${i}].ticket: [A-Za-z0-9_-]{1,63}`);
    if (name !== undefined && typeof name !== "string") throw new ValidationError(`players[${i}].name: строка`);
    players.push({ ticket, name: name as string | undefined, ...kin });
  });
  if (new Set(players.map((p) => p.ticket)).size !== players.length) throw new ValidationError("players: билеты повторяются");
  if (players.length < 1) throw new ValidationError("players: нужен хотя бы один человек");
  const latin = npcNames(npcRaw.map((n) => n.name));
  const npcs: NpcPlayer[] = npcRaw.map((n, i) => ({
    npc: true, name: n.name, latin: latin[i], key: `npc:${i}`, bot: n.bot,
    ...(n.race ? { race: n.race } : {}), ...(n.faith ? { faith: n.faith } : {}),
  }));

  const r = { ...DEFAULT_RULES[mode], ...((b.rules as object) ?? {}) } as Record<string, unknown>;
  const rules: Rules = {
    fraglimit: int(r.fraglimit, "rules.fraglimit", 1, 100),
    timelimit: int(r.timelimit, "rules.timelimit", 1, 60),
    arsenal: ((): Arsenal => {
      if (ARSENALS.includes(r.arsenal as Arsenal)) return r.arsenal as Arsenal;
      throw new ValidationError(`rules.arsenal: ${ARSENALS.join(" | ")}`);
    })(),
    instagib: bool(r.instagib, "rules.instagib"),
    powerups: bool(r.powerups, "rules.powerups"),
    items: bool(r.items, "rules.items"),
    warmup: int(r.warmup, "rules.warmup", 0, 60),
    bots: int(r.bots, "rules.bots", 0, 3),
  };

  const entrants = players.length + npcs.length;
  if (mode === "duel") {
    if (entrants !== 2) throw new ValidationError("duel: ровно 2 участника (люди и NPC)");
    if (rules.bots !== 0) throw new ValidationError("duel: безымянные боты не допускаются");
  } else {
    if (entrants < 2) throw new ValidationError("ffa: минимум 2 участника");
    if (entrants + rules.bots > FFA_MAX_CLIENTS) throw new ValidationError(`ffa: участников + ботов не больше ${FFA_MAX_CLIENTS}`);
  }
  return { match_id: b.match_id, mode, map: b.map, players, npcs, rules };
}

export function maxClients(req: MatchRequest): number {
  return req.mode === "duel" ? 2 + DUEL_SPECTATORS : Math.min(req.players.length + req.npcs.length + req.rules.bots, FFA_MAX_CLIENTS);
}

/**
 * A tie at the timelimit plays sudden death this long, s, then ends as a draw
 * (g_pangea_overtime; plain Quake 3 waits for a frag forever). Within the 3 min
 * the match's lifetime keeps for it (match.ts DEFAULT_TIMINGS).
 */
export const OVERTIME_S = 120;

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

/** Bots on the server: named NPC bots + plain FFA bots. */
export function allBots(req: MatchRequest): number {
  return req.npcs.length + req.rules.bots;
}

/** Console commands that add the bots after the first InitGame. */
export function botCommands(req: MatchRequest): string[] {
  const out = req.npcs.map((n) => `addbot ${n.bot.model} ${n.bot.skill} free 0 ${n.latin}`);
  for (let i = 0; i < req.rules.bots; i++) out.push(`addbot ${BOT_NAMES[i % BOT_NAMES.length]} 3`);
  return out;
}

/**
 * g_pangea_races: "ticket=race.faith,BotName=race" (the server matches tickets and bot
 * names; ".faith" only when known, a missing race is drawn as human).
 */
export function racesCvar(req: MatchRequest): string {
  const kin = (k: string, race?: string, faith?: string) => `${k}=${race ?? ""}${faith ? "." + faith : ""}`;
  return [
    ...req.players.filter((p) => p.race || p.faith).map((p) => kin(p.ticket, p.race, p.faith)),
    ...req.npcs.filter((n) => n.race || n.faith).map((n) => kin(n.latin, n.race, n.faith)),
  ].join(",");
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
    ["bot_enable", allBots(req) > 0 ? 1 : 0],
    ["g_pangea_tickets", req.players.map((p) => p.ticket).join(",")],
    ["g_pangea_arsenal", r.arsenal],
    ["g_pangea_instagib", r.instagib ? 1 : 0],
    ["g_pangea_powerups", r.powerups ? 1 : 0],
    ["g_pangea_items", r.items ? 1 : 0],
    ["g_pangea_bots", allBots(req)],
    ["g_pangea_autoexit", 1],
    ["g_pangea_overtime", OVERTIME_S],
    ["g_pangea_races", racesCvar(req)],
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
