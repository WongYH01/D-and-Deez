// Paste into the browser console on the play screen (F12). Times Send -> first Roll or Narration for each Turn.
// It opens its own /events stream, so it does not touch the app. Results: console.table and window.__latency.
// A Turn counts as "with tools" when a Roll arrives before any narration; a tool call that rolls nothing counts as
// "no tools", so judge those against the 5 s limit too if they feel slow.
(() => {
  const rows = (window.__latency = window.__latency || []);
  const realFetch = window.fetch;
  let t0 = null, first = null, sawRoll = false;
  const mark = (kind) => { if (t0 !== null && first === null) first = { ms: Math.round(performance.now() - t0), kind }; };
  window.fetch = (input, init) => {
    const url = typeof input === "string" ? input : input.url;
    if (/\/action$/.test(url) && (init?.method || "GET").toUpperCase() === "POST") { t0 = performance.now(); first = null; sawRoll = false; }
    return realFetch(input, init);
  };
  const es = new EventSource("/events");
  es.addEventListener("roll", () => { sawRoll = true; mark("roll"); });
  es.addEventListener("narration_delta", () => mark("narration"));
  es.addEventListener("turn_done", () => {
    if (t0 === null) return;
    rows.push({ at: new Date().toLocaleTimeString(), tools: sawRoll, first_output_ms: first?.ms ?? null, first: first?.kind ?? "-", total_ms: Math.round(performance.now() - t0), pass: first ? first.ms <= (sawRoll ? 5000 : 2000) : false });
    t0 = null;
    console.table(rows);
  });
  console.log("latency probe on; send a Turn");
})();
