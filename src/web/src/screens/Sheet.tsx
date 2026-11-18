import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

export type Item = { id: number; item: string; qty: number; equipped: boolean };

/** What the sheet reads of `GET /state`; the server derives every number, the UI never recomputes rules. */
export type Character = {
  name: string;
  class: string;
  level: number;
  hp: number;
  hp_max: number;
  temp_hp: number;
  xp: number;
  xp_next_level: number | null;
  ac: number;
  speed: number;
  proficiency_bonus: number;
  conditions: string[];
  gold: number;
  inventory: Item[];
  abilities: Record<string, { score: number; mod: number }>;
  saves: Record<string, number>;
  skill_list: { skill: string; ability: string; bonus: number; proficient: boolean }[];
  features: Record<string, string | number>;
};

export type Quest = { id: number; title: string; status: string; notes: string[] };

const TABS = ["Status", "Gear", "Skills", "Quests", "Notes"] as const;
type Tab = (typeof TABS)[number];

const signed = (n: number) => (n >= 0 ? `+${n}` : `−${-n}`);
const words = (s: string) => s.replaceAll("_", " ");
const ABILITY_ORDER = ["str", "dex", "con", "int", "wis", "cha"];

export function Sheet({ character: c, quests, campaignId, gearLocked, onEquip }: {
  character: Character;
  quests: Quest[];
  campaignId: number;
  gearLocked: boolean;
  onEquip: (item: Item, on: boolean) => void;
}) {
  const [tab, setTab] = useState<Tab>("Status");
  // Arrow keys move between tabs (WAI-ARIA tabs pattern).
  function onKey(e: React.KeyboardEvent, i: number) {
    const to = e.key === "ArrowRight" ? i + 1 : e.key === "ArrowLeft" ? i - 1 : null;
    if (to === null) return;
    const next = TABS[(to + TABS.length) % TABS.length];
    setTab(next);
    document.getElementById(`tab-${next}`)?.focus();
  }
  return (
    <aside className="space-y-3 rounded-lg border bg-card p-4 text-sm">
      <div>
        <h2 className="font-heading text-lg">{c.name}</h2>
        <p className="text-muted-foreground capitalize">
          Level {c.level} {c.class}
        </p>
      </div>
      <div role="tablist" aria-label="Character sheet" className="flex flex-wrap gap-1">
        {TABS.map((t, i) => (
          <button key={t} id={`tab-${t}`} role="tab" type="button" aria-selected={tab === t} aria-controls={`panel-${t}`}
            tabIndex={tab === t ? 0 : -1} onClick={() => setTab(t)} onKeyDown={(e) => onKey(e, i)}
            className="rounded-md px-2 py-1 outline-none focus-visible:ring-2 focus-visible:ring-ring aria-selected:bg-muted aria-selected:font-medium">
            {t}
          </button>
        ))}
      </div>
      {/* Every panel stays mounted so Notes keeps its text and pending save when another tab is shown. */}
      {TABS.map((t) => (
        <div key={t} id={`panel-${t}`} role="tabpanel" aria-labelledby={`tab-${t}`} hidden={tab !== t} className="space-y-3">
          {t === "Status" && <Status c={c} />}
          {t === "Gear" && <Gear c={c} locked={gearLocked} onEquip={onEquip} />}
          {t === "Skills" && <Skills c={c} />}
          {t === "Quests" && <Quests quests={quests} />}
          {t === "Notes" && <Notes campaignId={campaignId} />}
        </div>
      ))}
    </aside>
  );
}

function Status({ c }: { c: Character }) {
  return (
    <>
      <Bar label="HP" value={c.hp} max={c.hp_max} extra={c.temp_hp ? ` +${c.temp_hp} temp` : ""} />
      <Bar label="XP" value={c.xp} max={c.xp_next_level ?? c.xp} />
      <p>
        <span className="text-muted-foreground">AC </span>{c.ac}
        <span className="text-muted-foreground"> · Speed </span>{c.speed} ft
      </p>
      <p>
        <span className="text-muted-foreground">Conditions: </span>
        {c.conditions.length ? c.conditions.join(", ") : "none"}
      </p>
    </>
  );
}

function Gear({ c, locked, onEquip }: { c: Character; locked: boolean; onEquip: (item: Item, on: boolean) => void }) {
  const groups = [
    { name: "Equipped", items: c.inventory.filter((i) => i.equipped) },
    { name: "Carried", items: c.inventory.filter((i) => !i.equipped) },
  ];
  return (
    <>
      <p><span className="text-muted-foreground">Gold </span>{c.gold} gp</p>
      {groups.map(({ name, items }) => (
        <section key={name}>
          <h3 id={`gear-${name}`} className="text-muted-foreground">{name}</h3>
          <ul aria-labelledby={`gear-${name}`} className="mt-1 space-y-1">
            {items.map((i) => {
              const label = words(i.item);
              return (
                <li key={i.id} className="flex items-center justify-between gap-2">
                  <span className="capitalize">{label}{i.qty > 1 && ` ×${i.qty}`}</span>
                  <Button size="xs" variant="outline" disabled={locked} onClick={() => onEquip(i, !i.equipped)}
                    aria-label={`${i.equipped ? "Unequip" : "Equip"} ${label}`}>
                    {i.equipped ? "Unequip" : "Equip"}
                  </Button>
                </li>
              );
            })}
            {!items.length && <li className="text-muted-foreground">none</li>}
          </ul>
        </section>
      ))}
    </>
  );
}

function Skills({ c }: { c: Character }) {
  return (
    <>
      <p>
        <span className="text-muted-foreground">Proficiency </span>{signed(c.proficiency_bonus)}
        <span className="text-muted-foreground"> · AC </span>{c.ac}
        <span className="text-muted-foreground"> · Speed </span>{c.speed} ft
      </p>
      <section>
        <h3 id="abilities" className="text-muted-foreground">Abilities</h3>
        <ul aria-labelledby="abilities" className="mt-1 grid grid-cols-3 gap-1">
          {ABILITY_ORDER.map((a) => (
            <li key={a} className="rounded border px-1 text-center">
              <span className="block text-xs uppercase text-muted-foreground">{a}</span>
              {c.abilities[a].score} ({signed(c.abilities[a].mod)})
            </li>
          ))}
        </ul>
      </section>
      <section>
        <h3 id="saves" className="text-muted-foreground">Saving throws</h3>
        <ul aria-labelledby="saves" className="mt-1 grid grid-cols-3 gap-1">
          {ABILITY_ORDER.map((a) => (
            <li key={a} className="text-center"><span className="uppercase text-muted-foreground">{a} </span>{signed(c.saves[a])}</li>
          ))}
        </ul>
      </section>
      <section>
        <h3 id="skills" className="text-muted-foreground">Skills</h3>
        <ul aria-labelledby="skills" className="mt-1 space-y-0.5">
          {c.skill_list.map((s) => (
            <li key={s.skill} className="flex justify-between gap-2">
              <span className="capitalize">
                {s.proficient && <span aria-label="proficient" title="proficient">● </span>}
                {words(s.skill)}
              </span>
              <span>{signed(s.bonus)}</span>
            </li>
          ))}
        </ul>
      </section>
      {Object.keys(c.features).length > 0 && (
        <section>
          <h3 id="features" className="text-muted-foreground">Features</h3>
          <ul aria-labelledby="features" className="mt-1 space-y-0.5">
            {Object.entries(c.features).map(([name, value]) => (
              <li key={name} className="flex justify-between gap-2">
                <span className="capitalize">{words(name)}</span>
                <span>{value}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}

function Quests({ quests }: { quests: Quest[] }) {
  return (
    <ul aria-label="Quests" className="space-y-1">
      {quests.map((q) => (
        <li key={q.id} className="flex justify-between gap-2">
          <span>{q.title}</span>
          {q.status !== "active" && <span className="text-xs text-muted-foreground">{q.status}</span>}
        </li>
      ))}
      {!quests.length && <li>none</li>}
    </ul>
  );
}

const SAVE_DELAY = 800;

/** Player notes: one private page per Campaign, autosaved after a pause in typing and when the sheet closes. */
function Notes({ campaignId }: { campaignId: number }) {
  const [text, setText] = useState("");
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);
  const unsaved = useRef<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);

  const flush = useCallback(() => {
    clearTimeout(timer.current);
    if (unsaved.current === null) return;
    const body = JSON.stringify({ text: unsaved.current });
    unsaved.current = null;
    // shortcut: two saves are never in flight together in practice (one per pause); sequence them if that changes.
    fetch(`/campaigns/${campaignId}/notes`, {
      method: "PUT", headers: { "Content-Type": "application/json" }, body, keepalive: true,
    }).then((r) => setFailed(!r.ok), () => setFailed(true));
  }, [campaignId]);

  useEffect(() => {
    let live = true;
    fetch(`/campaigns/${campaignId}/notes`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error("load"))))
      .then((n) => {
        // Typing that began before the notes arrived wins.
        if (live && unsaved.current === null) setText(n.text);
      })
      .catch(() => live && setFailed(true))
      .finally(() => live && setLoaded(true));
    return () => {
      live = false;
      flush(); // the drawer closing must not lose the last words
    };
  }, [campaignId, flush]);

  return (
    <div className="space-y-1">
      <label htmlFor="player-notes" className="text-muted-foreground">Player notes</label>
      <Textarea id="player-notes" className="min-h-40" value={text} disabled={!loaded}
        placeholder="Names, clues, plans. Only you see this; Claude never does."
        onChange={(e) => {
          setText(e.target.value);
          unsaved.current = e.target.value;
          clearTimeout(timer.current);
          timer.current = setTimeout(flush, SAVE_DELAY);
        }} />
      {failed && <p role="alert" className="text-xs text-destructive">Your notes could not be saved.</p>}
    </div>
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
