import { describe, expect, it } from "vitest";
import { createSocket } from "node:dgram";
import WebSocket from "ws";
import { isPortHandshake, parsePortFromPath, startGateway } from "./gateway.js";

describe("helpers", () => {
  it("parses port from path", () => {
    expect(parsePortFromPath("/27960")).toBe(27960);
    expect(parsePortFromPath("/arena-ws/27963/")).toBe(27963);
    expect(parsePortFromPath("/27960?x=1")).toBe(27960);
    expect(parsePortFromPath("/abc")).toBeNull();
    expect(parsePortFromPath("/99999")).toBeNull();
  });
  it("detects SOCKFS port handshake", () => {
    expect(isPortHandshake(Buffer.from([255, 255, 255, 255, 0x70, 0x6f, 0x72, 0x74, 0x6d, 0x38]))).toBe(true);
    expect(isPortHandshake(Buffer.from("\xff\xff\xff\xffgetchallenge", "latin1"))).toBe(false);
  });
});

describe("bridge", () => {
  it("relays datagrams both ways and drops the port handshake", async () => {
    const udp = createSocket("udp4");
    await new Promise<void>((r) => udp.bind(0, "127.0.0.1", () => r()));
    const udpPort = udp.address().port;
    const got: string[] = [];
    udp.on("message", (m, rinfo) => { got.push(m.toString("latin1")); udp.send(Buffer.from("pong:" + m.toString("latin1")), rinfo.port, rinfo.address); });

    const gw = await startGateway({ listenHost: "127.0.0.1", listenPort: 0, minPort: 1, maxPort: 65535, log: () => {} });
    const addr = gw.server.address() as { port: number };
    const ws = new WebSocket(`ws://127.0.0.1:${addr.port}/${udpPort}`, "binary");
    await new Promise((r) => ws.once("open", r));
    const reply = new Promise<string>((r) => ws.once("message", (d) => r((d as Buffer).toString("latin1"))));
    ws.send(Buffer.from([255, 255, 255, 255, 0x70, 0x6f, 0x72, 0x74, 0x6d, 0x38]));
    ws.send(Buffer.from("hello", "latin1"));
    expect(await reply).toBe("pong:hello");
    expect(got).toEqual(["hello"]);
    expect(gw.connections(udpPort)).toBe(1);
    ws.close();
    await gw.close();
    udp.close();
  });

  it("rejects ports outside the range", async () => {
    const gw = await startGateway({ listenHost: "127.0.0.1", listenPort: 0, minPort: 27960, maxPort: 27961, log: () => {} });
    const addr = gw.server.address() as { port: number };
    const ws = new WebSocket(`ws://127.0.0.1:${addr.port}/30000`);
    const err = await new Promise<string>((r) => ws.once("unexpected-response", (_q, res) => r(String(res.statusCode))));
    expect(err).toBe("404");
    await gw.close();
  });
});
