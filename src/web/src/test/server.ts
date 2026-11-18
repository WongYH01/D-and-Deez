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
    calls.push({ key, body: init?.body ? JSON.parse(init.body as string) : undefined });
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
  return (type: string, payload: object) => {
    for (const s of streams) s.dispatchEvent(new MessageEvent(type, { data: JSON.stringify(payload) }));
  };
}
