import { vi } from "vitest";

export type Call = { key: string; body: unknown };

/**
 * Stub `fetch` with a route table ("POST /campaigns" → handler); records every call.
 * A handler returns (or promises) a JSON body (status 200) or a whole `Response` for any other status.
 */
export function fakeServer(routes: Record<string, () => unknown>): Call[] {
  const calls: Call[] = [];
  vi.stubGlobal("fetch", async (url: string, init?: RequestInit) => {
    const key = `${init?.method ?? "GET"} ${url}`;
    // A string body is JSON; an upload's body (a File) is recorded as it is.
    calls.push({ key, body: typeof init?.body === "string" ? JSON.parse(init.body) : init?.body });
    const handler = routes[key];
    if (!handler) return Response.json({ detail: "No route." }, { status: 404 });
    const out = await handler();
    return out instanceof Response ? out : Response.json(out);
  });
  return calls;
}

/** Stub `EventSource`; `emit` sends an event to every open stream, as `/events` does to every tab. */
export function fakeEvents() {
  const streams: FakeEventSource[] = [];
  class FakeEventSource extends EventTarget {
    onopen: (() => void) | null = null;
    onerror: (() => void) | null = null;
    constructor() {
      super();
      streams.push(this);
      queueMicrotask(() => this.onopen?.());
    }
    close() {
      if (streams.includes(this)) streams.splice(streams.indexOf(this), 1);
    }
  }
  vi.stubGlobal("EventSource", FakeEventSource);
  const emit = (type: string, payload: object) => {
    for (const s of streams) s.dispatchEvent(new MessageEvent(type, { data: JSON.stringify(payload) }));
  };
  /** `emit.drop()`: the stream errors, as when the server goes away; `emit.reconnect()`: the browser's retry succeeds. */
  emit.drop = () => streams.forEach((s) => s.onerror?.());
  emit.reconnect = () => streams.forEach((s) => s.onopen?.());
  return emit;
}
