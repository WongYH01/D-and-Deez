# v1 release check on the Pi (issue #20)

Runbook for measuring the design document's success criteria. Record results as comments on #20.

## 1. Deploy to the Pi

Pi 5 on a 64-bit OS, Docker installed, repo cloned.

```sh
cp .env.example .env          # set ANTHROPIC_API_KEY; keep the default models unless comparing
mkdir -p data backups         # before the first `up`, or Docker makes them root-owned
docker compose up -d --build
curl -i http://localhost:8000/health    # expect 200
hostname -I                              # play from another device at http://<pi-ip>:8000
```

Before the 2-hour run, copy `data/pidm.sqlite` aside (or start from a fresh `data/`) so the report covers one Session.

## 2. First-output latency (criterion 1)

On the playing device, open the play screen, press F12, paste `scripts/latency_probe.js` into the console, then play.
Each Turn adds a row: `first_output_ms`, `tools`, `pass` (limit 2000 ms without tools, 5000 ms with). Use a device on
home Wi-Fi, not the Pi itself. Play at least 10 Turns of each kind (talk, a skill check, a fight) and note the slowest.
Copy `JSON.stringify(window.__latency)` into the #20 comment.

## 3. Cost (any time, and at the end)

On the Pi (or a copy of the DB, stdlib only):

```sh
python3 scripts/session_report.py --db data/pidm.sqlite --no-log     # cost per 30 min + running total
```

Prices default to Sonnet 5.5 ($2 in / $10 out / $0.10 cache read per MTok). If `PIDM_MODEL` differs, pass
`--price-in --price-out --price-cache-read`. Turn calls only: Recap and bible-planning calls are not stored. For the
true bill, compare with the Anthropic Console usage page for the same hours.

## 4. State contradictions (criterion 2)

```sh
python3 scripts/session_report.py --db data/pidm.sqlite > session.txt
```

Read `session.txt` top to bottom after the 2-hour Session. Look for: narrated HP, gold, items or conditions that
disagree with the Rolls or the sheet; dead things acting; places or NPCs changing facts; a Roll the narration ignores.
Also check the sheet on screen against the narration at the end. Count contradictions; the target is zero.

## 5. Ending in one Session (criterion 3)

Create a one-shot Campaign, play until the Ending screen shows. Note the Ending kind, Turn count and elapsed time.

## 6. Recap accuracy (criterion 4)

End the Session (writes the Final recap and a backup in `backups/`), start a new Session on the same Campaign,
and compare the Recap with `session.txt`. List anything missing, invented or wrong.

## 7. Findings comment template

```
### Result: pass / fail
- Latency: n Turns, slowest no-tool __ ms, slowest with-tool __ ms
- Session length / Turns: __ / __   Contradictions: __ (list)
- Ending reached: __ in __ min
- Recap: accurate / issues (list)
- Cost: $__ per 30 min, $__ total (Turn calls)
- Follow-ups: #__
```

Close #20 only when all four criteria pass; file a follow-up issue for each failure.
