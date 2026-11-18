import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { fakeServer } from "@/test/server";
import { Campaigns } from "./Campaigns";

const campaign = (id: number, adapted: boolean) => ({
  id, name: `Tale ${id}`, status: "active", length: "one-shot", premise: "A premise.", ending: null,
  setup_error: "", adapted,
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

test("a replanned Campaign shows only a neutral line", async () => {
  fakeServer({ "GET /campaigns": () => [campaign(1, true), campaign(2, false)] });
  render(<Campaigns />);
  await screen.findByText("Tale 2");
  expect(screen.getAllByText("The story adapted.")).toHaveLength(1);
});
