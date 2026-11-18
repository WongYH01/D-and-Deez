/** The play log: one pure reducer folds `/events` and `GET /log` into Turns keyed by `turn_seq`. */

export type Roll = {
  purpose: string;
  expr: string;
  dice: number[];
  total: number;
  target: number | null;
  outcome: string | null;
};

export type LogTurn = {
  seq: number;
  playerText: string;
  rolls: Roll[];
  narration: string;
  status: "running" | "committed" | "failed";
  error?: string;
};

export type PlayLog = { turns: LogTurn[] };

export type LogAction =
  | ({ type: "roll"; turn_seq: number } & Roll)
  | { type: "narration_delta"; turn_seq: number; text: string }
  | { type: "turn_done"; turn_seq: number }
  | { type: "error"; turn_seq: number; message: string }
  | { type: "submitted"; turn_seq: number; text: string }
  | { type: "loaded"; turns: ServerTurn[] };

/** One committed Turn as `GET /log` returns it. */
export type ServerTurn = { seq: number; player_text: string; narration: string; rolls: Roll[] };

export const emptyLog: PlayLog = { turns: [] };

const blank = (seq: number): LogTurn => ({ seq, playerText: "", rolls: [], narration: "", status: "running" });

/** Apply `change` to the Turn with `seq`, adding a running Turn first if none has it yet. */
function update(log: PlayLog, seq: number, change: (t: LogTurn) => LogTurn): PlayLog {
  const turns = log.turns.some((t) => t.seq === seq) ? log.turns : [...log.turns, blank(seq)];
  return { ...log, turns: turns.map((t) => (t.seq === seq ? change(t) : t)) };
}

export function foldLog(log: PlayLog, action: LogAction): PlayLog {
  switch (action.type) {
    case "roll": {
      const { type: _, turn_seq, ...roll } = action;
      return update(log, turn_seq, (t) => ({ ...t, rolls: [...t.rolls, roll] }));
    }
    case "narration_delta":
      return update(log, action.turn_seq, (t) => ({ ...t, narration: t.narration + action.text }));
    case "turn_done":
      return update(log, action.turn_seq, (t) => ({ ...t, status: "committed" }));
    case "error":
      return update(log, action.turn_seq, (t) => ({
        ...t, rolls: [], narration: "", status: "failed", error: action.message,
      }));
    case "submitted": {
      // A new action clears earlier failed Turns, but not this one: its error can beat the POST response.
      const kept = { ...log, turns: log.turns.filter((t) => t.status !== "failed" || t.seq === action.turn_seq) };
      return update(kept, action.turn_seq, (t) => ({ ...t, playerText: action.text }));
    }
    case "loaded": {
      // GET /log holds committed Turns only; keep the running and failed Turns it cannot know about.
      const known = new Set(action.turns.map((t) => t.seq));
      const committed: LogTurn[] = action.turns.map((t) => ({
        seq: t.seq, playerText: t.player_text, rolls: t.rolls, narration: t.narration, status: "committed",
      }));
      const pending = log.turns.filter((t) => t.status !== "committed" && !known.has(t.seq));
      return { turns: [...committed, ...pending].sort((a, b) => a.seq - b.seq) };
    }
  }
}

/** Input stays locked while a Turn runs: one in the log, or `running_turn_seq` from `GET /state` that the
 * log has not yet seen end (that fetch can land just after `turn_done`). */
export function isLocked(log: PlayLog, runningSeq: number | null): boolean {
  if (log.turns.some((t) => t.status === "running")) return true;
  return runningSeq !== null && !log.turns.some((t) => t.seq === runningSeq);
}
