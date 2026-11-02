import { createServer } from "node:http";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { EventEmitter } from "node:events";
import { PassThrough } from "node:stream";
import { describe, expect, it } from "vitest";
import { Reporter, sign } from "../src/reporter.js";
import { createApi, Manager } from "../src/server.js";
import type { MatchResult } from "../src/logparse.js";
import type { ChildLike } from "../src/match.js";

const result: MatchResult = { match_id: "pvp-9", mode: "duel", reason: "fraglimit", duration_s: 100,
  places: [{ ticket: "a", score: 10, place: 1 }, { ticket: "b", score: 3, place: 2 }], left_early: [] };

function tmp() { return mkdtempSync(join(tmpdir(), "arena-test-")); }

async function listen(handler: Parameters<typeof createServer>[1]) {
  const srv = createServer(handler);
  await new Promise<void>((r) => srv.listen(0, "127.0.0.1", () => r()));
  return { srv, url: `http://127.0.0.1:${(srv.address() as { port: number }).port}` };
}

describe("reporter", () => {
  it("signs the body and retries until Pangea answers 2xx", async () => {
    let calls = 0;
    const got: { sig: string; body: string }[] = [];
    const { srv, url } = await listen((req, res) => {
      let body = "";
      req.on("data", (c) => (body += c));
      req.on("end", () => {
        got.push({ sig: String(req.headers["x-arena-signature"]), body });
        res.writeHead(++calls < 3 ? 503 : 200).end("{}");
      });
    });
    const dir = tmp();
    const rep = new Reporter({ url: url + "/api/pvp/arena-result/", secret: "s3cret-s3cret-s3cret", journalPath: join(dir, "results.jsonl"),
      firstDelayMs: 20, log: () => {} });
    rep.submit(result);
    await new Promise((r) => setTimeout(r, 300));
    expect(calls).toBe(3);
    expect(JSON.parse(got[0].body)).toEqual(result);
    expect(got[0].sig).toBe(sign(got[0].body, "s3cret-s3cret-s3cret"));
    const journal = readFileSync(join(dir, "results.jsonl"), "utf8").trim().split("\n").map((l) => JSON.parse(l));
    expect(journal.map((e) => e.event)).toEqual(["result", "delivered"]);
    srv.close();
  });

  it("gives up after maxAge and resumes undelivered results from the journal", async () => {
    const dir = tmp();
    const path = join(dir, "results.jsonl");
    const old = new Date(Date.now() - 2 * 3_600_000).toISOString();
    const fresh = new Date().toISOString();
    writeFileSync(path, [
      JSON.stringify({ ts: old, event: "result", match_id: "old", body: "{}" }),
      JSON.stringify({ ts: fresh, event: "result", match_id: "fresh", body: JSON.stringify(result) }),
      JSON.stringify({ ts: fresh, event: "result", match_id: "done", body: "{}" }),
      JSON.stringify({ ts: fresh, event: "delivered", match_id: "done", status: 200 }),
    ].join("\n") + "\n");
    const seen: string[] = [];
    const { srv, url } = await listen((req, res) => {
      let b = ""; req.on("data", (c) => (b += c)); req.on("end", () => { seen.push(JSON.parse(b).match_id); res.writeHead(200).end(); });
    });
    const rep = new Reporter({ url, secret: "x".repeat(16), journalPath: path, log: () => {} });
    expect(rep.resumePending()).toBe(2);
    await new Promise((r) => setTimeout(r, 200));
    expect(seen).toEqual(["pvp-9"]);
    const events = readFileSync(path, "utf8").trim().split("\n").map((l) => JSON.parse(l)).slice(4).map((e) => `${e.match_id}:${e.event}`);
    expect(events.sort()).toEqual(["fresh:delivered", "old:gave_up"]);
    srv.close();
  });
});

describe("api", () => {
  it("auth, create, list, cancel; reports the cancelled match", async () => {
    const dir = tmp();
    const submitted: MatchResult[] = [];
    const reporter = { submit: (r: MatchResult) => submitted.push(r) } as unknown as Reporter;
    const spawned: string[][] = [];
    const manager = new Manager({
      secret: "k".repeat(20), ioq3ded: "/bin/false", basepath: "/c", basegame: "baseoa", stateDir: dir,
      minPort: 27960, maxPort: 27961, maps: { duel: ["oa_dm7"], ffa: ["oa_dm4"] }, maxMatches: 4, log: () => {},
      spawnServer: (_req, _port, args) => {
        spawned.push(args);
        const c = new EventEmitter() as ChildLike;
        Object.assign(c, { stdout: new PassThrough(), stdin: new PassThrough(),
          kill: () => { queueMicrotask(() => c.emit("exit", null, "SIGTERM")); return true; } });
        return c;
      },
    }, reporter);
    const api = createApi(manager, "k".repeat(20));
    await new Promise<void>((r) => api.listen(0, "127.0.0.1", () => r()));
    const base = `http://127.0.0.1:${(api.address() as { port: number }).port}`;
    const H = { "x-arena-secret": "k".repeat(20), "content-type": "application/json" };
    const body = (id: string) => JSON.stringify({ match_id: id, mode: "duel", map: "oa_dm7", players: [{ ticket: "a" }, { ticket: "b" }] });

    expect((await fetch(`${base}/matches`, { method: "POST", body: body("m1") })).status).toBe(401);
    expect((await fetch(`${base}/health`)).status).toBe(200);

    const r1 = await fetch(`${base}/matches`, { method: "POST", headers: H, body: body("m1") });
    expect(r1.status).toBe(201);
    const j1 = await r1.json();
    expect(j1).toMatchObject({ port: 27960, ws_path: "/arena-ws/27960" });
    expect(Date.parse(j1.expires_at)).toBeGreaterThan(Date.now());
    expect(spawned[0].join(" ")).toContain("+exec match.cfg +map oa_dm7");
    expect(readFileSync(join(dir, "matches", "m1", "baseoa", "match.cfg"), "utf8")).toContain('set g_pangea_tickets "a,b"');

    expect((await fetch(`${base}/matches`, { method: "POST", headers: H, body: body("m1") })).status).toBe(409);
    expect((await (await fetch(`${base}/matches`, { method: "POST", headers: H, body: body("m2") })).json()).port).toBe(27961);
    expect((await fetch(`${base}/matches`, { method: "POST", headers: H, body: body("m3") })).status).toBe(503);
    expect((await fetch(`${base}/matches`, { method: "POST", headers: H, body: "{" })).status).toBe(400);

    const list = await (await fetch(`${base}/matches`, { headers: H })).json();
    expect(list.map((m: { match_id: string }) => m.match_id)).toEqual(["m1", "m2"]);
    expect(manager.wsLimit(27960)).toBe(6);
    expect(manager.wsLimit(27965)).toBeUndefined();

    expect((await fetch(`${base}/matches/m1/cancel`, { method: "POST", headers: H })).status).toBe(200);
    await new Promise((r) => setTimeout(r, 20));
    expect(submitted.map((r) => [r.match_id, r.reason])).toEqual([["m1", "cancelled"]]);
    expect(manager.matchOnPort(27960)).toBeUndefined();
    manager.stopAll();
    api.close();
  });
});
