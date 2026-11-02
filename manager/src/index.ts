#!/usr/bin/env node
// Pangea Arena manager: HTTP API + WS->UDP gateway + one ioq3ded per match.
// Configuration — environment variables (see docs/manager.md).

import { resolve } from "node:path";
import { startGateway } from "pangea-arena-gateway";
import { Reporter } from "./reporter.js";
import { createApi, Manager } from "./server.js";
import type { Mode } from "./rules.js";

const env = process.env;
const root = resolve(new URL("../..", import.meta.url).pathname);

function hostPort(v: string, def: string): [string, number] {
  const [h, p] = (v || def).split(":");
  return [h, Number(p)];
}

const secret = env.ARENA_SECRET ?? "";
if (secret.length < 16) {
  console.error("ARENA_SECRET is required (at least 16 characters)");
  process.exit(2);
}
const [minPort, maxPort] = (env.ARENA_PORTS || "27960-27979").split("-").map(Number);
const maps: Record<Mode, string[]> = {
  duel: (env.ARENA_MAPS_DUEL || "czest1tourney,pul1duel-oa,oa_dm7,am_lavaarena").split(","),
  ffa: (env.ARENA_MAPS_FFA || "oa_dm4,czest1dm,oa_dm1").split(","),
};
const stateDir = resolve(env.ARENA_STATE_DIR || `${root}/manager/state`);

const reporter = new Reporter({
  url: env.ARENA_RESULT_URL || "",
  secret: env.ARENA_RESULT_SECRET || secret,
  journalPath: `${stateDir}/results.jsonl`,
});
const manager = new Manager({
  secret,
  ioq3ded: env.ARENA_IOQ3DED || `${root}/build-native/Release/ioq3ded`,
  basepath: env.ARENA_BASEPATH || `${root}/content/openarena`,
  basegame: env.ARENA_BASEGAME || "baseoa",
  stateDir,
  minPort,
  maxPort,
  maps,
  maxMatches: Number(env.ARENA_MAX_MATCHES || 4),
}, reporter);

const [apiHost, apiPort] = hostPort(env.ARENA_LISTEN || "", "127.0.0.1:27950");
const [gwHost, gwPort] = hostPort(env.ARENA_GATEWAY_LISTEN || "", "127.0.0.1:27961");

const api = createApi(manager, secret);
api.listen(apiPort, apiHost, () => console.log(`[manager] API http://${apiHost}:${apiPort}`));
const gateway = await startGateway({
  listenHost: gwHost,
  listenPort: gwPort,
  minPort,
  maxPort,
  allowPort: (p) => manager.matchOnPort(p) !== undefined,
  limitForPort: (p) => manager.wsLimit(p),
});
const resumed = reporter.resumePending();
if (resumed) console.log(`[manager] re-sending ${resumed} undelivered result(s)`);

for (const sig of ["SIGINT", "SIGTERM"] as const) {
  process.on(sig, async () => {
    console.log(`[manager] ${sig}, stopping matches`);
    manager.stopAll();
    api.close();
    await gateway.close();
    setTimeout(() => process.exit(0), 1500);
  });
}
