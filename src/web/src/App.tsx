import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { About } from "@/screens/About";

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
        {/* Wired to POST /session/end with the play screen (M5.2). */}
        <Button variant="ghost">End session</Button>
        <Button variant="ghost" render={<a href="#/about" />} nativeButton={false}>
          About
        </Button>
      </header>
      <main className="mx-auto max-w-3xl p-4">
        {screen === "about" && <About />}
        {screen === "play" && <Placeholder title="Play" />}
        {screen === "campaigns" && <Placeholder title="Campaigns" />}
        {screen === "setup" && <Placeholder title="New campaign" />}
      </main>
    </div>
  );
}
