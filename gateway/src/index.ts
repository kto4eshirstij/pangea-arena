#!/usr/bin/env node
// CLI: node dist/index.js --listen 27961 --udp-host 127.0.0.1 [--min 27960 --max 27979]
import { startGateway } from "./gateway.js";

function arg(name: string, def?: string): string | undefined {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 ? process.argv[i + 1] : def;
}

const gw = await startGateway({
  listenHost: arg("host", "0.0.0.0"),
  listenPort: Number(arg("listen", "27961")),
  udpHost: arg("udp-host", "127.0.0.1"),
  minPort: Number(arg("min", "27960")),
  maxPort: Number(arg("max", "27979")),
  maxPerPort: Number(arg("per-port", "4")),
});
for (const sig of ["SIGINT", "SIGTERM"]) process.on(sig, () => gw.close().then(() => process.exit(0)));
