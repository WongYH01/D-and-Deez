import { expect, test } from "vitest";
import { type LogAction, type PlayLog, emptyLog, foldLog, isLocked } from "./log";

const roll = (turn_seq: number, purpose: string, total: number): LogAction => ({
  type: "roll", turn_seq, purpose, expr: "1d20+3", dice: [total - 3], total, target: 12, outcome: "success",
});

const fold = (...actions: LogAction[]): PlayLog => actions.reduce(foldLog, emptyLog);

test("roll lines stay in the order they arrive", () => {
  const log = fold(roll(1, "Stealth", 17), roll(1, "Perception", 9), roll(1, "Attack", 14));
  expect(log.turns[0].rolls.map((r) => r.purpose)).toEqual(["Stealth", "Perception", "Attack"]);
});

test("narration deltas append to the Turn's Narration", () => {
  const log = fold(
    { type: "narration_delta", turn_seq: 2, text: "You slip " },
    { type: "narration_delta", turn_seq: 2, text: "past unnoticed." },
  );
  expect(log.turns).toHaveLength(1);
  expect(log.turns[0].narration).toBe("You slip past unnoticed.");
});

test("turn_done commits the Turn with its action, Roll lines and Narration", () => {
  const log = fold(
    { type: "submitted", turn_seq: 3, text: "I sneak behind the bar" },
    roll(3, "Stealth", 17),
    { type: "narration_delta", turn_seq: 3, text: "Nobody sees you." },
    { type: "turn_done", turn_seq: 3 },
  );
  expect(log.turns).toEqual([
    {
      seq: 3,
      playerText: "I sneak behind the bar",
      rolls: [{ purpose: "Stealth", expr: "1d20+3", dice: [14], total: 17, target: 12, outcome: "success" }],
      narration: "Nobody sees you.",
      prompt: null,
      answered: 0,
      status: "committed",
    },
  ]);
});

test("error drops only that Turn's partial lines and keeps its action for Retry", () => {
  const log = fold(
    { type: "submitted", turn_seq: 5, text: "I look around" },
    roll(5, "Perception", 9),
    { type: "turn_done", turn_seq: 5 },
    { type: "submitted", turn_seq: 6, text: "I touch the rune" },
    roll(6, "Arcana", 4),
    { type: "narration_delta", turn_seq: 6, text: "Fire bl" },
    { type: "error", turn_seq: 6, message: "The turn failed; nothing changed." },
  );
  expect(log.turns[0]).toMatchObject({ seq: 5, status: "committed" });
  expect(log.turns[0].rolls).toHaveLength(1);
  expect(log.turns[1]).toEqual({
    seq: 6,
    playerText: "I touch the rune",
    rolls: [],
    narration: "",
    prompt: null,
    answered: 0,
    status: "failed",
    error: "The turn failed; nothing changed.",
  });
});

test("submitting again clears a failed Turn", () => {
  const log = fold(
    { type: "submitted", turn_seq: 6, text: "I touch the rune" },
    { type: "error", turn_seq: 6, message: "The turn failed; nothing changed." },
    { type: "submitted", turn_seq: 7, text: "I touch the rune" },
  );
  expect(log.turns.map((t) => [t.seq, t.status])).toEqual([[7, "running"]]);
});

test("an error that beats POST /action's response leaves the Turn failed", () => {
  const log = fold(
    { type: "error", turn_seq: 6, message: "The turn failed; nothing changed." },
    { type: "submitted", turn_seq: 6, text: "I touch the rune" },
  );
  expect(log.turns).toEqual([
    { seq: 6, playerText: "I touch the rune", rolls: [], narration: "", prompt: null, answered: 0, status: "failed",
      error: "The turn failed; nothing changed." },
  ]);
});

test("GET /log keeps Turns it does not know yet: a running Turn's streamed lines and a failed Turn", () => {
  const log = fold(
    { type: "submitted", turn_seq: 2, text: "I hide" },
    { type: "error", turn_seq: 2, message: "failed" },
    roll(3, "Athletics", 15),
    { type: "turn_done", turn_seq: 1 },
    { type: "loaded", turns: [{ seq: 1, player_text: "I wait", narration: "Time passes.", rolls: [] }] },
  );
  expect(log.turns.map((t) => [t.seq, t.playerText, t.rolls.length, t.status])).toEqual([
    [1, "I wait", 0, "committed"],
    [2, "I hide", 0, "failed"],
    [3, "", 1, "running"],
  ]);
});

test("events for different turn_seq values never mix", () => {
  const log = fold(
    roll(8, "Stealth", 17),
    roll(9, "Attack", 20),
    { type: "narration_delta", turn_seq: 9, text: "Hit." },
    { type: "narration_delta", turn_seq: 8, text: "Hidden." },
    { type: "error", turn_seq: 9, message: "failed" },
  );
  expect(log.turns.map((t) => [t.seq, t.rolls.map((r) => r.purpose), t.narration, t.status])).toEqual([
    [8, ["Stealth"], "Hidden.", "running"],
    [9, [], "", "failed"],
  ]);
});

test("GET /log replaces the log with the Session's committed Turns", () => {
  const log = fold(roll(1, "Stealth", 17), {
    type: "loaded",
    turns: [
      { seq: 0, player_text: "", narration: "The tavern door creaks open.", rolls: [] },
      {
        seq: 1,
        player_text: "I sneak behind the bar",
        narration: "Nobody sees you.",
        rolls: [{ purpose: "Stealth", expr: "1d20+3", dice: [14], total: 17, target: 12, outcome: "success" }],
      },
    ],
  });
  expect(log.turns.map((t) => [t.seq, t.playerText, t.rolls.length, t.status])).toEqual([
    [0, "", 0, "committed"],
    [1, "I sneak behind the bar", 1, "committed"],
  ]);
});

test("input is locked while a Turn runs, including one only GET /state knows about", () => {
  const running = fold({ type: "submitted", turn_seq: 2, text: "I wait" });
  expect(isLocked(running, null)).toBe(true);
  expect(isLocked(fold({ type: "submitted", turn_seq: 2, text: "I wait" }, { type: "turn_done", turn_seq: 2 }), null)).toBe(false);
  // After a reload the Turn is not in the log yet; GET /state's running_turn_seq holds the lock.
  expect(isLocked(emptyLog, 2)).toBe(true);
  // A stale running_turn_seq fetched just before the Turn ended must not hold the lock.
  expect(isLocked(fold({ type: "turn_done", turn_seq: 2 }), 2)).toBe(false);
  expect(isLocked(fold({ type: "error", turn_seq: 2, message: "x" }), 2)).toBe(false);
});

test("events that arrive before POST /action returns land on the same Turn", () => {
  const log = fold(roll(4, "Athletics", 11), { type: "submitted", turn_seq: 4, text: "I climb" });
  expect(log.turns).toHaveLength(1);
  expect(log.turns[0]).toMatchObject({ playerText: "I climb", status: "running" });
  expect(log.turns[0].rolls).toHaveLength(1);
});

test("narration_discard drops the text streamed so far for that Turn only", () => {
  const log = fold(
    { type: "narration_delta", turn_seq: 5, text: "You hit! " },
    { type: "narration_delta", turn_seq: 6, text: "Elsewhere." },
    { type: "narration_discard", turn_seq: 5 },
    { type: "narration_delta", turn_seq: 5, text: "The die settles." },
  );
  expect(log.turns.map((t) => [t.seq, t.narration])).toEqual([[5, "The die settles."], [6, "Elsewhere."]]);
});

const prompt = (turn_seq: number, n: number): LogAction => ({
  type: "roll_prompt", turn_seq, n, purpose: "Wren perception check", bonus: 3, target: 12, versus: null, mode: "normal",
});

test("a roll_prompt holds the Turn's prompt until the Roll that answers it", () => {
  const open = fold({ type: "submitted", turn_seq: 7, text: "I look" }, prompt(7, 0));
  expect(open.turns[0].prompt).toMatchObject({ n: 0, bonus: 3 });
  expect(isLocked(open, 7)).toBe(true);
  const rolled = foldLog(open, { ...(roll(7, "Perception", 15) as object), answers_prompt: 0 } as LogAction);
  expect(rolled.turns[0].prompt).toBeNull();
  expect(rolled.turns[0].rolls).toHaveLength(1);
  expect(rolled.turns[0].rolls[0]).not.toHaveProperty("answers_prompt");
});

test("a prompt that arrives after its answer (a stale GET /state) stays closed", () => {
  const log = fold(
    prompt(7, 0),
    { type: "prompt_answered", turn_seq: 7, n: 0 },
    prompt(7, 0),
  );
  expect(log.turns[0].prompt).toBeNull();
  expect(foldLog(log, prompt(7, 1)).turns[0].prompt).toMatchObject({ n: 1 }); // the next prompt still opens
});

test("a Roll answering the prompt can beat the prompt itself", () => {
  const log = fold({ ...(roll(7, "Perception", 15) as object), answers_prompt: 0 } as LogAction, prompt(7, 0));
  expect(log.turns[0].prompt).toBeNull();
});

test("turn_done and error clear an open prompt", () => {
  expect(fold(prompt(7, 0), { type: "turn_done", turn_seq: 7 }).turns[0].prompt).toBeNull();
  expect(fold(prompt(7, 0), { type: "error", turn_seq: 7, message: "x" }).turns[0].prompt).toBeNull();
});
