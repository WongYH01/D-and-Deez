import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { fakeEvents, fakeServer } from "@/test/server";
import { Play } from "./Play";

type Item = { id: number; item: string; qty: number; equipped: boolean };

/** A `GET /state` body with the given inventory; everything else fixed. */
const state = (inventory: Item[], extra: object = {}) => ({
  session_id: 1, campaign_id: 1, campaign_name: "Saltmarsh", running_turn_seq: null, encounter: null, clocks: [],
  character: {
    name: "Ada", class: "fighter", level: 1, hp: 12, hp_max: 12, temp_hp: 0, xp: 0, xp_next_level: 300,
    conditions: [], inventory,
  },
  quests: [
    { id: 1, title: "Find the smugglers", status: "active", notes: [] },
    { id: 2, title: "Rescue the cat", status: "completed", notes: [] },
  ],
  ...extra,
});

const sword = { id: 4, item: "longsword", qty: 1, equipped: false };
const rations = { id: 5, item: "rations", qty: 3, equipped: false };

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

test("the sheet lists the inventory and the Quests from GET /state", async () => {
  fakeEvents();
  fakeServer({ "GET /state": () => state([{ ...sword, equipped: true }, rations]), "GET /log?session=1": () => [] });
  render(<Play />);

  const inventory = await screen.findByRole("list", { name: "Inventory" });
  expect(within(inventory).getByText("longsword")).toBeTruthy();
  expect(within(inventory).getByText("equipped")).toBeTruthy();
  expect(within(inventory).getByText("rations ×3")).toBeTruthy();
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

  fireEvent.click(await screen.findByRole("button", { name: "Equip longsword" }));

  await screen.findByRole("button", { name: "Unequip longsword" });
  expect(screen.getByText("equipped")).toBeTruthy();
  expect(calls.map((c) => c.key)).not.toContain("POST /action");
});

test("another tab's equip reaches this sheet through state_changed", async () => {
  const emit = fakeEvents();
  let current = state([sword]);
  fakeServer({ "GET /state": () => current, "GET /log?session=1": () => [] });
  render(<Play />);
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
  await screen.findByRole("list", { name: "Inventory" });
  expect(screen.queryByRole("list", { name: "Clocks" })).toBeNull();
});
