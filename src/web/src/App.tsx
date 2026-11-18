import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { About } from "@/screens/About";
import { Campaigns } from "@/screens/Campaigns";
import { Play } from "@/screens/Play";

const SCREENS = ["play", "campaigns", "about", "setup"] as const;
export type Screen = (typeof SCREENS)[number];

/** `#/about` → "about"; anything unknown falls back to the play screen. */
export function screenFor(hash: string): Screen {
  const name = hash.replace(/^#\/?/, "");
  return (SCREENS as readonly string[]).includes(name) ? (name as Screen) : "play";
}

function useScreen(): Screen {
  const [screen, setScreen] = useState(() => screenFor(location.hash));
  useEffect(() => {
    const onChange = () => setScreen(screenFor(location.hash));
    addEventListener("hashchange", onChange);
    return () => removeEventListener("hashchange", onChange);
  }, []);
  return screen;
}

/** Close the open Session (the server writes its Final recap); a 409 means a Turn is running. */
async function endSession() {
  const r = await fetch("/session/end", { method: "POST" });
  if (r.ok) location.hash = "#/campaigns";
  else alert((await r.json()).detail ?? "The Session could not be ended.");
}

function Placeholder({ title }: { title: string }) {
  return <h1 className="font-heading text-2xl">{title}</h1>;
}

export function App() {
  const screen = useScreen();
  return (
    <div className="min-h-svh">
      <header className="flex items-center gap-2 border-b px-4 py-2">
        <a href="#/play" className="mr-auto font-heading text-lg text-primary">
          Pi Dungeon Master
        </a>
        <Button variant="ghost" render={<a href="#/campaigns" />} nativeButton={false}>
          Campaigns
        </Button>
        <Button variant="ghost" onClick={() => void endSession()}>
          End session
        </Button>
        <Button variant="ghost" render={<a href="#/about" />} nativeButton={false}>
          About
        </Button>
      </header>
      <main className="mx-auto max-w-5xl p-4">
        {screen === "about" && <About />}
        {screen === "play" && <Play />}
        {screen === "campaigns" && <Campaigns />}
        {screen === "setup" && <Placeholder title="New campaign" />}
      </main>
    </div>
  );
}
