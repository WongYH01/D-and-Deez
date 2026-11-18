import { render, screen } from "@testing-library/react";
import { afterEach, expect, test } from "vitest";
import { App, screenFor } from "./App";

afterEach(() => {
  location.hash = "";
});

test("hash routes pick a screen, and anything else falls back to play", () => {
  expect(screenFor("#/about")).toBe("about");
  expect(screenFor("#/campaigns")).toBe("campaigns");
  expect(screenFor("#/setup")).toBe("setup");
  expect(screenFor("")).toBe("play");
  expect(screenFor("#/nowhere")).toBe("play");
});

test("the About page shows the SRD 5.1 attribution", () => {
  location.hash = "#/about";
  render(<App />);
  expect(screen.getByText(/System Reference Document 5\.1/)).toBeTruthy();
  expect(screen.getByText(/Creative Commons Attribution 4\.0/)).toBeTruthy();
});
