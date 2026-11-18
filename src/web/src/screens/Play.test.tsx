import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { fakeEvents, fakeServer } from "@/test/server";
import { Play } from "./Play";

type Item = { id: number; item: string; qty: number; equipped: boolean };

/** A `GET /state` body with the given inventory; everything else fixed. */
const state = (inventory: Item[], extra: object = {}) => ({
  session_id: 1, campaign_id: 1, campaign_name: "Saltmarsh", running_turn_seq: null, pending_prompt: null,
  auto_roll: false, encounter: null, clocks: [],
  character: {
    name: "Ada", class: "fighter", level: 1, hp: 12, hp_max: 12, temp_hp: 0, xp: 0, xp_next_level: 300,
    ac: 19, speed: 30, proficiency_bonus: 2, gold: 15, conditions: [], inventory,
    abilities: { str: { score: 16, mod: 3 }, dex: { score: 14, mod: 2 }, con: { score: 15, mod: 2 },
      int: { score: 9, mod: -1 }, wis: { score: 13, mod: 1 }, cha: { score: 11, mod: 0 } },
    saves: { str: 5, dex: 2, con: 4, int: -1, wis: 1, cha: 0 },
    skill_list: [
      { skill: "athletics", ability: "str", bonus: 5, proficient: true },
      { skill: "stealth", ability: "dex", bonus: 2, proficient: false },
    ],
    features: { second_wind: "ready" },
    spell_slots: [] as { level: number; used: number; max: number }[],
  },
  quests: [
    { id: 1, title: "Find the smugglers", status: "active", notes: [] },
    { id: 2, title: "Rescue the cat", status: "completed", notes: [] },
  ],
  ...extra,
});

const sword = { id: 4, item: "longsword", qty: 1, equipped: false };
const rations = { id: 5, item: "rations", qty: 3, equipped: false };

/** The sheet opens on Status; switch to another tab. */
const openTab = async (name: string) => fireEvent.click(await screen.findByRole("tab", { name }));

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

test("the sheet lists the inventory and the Quests from GET /state", async () => {
  fakeEvents();
  fakeServer({ "GET /state": () => state([{ ...sword, equipped: true }, rations]), "GET /log?session=1": () => [] });
  render(<Play />);
  await openTab("Gear");

  const equipped = await screen.findByRole("list", { name: "Equipped" });
  expect(within(equipped).getByText("longsword")).toBeTruthy();
  expect(within(screen.getByRole("list", { name: "Carried" })).getByText("rations ×3")).toBeTruthy();
  expect(screen.getByText("15 gp")).toBeTruthy();
  await openTab("Quests");
  const quests = screen.getByRole("list", { name: "Quests" });
  expect(within(quests).getByText("Find the smugglers")).toBeTruthy();
  expect(within(quests).getByText("completed")).toBeTruthy();
});

test("Equip updates the sheet from the returned state, with no Turn", async () => {
  fakeEvents();
  const calls = fakeServer({
    "GET /state": () => state([sword]),
    "GET /log?session=1": () => [],
    "POST /inventory/4/equip": () => state([{ ...sword, equipped: true }]),
  });
  render(<Play />);
  await openTab("Gear");

  fireEvent.click(await screen.findByRole("button", { name: "Equip longsword" }));

  await screen.findByRole("button", { name: "Unequip longsword" });
  expect(within(screen.getByRole("list", { name: "Equipped" })).getByText("longsword")).toBeTruthy();
  expect(calls.map((c) => c.key)).not.toContain("POST /action");
});

test("another tab's equip reaches this sheet through state_changed", async () => {
  const emit = fakeEvents();
  let current = state([sword]);
  fakeServer({ "GET /state": () => current, "GET /log?session=1": () => [] });
  render(<Play />);
  await openTab("Gear");
  await screen.findByRole("button", { name: "Equip longsword" });

  current = state([{ ...sword, equipped: true }]);
  emit("state_changed", { turn_seq: null });

  await screen.findByRole("button", { name: "Unequip longsword" });
});

test.each([
  ["a Turn is running", { running_turn_seq: 3 }],
  ["an Encounter is active", { encounter: { round: 1, active: "Ada", order: [] } }],
])("Equip and Unequip are disabled while %s", async (_, extra) => {
  fakeEvents();
  fakeServer({ "GET /state": () => state([sword, { ...rations, equipped: true }], extra), "GET /log?session=1": () => [] });
  render(<Play />);
  await openTab("Gear");

  expect((await screen.findByRole("button", { name: "Equip longsword" }) as HTMLButtonElement).disabled).toBe(true);
  expect((screen.getByRole("button", { name: "Unequip rations" }) as HTMLButtonElement).disabled).toBe(true);
});

test("a refused equip shows the server's reason", async () => {
  fakeEvents();
  fakeServer({
    "GET /state": () => state([sword]),
    "GET /log?session=1": () => [],
    "POST /inventory/4/equip": () => Response.json({ detail: "A Turn is running." }, { status: 409 }),
  });
  render(<Play />);
  await openTab("Gear");

  fireEvent.click(await screen.findByRole("button", { name: "Equip longsword" }));

  await screen.findByText("A Turn is running.");
  expect(screen.getByRole("button", { name: "Equip longsword" })).toBeTruthy();
});

test("a GET /state sent before an equip cannot overwrite the equip's result when it lands last", async () => {
  const emit = fakeEvents();
  let answer: () => unknown = () => state([sword]);
  let landStale = () => {};
  fakeServer({
    "GET /state": () => answer(),
    "GET /log?session=1": () => [],
    "POST /inventory/4/equip": () => state([{ ...sword, equipped: true }]),
  });
  render(<Play />);
  await openTab("Gear");
  await screen.findByRole("button", { name: "Equip longsword" });

  answer = () => new Promise((resolve) => (landStale = () => resolve(state([sword]))));
  emit("state_changed", { turn_seq: null }); // its GET /state is now in flight
  fireEvent.click(screen.getByRole("button", { name: "Equip longsword" }));
  await screen.findByRole("button", { name: "Unequip longsword" });
  landStale();

  await new Promise((r) => setTimeout(r, 0));
  expect(screen.getByRole("button", { name: "Unequip longsword" })).toBeTruthy();
});

test("a refusal without a JSON body still shows a notice", async () => {
  fakeEvents();
  fakeServer({
    "GET /state": () => state([sword]),
    "GET /log?session=1": () => [],
    "POST /inventory/4/equip": () => new Response("Bad Gateway", { status: 502 }),
  });
  render(<Play />);
  await openTab("Gear");

  fireEvent.click(await screen.findByRole("button", { name: "Equip longsword" }));

  await screen.findByText("The server refused the change.");
});

test("the Encounter panel lists the fight in order, marks the active Combatant and follows state_changed", async () => {
  const emit = fakeEvents();
  const fight = (goblin: string, conditions: string[]) => ({
    encounter: {
      round: 2, active: "Goblin 1", order: [
        { name: "Goblin 1", initiative: 15, conditions, health: goblin },
        { name: "Ada", initiative: 12, conditions: [], health: "unhurt" },
      ],
    },
  });
  let current = state([], fight("wounded", []));
  fakeServer({ "GET /state": () => current, "GET /log?session=1": () => [] });
  render(<Play />);

  const panel = await screen.findByRole("list", { name: "Encounter" });
  const rows = within(panel).getAllByRole("listitem");
  expect(rows.map((r) => r.textContent)).toEqual(["Goblin 1wounded", "Adaunhurt"]);
  expect(rows[0].getAttribute("aria-current")).toBe("true");
  expect(rows[1].getAttribute("aria-current")).toBeNull();
  expect(screen.getByText("Round 2")).toBeTruthy();

  current = state([], fight("down", ["prone"]));
  emit("state_changed", { turn_seq: 4 });
  await within(panel).findByText("down");
  expect(within(panel).getByText("prone")).toBeTruthy();

  current = state([]);
  emit("state_changed", { turn_seq: 5 });
  await vi.waitFor(() => expect(screen.queryByRole("list", { name: "Encounter" })).toBeNull());
});

test("each Visible clock shows its name and segments and fills on state_changed", async () => {
  const emit = fakeEvents();
  let current = state([], { clocks: [{ name: "The vote is called", filled: 1, segments: 4 }] });
  fakeServer({ "GET /state": () => current, "GET /log?session=1": () => [] });
  render(<Play />);

  const clocks = await screen.findByRole("list", { name: "Clocks" });
  expect(within(clocks).getByText("1/4")).toBeTruthy();
  const meter = within(clocks).getByRole("meter", { name: "The vote is called" });
  expect(meter.getAttribute("aria-valuenow")).toBe("1");
  expect(meter.children).toHaveLength(4);

  current = state([], { clocks: [{ name: "The vote is called", filled: 3, segments: 4 }] });
  emit("state_changed", { turn_seq: 2 });
  await within(clocks).findByText("3/4");
});

test("no Clocks panel shows when no Clock is visible", async () => {
  fakeEvents();
  fakeServer({ "GET /state": () => state([]), "GET /log?session=1": () => [] });
  render(<Play />);
  await screen.findByRole("tablist", { name: "Character sheet" });
  expect(screen.queryByRole("list", { name: "Clocks" })).toBeNull();
});

test("campaign_ended shows the Ending after the epilogue, locks input and offers New campaign", async () => {
  const emit = fakeEvents();
  fakeServer({ "GET /state": () => state([]), "GET /log?session=1": () => [
    { seq: 4, player_text: "I strike the king", narration: "The king falls. Peace returns.", rolls: [] },
  ] });
  render(<Play />);
  await screen.findByText("The king falls. Peace returns.");

  emit("campaign_ended", { campaign_id: 1, ending: "victory" });

  await screen.findByText("The Campaign has ended: Victory.");
  expect((screen.getByLabelText("Your action") as HTMLInputElement).disabled).toBe(true);
  expect(screen.getByText("New campaign").closest("a")!.getAttribute("href")).toBe("#/setup");
});

test("a Retired Ending from another tab stays on screen though the Session is gone", async () => {
  const emit = fakeEvents();
  let gone = false;
  fakeServer({
    "GET /state": () => (gone ? Response.json({ detail: "No Session is open." }, { status: 404 }) : state([])),
    "GET /log?session=1": () => [],
  });
  location.hash = "#/play";
  render(<Play />);
  await screen.findByRole("tablist", { name: "Character sheet" });

  gone = true;
  emit("state_changed", { turn_seq: null });
  emit("campaign_ended", { campaign_id: 1, ending: "retired" });

  await screen.findByText("The Campaign has ended: Retired.");
  expect(location.hash).toBe("#/play");
});

test("on a phone the sheet is a drawer opened from a button", async () => {
  vi.stubGlobal("matchMedia", () => ({ matches: false, addEventListener() {}, removeEventListener() {} }));
  fakeEvents();
  fakeServer({ "GET /state": () => state([sword]), "GET /log?session=1": () => [] });
  render(<Play />);

  await screen.findByRole("button", { name: "Character sheet" });
  expect(screen.queryByRole("tablist")).toBeNull();

  fireEvent.click(screen.getByRole("button", { name: "Character sheet" }));

  await screen.findByRole("tablist", { name: "Character sheet" });
  await openTab("Gear");
  expect(within(await screen.findByRole("list", { name: "Carried" })).getByText("longsword")).toBeTruthy();
  expect(screen.getByRole("dialog")).toBeTruthy();
});

// --- tabs, Skills, Player notes, Roll prompt and Auto-roll (issue #26) ----------------------------------

const prompt = { turn_seq: 3, n: 0, purpose: "Ada perception check", bonus: 3, target: 12, versus: null, mode: "normal" };
const base = { "GET /state": () => state([sword]), "GET /log?session=1": () => [] };

test("the sheet's tabs switch between Status, Gear, Skills, Quests and Notes", async () => {
  fakeEvents();
  fakeServer(base);
  render(<Play />);

  const tabs = await screen.findAllByRole("tab");
  expect(tabs.map((t) => t.textContent)).toEqual(["Status", "Gear", "Skills", "Quests", "Notes"]);
  expect(screen.getByRole("meter", { name: "HP" })).toBeTruthy(); // Status
  expect(screen.queryByRole("list", { name: "Carried" })).toBeNull();

  await openTab("Skills");
  const skills = screen.getByRole("list", { name: "Skills" });
  expect(within(skills).getByText("athletics").textContent).toContain("●");
  expect(within(skills).getByText("stealth").textContent).not.toContain("●");
  expect(within(skills).getByText("+5")).toBeTruthy();
  expect(within(screen.getByRole("list", { name: "Abilities" })).getByText("16 (+3)")).toBeTruthy();
  expect(within(screen.getByRole("list", { name: "Saving throws" })).getByText("−1", { exact: false })).toBeTruthy();
  expect(within(screen.getByRole("list", { name: "Features" })).getByText("ready")).toBeTruthy();
  expect(screen.getByText("Proficiency", { exact: false }).parentElement?.textContent).toContain("+2");
  expect(screen.queryByRole("list", { name: "Carried" })).toBeNull();

  // The arrow keys move along the tabs.
  fireEvent.keyDown(screen.getByRole("tab", { name: "Skills" }), { key: "ArrowRight" });
  expect(screen.getByRole("tab", { name: "Quests" }).getAttribute("aria-selected")).toBe("true");
});

test("Player notes load, autosave after typing and are sent nowhere else", async () => {
  fakeEvents();
  const calls = fakeServer({ ...base, "GET /campaigns/1/notes": () => ({ text: "The ferryman lies." }),
    "PUT /campaigns/1/notes": () => ({}) });
  render(<Play />);
  await openTab("Notes");

  const box = (await screen.findByLabelText("Player notes")) as HTMLTextAreaElement;
  await vi.waitFor(() => expect(box.value).toBe("The ferryman lies."));
  fireEvent.change(box, { target: { value: "The ferryman lies. Ask Osric." } });
  expect(calls.some((c) => c.key === "PUT /campaigns/1/notes")).toBe(false); // debounced

  await vi.waitFor(() => expect(calls.find((c) => c.key === "PUT /campaigns/1/notes")?.body)
    .toEqual({ text: "The ferryman lies. Ask Osric." }), { timeout: 3000 });
  expect(calls.filter((c) => c.key === "PUT /campaigns/1/notes")).toHaveLength(1);
  expect(calls.map((c) => c.key)).not.toContain("POST /action");
});

test("unsaved notes are saved when the sheet goes away", async () => {
  fakeEvents();
  const calls = fakeServer({ ...base, "GET /campaigns/1/notes": () => ({ text: "" }), "PUT /campaigns/1/notes": () => ({}) });
  const { unmount } = render(<Play />);
  await openTab("Notes");
  const box = (await screen.findByLabelText("Player notes")) as HTMLTextAreaElement;
  await vi.waitFor(() => expect(box.disabled).toBe(false));
  fireEvent.change(box, { target: { value: "quick" } });

  unmount();

  await vi.waitFor(() => expect(calls.find((c) => c.key === "PUT /campaigns/1/notes")?.body).toEqual({ text: "quick" }));
});

test("a Roll prompt shows the check and its Roll button posts the answer; the log keeps the Roll", async () => {
  const emit = fakeEvents();
  const calls = fakeServer({ ...base, "POST /roll": () => ({}) });
  render(<Play />);
  await screen.findByRole("tablist");

  emit("roll_prompt", prompt);

  const card = await screen.findByRole("group", { name: "Roll prompt" });
  expect(card.textContent).toContain("Ada perception check, DC 12, +3");
  expect((screen.getByLabelText("Your action") as HTMLInputElement).disabled).toBe(true); // locked while it is open
  fireEvent.click(within(card).getByRole("button", { name: "Roll" }));

  await vi.waitFor(() => expect(screen.queryByRole("group", { name: "Roll prompt" })).toBeNull());
  expect(calls.map((c) => c.key)).toContain("POST /roll");
  emit("roll", { turn_seq: 3, answers_prompt: 0, purpose: "Ada perception check", expr: "d20+3", dice: [9], total: 12,
    target: 12, outcome: "success" });
  await screen.findByText("[Ada perception check] d20+3 = 12 vs 12: success");
});

test("an advantage prompt against an opponent names both", async () => {
  const emit = fakeEvents();
  fakeServer(base);
  render(<Play />);
  await screen.findByRole("tablist");

  emit("roll_prompt", { ...prompt, purpose: "Ada athletics (contest)", target: null, versus: "Goblin 1", mode: "advantage" });

  expect((await screen.findByRole("group", { name: "Roll prompt" })).textContent)
    .toContain("Ada athletics (contest), vs Goblin 1, +3, advantage");
});

test("the Roll prompt reappears after a reload while the Turn waits", async () => {
  fakeEvents();
  fakeServer({ ...base, "GET /state": () => state([sword], { running_turn_seq: 3, pending_prompt: prompt }) });
  render(<Play />);

  expect((await screen.findByRole("group", { name: "Roll prompt" })).textContent).toContain("DC 12");
});

test("the Auto-roll toggle saves on the server and is restored from GET /state", async () => {
  fakeEvents();
  let on = false;
  const calls = fakeServer({ ...base, "GET /state": () => state([sword], { auto_roll: on }),
    "PUT /campaigns/1/auto_roll": () => ((on = true), { auto_roll: true }) });
  render(<Play />);

  const box = (await screen.findByLabelText(/Auto-roll/)) as HTMLInputElement;
  expect(box.checked).toBe(false);
  fireEvent.click(box);

  await vi.waitFor(() => expect((screen.getByLabelText(/Auto-roll/) as HTMLInputElement).checked).toBe(true));
  expect(calls.find((c) => c.key === "PUT /campaigns/1/auto_roll")?.body).toEqual({ on: true });
});

test("the sheet shows spell slots used and max for a caster only", async () => {
  fakeEvents();
  const caster = state([]);
  caster.character.spell_slots = [{ level: 1, used: 1, max: 2 }, { level: 2, used: 0, max: 2 }];
  fakeServer({ "GET /state": () => caster, "GET /log?session=1": () => [] });
  render(<Play />);

  const list = await screen.findByRole("list", { name: "Spell slots" });
  expect(within(list).getByText("Level 1").nextSibling?.textContent).toBe("1 used / 2");
  expect(within(list).getByText("Level 2").nextSibling?.textContent).toBe("0 used / 2");
  cleanup();

  fakeServer({ "GET /state": () => state([]), "GET /log?session=1": () => [] });
  render(<Play />);
  await screen.findByText("AC");
  expect(screen.queryByRole("list", { name: "Spell slots" })).toBeNull();
});
