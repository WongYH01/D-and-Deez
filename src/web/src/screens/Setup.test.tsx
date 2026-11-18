import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { fakeServer } from "@/test/server";
import { Setup } from "./Setup";

const campaign = (status: string, extra: object = {}) => ({
  id: 7, name: "", status, length: "one-shot", premise: null, ending: null, setup_error: "", adapted: false,
  source_id: null, summary: null, warnings: [], ...extra,
});

/** GET /campaigns answers each list in turn, then repeats the last. */
const lists = (...answers: object[][]) => () => (answers.length > 1 ? answers.shift() : answers[0]);

const next = () => fireEvent.click(screen.getByRole("button", { name: "Next" }));

/** Walk the five steps with the default choices, a name and a hook, and submit. */
function fillAndSubmit() {
  next(); // Setting
  next(); // Tone
  next(); // Length
  fireEvent.change(screen.getByLabelText("Lines"), { target: { value: "spiders" } });
  next(); // Lines and veils
  fireEvent.change(screen.getByLabelText("Character name"), { target: { value: "Ada" } });
  fireEvent.change(screen.getByLabelText("Backstory hook"), { target: { value: "Owes the guild." } });
  fireEvent.click(screen.getByRole("button", { name: "Create campaign" }));
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  location.hash = "";
});

test("a Campaign set up in the wizard is generated, then shows only its premise", async () => {
  const calls = fakeServer({
    "POST /campaigns": () => ({ campaign_id: 7 }),
    "GET /campaigns": lists(
      [campaign("generating")],
      [campaign("ready", { premise: "A drowned bell tolls under the harbour." })],
    ),
  });
  render(<Setup />);
  fillAndSubmit();

  expect(await screen.findByText(/Generating/)).toBeTruthy();
  expect(await screen.findByText("A drowned bell tolls under the harbour.", {}, { timeout: 3000 })).toBeTruthy();
  expect(calls[0]).toEqual({
    key: "POST /campaigns",
    body: {
      setting: "High fantasy", tone: "Heroic", length: "one-shot", lines: "spiders", veils: "",
      template: "fighter", character_name: "Ada", hook: "Owes the guild.",
    },
  });
});

test("Accept starts Session 1 and lands on the play screen", async () => {
  const calls = fakeServer({
    "POST /campaigns": () => ({ campaign_id: 7 }),
    "GET /campaigns": lists([campaign("ready", { premise: "A drowned bell." })]),
    "POST /session/start": () => ({ session_id: 1 }),
  });
  render(<Setup />);
  fillAndSubmit();
  fireEvent.click(await screen.findByRole("button", { name: "Accept" }));

  await vi.waitFor(() => expect(location.hash).toBe("#/play"));
  expect(calls.at(-1)).toEqual({ key: "POST /session/start", body: { campaign_id: 7 } });
});

test("Regenerate replaces the premise on the same Campaign", async () => {
  let premise = "A drowned bell.";
  const calls = fakeServer({
    "POST /campaigns": () => ({ campaign_id: 7 }),
    "GET /campaigns": () => [campaign("ready", { premise })],
    "POST /campaigns/7/regenerate": () => {
      premise = "A plague of silent crows.";
      return { campaign_id: 7 };
    },
  });
  render(<Setup />);
  fillAndSubmit();
  fireEvent.click(await screen.findByRole("button", { name: "Regenerate" }));

  expect(await screen.findByText("A plague of silent crows.")).toBeTruthy();
  expect(screen.queryByText("A drowned bell.")).toBeNull();
  expect(calls.filter((c) => c.key.startsWith("POST /campaigns")).map((c) => c.key))
    .toEqual(["POST /campaigns", "POST /campaigns/7/regenerate"]);
});

test("a failed setup shows its error and offers to try again", async () => {
  fakeServer({
    "POST /campaigns": () => ({ campaign_id: 7 }),
    "GET /campaigns": lists([campaign("failed", { setup_error: "The bible failed its checks 3 times." })]),
  });
  render(<Setup />);
  fillAndSubmit();

  expect(await screen.findByText("The bible failed its checks 3 times.")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Try again" }));
  expect(screen.getByLabelText<HTMLInputElement>("Character name").value).toBe("Ada");
});

test("a Campaign gone from the list stops the spinner with an error", async () => {
  fakeServer({
    "POST /campaigns": () => ({ campaign_id: 7 }),
    "GET /campaigns": () => [],
  });
  render(<Setup />);
  fillAndSubmit();

  expect(await screen.findByText("The Campaign no longer exists.")).toBeTruthy();
});

const adventure = () => new File(["# The Reed Shore\nFog."], "bell.md", { type: "text/markdown" });

/** Switch to the import path, choose a file and walk its three steps. */
function importAndSubmit() {
  fireEvent.click(screen.getByRole("button", { name: "Import an adventure instead" }));
  fireEvent.change(screen.getByLabelText(/Adventure file/), { target: { files: [adventure()] } });
  next(); // Adventure
  next(); // Lines and veils
  fireEvent.click(screen.getByRole("button", { name: "Create campaign" })); // Character
}

const review = { source_id: 3, summary: { acts: 2, npcs: 5, locations: 9 }, warnings: ["Harder for one Character."] };

test("an imported adventure is uploaded, then reviewed as counts and warnings only", async () => {
  const calls = fakeServer({
    "POST /sources?filename=bell.md": () => ({ source_id: 3 }),
    "POST /campaigns": () => ({ campaign_id: 7 }),
    "GET /campaigns": lists([campaign("ready", { premise: "A drowned bell.", ...review })]),
  });
  render(<Setup />);
  importAndSubmit();

  expect(await screen.findByText("A drowned bell.")).toBeTruthy();
  expect(screen.getByText("2 acts, 5 NPCs, 9 locations")).toBeTruthy();
  expect(screen.getByText("Harder for one Character.")).toBeTruthy();
  expect((calls[0].body as File).name).toBe("bell.md");
  expect(calls[1]).toEqual({
    key: "POST /campaigns",
    body: { lines: "", veils: "", template: "fighter", character_name: "", hook: "", source_id: 3 },
  });
});

test("Cancel deletes the imported source and returns to the form", async () => {
  const calls = fakeServer({
    "POST /sources?filename=bell.md": () => ({ source_id: 3 }),
    "POST /campaigns": () => ({ campaign_id: 7 }),
    "GET /campaigns": lists([campaign("ready", { premise: "A drowned bell.", ...review })]),
    "DELETE /sources/3": () => ({}),
  });
  render(<Setup />);
  importAndSubmit();
  fireEvent.click(await screen.findByRole("button", { name: "Cancel" }));

  expect(await screen.findByText("New campaign")).toBeTruthy();
  expect(calls.at(-1)?.key).toBe("DELETE /sources/3");
});

test("a rejected upload shows the reason and stays on the form", async () => {
  fakeServer({
    "POST /sources?filename=bell.md": () => Response.json({ detail: "That PDF has no text layer." }, { status: 400 }),
  });
  render(<Setup />);
  importAndSubmit();

  expect(await screen.findByText("That PDF has no text layer.")).toBeTruthy();
  expect(screen.getByLabelText(/Adventure file/)).toBeTruthy();
});

test("a generated Campaign's review has no Cancel and no warnings", async () => {
  fakeServer({
    "POST /campaigns": () => ({ campaign_id: 7 }),
    "GET /campaigns": lists([campaign("ready", { premise: "A drowned bell." })]),
  });
  render(<Setup />);
  fillAndSubmit();

  expect(await screen.findByText("A drowned bell.")).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Cancel" })).toBeNull();
  expect(screen.queryByLabelText("Warnings")).toBeNull();
});
