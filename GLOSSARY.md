# Pi Dungeon Master

A single-player, text-based D&D 5e game. Claude narrates; the app's code referees the rules and plans the story.

## Play

**Campaign**:
One story from setup to an Ending, played by one character over one or more Sessions.
_Avoid_: Game, adventure (reserved for imported human-written material in v2)

**Session**:
One sitting of play within a Campaign, opened and closed by the player, with its own Recap.
_Avoid_: Game night, run

**Turn**:
One player action, resolved by the engine and narrated by Claude.
_Avoid_: Round, move, step

**Tool round**:
One Claude call within a Turn; a Turn has one or more, up to the Tool round cap.
_Avoid_: Round, iteration, LLM turn

**Tool round cap**:
The most Tool rounds a Turn may use before Claude must narrate with tools disabled.
_Avoid_: Round cap

**Narration**:
The prose Claude writes in the final Tool round of a Turn, the only text the player sees.
_Avoid_: Response, output

**Recap**:
A short summary of play so far: the Rolling recap of the current Session, or the Final recap of a finished one.
_Avoid_: Summary, memory

**Lines and veils**:
Player-set content limits: Lines are never shown; Veils happen off-screen.
_Avoid_: Filters, content settings

## Mechanics

**Character**:
The single player character, built from a Template.
_Avoid_: PC, player, hero

**Template**:
A pre-made level 1 character for one class.
_Avoid_: Preset, archetype, build

**Encounter**:
A fight, from start to end, with its Combatants.
_Avoid_: Combat, battle

**Combatant**:
A participant in an Encounter other than the Character, built from a monster stat block.
_Avoid_: Enemy, mob, NPC (an NPC is a story figure, not necessarily a fighter)

**Combat round**:
One pass through initiative order in which every Combatant and the Character act once.
_Avoid_: Round

**Combatant's turn**:
One Combatant's or the Character's slot within a Combat round.
_Avoid_: Turn (reserved for the player's action)

**Roll**:
One dice result produced by the engine, with its purpose, expression, total, target and outcome.
_Avoid_: Dice result

**Ruleset**:
The single SRD version a Campaign follows: SRD 5.1 or SRD 5.2.
_Avoid_: Edition, rules version

## Story

**Campaign bible**:
The hidden plan for a Campaign, generated at setup: premise, antagonist, Acts, Beats, Secrets, Clues, Clocks, NPCs, locations, Endings and the opening scene.
_Avoid_: Plan, script, outline

**Act**:
A major part of a Campaign with its own goal, made of 2 to 4 Beats.
_Avoid_: Chapter, arc

**Beat**:
A story milestone within an Act that moves the plot forward.
_Avoid_: Milestone, objective, plot point

**Secret**:
A revelation the player needs in order to progress.
_Avoid_: Mystery, twist

**Clue**:
One piece of evidence, placed in a location, that points to a Secret; every Secret has at least three.
_Avoid_: Hint, lead

**Clock**:
A segmented progress track that fills as time passes or threats go unchecked, with a consequence when full.
_Avoid_: Timer, countdown, tracker

**Main clock**:
The Clock tracking the antagonist's plan; it decides Victory or Defeat.
_Avoid_: Doom clock

**Director block**:
The per-Turn summary of story state given to Claude: current Act and goal, open Beats, local Clues, Clocks, and Turns since last progress.
_Avoid_: Story context, plot state

**Stall**:
Eight Turns in a row with no Beat, Clue or Clock progress.
_Avoid_: Idle, stuck

**Ending**:
How a Campaign concludes: Victory, Defeat, Fallen hero or Retired, each with a fixed condition.
_Avoid_: Outcome, finale
