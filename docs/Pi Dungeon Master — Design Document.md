# Pi Dungeon Master — Design Document

Nov 17, 2026 · @W

## Overview

Pi Dungeon Master is a single-player, text-based D&D 5e game served as a web app. Claude (via the Anthropic API) is the narrator; the app's own code is the referee and the story planner. It ships as one Docker image that runs the same way on a PC for testing and on a Raspberry Pi 5 for everyday play.

**Problem.** LLM game masters tell good scenes but lose track of state, invent rules, and wander without a plot. This design gives scene-level storytelling to Claude and keeps every number, rule, world fact and plot thread in code and SQLite.

**Goals**

- Play a full scene in a browser: type an action, read streamed narration, see the character sheet update.
- No rule drift on mechanics: dice, damage, conditions, XP and inventory are computed by code, never by the model.
- A real story arc: every campaign has a setting, an opening hook, a plot that can't dead-end, and defined endings.
- Continuity: v1 carries the story across sessions through recaps and the campaign plan; v2 adds long-term recall of individual NPCs, places and events.
- One container image that runs on a PC (amd64) and a Raspberry Pi 5 (arm64), with no local model inference.

**Non-goals for v1**

- Voice input and output (planned for v3).
- Multiplayer, or more than one player character.
- Spellcasting classes (v2); v1 characters are non-casters.
- Non-fantasy settings such as cyberpunk (a possible v2 reskin).
- Physical dice recognition and the Pi 4 worker (shelved).
- Content beyond the free System Reference Document (SRD).

**Success criteria (targets, measured in M5)**

- First visible output (a roll line or narration) within 2 s of Send for turns with no tool calls, and within 5 s for turns with tool calls, on home Wi-Fi.
- A 2-hour session ends with zero state contradictions in a manual review of the turn and roll logs.
- A one-shot campaign reaches one of its defined endings within a single session.
- A new session opens with an accurate recap of the previous one.

## Scope and phasing

v1 ships a text-only web app with a planned story arc, packaged as a container from day one. Long-term memory and spellcasting follow in v2, voice in v3, and the Pi 4 is shelved.

| Phase | Delivers | Milestones |
| --- | --- | --- |
| v1 (MVP) | Container image and dev setup, game engine with non-caster mechanics, SRD rules grounding, campaign setup and story director, streaming web UI, session recaps | M0 to M5 |
| v2 | World graph, scene recall, DM notes, spellcasting, adventure import, between-session replanning, optional non-fantasy reskins | M6 |
| v3 | Voice: push-to-talk speech-to-text into the same action endpoint, Piper text-to-speech out | M7 |
| Shelved | Pi 4 as a background worker; camera-read physical dice | None |

Every phase reuses the same turn pipeline. Voice in v3 is only a new way to submit `POST /action` and a new way to output narration, so v1 is built with that in mind.

## System architecture

Everything runs as one Python process inside one Docker container, on a PC or the Pi 5; the only outside dependency is the Claude API.

&#91;embedded content: system architecture · 8 components in one container\]

The browser talks only to the FastAPI server. Claude never touches the database: every change to game or story state is a tool call that the engine validates, and the orchestrator and background worker also write only through the engine's data layer. The context builder only reads.

## Turn lifecycle

A turn is one player action, resolved by code and narrated by Claude. Nothing is written to the database until the turn ends: game-state changes, the turn record and its rolls are held in memory and written in one short transaction, so a failed turn leaves no partial state.

1. **Submit.** The player types an action and presses Send; the browser calls `POST /action`. If a turn is already running (`running_turn_id` in `GET /state`), the server answers 409.
2. **Open the turn.** The orchestrator sets `running_turn_id` in memory, and the engine loads the campaign's game state into a tree of in-memory Python objects for this turn.
3. **Assemble context.** The context builder reads the state snapshot, the story director block, the session recap, rule sections matching keywords in the action, and (from v2) world facts and similar past scenes, then trims them to the token budget. No LLM call is needed.
4. **Call Claude.** The orchestrator sends the request with streaming on.
5. **Tool rounds.** When Claude requests tools, the engine validates each call against the in-memory state tree, computes the result, and changes only the tree. Each roll is held with the turn and sent at once as a `roll` event. The narration contract tells Claude to write no prose in a round that calls tools; any text it writes anyway is never shown and is stripped from the assistant message before the next round, so Claude never assumes the player has read it. In combat, Claude ends the player's action with resolve\_npc\_turns, which plays every monster turn in code, so a whole combat round fits in one tool call.
6. **Final round.** Only the round that ends without tool calls streams to the browser as `narration_delta` events. If the round cap (default 4) is reached, the orchestrator makes one last call with tools disabled, so Claude narrates from the results it has instead of the turn being thrown away.
7. **Commit.** In one short transaction the engine writes the changed parts of the state tree to the game tables, and the orchestrator saves the `turns` row (status `committed`, the narration and the token counts) with its rolls. The server then emits `state_changed` and `turn_done`, and the browser refreshes the sheet.
8. **Fail safely.** If the API still fails after retries with backoff, the state tree and the turn's rolls are discarded, a `turns` row with status `failed` and its token counts is saved, and an `error` event is sent. The UI removes that turn's partial lines and offers Retry, which starts a new turn with fresh rolls.
9. **Reconnect.** A browser that reconnects or reloads opens a new event stream and re-fetches `GET /log` and `GET /state`. Events are not replayed: while `running_turn_id` is set the input stays locked, and the turn appears from `GET /log` once `turn_done` arrives.
10. **Background upkeep.** Every 10 turns the background worker updates the rolling recap, and at session end it writes the final recap; from v2 it also summarises scenes, extracts world facts and stores scene embeddings. Jobs run one at a time in the same process, so two jobs never overwrite each other. Recap writes go through the same data layer in their own short transactions; from v2, fact changes wait until no turn is running, so state never shifts mid-turn.

A crash or restart mid-turn loses only that turn, because nothing of it was written; the player retypes the action.

## Data model

All data lives in one SQLite file in WAL mode on a mounted volume, so the sheet can be read while a turn writes. Every write goes through one data layer inside the engine module: game state changes only through validated tools, and the orchestrator and background worker use the same layer for their own tables.

| Table | Key columns | Written by | Phase |
| --- | --- | --- | --- |
| `campaigns` | id, name, setting, tone, length, ruleset, lines, veils, status, ending | Setup | v1 |
| `characters` | id, campaign\_id, name, template, level, xp, hp\_current, hp\_max, ac, ability scores, gold, conditions, death\_saves, hit\_dice | Engine | v1 |
| `skills` | character\_id, skill, proficient | Engine | v1 |
| `inventory` | character\_id, item\_ref, qty, equipped | Engine | v1 |
| `quests` | id, campaign\_id, title, status, notes | Engine | v1 |
| `beats` | id, campaign\_id, act, order, goal, status, resolved\_turn | Setup, engine | v1 |
| `clocks` | id, campaign\_id, name, segments, filled, consequence, visible | Setup, engine | v1 |
| `secrets` | id, campaign\_id, revelation, beat\_id | Setup | v1 |
| `clues` | id, secret\_id, description, location, revealed\_turn | Setup, engine | v1 |
| `encounters` | id, session\_id, status, round, active\_combatant | Engine | v1 |
| `combatants` | encounter\_id, name, monster\_ref, hp, ac, initiative, conditions | Engine | v1 |
| `sessions` | id, campaign\_id, started\_at, ended\_at, rolling\_recap, final\_recap | Orchestrator, worker | v1 |
| `scenes` | id, session\_id, start\_turn, end\_turn, summary | Engine (`end_scene`), worker | v2 |
| `turns` | id, session\_id, seq, player\_text, narration, status (committed, failed), tokens\_in, tokens\_out, tokens\_cached | Orchestrator | v1 |
| `rolls` | turn\_id, purpose, expr, dice, total, target, outcome | Engine | v1 |
| `srd_monsters`, `srd_spells`, `srd_items` | slug, name, data (JSON) | Import script, read-only | v1 |
| `rules_fts` | section, body (FTS5 virtual table) | Import script, read-only | v1 |
| `entities` | id, name, kind (npc, place, faction, item), aliases, summary | Engine, worker | v2 |
| `facts` | subject\_id, relation, object\_id, valid\_from\_turn, valid\_to\_turn, source\_turn | Engine, worker | v2 |
| `scene_vec` | scene\_id, embedding (sqlite-vec `vec0` table) | Worker | v2 |
| `dm_notes` | id, campaign\_id, note, updated\_turn | Engine (`write_note`) | v2 |
| `spell_slots` | character\_id, level, max, used | Engine | v2 |

From v2, adventure import adds `sources`, `source_chunks` (FTS5) and `campaigns.source_id`; see Adventure import.

**Derived values are computed, not stored.** Ability modifiers, skill bonuses and proficiency bonus are calculated from level and ability scores on read, so they cannot fall out of sync.

**Facts carry a validity window.** A fact is never deleted when it stops being true; its `valid_to_turn` is set instead ("Mira works for the Guild" until turn 212). Retrieval only reads facts where `valid_to_turn` is empty. Turn numbers, not wall-clock time, mark validity because they follow the story's order.

**Rolls are saved with their turn.** Every roll of a committed turn is kept in `rolls`, so narration can be checked against what the dice said. A failed turn's rolls are discarded with it.

## LLM integration

Claude narrates scenes and decides what to attempt; every mechanical and plot result comes back from a tool. The prompt is ordered so that both the campaign-level material and the per-turn context are served from the cache on every tool round.

**Models (configurable).** Claude Sonnet 5.5 (`claude-sonnet-5-5`) narrates and plans the campaign. Claude Haiku 5.5 (`claude-haiku-5-5`) writes recaps and scene summaries. Whether Opus is worth its extra latency for narration or campaign planning is an open question.

**Prompt layout, in cache order**

1. Tool definitions. *Fixed.*
2. System prompt: DM persona and style, the narration contract (below), the condensed core-rules sheet, the campaign bible, and the lines and veils. *Fixed for the whole campaign; cache breakpoint 1.*
3. Recent turns as clean pairs of player action and final narration, with no context blocks or tool calls: a sliding window of the last 8 turns. *Not cached across turns in v1.*
4. The final user message: the dynamic context block (state snapshot, director block, session recap, retrieved rule sections, and from v2 world facts, past scenes and DM notes) followed by the player's action. *Cache breakpoint 2.*

Breakpoint 2 means rounds 2 to 4 of the same turn reread everything up to the action from the cache. Everything before breakpoint 1 stays byte-identical across turns. The default cache lifetime is 5 minutes, refreshed on each hit, which normal play keeps warm. Caching the history across turns (a third breakpoint, with a window that drops five turns at a time) is a later optimisation, worth adding only if the logged token counts show the history is a real share of cost.

**Narration contract (in the system prompt)**

- Call every mechanics or story tool before writing any narration; a round that calls tools contains no prose.
- Never state HP, XP, gold, item counts or clock progress from memory; use the snapshot or a tool result.
- Never invent dice results or modifiers.
- Respect the lines (never shown) and veils (happen off-screen).
- Improvise freely where the rules are silent, and never contradict an engine result.

**Tools (v1)**

| Tool | What the engine does |
| --- | --- |
| `roll(expr, purpose)` | Rolls dice such as `2d6+3` with the operating system's random source (no fixed seed) and logs the purpose |
| `skill_check(character, skill, dc)` | d20 + computed bonus against a DC |
| `saving_throw(target, ability, dc)` | d20 + save bonus against a DC; applies the effect on failure when given |
| `contest(a, skill_a, b, skill_b)` | Opposed check, for grapples, shoves, Stealth against Perception |
| `attack(attacker, target, weapon)` | Roll to hit against AC, roll damage on a hit, apply it, return the result |
| `apply_damage` / `heal` | Changes HP within limits, applies resistances, starts death saves at 0 HP |
| `set_condition(target, condition, on, duration)` | Adds or removes an SRD condition with an optional duration in rounds |
| `start_encounter(monsters)` / `resolve_npc_turns()` / `end_encounter()` | Builds combatants from stat blocks and rolls initiative; plays every monster turn in initiative order with simple engine tactics, ticking durations and rolling the player's death save when due, and stops when it is the player's turn again; closes the fight |
| `rest(kind)` | Short or long rest: hit dice, HP, condition and exhaustion recovery |
| `add_item` / `remove_item` / `adjust_gold` | Changes inventory and gold; rejects removing what the character lacks |
| `grant_xp(amount, reason)` | Adds XP and levels up at the threshold |
| `update_quest(id, status, note)` | Creates or updates a quest |
| `advance_beat(beat_id, outcome)` | Marks a story beat resolved, if it belongs to the current act |
| `tick_clock(clock_id, segments, reason)` | Fills a clock; returns its consequence when full |
| `reveal_clue(clue_id)` | Marks a clue found and returns its text |
| `end_campaign(ending)` | Accepted only when an ending condition holds (see Story design) |
| `lookup_rule(query)` / `lookup_srd(kind, slug)` | Full-text rule search; a monster, spell or item record |

v2 adds `cast_spell`, `add_fact` / `retire_fact`, `write_note` (which also records rulings) and `end_scene`. The engine validates every argument against the turn's in-memory state tree; an invalid call returns an error message to Claude rather than changing anything, so Claude can correct itself within the turn.

## Rules grounding

Rules come from the free D&D System Reference Document, loaded into the image's database at setup, and are applied in three layers from most to least strict. Claude's own memory of D&D is the last resort, never the source.

**Source and licence.** Both SRD 5.1 (2014 rules) and SRD 5.2 (2024 rules) are released under CC-BY-4.0, which permits use with attribution. Each campaign stores one ruleset in `campaigns.ruleset`, never a mix. v1 defaults to SRD 5.1 because its structured datasets are more mature; moving to 5.2 is an open question. The UI shows the required attribution on an About page.

**v1 rules coverage.** v1 supports non-spellcasting SRD classes (for example Fighter, Rogue and Barbarian) and characters start from a pre-made template (one per class), chosen at campaign setup. Monsters that cast spells use their stat-block attacks only. Spellcasting, spell slots and a full character builder (standard array and skill choices) arrive in v2.

**Layer 1: mechanics in code.** Ability modifiers, proficiency, skill checks, saving throws, contests, attacks against AC, damage, healing, conditions and their durations, initiative and turn order, death saves, rests, XP and level-ups are Python functions reached only through the tools in LLM integration, so Claude cannot apply them wrongly.

**Layer 2: structured data.** Monster stat blocks, spells and items are imported as JSON into the `srd_*` tables from an open SRD dataset (the 5e-srd-api project for 5.1; an SRD 5.2 API for 2024 rules). Lookups are local, so they work offline and take milliseconds.

**Layer 3: rule text search.** The SRD's prose rules (grappling, cover, resting, exploration) are split into sections and indexed with SQLite FTS5. Keyword search fits this better than semantic search, because rule questions use exact terms.

- A short core-rules sheet (actions, checks, conditions) sits in the cached system prompt.
- When the action contains a rule keyword (for example "grapple" or "hide"), the top two matching sections are added to the dynamic context before the call, saving a tool round.
- For anything else, Claude can call `lookup_rule(query)`.

**Order of authority.** Engine result, then SRD data, then SRD text, then Claude's judgement. Where the rules are silent, Claude rules as a DM would.

## Story design

The plot is planned before play in a hidden campaign bible, tracked in tables during play, and steered every turn by a director block in the prompt. Claude improvises each scene; the structure decides where scenes lead, keeps the plot from stalling, and decides when the campaign ends.

### 1. Campaign setup (session zero)

Before the first session the player fills in a short setup form.

| Choice | Options in v1 | Effect |
| --- | --- | --- |
| Setting | High fantasy, dark fantasy, sword and sorcery, pirate isles, or a free-text fantasy premise | Sets the world, names, factions and description style |
| Tone | Heroic, grim, comedic, mystery-heavy | Guides narration style and how harsh consequences are |
| Length | One-shot (1 session, 1 act) or short campaign (3 to 5 sessions, 3 acts) | Sets the number of acts, beats and clock sizes |
| Lines and veils | Free text: topics never shown, and topics kept off-screen | Written into the system prompt as hard limits |
| Character | A class template, a name and a two-line backstory hook | Ties the opening hook to the character |

The SRD's mechanics are fantasy: swords, armour and monsters. A cyberpunk or sci-fi game would reuse the same numbers with different names (a laser pistol played as a hand crossbow). That reskin is possible but deferred to v2, so v1 offers fantasy settings only.

### 2. The campaign bible

One Claude call turns the setup into a campaign bible, returned as JSON and checked against a schema before it is saved. A bible that fails validation is regenerated. It contains:

- **Premise and central question:** what the story is about and what the player must decide or stop.
- **Antagonist:** their goal, their plan, and what happens if no one interferes.
- **Acts and beats:** each act has a goal and 2 to 4 beats, the story milestones that move it forward.
- **Secrets and clues:** every revelation the player needs to progress has at least three clues in different places, following the [Three Clue Rule](https://thealexandrian.net/wordpress/1118/roleplaying-games/three-clue-rule), so one missed clue cannot stall the plot.
- **Clocks:** progress clocks in the style of Blades in the Dark, such as an 8-segment "Ritual completes" clock for the antagonist's plan, each with a consequence when full.
- **Key NPCs and locations,** each with a motive or purpose.
- **Endings:** victory and defeat, each with the condition that triggers it.
- **Opening scene:** a hook that starts mid-action and connects to the character's backstory.

Beats, clocks, secrets and clues go into their own tables, and the full bible goes into the cached system prompt. The player never sees it.

### 3. Starting

The first session opens with the bible's opening scene, narrated as turn 0, ending on a question to the player. Later sessions open with the recap and a reminder of where the player left off.

### 4. Progressing

Every turn the dynamic context carries a director block: the current act and its goal, open beats, clues available in the current location, clock states, and turns since the last progress.

- Claude calls `advance_beat` when a beat's goal is met, `reveal_clue` when a clue is found, and `tick_clock` when time passes, the player fails a check with consequences, or the player ignores a threat.
- When an act's beats are all resolved, the engine opens the next act.
- **Stall detection:** if 8 turns pass with no beat, clue or clock progress, the director block tells Claude to bring a clue or complication to the player, such as a messenger arriving or an ambush.
- **Off-script play is allowed:** the bible is a guide, not a script. Claude may add minor NPCs and places freely; the bible itself does not change in v1.

### 5. Replanning between sessions (v2)

Deferred to v2. In v1 the bible stays fixed for the whole campaign: three clues per secret and stall detection keep the plot moving when the player goes off-script, and a one-shot never needs a replan. From v2, at session end the background worker compares the bible with what actually happened and revises future beats, clues and clocks; for example, if the player killed the informant, his clues move elsewhere.

### 6. Ending

`end_campaign` is accepted only when one of these holds:

| Ending | Condition |
| --- | --- |
| Victory | The final beat is resolved before the main clock fills |
| Defeat | The main clock fills before the final beat is resolved |
| Fallen hero | The character dies after three failed death saves |
| Retired | The player ends the campaign from the UI |

Claude then writes an epilogue (a narrow victory, with the clock nearly full or a secret still hidden, can be told as bittersweet), the campaign is marked complete, and the character can be carried into a new campaign.

## Adventure import (v2)

Deferred to v2 (M6); v1 campaigns are always generated. From v2, a campaign can start from a human-written adventure instead of a generated one. The importer converts the adventure into the same campaign bible and keeps the author's original text, so Claude narrates the writer's scenes and improvises only in the gaps. The project is for personal use, so any adventure the player owns or has downloaded can be imported; imported files are never redistributed.

**Pipeline**

1. **Upload.** The setup wizard accepts a PDF, Markdown or text file, stored under `/data/sources`.
2. **Extract.** PDFs are sent to Claude as documents so page layout is kept, or converted to text for plain files. The text is split by heading into locations, NPCs, encounters, read-aloud text, secrets and other sections.
3. **Convert.** Claude maps the adventure into the bible schema: acts and beats from its chapters or areas, locations, NPCs, secrets and their clues, the opening hook, and endings. Like a generated bible, it is checked against the JSON schema and retried on failure.
4. **Fill the gaps.** The importer flags any secret with fewer than three clues and adds clues in other locations. It adds a main clock and a defeat ending when the adventure has none. It maps monsters to SRD stat blocks, using the nearest SRD creature when a monster isn't in the SRD.
5. **Adapt for one player.** Published adventures assume a party of four or five. Cutting monster HP alone does not work for one character, because a single failed save against paralysis or a stun ends the fight with no ally to help. The importer instead starts the character one or two levels above the adventure's recommended level, adds a sidekick NPC that the engine plays in combat, and gives the character one reroll of a failed saving throw per long rest. It reduces monster count only where an encounter still exceeds the solo difficulty budget, and the bible notes where a puzzle or scene needs a second person.
6. **Spoiler-safe review.** The player sees only a summary: counts of acts, NPCs and locations, plus warnings such as "3 secrets had fewer than three clues". The full plan stays hidden unless the player chooses to open it.
7. **Play.** When the player enters a location or meets an NPC, the context builder pulls that part of the original text into the dynamic context. Claude narrates from it, keeping read-aloud text close to the author's wording.

**Storage.** `sources` holds each uploaded file (title, author, file path, hash, import date). `source_chunks` is an FTS5 table of the split text, each chunk tagged with its kind and the bible location or NPC it belongs to. `campaigns.source_id` links a campaign to its adventure.

**Good first imports**

| Adventure | Why start here |
| --- | --- |
| [One Page Dungeon Contest entries](https://spielknights.gumroad.com/l/2024opdc) | Hundreds of short, mostly system-neutral dungeons; ideal one-shots and importer test data |
| [Secrets of Skyhorn Lighthouse](https://www.belloflostsouls.net/2026/07/dd-five-one-shot-adventures-you-can-get-absolutely-free.html) (Arcane Library, level 5) | Free, and praised for exceptionally clear layout, which helps the importer |
| [The Wild Sheep Chase](https://www.belloflostsouls.net/2026/07/dd-five-one-shot-adventures-you-can-get-absolutely-free.html) (Winghorn Press) | Free comedic one-shot, a good test of tone settings |
| [A Most Potent Brew](https://geektogeekmedia.com/geekery/tabletop-gaming/best-free-dnd-one-shots-5e/) | Pay-what-you-want and runs on the free Basic Rules alone |
| [Borderlands Quest: Dagger Danger](https://dungeonsanddragonsfan.com/borderland-quest-dagger-danger/) (Wizards of the Coast, 2026) | Free official beginner one-shot on D&D Beyond |
| Adventures from books the player owns | Longer campaigns once the importer handles one-shots well |

## Memory strategy

Each kind of memory is stored in the shape that fits it and fetched by code before the Claude call, so Claude sees a small, relevant slice instead of the whole campaign. The API round trip is the bottleneck, not local lookups, so nothing is retrieved through extra tool calls.

| Layer | Holds | Store | How it reaches the prompt | Phase |
| --- | --- | --- | --- | --- |
| Game state | Sheet, conditions, inventory, quests, current encounter | Game tables | Full snapshot every turn | v1 |
| Story state | Current act, open beats, local clues, clocks, turns since progress | Story tables | Director block every turn | v1 |
| Campaign plan | The campaign bible | `campaigns`, story tables | Cached system prompt | v1 |
| Recent turns | Last 8 action and narration pairs, verbatim | `turns` | Messages before the final user message | v1 |
| Session recap | Rolling summary of this session plus the last session's final recap | `sessions` | Always in the dynamic context | v1 |
| World graph | NPCs, places, factions, items and their relations over time | `entities`, `facts` | Current facts within 2 hops of entities named in the action or the last narration | v2 |
| Scene recall | One summary per finished scene | `scenes`, `scene_vec` | Top 3 scenes most similar to the action | v2 |
| DM notes | Claude's own notes: running jokes, planned callbacks, player preferences | `dm_notes` | All notes for the campaign, preloaded; written with `write_note` | v2 |

**Scenes (v2).** A scene ends when Claude calls `end_scene` (a change of location, the end of an encounter, a long rest) or after 15 turns without one. Scenes are the unit for scene summaries and scene recall.

**Finding entities without an LLM call.** Entities tied to the current location and scene are always included, so "him" or "the tavern" still resolves. The context builder also matches the action and the last two narrations against entity names and aliases as whole words, ignoring case and skipping aliases shorter than four letters or on a stop-word list, then pulls their current facts (`valid_to_turn` empty) within 2 hops.

**Writing memory.** Every 10 turns and at session end, the background worker (Haiku) folds the turns since its last update into the rolling recap. From v2 it also summarises each finished scene, proposes new or retired facts, which go through the engine's fact functions so validation stays in one place, and stores the scene embedding. Embeddings come from Voyage AI, Anthropic's recommended provider (Anthropic has no embedding model of its own), or a small local model; which one is an open question.

**Budget (v1).** The dynamic context block and the recent-turn history share one token budget, 8,000 tokens by default and set in config. When it is exceeded, content is dropped in this order: rule sections beyond the top two, then (v2) scene recall and facts more than one hop away, then the oldest recent turns. The state snapshot, director block and recap are never dropped.

**Recap length.** The rolling recap is capped at 400 words and the previous session's final recap at 250. The worker rewrites the recap from the old recap plus the turns since its last update instead of appending to it, so it never grows past the cap however long a session runs.

**Campaign plan size.** A generated bible stays small, around 2,000 to 3,000 tokens, so v1 puts it in the system prompt whole. Imported adventures (v2) can be far larger; they will carry only the outline and the current act, with the original text fetched from `source_chunks` per location.

**Why not the Claude memory tool or a graph database.** The memory tool stores files outside SQLite, so they would miss turn rollback and backups, and each read costs a tool round; DM notes therefore live in `dm_notes`. A campaign's world is at most thousands of facts, which one SQLite table answers in milliseconds. Kuzu, the usual embedded graph database, was archived in October 2025, and Graphiti needs a separate graph database and LLM calls to build its graph; both are held in reserve.

## Web UI

Two screens: a setup wizard for new campaigns, and the play screen with the character sheet on the left, the story log on the right and the action box under the log. The sheet always shows what the database says, never what the narration claims.

```
+----------------------+---------------------------------------+
| Kael · Lv 3 Rogue    |  The tavern door creaks open...       |
| HP 18/24             |                                       |
| XP 450/900           |  > I sneak behind the bar             |
| Conditions: none     |  [Stealth] d20+5 = 17 vs DC 15: pass  |
| Skills               |  You slip past unnoticed...           |
| Inventory            |                                       |
| Quests               |                                       |
| Clocks (visible)     |                                       |
| Encounter (if any)   |  [ What do you do?          ] [Send]  |
+----------------------+---------------------------------------+
```

**Setup wizard.** Setting, tone, length, lines and veils, then a class template, name and backstory hook. Submitting it calls `POST /campaigns` and polls `GET /campaigns` with a spinner while the bible is generated, then shows a spoiler-free premise the player can accept or regenerate before session 1 opens with the opening scene.

**Play screen interactions**

- Enter or Send submits the action and shows a thinking indicator until the first roll line or narration arrives. The input locks until `turn_done` or `error` arrives, and stays locked after a reload while `running_turn_id` is set.
- Each `roll` event renders as its own log line: the purpose, the expression, the total, the target and the outcome.
- Narration appears word by word as `narration_delta` events arrive.
- On `state_changed`, the sidebar re-fetches `GET /state`; HP and XP bars animate to the new values.
- On `error`, that turn's partial lines are removed and a Retry button appears.
- Equip and unequip are direct actions that skip Claude. They are disabled while a turn is running or an encounter is active; anything else is typed as an action.
- On page load, `GET /log` restores the session's committed history; a turn still running appears when it commits.
- Clocks appear in the sidebar only when the bible marks them visible (for example a public countdown); hidden clocks stay secret.
- On `campaign_ended`, the log shows the epilogue and the sidebar offers New campaign or Continue with this character.
- Header controls: Campaigns, End session (triggers the final recap), About (SRD attribution).

**Stack.** Server-rendered HTML from FastAPI with htmx and a small script for the event stream. It works in any modern browser on a laptop or phone. A React front end can replace it later without changing the API.

## API surface

The browser sends commands over plain HTTP and receives everything a turn produces over one server-sent events (SSE) stream. The same endpoints will serve the v3 voice client.

| Method and path | Purpose | Response |
| --- | --- | --- |
| `GET /` | The setup wizard or the play screen | HTML |
| `GET /health` | Liveness check for the container | 200 |
| `POST /campaigns` | Create a campaign from the setup form; generates the bible and validates it | 202 with `campaign_id`; status is `generating` until the bible is ready |
| `GET /campaigns` | List campaigns and their status | JSON |
| `GET /state` | Sheet, conditions, inventory, quests, encounter, visible clocks, `running_turn_id` | JSON |
| `GET /log?session=<id>` | Committed turns and rolls for a session | JSON |
| `POST /action` | Submit `{text}` for the open session | 202 with `turn_id`; 409 if a turn is running or no session is open |
| `GET /events` | The SSE stream | Events below |
| `POST /session/start` | Open a session. If the previous session has no final recap, it is written first. The opening narration is stored as turn 0 and streamed | 202 with `session_id` |
| `POST /session/end` | Close the session; the worker writes the final recap | 202 |
| `POST /inventory/{item_id}/equip`, `/unequip` | Direct equip actions | 200 with new state; 409 while a turn is running or an encounter is active |

| Event | Payload | When |
| --- | --- | --- |
| `narration_delta` | turn\_id, text | While the final round streams |
| `roll` | turn\_id, purpose, expr, dice, total, target, outcome | After each engine roll |
| `state_changed` | turn\_id (empty for direct actions) | After a turn commits or a direct action |
| `turn_done` | turn\_id | After the commit |
| `error` | turn\_id, message, retryable | When a turn fails |
| `campaign_ended` | campaign\_id, ending | After `end_campaign` commits |

There is one player, so there is one stream. Events have no ids and are not buffered: a browser that reconnects re-fetches `GET /log` and `GET /state` instead (Turn lifecycle 9).

## Non-functional requirements

The host does light work; latency and cost are set almost entirely by the Claude API calls, so most requirements are about sending less and waiting less.

| Area | Requirement | How |
| --- | --- | --- |
| Latency | First visible output within 2 s for turns without tools, 5 s with tools (targets) | Roll events stream as soon as each roll happens, with a thinking indicator until then; two cache breakpoints; retrieval before the call; bundled tools (`attack` rolls and applies damage in one call) |
| Latency | Full turn bounded | Round cap (default 4), then one last call with tools disabled |
| Cost | Cost per turn visible and flat over a campaign | Token and cached-token counts on every `turns` row, failed turns included; one token budget for context and history |
| Integrity | No partial game state | State tree, turn row and rolls written in one short transaction at commit; discarded on failure |
| Durability | No more than one session of play lost | A `VACUUM INTO` snapshot at every session end, written to a separate backups folder |
| Availability | Survives restarts | Container restart policy `unless-stopped`; a turn cut off by a restart was never written, so it is simply retyped |
| Portability | Same build on PC and Pi | One Dockerfile built on linux/amd64 and linux/arm64; all state in one mounted volume (see Deployment) |
| Security | API key never leaves the server | Key passed to the container from an env file outside the image; never sent to the browser |
| Security | Not reachable from the internet | Port bound to the host or home network; remote play only through Tailscale; no port forwarding |
| Robustness | Tool calls cannot corrupt state | Engine validates every argument against the in-memory state tree |

No local model runs in the container, so CPU and memory use stay low on a Pi 5.

## Deployment

The app ships as one Dockerfile that each machine builds locally, so the same build runs on a PC (linux/amd64) for fast testing and on the Pi 5 (linux/arm64) for play. All state is one SQLite file in a mounted folder, so a campaign moves between machines by copying that folder.

**Image.** Built on the official `python:3.12-slim` base, which exists for both architectures. It contains the app, its Python dependencies (FastAPI and the Anthropic SDK; sqlite-vec from v2) and the SRD import, and runs as a non-root user. The FastAPI server, turn orchestrator and background worker run in one process, so there is a single writer to the database.

**Build.** Each machine builds its own image with `docker compose up -d --build`; the base image and the v1 dependencies have arm64 wheels, so the Pi 5 builds it in a few minutes. A multi-platform `docker buildx` build pushed to a registry can come later if rebuilding on the Pi gets slow.

```yaml
# compose.yaml
services:
  dm:
    build: ../documentation
    ports: [ "8000:8000" ]
    env_file: .env              # ANTHROPIC_API_KEY, models, round cap, budgets
    volumes:
      - ./data:/data            # SQLite database
      - ./backups:/backups      # snapshots at session end; ideally on another disk
    restart: unless-stopped
```

| Environment | Platform | How it runs | Used for |
| --- | --- | --- | --- |
| Dev (PC) | linux/amd64 via Docker Desktop or Docker Engine | `compose.override.yaml` mounts the source and runs the server with auto-reload | Writing code, quick play-tests |
| Tests (PC or CI) | linux/amd64 | `docker compose run dm pytest`, with a fake Claude client | Engine, story and pipeline tests without API cost |
| Play (Pi 5) | linux/arm64 on Raspberry Pi OS 64-bit | `git pull && docker compose up -d --build`; data folder on the NVMe drive | Everyday play |

**Tests.** Engine and story code is plain Python and is unit-tested without Claude. The tool loop is tested with a fake Claude client that returns scripted narration and tool calls, so those tests are fast, free and repeatable. A mode that records real responses as fixtures can come later if scripting them gets tedious.

**Rules for the data folder.** Keep it on a local disk, never a network share, because SQLite's locking is unreliable there. Only one container may use a given data folder at a time. Put the backups folder on a different disk from the data folder (for example a USB drive on the Pi), so one failed drive does not take both.

## Risks and mitigations

The largest risks are narration that disagrees with the engine and a plot that stalls or rails the player; most others are latency and cost creeping up over a campaign.

| Risk | Effect | Mitigation |
| --- | --- | --- |
| Claude describes an outcome before its tool result | Story says "you hit" when the roll missed | No prose in tool rounds, and any written is stripped before the next round; only the final round streams; narration contract; roll audit trail checked in M5 |
| Claude contradicts state (spends gold the character lacks) | Story and sheet disagree | Snapshot every turn; engine rejects impossible changes and returns the error to Claude |
| Plot dead-ends | Player stuck with no lead | Three clues per secret; stall detection pushes a clue or complication after 8 idle turns |
| Plot railroads the player | Player choices feel ignored | Bible is a guide; off-script NPCs and places allowed; v2 replanning adapts beats to what happened |
| Invalid or incoherent bible | Broken campaign from turn 0 | JSON schema validation, regenerate on failure; setup shows a spoiler-free premise for the player to accept |
| Content crosses the player's limits | Unwanted scenes | Lines and veils in the cached system prompt; a Flag-and-retry button can follow if needed |
| Context grows over a long campaign | Slower, costlier turns | One token budget with a fixed drop order; recap, bible and graph replace raw history |
| Many tool rounds in one turn | Long waits | Bundled tools; resolve\_npc\_turns plays a whole combat round in one call; round cap, then one narration-only call |
| Cache misses | Higher cost and latency | Fixed system prompt per campaign; two breakpoints; cached tokens logged per turn |
| API outage or rate limit | Turn fails | Retry with backoff, then mark failed and offer Retry |
| A dependency lacks an arm64 build | Image builds on PC but not for the Pi | The Pi builds the image itself from M0; pure-Python or multi-arch dependencies only |
| Mixed rulesets | Stat blocks and rule text disagree | One SRD version per campaign in `campaigns.ruleset` |
| Licence non-compliance | Distribution problems later | SRD content only; attribution on the About page |
| Import misreads an adventure (v2) | Wrong NPCs, missing clues or broken acts | Schema validation; spoiler-safe warnings at review; original text retrieved during play so narration still follows the author |

## Milestones

Each milestone ends in something testable, the container comes first so every later milestone is tested on the PC and the Pi, and the engine and story are proven in a terminal before any UI exists. No dates are set yet.

1. **M0: Container and dev setup.** Dockerfile, `compose.yaml`, dev override with auto-reload, and `/health`. *Exit: the image builds on the PC and on the Pi and answers* `/health` *on both.*
2. **M1: Engine and terminal loop.** Data layer and schema, dice, every v1 mechanics tool, the in-memory state tree, three class templates, and hand-written monster fixtures, plus a command-line loop that calls Claude with tool use. *Exit: in the terminal, a scene with a skill check, a contest and a fight against three monsters, resolved with resolve\_npc\_turns, applies a condition and reaches death saves, and unit tests cover each tool, with a fake Claude client for the tool loop.*
3. **M2: Rules grounding.** SRD import into the `srd_*` tables replacing the fixtures, the FTS5 index, keyword retrieval, `lookup_rule` and `lookup_srd`. *Exit: encounters use real stat blocks, and a grapple uses `contest` with the grappling rules in context.*
4. **M3: Story director.** Setup inputs, bible generation with schema validation, story tables and tools, director block, stall detection and endings. *Exit: a one-shot plays from its opening hook to a valid ending in the terminal, and a scripted idle run triggers a clue within 8 turns.*
5. **M4: Server and streaming.** FastAPI endpoints, the SSE stream, the turn protocol (stripped tool-round text, the narration-only final call, commit and failure paths), both cache breakpoints, the token budget, background recaps, and session start and end. *Exit: a turn submitted with curl streams rolls and narration; a forced API failure leaves game state unchanged and saves a failed turn row; turn 2 reports cached tokens; a session started without the previous final recap writes it first; campaign creation returns at once and the campaign shows as ready when its bible is saved.*
6. **M5: Web UI (v1 release).** Setup wizard, sheet with conditions and visible clocks, log with roll lines, direct equip actions, reload recovery, campaign ending and the About page. *Exit: the success criteria in the Overview are met on the Pi.*
7. **M6: v2.** World graph, scenes and scene recall, DM notes (which also hold rulings), spellcasting with spell slots, a full character builder, adventure import with solo scaling, between-session replanning, and optional non-fantasy reskins. *Exit: an NPC introduced in session 1 is recalled correctly in session 3 without replaying old turns, a spellcaster completes a fight, and an imported one-page dungeon plays to an ending using its original room text.*
8. **M7: Voice (v3).** Push-to-talk speech-to-text feeding `POST /action`, and Piper text-to-speech reading narration aloud. *Exit: a full scene played by voice alone.*

## Open questions

- [ ] Ruleset: start on SRD 5.1 (2014) as proposed, or go straight to SRD 5.2 (2024)?
- [ ] Models: is Opus worth its extra latency for narration, or only for generating the campaign bible? Decide after M3 play-tests.
- [ ] History caching: after M5, do the logged token counts justify a third breakpoint after the recent turns, with a window that drops five turns at a time?
- [ ] Encounter panel: show enemy HP and initiative order, or only describe them in narration?
- [ ] Clocks: should the player see the antagonist's main clock, or only feel it through the story?
- [ ] Non-fantasy settings in v2: reskin SRD mechanics, or add a separate open ruleset?
- [ ] Character carry-over: keep level and gear in a new campaign, or reset to level 1?
- [ ] Embeddings in v2: Voyage AI (an extra API and key) or a small local model in the container?
- [ ] Remote play: is Tailscale needed for v1, or is home Wi-Fi enough?
- [ ] Import (v2): send PDFs to Claude as whole documents, or extract text locally first to save tokens?

## Design review

An independent auditor reviewed the first draft's logical flow on 2026-11-17 and raised 15 issues. All 15 are resolved in this revision, which also adds Story design and Deployment. A second review the same day raised 13 more; they are listed in the second table below.

| # | Severity | Finding | Resolution |
| --- | --- | --- | --- |
| 1 | High | Streamed text from tool rounds could state outcomes before results; rollback discarded text already shown | Tool-round text held back, only the final round streams, narration-only last call at the cap (Turn lifecycle 5, 6) |
| 2 | High | Turn record, rolls and tokens were lost on rollback; one long write transaction blocked other writers | Turn row and rolls committed immediately; game changes held in a change set and applied in one short transaction (Turn lifecycle 2, 7, 8) |
| 3 | High | Tools did not cover saves, conditions, contests, rests, turn order or spells | Added `saving_throw`, `contest`, `set_condition`, `advance_turn`, `rest`; spellcasting moved to v2 (LLM integration, Rules grounding) |
| 4 | High | Memory-tool files sat outside rollback and backups, and cost tool rounds | DM notes moved to the `dm_notes` table, preloaded into context (Memory strategy) |
| 5 | Medium | One cache breakpoint left tool rounds 2 to 4 uncached | Dynamic context moved into the final user message; second breakpoint added (LLM integration) |
| 6 | Medium | 2 s first-words target unreachable on tool turns | Target redefined as first visible output, 2 s without tools and 5 s with (Overview, NFR) |
| 7 | Medium | M1 depended on M2 data and an undecided character creation; M3 exit untested | Fixtures and class templates in M1; M4 exit tests caching, recaps and reconnects (Milestones) |
| 8 | Medium | Token budget needed in v1 but built in v2 | Budget in v1 with a defined drop order (Memory strategy, M4) |
| 9 | Medium | Missing final recap; opening recap had no storage | Missing recap generated at session start; opening stored as turn 0 (API surface) |
| 10 | Medium | Equip could race with a running turn; `turn_id` missing for direct actions | 409 while a turn runs or an encounter is active; `turn_id` optional (API surface) |
| 11 | Medium | Reconnect lost streamed text and unlocked the input | Event ids, per-turn buffer, `Last-Event-ID` replay, `running_turn_id` (Turn lifecycle 9, API surface) |
| 12 | Low to Medium | Diagram showed only the engine writing; worker missing | One data layer for all writes; worker added to the diagram (Data model, System architecture) |
| 13 | Low to Medium | Scene, campaign and ruling log undefined | `scenes`, `campaigns` and `rulings` tables; `end_scene` and `record_ruling` tools |
| 14 | Low | Long-term NPC recall listed as a v1 goal | Goal split: recaps in v1, long-term recall in v2 (Overview) |
| 15 | Low | Seed policy, roll purpose, WAL backups, retired facts | System random source; `purpose` on rolls; `VACUUM INTO`; current facts only |

**Second review.** Twelve of the 13 findings were accepted; one design choice was kept, with the reason given.

| # | Finding | Verdict | Resolution |
| --- | --- | --- | --- |
| 1 | The recent-turn history was never served from the cache across turns | Accepted | History is clean action and narration pairs, with a breakpoint after it, and the window drops five turns at a time (LLM integration) |
| 2 | A 4-round cap cannot fit a combat round against several monsters | Accepted | `resolve_npc_turns` plays every monster and sidekick turn in code in one call (LLM integration) |
| 3 | Campaign creation and session start blocked the HTTP request for a minute or more | Accepted | Both return 202 and run as background jobs that report `job_progress` events (API surface) |
| 4 | Background jobs could overwrite each other or change facts mid-turn | Partly accepted | One job queue run in order; v2 fact changes wait until no turn is running. A slightly stale recap is harmless, because recent turns are sent verbatim (Turn lifecycle 9) |
| 5 | Solo scaling by cutting HP fails against save-or-lose effects | Accepted | One or two bonus levels, an engine-played sidekick and one save reroll per long rest (Adventure import) |
| 6 | No feedback while non-roll tools run | Accepted | `tool_status` events (Turn lifecycle 5, API surface) |
| 7 | Plain string search misses pronouns and matches common words | Accepted | Entities at the current location are always included; whole-word, case-insensitive matching with a stop list (Memory strategy) |
| 8 | A command POST plus a separate event stream is unconventional | Kept | It lets a reloaded page reattach to a turn still running; dropped connections are already covered by `Last-Event-ID` replay |
| 9 | The change set needed every tool to query SQLite and pending changes together | Accepted | An in-memory state tree loaded per turn and written at commit (Turn lifecycle 2, 5, 7) |
| 10 | Hidden tool-round text left gaps in the final narration | Accepted | No prose in tool rounds, and any text written is stripped before the next round (Turn lifecycle 5) |
| 11 | Pre-made templates were the only way to build a character | Accepted | Standard array with two class skills offered alongside templates (Story design, Rules grounding) |
| 12 | Backups landed on the same mount, on a nightly timer | Accepted | Snapshots at session end into a separate backups mount (Deployment) |
| 13 | The health check started a Python process every interval | Accepted (minor) | `curl` health check (Deployment) |

### Simplification pass

A later pass on 2026-11-17 trimmed robustness that a one-player game on a Pi does not need in v1, mostly by moving it to v2 or a later optimisation; the core loop, code-computed mechanics, bounded context and plot structure are unchanged.

| Area | Change | Why |
| --- | --- | --- |
| Event stream | Dropped event ids, the per-turn buffer and `Last-Event-ID` replay; a reconnecting browser re-fetches `GET /log` and `GET /state` | One player on home Wi-Fi; a reload already recovers everything committed |
| Turn records | Turn row and rolls written in the same commit transaction as the state; no `running` status, void rolls or start-up sweep | Same no-partial-state guarantee with one write path; a crashed turn is just retyped |
| Prompt caching | Two breakpoints and a plain 8-turn window; the history breakpoint and five-turn drop are a later optimisation | History is a few thousand tokens; the extra rules saved little |
| Progress events | Dropped `tool_status` and `job_progress`; the UI shows a thinking indicator, the wizard polls `GET /campaigns`, and session start writes a missing recap inline | Same feedback without two event types or a job framework |
| Adventure import | Whole pipeline, solo scaling (sidekick, bonus levels, save rerolls) and bible trimming moved to v2 (M6) | Largest v1 feature, and not needed to play a generated campaign |
| Story director | Replanning and bible versions moved to v2; bittersweet folded into victory as narration; Flag button deferred | Three clues and stall detection keep a fixed bible playable; one-shots never replan |
| Scenes and rulings | `end_scene`, `scenes`, `record_ruling` and `rulings` moved to v2; the recap updates every 10 turns | Scenes only fed v2 recall; rulings fit in v2 DM notes |
| Characters | Templates only in v1; the standard array joins the v2 character builder | One fewer setup step to build and validate |
| Deployment and tests | Each machine builds locally; no registry, CI multi-arch build or compose health check; a fake Claude client replaces replay mode | Two machines and one user; scripted fakes cover the tool loop |

## References

- [D&D System Reference Document 5.1 and 5.2, CC-BY-4.0](https://dndbeyond.com/srd) (D&D Beyond)
- [5e-srd-api: SRD 5.1 data as a REST API](https://github.com/5e-bits/5e-srd-api)
- [The DM's Toolkit SRD 5.2 API](https://apisearch.thedmstoolkit.com/)
- [Prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) (Claude API docs)
- [Memory tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool) (Claude API docs)
- [Embeddings and Voyage AI](https://docs.anthropic.com/en/docs/build-with-claude/embeddings) (Claude API docs)
- [sqlite-vec](https://github.com/asg017/sqlite-vec)
- [Graphiti temporal knowledge graph](https://github.com/getzep/graphiti)
- [What is KuzuDB, and its October 2025 archive](https://www.puppygraph.com/blog/what-is-kuzudb)
- [Large Language Models Are Bad Dice Players (2026)](https://arxiv.org/html/2601.05414v1)
- [Large Language Models and Games: A Survey and Roadmap](https://arxiv.org/pdf/2402.18659)
- [Building a D&D Dungeon Master out of Claude](https://xebia.com/blog/building-a-dnd-dungeon-master-out-of-claude-part-i/) (Xebia)
- [dm20-protocol: D&D 5e MCP server with a Narrator and an Arbiter](https://github.com/Polloinfilzato/dm20-protocol)
- [Piper TTS on a Raspberry Pi 5](https://localaimaster.com/blog/piper-tts-setup-guide) (for v3)
- [The Three Clue Rule](https://thealexandrian.net/wordpress/1118/roleplaying-games/three-clue-rule) (The Alexandrian)
- [Progress clocks, Blades in the Dark](https://roll20.net/compendium/BITD/Progress%20clocks) (Roll20 compendium)
- [Lines and veils and other safety tools](https://slyflourish.com/safety_tools.html) (Sly Flourish)
- [Multi-platform builds](https://docs.docker.com/build/building/multi-platform/) (Docker docs)
- [2024 One Page Dungeon Contest compendium](https://spielknights.gumroad.com/l/2024opdc) (CC BY-SA)
- [Five free one-shot adventures](https://www.belloflostsouls.net/2026/07/dd-five-one-shot-adventures-you-can-get-absolutely-free.html) (Bell of Lost Souls, July 2026)
