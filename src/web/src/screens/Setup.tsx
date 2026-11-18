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
};
const STEPS = ["Setting", "Tone", "Length", "Lines and veils", "Character"];

type Phase =
  | { kind: "form" }
  | { kind: "generating"; id: number }
  | { kind: "ready"; id: number; premise: string }
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

function Field({ id, label, children }: { id: string; label: string; children: ReactNode }) {
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
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
      else if (c?.status === "ready") setPhase({ kind: "ready", id: c.id, premise: c.premise ?? "" });
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

  const custom = setting === CUSTOM;
  const last = step === STEPS.length - 1;

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (custom && !premise.trim()) return;
    if (!last) return setStep(step + 1);
    const r = await post("/campaigns", {
      setting: custom ? premise.trim() : setting, tone, length, lines, veils,
      template, character_name: characterName, hook,
    }, "The Campaign could not be created.");
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
    const { id } = phase;
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
        {notice && <p className="text-sm text-destructive" role="alert">{notice}</p>}
        <div className="flex gap-2">
          <Button autoFocus disabled={busy} onClick={() => void accept()}>Accept</Button>
          <Button variant="outline" disabled={busy} onClick={() => void regenerate()}>Regenerate</Button>
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
          Step {step + 1} of {STEPS.length}: {STEPS[step]}
        </p>
      </div>
      {step === 0 && (
        <>
          <Choice id="setting" label="Setting" items={SETTINGS} value={setting} onChange={setSetting} />
          {custom && (
            <Field id="premise" label="Your premise">
              <Textarea id="premise" required autoFocus value={premise} onChange={(e) => setPremise(e.target.value)} />
            </Field>
          )}
        </>
      )}
      {step === 1 && <Choice id="tone" label="Tone" items={TONES} value={tone} onChange={setTone} />}
      {step === 2 && <Choice id="length" label="Length" items={LENGTHS} value={length} onChange={setLength} />}
      {step === 3 && (
        <>
          <Field id="lines" label="Lines">
            <Textarea id="lines" autoFocus placeholder="Topics never shown" value={lines}
              onChange={(e) => setLines(e.target.value)} />
          </Field>
          <Field id="veils" label="Veils">
            <Textarea id="veils" placeholder="Topics kept off-screen" value={veils}
              onChange={(e) => setVeils(e.target.value)} />
          </Field>
        </>
      )}
      {step === 4 && (
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
        <Button type="submit" disabled={busy || (custom && !premise.trim())}>
          {last ? "Create campaign" : "Next"}
        </Button>
      </div>
    </form>
  );
}
