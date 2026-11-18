import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { type LogTurn, type Roll, emptyLog, foldLog, isLocked } from "@/play/log";

/** The parts of `GET /state` the play screen shows. */
type StateView = {
  session_id: number;
  running_turn_seq: number | null;
  character: {
    name: string;
    class: string;
    level: number;
    hp: number;
    hp_max: number;
    temp_hp: number;
    xp: number;
    xp_next_level: number | null;
    conditions: string[];
  };
};

const TURN_EVENTS = ["roll", "narration_delta", "turn_done", "error"] as const;

export function Play() {
  const [view, setView] = useState<StateView | null>(null);
  const [log, dispatch] = useReducer(foldLog, emptyLog);
  const [sending, setSending] = useState(false);
  const [notice, setNotice] = useState("");

  const refreshState = useCallback(async (): Promise<StateView | null> => {
    const r = await fetch("/state");
    if (r.status === 404) {
      location.hash = "#/campaigns";
      return null;
    }
    if (!r.ok) {
      setNotice("The server could not load the Session.");
      return null;
    }
    const s: StateView = await r.json();
    setView(s);
    return s;
  }, []);

  // Events have no ids and are never replayed, so every (re)connect rebuilds from GET /state and GET /log.
  const restore = useCallback(async () => {
    const s = await refreshState();
    if (s) dispatch({ type: "loaded", turns: await (await fetch(`/log?session=${s.session_id}`)).json() });
  }, [refreshState]);

  useEffect(() => {
    const es = new EventSource("/events");
    // Fetch only once subscribed, so a Turn that ends after the fetch still reaches the log.
    es.onopen = () => void restore();
    for (const type of TURN_EVENTS) {
      es.addEventListener(type, (e) => dispatch({ type, ...JSON.parse((e as MessageEvent).data) }));
    }
    es.addEventListener("state_changed", () => void refreshState());
    // The committed log carries the action text, which another tab's events never sent.
    es.addEventListener("turn_done", () => void restore());
    return () => es.close();
  }, [restore, refreshState]);

  async function submit(text: string) {
    setSending(true);
    setNotice("");
    try {
      const r = await fetch("/action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (!r.ok) {
        setNotice((await r.json()).detail ?? "The action was refused.");
        return false;
      }
      dispatch({ type: "submitted", turn_seq: (await r.json()).turn_seq, text });
      return true;
    } finally {
      setSending(false);
    }
  }

  const locked = !view || sending || isLocked(log, view.running_turn_seq);
  const live = log.turns.find((t) => t.status === "running");
  const thinking = !!view && locked && (!live || (live.rolls.length === 0 && !live.narration));

  return (
    <div className="grid gap-4 md:grid-cols-[16rem_1fr]">
      {view && <SheetPanel view={view} />}
      <section className="flex min-w-0 flex-col gap-3">
        <StoryLog turns={log.turns} thinking={thinking} onRetry={(t) => void submit(t.playerText)} locked={locked} />
        {notice && <p className="text-sm text-destructive">{notice}</p>}
        <ActionBox locked={locked} onSubmit={submit} />
      </section>
    </div>
  );
}

function SheetPanel({ view: { character: c } }: { view: StateView }) {
  return (
    <aside className="space-y-3 rounded-lg border bg-card p-4 text-sm">
      <div>
        <h2 className="font-heading text-lg">{c.name}</h2>
        <p className="text-muted-foreground capitalize">
          Level {c.level} {c.class}
        </p>
      </div>
      <Bar label="HP" value={c.hp} max={c.hp_max} extra={c.temp_hp ? ` +${c.temp_hp} temp` : ""} />
      <Bar label="XP" value={c.xp} max={c.xp_next_level ?? c.xp} />
      <p>
        <span className="text-muted-foreground">Conditions: </span>
        {c.conditions.length ? c.conditions.join(", ") : "none"}
      </p>
    </aside>
  );
}

function Bar({ label, value, max, extra = "" }: { label: string; value: number; max: number; extra?: string }) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 100;
  return (
    <div>
      <div className="flex justify-between">
        <span className="text-muted-foreground">{label}</span>
        <span>
          {value}/{max}
          {extra}
        </span>
      </div>
      <div className="mt-1 h-2 overflow-hidden rounded-full bg-muted" role="meter" aria-label={label}
        aria-valuenow={value} aria-valuemin={0} aria-valuemax={max}>
        <div className="h-full bg-primary transition-[width] duration-700 ease-out" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function rollLine(r: Roll): string {
  const vs = r.target !== null ? ` vs ${r.target}` : "";
  const outcome = r.outcome ? `: ${r.outcome}` : "";
  return `[${r.purpose}] ${r.expr} = ${r.total}${vs}${outcome}`;
}

function StoryLog({ turns, thinking, locked, onRetry }: {
  turns: LogTurn[];
  thinking: boolean;
  locked: boolean;
  onRetry: (t: LogTurn) => void;
}) {
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => end.current?.scrollIntoView?.({ block: "end" }), [turns, thinking]);
  return (
    <div className="max-h-[70svh] min-h-64 space-y-4 overflow-y-auto rounded-lg border p-4 font-serif leading-relaxed"
      aria-live="polite">
      {turns.map((t) => (
        <div key={t.seq} className="space-y-1">
          {t.playerText && <p className="font-sans text-primary">&gt; {t.playerText}</p>}
          {t.rolls.map((r, i) => (
            <p key={i} className="font-sans text-sm text-muted-foreground">{rollLine(r)}</p>
          ))}
          {t.narration && <p className="whitespace-pre-wrap">{t.narration}</p>}
          {t.status === "failed" && (
            <div className="flex items-center gap-2 font-sans text-sm text-destructive">
              <span>{t.error}</span>
              {t.playerText && (
                <Button size="sm" variant="outline" disabled={locked} onClick={() => onRetry(t)}>
                  Retry
                </Button>
              )}
            </div>
          )}
        </div>
      ))}
      {thinking && <p className="animate-pulse font-sans text-sm text-muted-foreground">The Dungeon Master is thinking…</p>}
      <div ref={end} />
    </div>
  );
}

function ActionBox({ locked, onSubmit }: { locked: boolean; onSubmit: (text: string) => Promise<boolean> }) {
  const [text, setText] = useState("");
  async function send() {
    const t = text.trim();
    if (t && !locked && (await onSubmit(t))) setText("");
  }
  return (
    <form className="flex gap-2" onSubmit={(e) => (e.preventDefault(), void send())}>
      <input
        className="min-w-0 flex-1 rounded-md border border-input bg-transparent px-3 py-2 outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
        placeholder="What do you do?"
        aria-label="Your action"
        value={text}
        onChange={(e) => setText(e.target.value)}
        disabled={locked}
      />
      <Button type="submit" disabled={locked || !text.trim()}>
        Send
      </Button>
    </form>
  );
}
