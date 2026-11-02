// Delivery of match results to Pangea (Evennia) with HMAC signature, retries
// with backoff for up to an hour, and a JSONL journal that survives restarts.

import { createHmac } from "node:crypto";
import { appendFileSync, existsSync, mkdirSync, readFileSync } from "node:fs";
import { dirname } from "node:path";
import type { MatchResult } from "./logparse.js";

export interface ReporterOptions {
  url: string;                 // empty = journal only
  secret: string;
  journalPath: string;
  maxAgeMs?: number;           // give up after (default 1 h)
  firstDelayMs?: number;       // first retry delay (default 5 s)
  maxDelayMs?: number;         // backoff cap (default 5 min)
  fetchImpl?: typeof fetch;
  log?: (m: string) => void;
  now?: () => number;
}

type JournalEntry =
  | { ts: string; event: "result"; match_id: string; body: string }
  | { ts: string; event: "delivered"; match_id: string; status: number }
  | { ts: string; event: "gave_up"; match_id: string; error: string };

export function sign(body: string, secret: string): string {
  return createHmac("sha256", secret).update(body).digest("hex");
}

export class Reporter {
  private o: Required<Omit<ReporterOptions, "fetchImpl" | "log" | "now">> & Pick<ReporterOptions, "fetchImpl" | "log" | "now">;
  private pending = new Map<string, NodeJS.Timeout>();

  constructor(opts: ReporterOptions) {
    this.o = { maxAgeMs: 3_600_000, firstDelayMs: 5_000, maxDelayMs: 300_000, ...opts };
    mkdirSync(dirname(this.o.journalPath), { recursive: true });
  }

  private now(): number {
    return this.o.now ? this.o.now() : Date.now();
  }

  private log(m: string): void {
    (this.o.log ?? ((s: string) => console.log(`[reporter] ${s}`)))(m);
  }

  private journal(e: JournalEntry): void {
    appendFileSync(this.o.journalPath, JSON.stringify(e) + "\n");
  }

  /** Records and starts delivering a result. */
  submit(result: MatchResult): void {
    const body = JSON.stringify(result);
    this.journal({ ts: new Date(this.now()).toISOString(), event: "result", match_id: result.match_id, body });
    void this.deliver(result.match_id, body, this.now(), 0);
  }

  /** Re-sends results from the journal that were neither delivered nor given up. */
  resumePending(): number {
    if (!existsSync(this.o.journalPath)) return 0;
    const open = new Map<string, { body: string; ts: number }>();
    for (const line of readFileSync(this.o.journalPath, "utf8").split("\n")) {
      if (!line.trim()) continue;
      let e: JournalEntry;
      try { e = JSON.parse(line); } catch { continue; }
      if (e.event === "result") open.set(e.match_id, { body: e.body, ts: Date.parse(e.ts) });
      else open.delete(e.match_id);
    }
    for (const [id, { body, ts }] of open) {
      if (this.now() - ts > this.o.maxAgeMs) {
        this.journal({ ts: new Date(this.now()).toISOString(), event: "gave_up", match_id: id, error: "expired while manager was down" });
        continue;
      }
      void this.deliver(id, body, ts, 0);
    }
    return open.size;
  }

  get inFlight(): number {
    return this.pending.size;
  }

  stop(): void {
    for (const t of this.pending.values()) clearTimeout(t);
    this.pending.clear();
  }

  private async deliver(id: string, body: string, firstTs: number, attempt: number): Promise<void> {
    this.pending.delete(id);
    if (!this.o.url) {
      this.log(`${id}: no ARENA_RESULT_URL, result kept in journal only`);
      return;
    }
    let error = "";
    try {
      const res = await (this.o.fetchImpl ?? fetch)(this.o.url, {
        method: "POST",
        headers: { "content-type": "application/json", "x-arena-signature": sign(body, this.o.secret) },
        body,
        signal: AbortSignal.timeout(10_000),
      });
      if (res.ok || (res.status >= 400 && res.status < 500 && res.status !== 408 && res.status !== 429)) {
        // 2xx — done; other 4xx — Pangea rejected it, retrying will not help
        this.journal({ ts: new Date(this.now()).toISOString(), event: res.ok ? "delivered" : "gave_up", match_id: id,
          ...(res.ok ? { status: res.status } : { error: `HTTP ${res.status}` }) } as JournalEntry);
        this.log(`${id}: ${res.ok ? "delivered" : "rejected"} (HTTP ${res.status})`);
        return;
      }
      error = `HTTP ${res.status}`;
    } catch (e) {
      error = (e as Error).message;
    }
    const delay = Math.min(this.o.firstDelayMs * 2 ** attempt, this.o.maxDelayMs);
    if (this.now() + delay - firstTs > this.o.maxAgeMs) {
      this.journal({ ts: new Date(this.now()).toISOString(), event: "gave_up", match_id: id, error });
      this.log(`${id}: gave up (${error})`);
      return;
    }
    this.log(`${id}: ${error}, retry in ${Math.round(delay / 1000)} s`);
    this.pending.set(id, setTimeout(() => void this.deliver(id, body, firstTs, attempt + 1), delay));
  }
}
