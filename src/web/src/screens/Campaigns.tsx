import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";

/** One entry of `GET /campaigns`. */
export type CampaignView = {
  id: number;
  name: string;
  status: "generating" | "ready" | "active" | "complete" | "failed";
  length: string;
  premise: string | null;
  ending: string | null;
  setup_error: string;
  adapted: boolean;
  /** Set for an imported adventure: its counts and warnings, never the plan or the text. */
  source_id: number | null;
  summary: { acts: number; npcs: number; locations: number } | null;
  warnings: string[];
};

/** The server's refusal (a 404 or 409 `detail`) as a readable message. */
export async function refusal(r: Response, fallback: string): Promise<string> {
  const detail = (await r.json().catch(() => ({}))).detail;
  return typeof detail === "string" ? detail : fallback;
}

export function Campaigns() {
  const [campaigns, setCampaigns] = useState<CampaignView[] | null>(null);
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  const latest = useRef(0);
  const load = useCallback(async () => {
    // Only the newest list counts, so a slow mount-time fetch never undoes a Retire.
    const call = ++latest.current;
    const r = await fetch("/campaigns");
    const list = r.ok ? await r.json() : null;
    if (call !== latest.current) return;
    if (list) setCampaigns(list);
    else setNotice("The server could not list the Campaigns.");
  }, []);

  useEffect(() => void load(), [load]);

  async function post(url: string, body: object | undefined, fallback: string): Promise<boolean> {
    setBusy(true);
    setNotice("");
    try {
      const r = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: body && JSON.stringify(body),
      });
      if (!r.ok) setNotice(await refusal(r, fallback));
      return r.ok;
    } finally {
      setBusy(false);
    }
  }

  async function continueCampaign(c: CampaignView) {
    // The server closes any other open Session; the play screen streams the opening or resume Turn.
    if (await post("/session/start", { campaign_id: c.id }, "The Session could not be started.")) {
      location.hash = "#/play";
    }
  }

  async function retireCampaign(c: CampaignView) {
    if (!confirm(`Retire "${c.name}"? The Campaign ends for good.`)) return;
    await post(`/campaigns/${c.id}/retire`, undefined, "The Campaign could not be retired.");
    await load();
  }

  return (
    <section className="space-y-4">
      <div className="flex items-center gap-2">
        <h1 className="mr-auto font-heading text-2xl">Campaigns</h1>
        <Button render={<a href="#/setup" />} nativeButton={false}>
          New campaign
        </Button>
      </div>
      {notice && <p className="text-sm text-destructive" role="alert">{notice}</p>}
      {campaigns?.length === 0 && <p className="text-muted-foreground">No Campaigns yet.</p>}
      <ul className="space-y-2">
        {campaigns?.map((c) => {
          const playable = c.status === "ready" || c.status === "active";
          return (
            <li key={c.id} className="flex flex-wrap items-center gap-2 rounded-lg border bg-card p-4">
              <div className="mr-auto min-w-0">
                <h2 className="font-heading text-lg">{c.name || "Untitled Campaign"}</h2>
                <p className="text-sm text-muted-foreground capitalize">
                  {c.status} · {c.length}
                  {c.ending && ` · ${c.ending}`}
                </p>
                {c.adapted && <p className="text-sm text-muted-foreground">The story adapted.</p>}
                {c.status === "failed" && c.setup_error && (
                  <p className="text-sm text-destructive">{c.setup_error}</p>
                )}
              </div>
              {playable && (
                <>
                  <Button disabled={busy} onClick={() => void continueCampaign(c)}>
                    Continue
                  </Button>
                  <Button variant="outline" disabled={busy} onClick={() => void retireCampaign(c)}>
                    Retire
                  </Button>
                </>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
