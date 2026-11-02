// Parsing of ioq3ded console output (G_LogPrintf lines are echoed to stdout
// without the time prefix on a dedicated server).

export type LogEvent =
  | { kind: "ticket"; ticket: string; client: number }
  | { kind: "connect"; client: number }
  | { kind: "begin"; client: number }
  | { kind: "disconnect"; client: number }
  | { kind: "initgame" }
  | { kind: "warmup" }
  | { kind: "kill"; killer: number; victim: number; mod: string }
  | { kind: "exit"; reason: string }
  | { kind: "score"; score: number; ping: number; client: number; name: string }
  | { kind: "quit" };

/** Strips an optional "  0:23 " games.log time prefix. */
function stripTime(line: string): string {
  return line.replace(/^\s*\d+:\d{2}\s+/, "").replace(/\r$/, "");
}

export function parseLine(raw: string): LogEvent | null {
  const line = stripTime(raw);
  let m: RegExpExecArray | null;
  if ((m = /^Pangea: ticket (\S+) client (\d+)$/.exec(line))) return { kind: "ticket", ticket: m[1], client: +m[2] };
  if (line === "Pangea: quit") return { kind: "quit" };
  if ((m = /^ClientConnect: (\d+)$/.exec(line))) return { kind: "connect", client: +m[1] };
  if ((m = /^ClientBegin: (\d+)$/.exec(line))) return { kind: "begin", client: +m[1] };
  if ((m = /^ClientDisconnect: (\d+)$/.exec(line))) return { kind: "disconnect", client: +m[1] };
  if (line.startsWith("InitGame:")) return { kind: "initgame" };
  if (line === "Warmup:") return { kind: "warmup" };
  if ((m = /^Kill: (\d+) (\d+) \d+: .* by (MOD_\w+)$/.exec(line))) return { kind: "kill", killer: +m[1], victim: +m[2], mod: m[3] };
  if ((m = /^Exit: (.*)$/.exec(line))) return { kind: "exit", reason: m[1] };
  if ((m = /^score: (-?\d+)\s+ping: (\d+)\s+client: (\d+) (.*)$/.exec(line))) {
    return { kind: "score", score: +m[1], ping: +m[2], client: +m[3], name: m[4] };
  }
  return null;
}

export type ExitReason = "fraglimit" | "timelimit" | "no_show" | "forfeit" | "crash" | "cancelled";

export function exitReason(text: string): ExitReason | null {
  if (/^Fraglimit hit/i.test(text)) return "fraglimit";
  if (/^Timelimit hit/i.test(text)) return "timelimit";
  return null;
}

export interface Place {
  ticket: string;
  score: number;
  place: number;
}

export interface MatchResult {
  match_id: string;
  mode: "duel" | "ffa";
  reason: ExitReason;
  duration_s: number;
  places: Place[];
  left_early: string[];
}

/**
 * Accumulates the log of one match: which client slot holds which ticket,
 * who is present, and the final scoreboard.
 */
export class MatchLog {
  /** client slot -> ticket ("bot" for bots), for currently connected clients */
  readonly slots = new Map<number, string>();
  /** tickets that are connected right now */
  readonly present = new Set<string>();
  /** tickets that have ever connected */
  readonly seen = new Set<string>();
  /** tickets that disconnected and did not come back (yet) */
  readonly gone = new Set<string>();
  exitText: string | null = null;
  scores: { ticket: string; score: number }[] = [];
  initGames = 0;
  quit = false;

  apply(ev: LogEvent): void {
    switch (ev.kind) {
      case "ticket":
        this.slots.set(ev.client, ev.ticket);
        if (ev.ticket !== "bot") {
          this.present.add(ev.ticket);
          this.seen.add(ev.ticket);
          this.gone.delete(ev.ticket);
        }
        break;
      case "disconnect": {
        const t = this.slots.get(ev.client);
        this.slots.delete(ev.client);
        if (t && t !== "bot") {
          this.present.delete(t);
          // after Exit the server kicks everyone — that is not leaving early
          if (this.exitText === null) this.gone.add(t);
        }
        break;
      }
      case "initgame":
        this.initGames++;
        break;
      case "exit":
        this.exitText = ev.reason;
        this.scores = [];
        break;
      case "score": {
        if (this.exitText === null) break;
        const t = this.slots.get(ev.client);
        if (t && t !== "bot") this.scores.push({ ticket: t, score: ev.score });
        break;
      }
      case "quit":
        this.quit = true;
        break;
    }
  }

  feed(text: string): void {
    for (const line of text.split("\n")) {
      const ev = parseLine(line);
      if (ev) this.apply(ev);
    }
  }
}

/**
 * Final places. Order: the scoreboard (sorted by score), then everybody else —
 * players who left early or never came — sharing the last place. Equal scores share a place.
 */
export function computePlaces(scores: { ticket: string; score: number }[], allTickets: string[], leftEarly: string[]): Place[] {
  const out: Place[] = [];
  const left = new Set(leftEarly);
  const ranked = scores.filter((s) => !left.has(s.ticket));
  ranked.sort((a, b) => b.score - a.score);
  ranked.forEach((s, i) => {
    const place = i > 0 && ranked[i - 1].score === s.score ? out[i - 1].place : i + 1;
    out.push({ ticket: s.ticket, score: s.score, place });
  });
  const scoreOf = new Map(scores.map((s) => [s.ticket, s.score]));
  const lastPlace = out.length + 1;
  for (const t of allTickets) {
    if (out.some((p) => p.ticket === t)) continue;
    out.push({ ticket: t, score: scoreOf.get(t) ?? 0, place: lastPlace });
  }
  return out;
}
