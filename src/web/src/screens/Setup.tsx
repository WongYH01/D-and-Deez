import { type FormEvent, type ReactNode, useEffect, useState } from "react";
import { LoaderCircleIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { type CampaignView, refusal } from "@/screens/Campaigns";

// Setup choices from the design document's Story design §1 (Campaign setup).
const CUSTOM = "custom";
const SETTINGS = {
  "High fantasy": "High fantasy",
  "Dark fantasy": "Dark fantasy",
  "Sword and sorcery": "Sword and sorcery",
  "Pirate isles": "Pirate isles",
  [CUSTOM]: "My own fantasy premise",
};
const TONES = { Heroic: "Heroic", Grim: "Grim", Comedic: "Comedic", "Mystery-heavy": "Mystery-heavy" };
const LENGTHS = { "one-shot": "One-shot (1 session)", short: "Short campaign (3 to 5 sessions)" };
const TEMPLATES = {
  fighter: "Fighter: Human Champion",
  rogue: "Rogue: Lightfoot Halfling Thief",
  barbarian: "Barbarian: Half-Orc Berserker",
  wizard: "Wizard: Human, a spellcaster",
  cleric: "Cleric: Human Life Domain, a spellcaster",
};
const STEPS = ["Setting", "Tone", "Length", "Lines and veils", "Character"];
// An imported adventure brings its own setting, tone and length.
const IMPORT_STEPS = ["Adventure", "Lines and veils", "Character"];

type Phase =
  | { kind: "form" }
  | { kind: "generating"; id: number }
  | { kind: "ready"; id: number; premise: string; view: CampaignView }
  | { kind: "failed"; error: string };

/** A labelled shadcn select over a value → label table. */
function Choice({ id, label, items, value, onChange }: {
  id: string; label: string; items: Record<string, string>; value: string; onChange: (v: string) => void;
}) {
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <Select items={items} value={value} onValueChange={(v) => v && onChange(v)}>
        <SelectTrigger id={id} className="w-full sm:w-80" autoFocus>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {Object.entries(items).map(([v, text]) => (
            <SelectItem key={v} value={v}>{text}</SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

function Field({ id, label, hint, children }: { id: string; label: string; hint?: string; children: ReactNode }) {
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      {hint && <p id={`${id}-hint`} className="text-sm text-muted-foreground">{hint}</p>}
      {children}
    </div>
  );
}

export function Setup() {
  const [step, setStep] = useState(0);
  const [setting, setSetting] = useState("High fantasy");
  const [premise, setPremise] = useState("");
  const [tone, setTone] = useState("Heroic");
  const [length, setLength] = useState("one-shot");
  const [lines, setLines] = useState("");
  const [veils, setVeils] = useState("");
  const [template, setTemplate] = useState("fighter");
  const [characterName, setCharacterName] = useState("");
  const [hook, setHook] = useState("");
  const [importing, setImporting] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [phase, setPhase] = useState<Phase>({ kind: "form" });
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  // Poll GET /campaigns until the bible job moves the Campaign out of "generating".
  useEffect(() => {
    if (phase.kind !== "generating") return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      const r = await fetch("/campaigns").catch(() => null);
      const list: CampaignView[] | null = r?.ok ? await r.json().catch(() => null) : null;
      if (stopped) return;
      const c = list?.find((c) => c.id === phase.id);
      // A failed fetch retries; a list without the Campaign means it was deleted, so stop.
      if (list && !c) setPhase({ kind: "failed", error: "The Campaign no longer exists." });
      else if (c?.status === "ready") setPhase({ kind: "ready", id: c.id, premise: c.premise ?? "", view: c });
      else if (c?.status === "failed") setPhase({ kind: "failed", error: c.setup_error });
      else timer = setTimeout(poll, 1000);
    };
    void poll();
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, [phase]);

  async function post(url: string, body: object | undefined, fallback: string): Promise<Response | null> {
    setBusy(true);
    setNotice("");
    try {
      const r = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: body && JSON.stringify(body),
      });
      if (r.ok) return r;
      setNotice(await refusal(r, fallback));
      return null;
    } catch {
      setNotice(fallback);
      return null;
    } finally {
      setBusy(false);
    }
  }

  const steps = importing ? IMPORT_STEPS : STEPS;
  const name = steps[step];
  const custom = !importing && setting === CUSTOM;
  const last = step === steps.length - 1;

  function chooseMode(on: boolean) {
    setImporting(on);
    setStep(0);
    setNotice("");
  }

  /** Import step 1: send the file; the server extracts its text and answers with a source id, or a 400 reason. */
  async function upload(f: File): Promise<number | null> {
    setBusy(true);
    setNotice("");
    try {
      const r = await fetch(`/sources?filename=${encodeURIComponent(f.name)}`, { method: "POST", body: f });
      if (r.ok) return (await r.json()).source_id;
      setNotice(await refusal(r, "The adventure could not be uploaded."));
    } catch {
      setNotice("The adventure could not be uploaded.");
    } finally {
      setBusy(false);
    }
    return null;
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (custom && !premise.trim()) return;
    if (!last) return setStep(step + 1);
    const common = { lines, veils, template, character_name: characterName, hook };
    let body: object = { ...common, setting: custom ? premise.trim() : setting, tone, length };
    if (importing) {
      const source_id = file && (await upload(file));
      if (source_id == null) return setStep(0);
      body = { ...common, source_id };
    }
    const r = await post("/campaigns", body, "The Campaign could not be created.");
    if (r) setPhase({ kind: "generating", id: (await r.json()).campaign_id });
  }

  if (phase.kind === "generating") {
    return (
      <p role="status" className="flex items-center gap-2 text-muted-foreground">
        <LoaderCircleIcon className="size-5 animate-spin" aria-hidden />
        Generating your Campaign. This can take a minute.
      </p>
    );
  }

  if (phase.kind === "ready") {
    const { id, view } = phase;
    // Cancelling an import deletes the source and its Campaign.
    const cancel = async () => {
      const r = await fetch(`/sources/${view.source_id}`, { method: "DELETE" }).catch(() => null);
      if (r?.ok) setPhase({ kind: "form" });
      else setNotice(r ? await refusal(r, "The import could not be cancelled.") : "The import could not be cancelled.");
    };
    const accept = async () => {
      // The play screen streams Turn 0 once the Session opens.
      if (await post("/session/start", { campaign_id: id }, "The Session could not be started.")) {
        location.hash = "#/play";
      }
    };
    const regenerate = async () => {
      if (await post(`/campaigns/${id}/regenerate`, undefined, "The Campaign could not be regenerated.")) {
        setPhase({ kind: "generating", id });
      }
    };
    return (
      <section className="max-w-xl space-y-4">
        <h1 className="font-heading text-2xl">Your Campaign</h1>
        <p className="font-serif text-lg">{phase.premise}</p>
        {view.summary && (
          <p className="text-sm text-muted-foreground">
            {view.summary.acts} {view.summary.acts === 1 ? "act" : "acts"}, {view.summary.npcs} NPCs,{" "}
            {view.summary.locations} locations
          </p>
        )}
        {view.warnings.length > 0 && (
          <ul className="list-disc space-y-1 pl-5 text-sm" aria-label="Warnings">
            {view.warnings.map((w) => <li key={w}>{w}</li>)}
          </ul>
        )}
        {notice && <p className="text-sm text-destructive" role="alert">{notice}</p>}
        <div className="flex gap-2">
          <Button autoFocus disabled={busy} onClick={() => void accept()}>Accept</Button>
          <Button variant="outline" disabled={busy} onClick={() => void regenerate()}>Regenerate</Button>
          {view.source_id != null && (
            <Button variant="outline" disabled={busy} onClick={() => void cancel()}>Cancel</Button>
          )}
        </div>
      </section>
    );
  }

  if (phase.kind === "failed") {
    return (
      <section className="max-w-xl space-y-4">
        <h1 className="font-heading text-2xl">Setup failed</h1>
        <p className="text-destructive" role="alert">{phase.error || "The Campaign could not be generated."}</p>
        <Button autoFocus onClick={() => setPhase({ kind: "form" })}>Try again</Button>
      </section>
    );
  }

  return (
    <form onSubmit={(e) => void submit(e)} className="max-w-xl space-y-6">
      <div>
        <h1 className="font-heading text-2xl">New campaign</h1>
        <p className="text-sm text-muted-foreground">
          Step {step + 1} of {steps.length}: {name}
        </p>
        {step === 0 && (
          <Button type="button" variant="link" className="px-0" onClick={() => chooseMode(!importing)}>
            {importing ? "Generate a campaign instead" : "Import an adventure instead"}
          </Button>
        )}
      </div>
      {name === "Adventure" && (
        <Field id="adventure" label="Adventure file (PDF, Markdown or text)">
          <Input id="adventure" type="file" accept=".pdf,.md,.markdown,.txt"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          <p className="text-sm text-muted-foreground">
            The file stays on this machine. Claude reads its text once to plan the story, then only the part for
            where you are.
          </p>
        </Field>
      )}
      {name === "Setting" && (
        <>
          <Choice id="setting" label="Setting" items={SETTINGS} value={setting} onChange={setSetting} />
          {custom && (
            <Field id="premise" label="Your premise">
              <Textarea id="premise" required autoFocus value={premise} onChange={(e) => setPremise(e.target.value)} />
            </Field>
          )}
        </>
      )}
      {name === "Tone" && <Choice id="tone" label="Tone" items={TONES} value={tone} onChange={setTone} />}
      {name === "Length" && <Choice id="length" label="Length" items={LENGTHS} value={length} onChange={setLength} />}
      {name === "Lines and veils" && (
        <>
          <Field id="lines" label="Lines" hint="Topics that never appear in the story.">
            <Textarea id="lines" autoFocus aria-describedby="lines-hint" placeholder="e.g. graphic harm to children"
              value={lines} onChange={(e) => setLines(e.target.value)} />
          </Field>
          <Field id="veils" label="Veils" hint="Topics that may happen, but only off-screen.">
            <Textarea id="veils" aria-describedby="veils-hint" placeholder="e.g. torture" value={veils}
              onChange={(e) => setVeils(e.target.value)} />
          </Field>
        </>
      )}
      {name === "Character" && (
        <>
          <Choice id="template" label="Template" items={TEMPLATES} value={template} onChange={setTemplate} />
          <Field id="character-name" label="Character name">
            <Input id="character-name" placeholder="Leave blank for the Template's name" value={characterName}
              onChange={(e) => setCharacterName(e.target.value)} />
          </Field>
          <Field id="hook" label="Backstory hook">
            <Textarea id="hook" rows={2} placeholder="Two lines that tie your Character to the story" value={hook}
              onChange={(e) => setHook(e.target.value)} />
          </Field>
        </>
      )}
      {notice && <p className="text-sm text-destructive" role="alert">{notice}</p>}
      <div className="flex gap-2">
        {step > 0 && (
          <Button type="button" variant="outline" onClick={() => setStep(step - 1)}>
            Back
          </Button>
        )}
        <Button type="submit" disabled={busy || (custom && !premise.trim()) || (name === "Adventure" && !file)}>
          {last ? "Create campaign" : "Next"}
        </Button>
      </div>
    </form>
  );
}
