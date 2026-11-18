# Pi Dungeon Master

A single-player, text-based D&D 5e game. Claude narrates; the app's code referees the rules and plans the story.

## Play

**Campaign**:
One story from setup to an Ending, played by one character over one or more Sessions.
_Avoid_: Game, adventure (reserved for imported human-written material in v2)

**Session**:
One sitting of play within a Campaign, opened and closed by the player, with its own Recap. At most one Session is open at a time, across all Campaigns.
_Avoid_: Game night, run

**Open session**:
The one Session not yet closed; every player action goes to it. Opening a Session closes any other first.
_Avoid_: Current session, active session

**Turn**:
One player action, resolved by the engine and narrated by Claude. Turns are numbered across the whole Campaign, not per Session; Turn 0 is the Campaign's opening.
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

**Feature**:
A class ability with limited uses that recover on a rest, such as Rage or Second Wind, or an automatic bonus such as Sneak Attack.
_Avoid_: Ability (that is Strength, Dexterity and the rest), power, skill

**Encounter**:
A fight, from start to end, with its Combatants.
_Avoid_: Combat, battle

**Combatant**:
A participant in an Encounter other than the Character, built from a Stat block.
_Avoid_: Enemy, mob, NPC (an NPC is a story figure, not necessarily a fighter)

**Stat block**:
The SRD record of a monster's numbers and actions that a Combatant is built from.
_Avoid_: Monster data, fixture

**Combat round**:
One pass through initiative order in which every Combatant and the Character act once.
_Avoid_: Round

**Combatant's turn**:
One Combatant's or the Character's slot within a Combat round.
_Avoid_: Turn (reserved for the player's action)

**Roll**:
One dice result produced by the engine, with its purpose, expression, total, target and outcome.
_Avoid_: Dice result

**Roll prompt**:
A pause in a Turn where the player clicks to make the Character's d20 Roll; monster Rolls never prompt. Auto-roll skips it.
_Avoid_: Roll request, dice button

**Ruleset**:
The single SRD version a Campaign follows: SRD 5.1 or SRD 5.2.
_Avoid_: Edition, rules version

**Rule section**:
One headed piece of SRD rules prose, such as Grappling, given to Claude when the player's action names its rule or when Claude looks it up.
_Avoid_: Chunk, rule

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
A revelation the player needs in order to progress, belonging to one Act; learned as soon as any one of its Clues is revealed.
_Avoid_: Mystery, twist

**Location**:
A place named in the Campaign bible; the Character is always at exactly one. Places Claude invents during play are not Locations.
_Avoid_: Area, room, scene

**Quest**:
A goal the Character is pursuing, shown to the player in the quest log; Claude may add one at any time. Unrelated to Beats.
_Avoid_: Objective, task

**Player notes**:
A Campaign's one free-text page the player writes for themself; Claude never sees it. Unrelated to DM notes, which are Claude's own.
_Avoid_: Journal, notepad, DM notes

**Clue**:
One piece of evidence, placed in a Location, that points to a Secret; every Secret has at least three.
_Avoid_: Hint, lead

**Clock**:
A segmented progress track that fills as time passes or threats go unchecked, with a consequence when full.
_Avoid_: Timer, countdown, tracker

**Main clock**:
The Clock tracking the antagonist's plan; it decides Victory or Defeat.
_Avoid_: Doom clock

**Visible clock**:
A Clock the player can see, such as a public countdown, marked so in the Campaign bible; every other Clock, the Main clock included, stays hidden.
_Avoid_: Public clock, shown clock

**Director block**:
The per-Turn summary of story state given to Claude: current Act and goal, open Beats, local Clues, Clocks, and Turns since last progress.
_Avoid_: Story context, plot state

**Stall**:
Eight Turns in a row with no Beat advanced and no Clue revealed; moving and Clock ticks do not count as progress.
_Avoid_: Idle, stuck

**Ending**:
How a Campaign concludes: Victory, Defeat, Fallen hero or Retired, each with a fixed condition.
_Avoid_: Outcome, finale
