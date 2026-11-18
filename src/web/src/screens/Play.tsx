import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle, DrawerTrigger } from "@/components/ui/drawer";
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
    inventory: Item[];
  };
  quests: { id: number; title: string; status: string; notes: string[] }[];
  encounter: Encounter | null;
  clocks: Clock[];
};

/** A Visible clock; hidden Clocks, the Main clock included, never reach the UI. */
type Clock = { name: string; filled: number; segments: number };

/** The fight in initiative order; health is a word, never HP. */
type Encounter = {
  round: number;
  active: string;
  order: { name: string; initiative: number; conditions: string[]; health: string }[];
};

type Item = { id: number; item: string; qty: number; equipped: boolean };

const ENDING_NAMES: Record<string, string> = {
  victory: "Victory", defeat: "Defeat", fallen_hero: "Fallen hero", retired: "Retired",
};

const TURN_EVENTS = ["roll", "narration_delta", "turn_done", "error"] as const;

/** True from the `md` breakpoint up, where the sheet sits beside the log; no matchMedia (tests) counts as wide. */
function useWide(): boolean {
  const query = "(min-width: 768px)";
  const [wide, setWide] = useState(() => window.matchMedia?.(query).matches ?? true);
  useEffect(() => {
    const m = window.matchMedia?.(query);
    if (!m) return;
    const on = () => setWide(m.matches);
    m.addEventListener("change", on);
    return () => m.removeEventListener("change", on);
  }, []);
  return wide;
}

export function Play() {
  const wide = useWide();
  const [view, setView] = useState<StateView | null>(null);
  const [log, dispatch] = useReducer(foldLog, emptyLog);
  const [sending, setSending] = useState(false);
  const [notice, setNotice] = useState("");
  // Every Ending closes the Session, so only the `campaign_ended` event carries it; a reload lands on Campaigns.
  const [ending, setEnding] = useState<string | null>(null);
  const ended = useRef(false);

  // State answers can land in any order; show one only if its request was sent after the one on screen.
  const asked = useRef(0);
  const shown = useRef(0);
  const show = useCallback((n: number, s: StateView) => {
    if (n > shown.current) {
      shown.current = n;
      setView(s);
    }
  }, []);

  const refreshState = useCallback(async (): Promise<StateView | null> => {
    const n = ++asked.current;
    const r = await fetch("/state");
    if (r.status === 404) {
      // Retiring closes the Session, so the state is gone but the ended Campaign stays on screen.
      if (!ended.current) location.hash = "#/campaigns";
      return null;
    }
    if (!r.ok) {
      setNotice("The server could not load the Session.");
      return null;
    }
    const s: StateView = await r.json();
    show(n, s);
    return s;
  }, [show]);

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
    es.addEventListener("campaign_ended", (e) => {
      ended.current = true; // before the state fetch below can 404
      setEnding(JSON.parse((e as MessageEvent).data).ending);
    });
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

  // Equip skips Claude: the server answers with the new state and tells other tabs through state_changed.
  async function setEquipped(item: Item, on: boolean) {
    setSending(true);
    setNotice("");
    try {
      const n = ++asked.current;
      const r = await fetch(`/inventory/${item.id}/${on ? "equip" : "unequip"}`, { method: "POST" });
      if (r.ok) show(n, await r.json());
      else setNotice((await r.json().catch(() => ({}))).detail ?? "The server refused the change.");
    } finally {
      setSending(false);
    }
  }

  const locked = !view || sending || ending !== null || isLocked(log, view.running_turn_seq);
  const live = log.turns.find((t) => t.status === "running");
  const thinking = !!view && locked && ending === null && (!live || (live.rolls.length === 0 && !live.narration));

  const sheet = view && (
    <div className="space-y-4">
      <SheetPanel view={view} gearLocked={locked || !!view.encounter} onEquip={setEquipped} />
      {view.encounter && <EncounterPanel encounter={view.encounter} />}
      {view.clocks.length > 0 && <ClocksPanel clocks={view.clocks} />}
    </div>
  );

  // On a phone the log and action box fill the screen (App gives main the viewport height) and the sheet is a drawer.
  return (
    <div className="grid h-full gap-4 md:h-auto md:grid-cols-[16rem_1fr]">
      {wide && sheet}
      <section className="flex min-h-0 min-w-0 flex-col gap-3">
        {!wide && sheet && (
          <Drawer>
            <DrawerTrigger render={<Button variant="outline" className="self-start" />}>
              Character sheet
            </DrawerTrigger>
            <DrawerContent>
              <DrawerHeader>
                <DrawerTitle>Character sheet</DrawerTitle>
              </DrawerHeader>
              <div className="overflow-y-auto p-4 pt-0">{sheet}</div>
            </DrawerContent>
          </Drawer>
        )}
        <StoryLog turns={log.turns} thinking={thinking} ending={ending} onRetry={(t) => void submit(t.playerText)} locked={locked} />
        {notice && <p className="text-sm text-destructive">{notice}</p>}
        <ActionBox locked={locked} onSubmit={submit} />
      </section>
    </div>
  );
}

function SheetPanel({ view: { character: c, quests }, gearLocked, onEquip }: {
  view: StateView;
  gearLocked: boolean;
  onEquip: (item: Item, on: boolean) => void;
}) {
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
      <section>
        <h3 id="inventory" className="text-muted-foreground">Inventory</h3>
        <ul aria-labelledby="inventory" className="mt-1 space-y-1">
          {c.inventory.map((i) => {
            const name = i.item.replaceAll("_", " ");
            return (
            <li key={i.id} className="flex items-center justify-between gap-2">
              <span className="capitalize">{name}{i.qty > 1 && ` ×${i.qty}`}</span>
              <span className="flex items-center gap-2">
                {i.equipped && <span className="text-xs text-primary">equipped</span>}
                <Button size="xs" variant="outline" disabled={gearLocked} onClick={() => onEquip(i, !i.equipped)}
                  aria-label={`${i.equipped ? "Unequip" : "Equip"} ${name}`}>
                  {i.equipped ? "Unequip" : "Equip"}
                </Button>
              </span>
            </li>
            );
          })}
        </ul>
      </section>
      <section>
        <h3 id="quests" className="text-muted-foreground">Quests</h3>
        <ul aria-labelledby="quests" className="mt-1 space-y-1">
          {quests.map((q) => (
            <li key={q.id} className="flex justify-between gap-2">
              <span>{q.title}</span>
              {q.status !== "active" && <span className="text-xs text-muted-foreground">{q.status}</span>}
            </li>
          ))}
          {!quests.length && <li>none</li>}
        </ul>
      </section>
    </aside>
  );
}

function EncounterPanel({ encounter: { round, active, order } }: { encounter: Encounter }) {
  return (
    <aside className="space-y-2 rounded-lg border bg-card p-4 text-sm">
      <div className="flex justify-between">
        <h3 id="encounter" className="text-muted-foreground">Encounter</h3>
        <span className="text-muted-foreground">Round {round}</span>
      </div>
      <ul aria-labelledby="encounter" className="space-y-1">
        {order.map((c) => (
          <li key={c.name} aria-current={c.name === active || undefined}
            className="flex justify-between gap-2 rounded px-1 aria-[current]:bg-muted aria-[current]:font-medium">
            <span>
              {c.name}
              {c.conditions.length > 0 && <span className="text-xs text-muted-foreground"> {c.conditions.join(", ")}</span>}
            </span>
            <span className={c.health === "down" ? "text-muted-foreground" : c.health === "bloodied" ? "text-destructive" : ""}>
              {c.health}
            </span>
          </li>
        ))}
      </ul>
    </aside>
  );
}

function ClocksPanel({ clocks }: { clocks: Clock[] }) {
  return (
    <aside className="space-y-2 rounded-lg border bg-card p-4 text-sm">
      <h3 id="clocks" className="text-muted-foreground">Clocks</h3>
      <ul aria-labelledby="clocks" className="space-y-2">
        {clocks.map((c, n) => (
          <li key={n}>
            <div className="flex justify-between gap-2">
              <span>{c.name}</span>
              <span>{c.filled}/{c.segments}</span>
            </div>
            <div className="mt-1 flex gap-0.5" role="meter" aria-label={c.name}
              aria-valuenow={c.filled} aria-valuemin={0} aria-valuemax={c.segments}>
              {Array.from({ length: c.segments }, (_, i) => (
                <div key={i} className={`h-2 flex-1 rounded-sm transition-colors duration-700 ${i < c.filled ? "bg-primary" : "bg-muted"}`} />
              ))}
            </div>
          </li>
        ))}
      </ul>
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

function StoryLog({ turns, thinking, ending, locked, onRetry }: {
  turns: LogTurn[];
  thinking: boolean;
  ending: string | null;
  locked: boolean;
  onRetry: (t: LogTurn) => void;
}) {
  const end = useRef<HTMLDivElement>(null);
  // Braces: Chrome's scrollIntoView returns a Promise, which React would call as the cleanup.
  useEffect(() => {
    end.current?.scrollIntoView?.({ block: "end" });
  }, [turns, thinking, ending]);
  return (
    <div className="min-h-32 flex-1 space-y-4 overflow-y-auto md:max-h-[70svh] md:min-h-64 md:flex-none rounded-lg border p-4 font-serif leading-relaxed"
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
      {ending && (
        <p className="border-t pt-3 text-center font-sans font-medium">
          The Campaign has ended: {ENDING_NAMES[ending] ?? ending}.
          <Button className="ml-3" render={<a href="#/setup" />} nativeButton={false}>New campaign</Button>
        </p>
      )}
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
    <form className="flex shrink-0 gap-2" onSubmit={(e) => (e.preventDefault(), void send())}>
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
