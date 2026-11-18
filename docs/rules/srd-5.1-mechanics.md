# SRD 5.1 Mechanics Reference (v1 engine)

Rules reference for every mechanic the v1 engine implements, taken only from the System Reference Document 5.1 (2014 rules). Engine code and tests cite this file by section. No 2024 (SRD 5.2) rules appear here.

## Sources

- **Primary:** *System Reference Document 5.1*, Creative Commons version, Wizards of the Coast. URL: <https://media.wizards.com/2023/downloads/dnd/SRD_CC_v5.1.pdf> (403 pages, PDF 1.6). Retrieved 2026-11-17. The fallback URL (<https://media.wizards.com/2016/downloads/DND/SRD-OGL_V5.1.pdf>) was not needed.
- **Cross-check only:** 5e-bits/5e-database JSON, `src/2014/en/` at commit `536928f7460b5e5343dfb1805ded15706616765e` (latest commit touching that folder, dated 2026-09-12). Files used: `5e-SRD-Equipment.json`, `5e-SRD-Levels.json`, `5e-SRD-Classes.json`, `5e-SRD-Skills.json`, `5e-SRD-Weapon-Properties.json`, `5e-SRD-Conditions.json`. Base URL: <https://raw.githubusercontent.com/5e-bits/5e-database/536928f7460b5e5343dfb1805ded15706616765e/src/2014/en/>. Retrieved 2026-11-17. Where the PDF and JSON disagree, the PDF wins; see [PDF/JSON disagreements](#pdfjson-disagreements).

**Page numbers.** "p. N" is the page number printed in the PDF footer. It is the same as the PDF page index (page 1 is the Legal Information page).

**Quote normalisation.** Text was taken out with `pdftotext`. That tool turns every hyphen and dash in this PDF into a double hyphen (`well--ordered`, `focus--not`). In the quotes below, a doubled hyphen inside a word is shown as one hyphen (`two-handed`), and a doubled hyphen between words is shown as an em dash (`focus—not`). Bullets become list items; where a bulleted list or a stat-block list (for example a class's Hit Points and Proficiencies lines) is run into one quote, the items are separated with a semicolon or a full stop that the PDF does not print. The PDF's own typos are kept (for example a backtick for an apostrophe in "combatants`", p. 90). Nothing else was changed. Tables were rebuilt from the PDF's column order and checked against the JSON.

**Required attribution (quoted from SRD 5.1, Legal Information, p. 1):**

> This work includes material taken from the System Reference Document 5.1 ("SRD 5.1") by Wizards of the Coast LLC and available at https://dnd.wizards.com/resources/systems-reference-document. The SRD 5.1 is licensed under the Creative Commons Attribution 4.0 International License available at https://creativecommons.org/licenses/by/4.0/legalcode.

The same page says: "Please do not include any other attribution regarding Wizards other than that provided above. You may, however, include a statement on your work that it is "compatible with fifth edition" or "5E compatible.""

**Left out on purpose:** spells, the spell list, spellcasting rules, magic items, and the individual monster stat blocks. M2 imports those from the SRD dataset.

---

## 1. Ability scores, modifiers and proficiency bonus

### 1.1 Ability scores and modifiers

There are six abilities. A score of 10–11 is average, adventurers can reach 20, and monsters can reach 30.

> Six abilities provide a quick description of every creature's physical and mental characteristics: Strength, measuring physical power; Dexterity, measuring agility; Constitution, measuring endurance; Intelligence, measuring reasoning and memory; Wisdom, measuring perception and insight; Charisma, measuring force of personality

(SRD 5.1, Using Ability Scores, p. 76)

> A score of 10 or 11 is the normal human average, but adventurers and many monsters are a cut above average in most abilities. A score of 18 is the highest that a person usually reaches. Adventurers can have scores as high as 20, and monsters and divine beings can have scores as high as 30.

(SRD 5.1, Using Ability Scores — Ability Scores and Modifiers, p. 76)

Modifier = floor((score − 10) / 2).

> To determine an ability modifier without consulting the table, subtract 10 from the ability score and then divide the total by 2 (round down).

(SRD 5.1, Using Ability Scores — Ability Scores and Modifiers, p. 76)

**Ability Scores and Modifiers** (SRD 5.1, p. 76)

| Score | Modifier |
| --- | --- |
| 1 | −5 |
| 2–3 | −4 |
| 4–5 | −3 |
| 6–7 | −2 |
| 8–9 | −1 |
| 10–11 | +0 |
| 12–13 | +1 |
| 14–15 | +2 |
| 16–17 | +3 |
| 18–19 | +4 |
| 20–21 | +5 |
| 22–23 | +6 |
| 24–25 | +7 |
| 26–27 | +8 |
| 28–29 | +9 |
| 30 | +10 |

### 1.2 Proficiency bonus

Proficiency bonus depends on character level (table in 8.1). It is added at most once to a roll, and it is multiplied or divided at most once.

> Characters have a proficiency bonus determined by level. Monsters also have this bonus, which is incorporated in their stat blocks. The bonus is used in the rules on ability checks, saving throws, and attack rolls. Your proficiency bonus can't be added to a single die roll or other number more than once.

(SRD 5.1, Using Ability Scores — Proficiency Bonus, p. 77)

> If a circumstance suggests that your proficiency bonus applies more than once to the same roll, you still add it only once and multiply or divide it only once.

(SRD 5.1, Using Ability Scores — Proficiency Bonus, p. 77)

Doubling proficiency you don't have gives 0.

> if a feature or effect allows you to multiply your proficiency bonus when making an ability check that wouldn't normally benefit from your proficiency bonus, you still don't add the bonus to the check. For that check your proficiency bonus is 0, given the fact that multiplying 0 by any number is still 0.

(SRD 5.1, Using Ability Scores — Proficiency Bonus, p. 77)

> In general, you don't multiply your proficiency bonus for attack rolls or saving throws.

(SRD 5.1, Using Ability Scores — Proficiency Bonus, p. 77)

**Proficiency bonus by level** (from the Character Advancement table, SRD 5.1, Beyond 1st Level, p. 56)

| Levels | Proficiency bonus |
| --- | --- |
| 1–4 | +2 |
| 5–8 | +3 |
| 9–12 | +4 |
| 13–16 | +5 |
| 17–20 | +6 |

---

## 2. Ability checks, skills, advantage and disadvantage

### 2.1 Ability checks and DCs

Roll d20 + ability modifier (+ bonuses). The check succeeds if the total is equal to or greater than the DC.

> To make an ability check, roll a d20 and add the relevant ability modifier. As with other d20 rolls, apply bonuses and penalties, and compare the total to the DC. If the total equals or exceeds the DC, the ability check is a success

(SRD 5.1, Using Ability Scores — Ability Checks, p. 77)

**Typical Difficulty Classes** (SRD 5.1, p. 77)

| Task difficulty | DC |
| --- | --- |
| Very easy | 5 |
| Easy | 10 |
| Medium | 15 |
| Hard | 20 |
| Very hard | 25 |
| Nearly impossible | 30 |

The SRD has no rule that a natural 1 or 20 on an ability check fails or succeeds automatically. That rule exists only for attack rolls (4.13) and death saves (4.26).

### 2.2 Contests

Both sides roll checks, and the higher total wins. On a tie, nothing changes.

> Both participants in a contest make ability checks appropriate to their efforts. They apply all appropriate bonuses and penalties, but instead of comparing the total to a DC, they compare the totals of their two checks. The participant with the higher check total wins the contest.

(SRD 5.1, Using Ability Scores — Contests, p. 77)

> If the contest results in a tie, the situation remains the same as it was before the contest. Thus, one contestant might win the contest by default.

(SRD 5.1, Using Ability Scores — Contests, p. 77)

### 2.3 Skills

Each skill belongs to one ability. No skill uses Constitution. Proficiency adds the proficiency bonus.

> The skills related to each ability score are shown in the following list. (No skills are related to Constitution.)

(SRD 5.1, Using Ability Scores — Skills, p. 78)

| Ability | Skills |
| --- | --- |
| Strength | Athletics |
| Dexterity | Acrobatics, Sleight of Hand, Stealth |
| Intelligence | Arcana, History, Investigation, Nature, Religion |
| Wisdom | Animal Handling, Insight, Medicine, Perception, Survival |
| Charisma | Deception, Intimidation, Performance, Persuasion |

(SRD 5.1, Using Ability Scores — Skills, p. 78. JSON `5e-SRD-Skills.json` lists the same 18 skills and abilities.)

> proficiency in a skill means an individual can add his or her proficiency bonus to ability checks that involve that skill. Without proficiency in the skill, the individual makes a normal ability check.

(SRD 5.1, Using Ability Scores — Skills, p. 78)

Variant: the GM may pair a skill with a different ability, for example Constitution (Athletics).

> In such cases, the GM might ask for a check using an unusual combination of ability and skill, or you might ask your GM if you can apply a proficiency to a different check.

(SRD 5.1, Using Ability Scores — Variant: Skills with Different Abilities, p. 78)

What each skill covers (one-line summaries; full text on pp. 79–83):

- **Athletics**: "climbing, jumping, or swimming" (p. 79).
- **Acrobatics**: "your attempt to stay on your feet in a tricky situation" and "acrobatic stunts" (p. 80).
- **Sleight of Hand**: "an act of legerdemain or manual trickery" (p. 80).
- **Stealth**: "when you attempt to conceal yourself from enemies, slink past guards, slip away without being noticed, or sneak up on someone" (p. 80).
- **Arcana, History, Nature, Religion**: "recall lore about" their subject (p. 81).
- **Investigation**: "When you look around for clues and make deductions based on those clues" (p. 81).
- **Animal Handling**: "calm down a domesticated animal, keep a mount from getting spooked, or intuit an animal's intentions" (p. 82).
- **Insight**: "determine the true intentions of a creature" (p. 82).
- **Medicine**: "try to stabilize a dying companion or diagnose an illness" (p. 82).
- **Perception**: "spot, hear, or otherwise detect the presence of something" (p. 82).
- **Survival**: "follow tracks, hunt wild game, guide your group through frozen wastelands… predict the weather, or avoid quicksand" (p. 82).
- **Deception**: "convincingly hide the truth, either verbally or through your actions" (p. 82).
- **Intimidation**: "influence someone through overt threats, hostile actions, and physical violence" (p. 82).
- **Performance**: "delight an audience with music, dance, acting, storytelling" (p. 82).
- **Persuasion**: "influence someone or a group of people with tact, social graces, or good nature" (p. 82).

Tool proficiency adds the proficiency bonus to checks made with that tool.

> Proficiency with a tool allows you to add your proficiency bonus to any ability check you make using that tool.

(SRD 5.1, Equipment — Tools, p. 70)

> Thieves' Tools. … Proficiency with these tools lets you add your proficiency bonus to any ability checks you make to disarm traps or open locks.

(SRD 5.1, Equipment — Tools, pp. 70–71)

### 2.4 Passive checks

Passive score = 10 + all modifiers that apply. Add 5 for advantage; subtract 5 for disadvantage.

> 10 + all modifiers that normally apply to the check. If the character has advantage on the check, add 5. For disadvantage, subtract 5. The game refers to a passive check total as a score.

(SRD 5.1, Using Ability Scores — Passive Checks, p. 78)

### 2.5 Working together (help outside combat)

The leader rolls with advantage. A helper must be able to do the task alone. In combat, helping takes the Help action (4.7).

> The character who's leading the effort—or the one with the highest ability modifier—can make an ability check with advantage, reflecting the help provided by the other characters. In combat, this requires the Help action. A character can only provide help if the task is one that he or she could attempt alone.

(SRD 5.1, Using Ability Scores — Working Together, p. 79)

### 2.6 Group checks

Everyone rolls. If at least half succeed, the group succeeds.

> To make a group ability check, everyone in the group makes the ability check. If at least half the group succeeds, the whole group succeeds. Otherwise, the group fails.

(SRD 5.1, Using Ability Scores — Group Checks, p. 79)

### 2.7 Advantage and disadvantage

Roll two d20s and keep the higher (advantage) or the lower (disadvantage).

> you roll a second d20 when you make the roll. Use the higher of the two rolls if you have advantage, and use the lower roll if you have disadvantage.

(SRD 5.1, Using Ability Scores — Advantage and Disadvantage, p. 76)

Several sources of the same kind never add a third die.

> If multiple situations affect a roll and each one grants advantage or imposes disadvantage on it, you don't roll more than one additional d20.

(SRD 5.1, Using Ability Scores — Advantage and Disadvantage, p. 76)

If there is any advantage and any disadvantage, they cancel, whatever the count on each side.

> If circumstances cause a roll to have both advantage and disadvantage, you are considered to have neither of them, and you roll one d20. This is true even if multiple circumstances impose disadvantage and only one grants advantage or vice versa.

(SRD 5.1, Using Ability Scores — Advantage and Disadvantage, p. 76)

A reroll feature (such as Lucky) rerolls one of the two dice, chosen by the roller.

> When you have advantage or disadvantage and something in the game, such as the halfling's Lucky trait, lets you reroll the d20, you can reroll only one of the dice. You choose which one.

(SRD 5.1, Using Ability Scores — Advantage and Disadvantage, p. 76)

### 2.8 Inspiration

The SRD includes Inspiration. The GM awards it. You either have it or you don't. Spending it gives advantage on one attack roll, saving throw or ability check.

> You either have inspiration or you don't—you can't stockpile multiple "inspirations" for later use.

(SRD 5.1, Inspiration — Gaining Inspiration, p. 60)

> If you have inspiration, you can expend it when you make an attack roll, saving throw, or ability check. Spending your inspiration gives you advantage on that roll.

(SRD 5.1, Inspiration — Using Inspiration, p. 60)

You can also give your inspiration to another player character.

> Additionally, if you have inspiration, you can reward another player for good roleplaying, clever thinking, or simply doing something exciting in the game. When another player character does something that really contributes to the story in a fun and interesting way, you can give up your inspiration to give that character inspiration.

(SRD 5.1, Inspiration — Using Inspiration, p. 60)

### 2.9 Hiding

Hiding is a Dexterity (Stealth) check. It is contested by Wisdom (Perception) checks from creatures that search, or compared against passive Perception. You can't hide from a creature that can see you clearly.

> When you try to hide, make a Dexterity (Stealth) check. Until you are discovered or you stop hiding, that check's total is contested by the Wisdom (Perception) check of any creature that actively searches for signs of your presence. You can't hide from a creature that can see you clearly, and you give away your position if you make noise

(SRD 5.1, Using Ability Scores — Hiding, p. 80)

> In combat, most creatures stay alert for signs of danger all around, so if you come out of hiding and approach a creature, it usually sees you. However, under certain circumstances, the GM might allow you to stay hidden as you approach a creature that is distracted, allowing you to gain advantage on an attack roll before you are seen.

(SRD 5.1, Using Ability Scores — Hiding, pp. 80–81)

> the GM compares your Dexterity (Stealth) check with that creature's passive Wisdom (Perception) score, which equals 10 + the creature's Wisdom modifier, as well as any other bonuses or penalties. If the creature has advantage, add 5. For disadvantage, subtract 5.

(SRD 5.1, Using Ability Scores — Passive Perception, p. 81)

The GM decides when hiding is possible. An invisible creature can always try to hide.

> The GM decides when circumstances are appropriate for hiding.

(SRD 5.1, Using Ability Scores — Hiding, p. 80)

> An invisible creature can always try to hide. Signs of its passage might still be noticed, and it does have to stay quiet.

(SRD 5.1, Using Ability Scores — Hiding, p. 80)

Whether you can find a hidden creature or object depends on how obscured the area is (7.5).

> One of the main factors in determining whether you can find a hidden creature or object is how well you can see in an area, which might be lightly or heavily obscured, as explained in "The Environment."

(SRD 5.1, Using Ability Scores — What Can You See?, p. 81)

### 2.10 Using each ability (checks without a skill, attacks, AC, initiative)

Each ability has "other checks" that use no skill. The SRD's examples:

> A Strength check can model any attempt to lift, push, pull, or break something, to force your body through a space, or to otherwise apply brute force to a situation.

(SRD 5.1, Using Each Ability — Strength Checks, p. 79)

- **Other Strength checks**: "Force open a stuck, locked, or barred door", "Break free of bonds", "Push through a tunnel that is too small", "Hang on to a wagon while being dragged behind it", "Tip over a statue", "Keep a boulder from rolling" (p. 79).
- **Other Dexterity checks**: "Control a heavily laden cart on a steep descent", "Steer a chariot around a tight turn", "Pick a lock", "Disable a trap", "Securely tie up a prisoner", "Wriggle free of bonds", "Play a stringed instrument", "Craft a small or detailed object" (p. 80).
- **Constitution checks** (no skill applies): "Hold your breath", "March or labor for hours without rest", "Go without sleep", "Survive without food or water", "Quaff an entire stein of ale in one go" (p. 81).
- **Other Intelligence checks**: "Communicate with a creature without using words", "Estimate the value of a precious item", "Pull together a disguise to pass as a city guard", "Forge a document", "Recall lore about a craft or trade", "Win a game of skill" (p. 81).
- **Other Wisdom checks**: "Get a gut feeling about what course of action to follow", "Discern whether a seemingly dead or living creature is undead" (p. 82).
- **Other Charisma checks**: "Find the best person to talk to for news, rumors, and gossip", "Blend into a crowd to get the sense of key topics of conversation" (p. 83).

> Constitution checks are uncommon, and no skills apply to Constitution checks, because the endurance this ability represents is largely passive rather than involving a specific effort on the part of a character or monster.

(SRD 5.1, Using Each Ability — Constitution Checks, p. 81)

Animal Handling also covers controlling a mount during a risky manoeuvre.

> You also make a Wisdom (Animal Handling) check to control your mount when you attempt a risky maneuver.

(SRD 5.1, Using Each Ability — Wisdom Checks, p. 82)

Strength adds to melee weapon attack and damage rolls; Dexterity adds to ranged and finesse weapon attack and damage rolls.

> You add your Strength modifier to your attack roll and your damage roll when attacking with a melee weapon such as a mace, a battleaxe, or a javelin. You use melee weapons to make melee attacks in hand-to-hand combat, and some of them can be thrown to make a ranged attack.

(SRD 5.1, Using Each Ability — Strength: Attack Rolls and Damage, p. 79)

> You add your Dexterity modifier to your attack roll and your damage roll when attacking with a ranged weapon, such as a sling or a longbow. You can also add your Dexterity modifier to your attack roll and your damage roll when attacking with a melee weapon that has the finesse property, such as a dagger or a rapier.

(SRD 5.1, Using Each Ability — Dexterity: Attack Rolls and Damage, p. 80)

Dexterity adds to AC as the armor allows (12.2), and initiative is a Dexterity check (4.3).

> Depending on the armor you wear, you might add some or all of your Dexterity modifier to your Armor Class.

(SRD 5.1, Using Each Ability — Dexterity: Armor Class, p. 80)

> At the beginning of every combat, you roll initiative by making a Dexterity check. Initiative determines the order of creatures' turns in combat.

(SRD 5.1, Using Each Ability — Dexterity: Initiative, p. 80)

---

## 3. Saving throws

Roll d20 + ability modifier, plus the proficiency bonus if proficient. The effect sets the DC.

> To make a saving throw, roll a d20 and add the appropriate ability modifier. For example, you use your Dexterity modifier for a Dexterity saving throw. A saving throw can be modified by a situational bonus or penalty and can be affected by advantage and disadvantage, as determined by the GM.

(SRD 5.1, Using Ability Scores — Saving Throws, p. 83)

> Each class gives proficiency in at least two saving throws. … proficiency in a saving throw lets a character add his or her proficiency bonus to saving throws made using a particular ability score.

(SRD 5.1, Using Ability Scores — Saving Throws, p. 83)

> The Difficulty Class for a saving throw is determined by the effect that causes it. … Usually, a successful save means that a creature suffers no harm, or reduced harm, from an effect.

(SRD 5.1, Using Ability Scores — Saving Throws, p. 83)

A monster's save bonus is its ability modifier plus the proficiency bonus for its CR (table in 13.3).

> A saving throw bonus is the sum of a monster's relevant ability modifier and its proficiency bonus, which is determined by the monster's challenge rating

(SRD 5.1, Monsters — Saving Throws, p. 256)

---

## 4. Combat

### 4.1 Combat step by step

> 1. Determine surprise. … 2. Establish positions. … 3. Roll initiative. Everyone involved in the combat encounter rolls initiative, determining the order of combatants' turns. 4. Take turns. Each participant in the battle takes a turn in initiative order. 5. Begin the next round. When everyone involved in the combat has had a turn, the round ends. Repeat step 4 until the fighting stops.

(SRD 5.1, The Order of Combat — Combat Step by Step, p. 90)

A round is about 6 seconds.

> A round represents about 6 seconds in the game world.

(SRD 5.1, The Order of Combat, p. 90)

### 4.2 Surprise

Stealth checks are compared with passive Perception. A creature that doesn't notice the threat is surprised: on its first turn it can't move or act, and it can't react until that turn ends.

> If neither side tries to be stealthy, they automatically notice each other. Otherwise, the GM compares the Dexterity (Stealth) checks of anyone hiding with the passive Wisdom (Perception) score of each creature on the opposing side. Any character or monster that doesn't notice a threat is surprised at the start of the encounter.

(SRD 5.1, The Order of Combat — Surprise, p. 90)

> If you're surprised, you can't move or take an action on your first turn of the combat, and you can't take a reaction until that turn ends. A member of a group can be surprised even if the other members aren't.

(SRD 5.1, The Order of Combat — Surprise, p. 90)

### 4.3 Initiative

Initiative is a Dexterity check. One roll covers each group of identical creatures. The order stays the same every round.

> When combat starts, every participant makes a Dexterity check to determine their place in the initiative order. The GM makes one roll for an entire group of identical creatures, so each member of the group acts at the same time.

(SRD 5.1, The Order of Combat — Initiative, p. 90)

> The initiative order remains the same from round to round.

(SRD 5.1, The Order of Combat — Initiative, p. 90)

Ties: the GM orders tied monsters, players order tied characters, and the GM decides a monster-versus-PC tie. Optionally, tied creatures roll a d20 and the highest goes first.

> If a tie occurs, the GM decides the order among tied GM-controlled creatures, and the players decide the order among their tied characters. The GM can decide the order if the tie is between a monster and a player character. Optionally, the GM can have the tied characters and monsters each roll a d20 to determine the order, highest roll going first.

(SRD 5.1, The Order of Combat — Initiative, p. 90)

### 4.4 Your turn: movement and action

On your turn you can move up to your speed and take one action, in either order.

> On your turn, you can move a distance up to your speed and take one action. You decide whether to move first or take your action first.

(SRD 5.1, The Order of Combat — Your Turn, p. 90)

> Your speed—sometimes called your walking speed—is noted on your character sheet.

(SRD 5.1, The Order of Combat — Your Turn, p. 90)

> You can forgo moving, taking an action, or doing anything at all on your turn.

(SRD 5.1, The Order of Combat — Your Turn, p. 90)

You can split your movement around your action and between the attacks of one action.

> You can break up your movement on your turn, using some of your speed before and after your action.

(SRD 5.1, Movement and Position — Breaking Up Your Move, p. 91)

> If you take an action that includes more than one weapon attack, you can break up your movement even further by moving between those attacks.

(SRD 5.1, Movement and Position — Moving between Attacks, p. 91)

Interacting with one object per turn is free. A second object takes your action.

> You can also interact with one object or feature of the environment for free, during either your move or your action. … If you want to interact with a second object, you need to use your action.

(SRD 5.1, The Order of Combat — Other Activity on Your Turn, p. 91)

Talking is free. Some objects always need an action, and the GM can require an action for a free interaction that needs care.

> You can communicate however you are able, through brief utterances and gestures, as you take your turn.

(SRD 5.1, The Order of Combat — Other Activity on Your Turn, p. 91)

> Some magic items and other special objects always require an action to use, as stated in their descriptions. The GM might require you to use an action for any of these activities when it needs special care or when it presents an unusual obstacle.

(SRD 5.1, The Order of Combat — Other Activity on Your Turn, p. 91)

Examples of free object interactions:

> draw or sheathe a sword; open or close a door; withdraw a potion from your backpack; pick up a dropped axe; take a bauble from a table; remove a ring from your finger; stuff some food into your mouth; plant a banner in the ground; fish a few coins from your belt pouch; drink all the ale in a flagon; throw a lever or a switch; pull a torch from a sconce; take a book from a shelf you can reach; extinguish a small flame; don a mask; pull the hood of your cloak up and over your head; put your ear to a door; kick a small stone; turn a key in a lock; tap the floor with a 10-foot pole; hand an item to another character

(SRD 5.1, Movement and Position — Interacting with Objects Around You, p. 92)

Movement can mix walking, jumping, climbing and swimming; each part is deducted from your speed.

> Your movement can include jumping, climbing, and swimming. These different modes of movement can be combined with walking, or they can constitute your entire move. However you're moving, you deduct the distance of each part of your move from your speed until it is used up or until you are done moving.

(SRD 5.1, Movement and Position, p. 91)

With more than one speed, subtract the distance already moved from the new speed when you switch.

> If you have more than one speed, such as your walking speed and a flying speed, you can switch back and forth between your speeds during your move. Whenever you switch, subtract the distance you've already moved from the new speed. The result determines how much farther you can move. If the result is 0 or less, you can't use the new speed during the current move.

(SRD 5.1, Movement and Position — Using Different Speeds, p. 91)

Difficult terrain costs 1 extra foot per foot of movement. Another creature's space is difficult terrain.

> Every foot of movement in difficult terrain costs 1 extra foot. This rule is true even if multiple things in a space count as difficult terrain.

(SRD 5.1, Movement and Position — Difficult Terrain, p. 91)

> Low furniture, rubble, undergrowth, steep stairs, snow, and shallow bogs are examples of difficult terrain. The space of another creature, whether hostile or not, also counts as difficult terrain.

(SRD 5.1, Movement and Position — Difficult Terrain, p. 91)

Dropping prone is free. Standing up costs half your speed. Crawling costs 1 extra foot per foot.

> You can drop prone without using any of your speed. Standing up takes more effort; doing so costs an amount of movement equal to half your speed.

(SRD 5.1, Movement and Position — Being Prone, p. 91)

> You can't stand up if you don't have enough movement left or if your speed is 0. To move while prone, you must crawl or use magic such as teleportation. Every foot of movement while crawling costs 1 extra foot.

(SRD 5.1, Movement and Position — Being Prone, p. 92)

> Crawling 1 foot in difficult terrain, therefore, costs 3 feet of movement.

(SRD 5.1, Movement and Position — Being Prone, p. 92)

Moving through creatures: a nonhostile creature's space is always allowed. A hostile creature's space is allowed only if it is two or more sizes larger or smaller. You can't end your move in another creature's space.

> You can move through a nonhostile creature's space. In contrast, you can move through a hostile creature's space only if the creature is at least two sizes larger or smaller than you. … Whether a creature is a friend or an enemy, you can't willingly end your move in its space.

(SRD 5.1, Movement and Position — Moving Around Other Creatures, p. 92)

> Remember that another creature's space is difficult terrain for you. … If you leave a hostile creature's reach during your move, you provoke an opportunity attack.

(SRD 5.1, Movement and Position — Moving Around Other Creatures, p. 92)

A flying creature falls if it is knocked prone, its speed drops to 0, or it otherwise can't move, unless it can hover or magic holds it up.

> If a flying creature is knocked prone, has its speed reduced to 0, or is otherwise deprived of the ability to move, the creature falls, unless it has the ability to hover or it is being held aloft by magic, such as by the fly spell.

(SRD 5.1, Movement and Position — Flying Movement, p. 92)

**Size Categories** (SRD 5.1, Creature Size, p. 92)

| Size | Space |
| --- | --- |
| Tiny | 2½ by 2½ ft. |
| Small | 5 by 5 ft. |
| Medium | 5 by 5 ft. |
| Large | 10 by 10 ft. |
| Huge | 15 by 15 ft. |
| Gargantuan | 20 by 20 ft. or larger |

Space is the area a creature controls, not its body size. Eight Medium creatures fit around a Medium one.

> A creature's space is the area in feet that it effectively controls in combat, not an expression of its physical dimensions.

(SRD 5.1, Creature Size — Space, p. 92)

> Assuming Medium combatants, eight creatures can fit in a 5-foot radius around another one. Because larger creatures take up more space, fewer of them can surround a creature. If five Large creatures crowd around a Medium or smaller one, there's little room for anyone else. In contrast, as many as twenty Medium creatures can surround a Gargantuan one.

(SRD 5.1, Creature Size — Space, p. 92)

A creature can squeeze through a space big enough for a creature one size smaller.

> A creature can squeeze through a space that is large enough for a creature one size smaller than it. Thus, a Large creature can squeeze through a passage that's only 5 feet wide.

(SRD 5.1, Creature Size — Squeezing into a Smaller Space, p. 92)

Squeezing gives disadvantage on your attack rolls and Dexterity saves, and attackers have advantage against you.

> While squeezing through a space, a creature must spend 1 extra foot for every foot it moves there, and it has disadvantage on attack rolls and Dexterity saving throws. Attack rolls against the creature have advantage while it's in the smaller space.

(SRD 5.1, Creature Size — Squeezing into a Smaller Space, p. 92)

### 4.5 Bonus actions

You have a bonus action only when a feature grants one. You get at most one per turn. Anything that stops you taking actions also stops bonus actions.

> You can take a bonus action only when a special ability, spell, or other feature of the game states that you can do something as a bonus action. You otherwise don't have a bonus action to take. You can take only one bonus action on your turn, so you must choose which bonus action to use when you have more than one available.

(SRD 5.1, The Order of Combat — Bonus Actions, p. 90)

> You choose when to take a bonus action during your turn, unless the bonus action's timing is specified, and anything that deprives you of your ability to take actions also prevents you from taking a bonus action.

(SRD 5.1, The Order of Combat — Bonus Actions, pp. 90–91)

### 4.6 Reactions

You get one reaction, and it comes back at the start of your next turn. A reaction can happen on another creature's turn.

> A reaction is an instant response to a trigger of some kind, which can occur on your turn or on someone else's. The opportunity attack is the most common type of reaction. When you take a reaction, you can't take another one until the start of your next turn. If the reaction interrupts another creature's turn, that creature can continue its turn right after the reaction.

(SRD 5.1, The Order of Combat — Reactions, p. 91)

### 4.7 Actions in combat

You can take a listed action, a class action, or an improvised action.

> When you take your action on your turn, you can take one of the actions presented here, an action you gained from your class or a special feature, or an action that you improvise.

(SRD 5.1, Actions in Combat, p. 93)

**Improvised actions.** The GM rules whether an undescribed action is possible and what roll it needs.

> When you describe an action not detailed elsewhere in the rules, the GM tells you whether that action is possible and what kind of roll you need to make, if any, to determine success or failure.

(SRD 5.1, Actions in Combat, p. 93)

**Attack.** Makes one melee or ranged attack. Extra Attack adds more attacks.

> With this action, you make one melee or ranged attack. … Certain features, such as the Extra Attack feature of the fighter, allow you to make more than one attack with this action.

(SRD 5.1, Actions in Combat — Attack, p. 93)

**Cast a Spell.** Not used in v1 (no spellcasting).

> Each spell has a casting time, which specifies whether the caster must use an action, a reaction, minutes, or even hours to cast the spell.

(SRD 5.1, Actions in Combat — Cast a Spell, p. 93)

**Dash.** Adds movement equal to your speed after modifiers.

> When you take the Dash action, you gain extra movement for the current turn. The increase equals your speed, after applying any modifiers.

(SRD 5.1, Actions in Combat — Dash, p. 93)

> Any increase or decrease to your speed changes this additional movement by the same amount. If your speed of 30 feet is reduced to 15 feet, for instance, you can move up to 30 feet this turn if you dash.

(SRD 5.1, Actions in Combat — Dash, p. 93)

**Disengage.** Your movement doesn't provoke opportunity attacks for the rest of the turn.

> If you take the Disengage action, your movement doesn't provoke opportunity attacks for the rest of the turn.

(SRD 5.1, Actions in Combat — Disengage, p. 93)

**Dodge.** Until your next turn, attacks against you have disadvantage if you can see the attacker, and you have advantage on Dexterity saves. The benefit ends if you are incapacitated or your speed drops to 0.

> Until the start of your next turn, any attack roll made against you has disadvantage if you can see the attacker, and you make Dexterity saving throws with advantage. You lose this benefit if you are incapacitated (as explained in appendix PH-A) or if your speed drops to 0.

(SRD 5.1, Actions in Combat — Dodge, p. 93)

**Help.** The ally gets advantage on its next check for the task. Or, against a creature within 5 ft. of you, the ally's first attack before your next turn has advantage.

> When you take the Help action, the creature you aid gains advantage on the next ability check it makes to perform the task you are helping with, provided that it makes the check before the start of your next turn. Alternatively, you can aid a friendly creature in attacking a creature within 5 feet of you. … If your ally attacks the target before your next turn, the first attack roll is made with advantage.

(SRD 5.1, Actions in Combat — Help, p. 93)

**Hide.** Make a Dexterity (Stealth) check (2.9).

> When you take the Hide action, you make a Dexterity (Stealth) check in an attempt to hide, following the rules for hiding. If you succeed, you gain certain benefits, as described in the "Unseen Attackers and Targets" section.

(SRD 5.1, Actions in Combat — Hide, p. 93)

**Ready.** Choose a trigger and a response (an action, or moving up to your speed). The response uses your reaction.

> First, you decide what perceivable circumstance will trigger your reaction. Then, you choose the action you will take in response to that trigger, or you choose to move up to your speed in response to it. … When the trigger occurs, you can either take your reaction right after the trigger finishes or ignore the trigger.

(SRD 5.1, Actions in Combat — Ready, p. 93)

> Remember that you can take only one reaction per round.

(SRD 5.1, Actions in Combat — Ready, p. 93)

**Search.** A Wisdom (Perception) or Intelligence (Investigation) check.

> When you take the Search action, you devote your attention to finding something. Depending on the nature of your search, the GM might have you make a Wisdom (Perception) check or an Intelligence (Investigation) check.

(SRD 5.1, Actions in Combat — Search, p. 94)

**Use an Object.** For objects that take an action, or a second object in one turn.

> When an object requires your action for its use, you take the Use an Object action. This action is also useful when you want to interact with more than one object on your turn.

(SRD 5.1, Actions in Combat — Use an Object, p. 94)

### 4.8 Making an attack

An attack is any roll made as an attack roll.

> If there's ever any question whether something you're doing counts as an attack, the rule is simple: if you're making an attack roll, you're making an attack.

(SRD 5.1, Making an Attack, p. 94)

An attack has three steps: choose a target, determine modifiers (cover, advantage, disadvantage), resolve.

> 1. Choose a target. Pick a target within your attack's range: a creature, an object, or a location. 2. Determine modifiers. The GM determines whether the target has cover and whether you have advantage or disadvantage against the target. In addition, spells, special abilities, and other effects can apply penalties or bonuses to your attack roll. 3. Resolve the attack. You make the attack roll. On a hit, you roll damage, unless the particular attack has rules that specify otherwise. Some attacks cause special effects in addition to or instead of damage.

(SRD 5.1, Making an Attack, p. 94)

The attack hits if d20 + modifiers is equal to or greater than AC.

> To make an attack roll, roll a d20 and add the appropriate modifiers. If the total of the roll plus modifiers equals or exceeds the target's Armor Class (AC), the attack hits.

(SRD 5.1, Making an Attack — Attack Rolls, p. 94)

Modifiers: Strength for melee and Dexterity for ranged (finesse and thrown change this), plus proficiency with the weapon. Monsters use their stat-block bonus.

> When a monster makes an attack roll, it uses whatever modifier is provided in its stat block. Ability Modifier. The ability modifier used for a melee weapon attack is Strength, and the ability modifier used for a ranged weapon attack is Dexterity. Weapons that have the finesse or thrown property break this rule. … Proficiency Bonus. You add your proficiency bonus to your attack roll when you attack using a weapon with which you have proficiency

(SRD 5.1, Making an Attack — Modifiers to the Roll, p. 94)

### 4.9 Rolling 1 or 20 on an attack

A natural 20 always hits and is a critical hit. A natural 1 always misses.

> If the d20 roll for an attack is a 20, the attack hits regardless of any modifiers or the target's AC. This is called a critical hit. If the d20 roll for an attack is a 1, the attack misses regardless of any modifiers or the target's AC.

(SRD 5.1, Making an Attack — Rolling 1 or 20, p. 94)

### 4.10 Unseen attackers and targets

Attacking a target you can't see gives disadvantage. Attacking a creature that can't see you gives advantage. Attacking while hidden reveals you.

> When you attack a target that you can't see, you have disadvantage on the attack roll. … If the target isn't in the location you targeted, you automatically miss

(SRD 5.1, Making an Attack — Unseen Attackers and Targets, p. 94)

> When a creature can't see you, you have advantage on attack rolls against it. If you are hidden—both unseen and unheard—when you make an attack, you give away your location when the attack hits or misses.

(SRD 5.1, Making an Attack — Unseen Attackers and Targets, p. 94)

### 4.11 Ranged attacks

Beyond normal range: disadvantage. Beyond long range: you can't attack. An attack with a single range can't go beyond it.

> You can make ranged attacks only against targets within a specified range. If a ranged attack, such as one made with a spell, has a single range, you can't attack a target beyond this range.

(SRD 5.1, Ranged Attacks — Range, p. 95)

> Your attack roll has disadvantage when your target is beyond normal range, and you can't attack a target beyond the long range.

(SRD 5.1, Ranged Attacks — Range, p. 95)

A ranged attack has disadvantage while you are within 5 ft. of a hostile creature that can see you and isn't incapacitated.

> When you make a ranged attack with a weapon, a spell, or some other means, you have disadvantage on the attack roll if you are within 5 feet of a hostile creature who can see you and who isn't incapacitated.

(SRD 5.1, Ranged Attacks — Ranged Attacks in Close Combat, p. 95)

### 4.12 Melee attacks and unarmed strikes

Normal reach is 5 ft. Some creatures have more.

> Most creatures have a 5-foot reach and can thus attack targets within 5 feet of them when making a melee attack. Certain creatures (typically those larger than Medium) have melee attacks with a greater reach than 5 feet

(SRD 5.1, Melee Attacks, p. 95)

An unarmed strike deals 1 + Str modifier bludgeoning damage. Everyone is proficient with it, and it is not a weapon.

> Instead of using a weapon to make a melee weapon attack, you can use an unarmed strike: a punch, kick, head-butt, or similar forceful blow (none of which count as weapons). On a hit, an unarmed strike deals bludgeoning damage equal to 1 + your Strength modifier. You are proficient with your unarmed strikes.

(SRD 5.1, Melee Attacks, p. 95)

### 4.13 Opportunity attacks

A hostile creature you can see that leaves your reach provokes one melee attack, which uses your reaction. Disengage, teleporting and forced movement don't provoke.

> You can make an opportunity attack when a hostile creature that you can see moves out of your reach. To make the opportunity attack, you use your reaction to make one melee attack against the provoking creature. The attack occurs right before the creature leaves your reach.

(SRD 5.1, Melee Attacks — Opportunity Attacks, p. 95)

> You can avoid provoking an opportunity attack by taking the Disengage action. You also don't provoke an opportunity attack when you teleport or when someone or something moves you without using your movement, action, or reaction.

(SRD 5.1, Melee Attacks — Opportunity Attacks, p. 95)

### 4.14 Two-weapon fighting

After you take the Attack action with a light melee weapon held in one hand, you can use a bonus action to attack with a different light melee weapon in the other hand. That attack adds no positive ability modifier to damage.

> When you take the Attack action and attack with a light melee weapon that you're holding in one hand, you can use a bonus action to attack with a different light melee weapon that you're holding in the other hand. You don't add your ability modifier to the damage of the bonus attack, unless that modifier is negative. If either weapon has the thrown property, you can throw the weapon, instead of making a melee attack with it.

(SRD 5.1, Melee Attacks — Two-Weapon Fighting, p. 95)

### 4.15 Grappling

A grapple replaces one attack of the Attack action. The target must be no more than one size larger and within reach, and you need a free hand. Roll your Strength (Athletics) against the target's Strength (Athletics) or Dexterity (Acrobatics); the target chooses. If you win, the target is grappled.

> When you want to grab a creature or wrestle with it, you can use the Attack action to make a special melee attack, a grapple. If you're able to make multiple attacks with the Attack action, this attack replaces one of them.

(SRD 5.1, Melee Attacks — Grappling, p. 95)

> The target of your grapple must be no more than one size larger than you and must be within your reach. Using at least one free hand, you try to seize the target by making a grapple check instead of an attack roll: a Strength (Athletics) check contested by the target's Strength (Athletics) or Dexterity (Acrobatics) check (the target chooses the ability to use). If you succeed, you subject the target to the grappled condition … you can release the target whenever you like (no action required).

(SRD 5.1, Melee Attacks — Grappling, p. 95)

Escaping takes the grappled creature's action. It rolls Athletics or Acrobatics against the grappler's Athletics.

> A grappled creature can use its action to escape. To do so, it must succeed on a Strength (Athletics) or Dexterity (Acrobatics) check contested by your Strength (Athletics) check.

(SRD 5.1, Melee Attacks — Grappling: Escaping a Grapple, p. 95)

Dragging or carrying a grappled creature halves your speed, unless it is two or more sizes smaller than you.

> When you move, you can drag or carry the grappled creature with you, but your speed is halved, unless the creature is two or more sizes smaller than you.

(SRD 5.1, Melee Attacks — Grappling: Moving a Grappled Creature, p. 96)

Monster grapple attacks need no contest. To escape one, beat the stat block's escape DC, or 10 + the monster's Athletics modifier if no DC is given.

> When a monster hits with such an attack, it doesn't need to make an additional ability check to determine whether the grapple succeeds, unless the attack says otherwise.

(SRD 5.1, Monsters — Grapple Rules for Monsters, p. 259)

> If no escape DC is given, assume the DC is 10 + the monster's Strength (Athletics) modifier.

(SRD 5.1, Monsters — Grapple Rules for Monsters, p. 259)

Optional feat: Grappler is the only feat in SRD 5.1. Feats replace an Ability Score Improvement under an optional rule.

> Using the optional feats rule, you can forgo taking that feature to take a feat of your choice instead.

(SRD 5.1, Feats, p. 75)

> Grappler. Prerequisite: Strength 13 or higher. … You have advantage on attack rolls against a creature you are grappling. You can use your action to try to pin a creature grappled by you. To do so, make another grapple check. If you succeed, you and the creature are both restrained until the grapple ends.

(SRD 5.1, Feats — Grappler, p. 75)

### 4.16 Shoving

A shove replaces one attack. Use the same size, reach and contest rules as a grapple. If you win, the target is knocked prone or pushed 5 ft. away.

> Using the Attack action, you can make a special melee attack to shove a creature, either to knock it prone or push it away from you. If you're able to make multiple attacks with the Attack action, this attack replaces one of them. The target must be no more than one size larger than you and must be within your reach. Instead of making an attack roll, you make a Strength (Athletics) check contested by the target's Strength (Athletics) or Dexterity (Acrobatics) check (the target chooses the ability to use). If you win the contest, you either knock the target prone or push it 5 feet away from you.

(SRD 5.1, Contests in Combat — Shoving a Creature, p. 96)

### 4.17 Cover

Half cover gives +2 AC and Dex saves. Three-quarters cover gives +5. Total cover can't be targeted directly. Only the best cover counts. Cover counts only against an attack or effect from the far side.

> A target can benefit from cover only when an attack or other effect originates on the opposite side of the cover. There are three degrees of cover.

(SRD 5.1, Cover, p. 96)

> A target has half cover if an obstacle blocks at least half of its body. … A target has three-quarters cover if about three-quarters of it is covered by an obstacle. The obstacle might be a portcullis, an arrow slit, or a thick tree trunk. … A target has total cover if it is completely concealed by an obstacle.

(SRD 5.1, Cover, p. 96)

> If a target is behind multiple sources of cover, only the most protective degree of cover applies; the degrees aren't added together.

(SRD 5.1, Cover, p. 96)

> A target with half cover has a +2 bonus to AC and Dexterity saving throws. … The obstacle might be a low wall, a large piece of furniture, a narrow tree trunk, or a creature, whether that creature is an enemy or a friend. A target with three-quarters cover has a +5 bonus to AC and Dexterity saving throws.

(SRD 5.1, Cover, p. 96)

> A target with total cover can't be targeted directly by an attack or a spell, although some spells can reach such a target by including it in an area of effect.

(SRD 5.1, Cover, p. 96)

### 4.18 Hit points

> A creature's current hit points (usually just called hit points) can be any number from the creature's hit point maximum down to 0. … The loss of hit points has no effect on a creature's capabilities until the creature drops to 0 hit points.

(SRD 5.1, Damage and Healing — Hit Points, p. 96)

### 4.19 Damage rolls

Damage = dice + modifiers. A weapon adds the same ability modifier used to hit. Damage can't go below 0. Area damage is rolled once for all targets.

> With a penalty, it is possible to deal 0 damage, but never negative damage. When attacking with a weapon, you add your ability modifier—the same modifier used for the attack roll—to the damage.

(SRD 5.1, Damage and Healing — Damage Rolls, p. 96)

> If a spell or other effect deals damage to more than one target at the same time, roll the damage once for all of them.

(SRD 5.1, Damage and Healing — Damage Rolls, p. 96)

### 4.20 Critical hits

Roll every damage die of the attack twice (including Sneak Attack dice), then add modifiers once.

> Roll all of the attack's damage dice twice and add them together. Then add any relevant modifiers as normal.

(SRD 5.1, Damage and Healing — Critical Hits, pp. 96–97)

> If the attack involves other damage dice, such as from the rogue's Sneak Attack feature, you roll those dice twice as well.

(SRD 5.1, Damage and Healing — Critical Hits, p. 97)

### 4.21 Damage types

There are 13 types: acid, bludgeoning, cold, fire, force, lightning, necrotic, piercing, poison, psychic, radiant, slashing, thunder. A type has no rules of its own.

> Damage types have no rules of their own, but other rules, such as damage resistance, rely on the types.

(SRD 5.1, Damage and Healing — Damage Types, p. 97)

### 4.22 Resistance, vulnerability and immunity

Resistance halves the damage and vulnerability doubles it. Both apply after all other modifiers, and repeated instances count once.

> If a creature or an object has resistance to a damage type, damage of that type is halved against it. If a creature or an object has vulnerability to a damage type, damage of that type is doubled against it. Resistance and then vulnerability are applied after all other modifiers to damage.

(SRD 5.1, Damage and Healing — Damage Resistance and Vulnerability, p. 97)

> The 25 damage is first reduced by 5 and then halved, so the creature takes 10 damage. Multiple instances of resistance or vulnerability that affect the same damage type count as only one instance.

(SRD 5.1, Damage and Healing — Damage Resistance and Vulnerability, p. 97)

The SRD's worked example (25 − 5 = 20, halved = 10) rounds nothing, so it does not say which way to round. SRD 5.1 has no general rounding rule; see [Not in SRD 5.1](#not-in-srd-51).

Immunity is defined in the monster stat-block section, not with a rule of its own.

> Some creatures have vulnerability, resistance, or immunity to certain types of damage. Particular creatures are even resistant or immune to damage from nonmagical attacks (a magical attack is an attack delivered by a spell, a magic item, or another magical source). In addition, some creatures are immune to certain conditions.

(SRD 5.1, Monsters — Vulnerabilities, Resistances, and Immunities, p. 257)

### 4.23 Healing

Hit points regained are capped at the maximum. The dead can't regain hit points.

> When a creature receives healing of any kind, hit points regained are added to its current hit points. A creature's hit points can't exceed its hit point maximum, so any hit points regained in excess of this number are lost.

(SRD 5.1, Damage and Healing — Healing, p. 97)

> A creature that has died can't regain hit points until magic such as the revivify spell has restored it to life.

(SRD 5.1, Damage and Healing — Healing, p. 97)

### 4.24 Temporary hit points

Temporary HP are lost first. They don't stack (keep one pool, your choice), can't be healed, can go above the maximum, and don't wake you at 0 HP. They last until used up or a long rest, unless a duration is given.

> When you have temporary hit points and take damage, the temporary hit points are lost first, and any leftover damage carries over to your normal hit points.

(SRD 5.1, Damage and Healing — Temporary Hit Points, p. 98)

> Healing can't restore temporary hit points, and they can't be added together. If you have temporary hit points and receive more of them, you decide whether to keep the ones you have or to gain the new ones.

(SRD 5.1, Damage and Healing — Temporary Hit Points, p. 98)

> Because temporary hit points are separate from your actual hit points, they can exceed your hit point maximum. A character can, therefore, be at full hit points and receive temporary hit points.

(SRD 5.1, Damage and Healing — Temporary Hit Points, p. 98)

> If you have 0 hit points, receiving temporary hit points doesn't restore you to consciousness or stabilize you. They can still absorb damage directed at you while you're in that state, but only true healing can save you.

(SRD 5.1, Damage and Healing — Temporary Hit Points, pp. 98–99)

> Unless a feature that grants you temporary hit points has a duration, they last until they're depleted or you finish a long rest.

(SRD 5.1, Damage and Healing — Temporary Hit Points, p. 99)

### 4.25 Dropping to 0 HP, instant death, falling unconscious

At 0 HP you either die outright or fall unconscious.

> When you drop to 0 hit points, you either die outright or fall unconscious

(SRD 5.1, Damage and Healing — Dropping to 0 Hit Points, p. 97)

Instant death: if the damage left over after reaching 0 is equal to or greater than your HP maximum, you die.

> When damage reduces you to 0 hit points and there is damage remaining, you die if the remaining damage equals or exceeds your hit point maximum.

(SRD 5.1, Damage and Healing — Instant Death, p. 98)

Otherwise you fall unconscious, and you wake when you regain any HP.

> If damage reduces you to 0 hit points and fails to kill you, you fall unconscious (see appendix PH-A). This unconsciousness ends if you regain any hit points.

(SRD 5.1, Damage and Healing — Falling Unconscious, p. 98)

### 4.26 Death saving throws

Roll at the start of each of your turns at 0 HP. 10 or more is a success. Three successes make you stable; three failures kill you. A natural 1 counts as two failures. A natural 20 restores 1 HP. The counts reset when you regain HP or become stable.

> Whenever you start your turn with 0 hit points, you must make a special saving throw, called a death saving throw … Unlike other saving throws, this one isn't tied to any ability score.

(SRD 5.1, Damage and Healing — Death Saving Throws, p. 98)

> Roll a d20. If the roll is 10 or higher, you succeed. Otherwise, you fail. A success or failure has no effect by itself. On your third success, you become stable (see below). On your third failure, you die. The successes and failures don't need to be consecutive; keep track of both until you collect three of a kind. The number of both is reset to zero when you regain any hit points or become stable.

(SRD 5.1, Damage and Healing — Death Saving Throws, p. 98)

> Rolling 1 or 20. When you make a death saving throw and roll a 1 on the d20, it counts as two failures. If you roll a 20 on the d20, you regain 1 hit point.

(SRD 5.1, Damage and Healing — Death Saving Throws, p. 98)

Damage taken at 0 HP: one failure, or two from a critical hit. Damage equal to or greater than your HP maximum kills you.

> If you take any damage while you have 0 hit points, you suffer a death saving throw failure. If the damage is from a critical hit, you suffer two failures instead. If the damage equals or exceeds your hit point maximum, you suffer instant death.

(SRD 5.1, Damage and Healing — Death Saving Throws: Damage at 0 Hit Points, p. 98)

### 4.27 Stabilizing

First aid takes an action and a DC 10 Wisdom (Medicine) check; a healer's kit needs no check. A stable creature stays unconscious at 0 HP, starts dying again if it takes damage, and regains 1 HP after 1d4 hours.

> You can use your action to administer first aid to an unconscious creature and attempt to stabilize it, which requires a successful DC 10 Wisdom (Medicine) check.

(SRD 5.1, Damage and Healing — Stabilizing a Creature, p. 98)

> A stable creature doesn't make death saving throws, even though it has 0 hit points, but it does remain unconscious. The creature stops being stable, and must start making death saving throws again, if it takes any damage. A stable creature that isn't healed regains 1 hit point after 1d4 hours.

(SRD 5.1, Damage and Healing — Stabilizing a Creature, p. 98)

> Healer's Kit. … The kit has ten uses. As an action, you can expend one use of the kit to stabilize a creature that has 0 hit points, without needing to make a Wisdom (Medicine) check.

(SRD 5.1, Adventuring Gear, p. 67)

### 4.28 Monsters and death

Most monsters die at 0 HP. Important NPCs may make death saves instead.

> Most GMs have a monster die the instant it drops to 0 hit points, rather than having it fall unconscious and make death saving throws. Mighty villains and special nonplayer characters are common exceptions; the GM might have them fall unconscious and follow the same rules as player characters.

(SRD 5.1, Damage and Healing — Monsters and Death, p. 98)

### 4.29 Knocking a creature out

A melee attack that drops a creature to 0 HP can knock it out instead. The creature is then unconscious and stable.

> When an attacker reduces a creature to 0 hit points with a melee attack, the attacker can knock the creature out. The attacker can make this choice the instant the damage is dealt. The creature falls unconscious and is stable.

(SRD 5.1, Damage and Healing — Knocking a Creature Out, p. 98)

### 4.30 Mounted combat (brief)

A mount must be willing, at least one size larger than you, and the right shape. Mounting or dismounting costs half your speed. A controlled mount acts on your initiative and can only Dash, Disengage or Dodge.

> A willing creature that is at least one size larger than you and that has an appropriate anatomy can serve as a mount

(SRD 5.1, Mounted Combat, p. 99)

> The initiative of a controlled mount changes to match yours when you mount it. It moves as you direct it, and it has only three action options: Dash, Disengage, and Dodge.

(SRD 5.1, Mounted Combat — Controlling a Mount, p. 99)

> Once during your move, you can mount a creature that is within 5 feet of you or dismount. Doing so costs an amount of movement equal to half your speed. … you can't mount it if you don't have 15 feet of movement left or if your speed is 0.

(SRD 5.1, Mounted Combat — Mounting and Dismounting, p. 99)

Being moved against your mount's will, or being knocked prone, calls for a DC 10 Dex save or you fall off.

> If an effect moves your mount against its will while you're on it, you must succeed on a DC 10 Dexterity saving throw or fall off the mount, landing prone in a space within 5 feet of it. If you're knocked prone while mounted, you must make the same saving throw. If your mount is knocked prone, you can use your reaction to dismount it as it falls and land on your feet. Otherwise, you are dismounted and fall prone in a space within 5 feet it.

(SRD 5.1, Mounted Combat — Mounting and Dismounting, p. 99)

Only a trained mount can be controlled. An independent mount keeps its own initiative and acts as it wishes. An opportunity attack provoked by the mount can target either rider or mount.

> While you're mounted, you have two options. You can either control the mount or allow it to act independently. Intelligent creatures, such as dragons, act independently. You can control a mount only if it has been trained to accept a rider. Domesticated horses, donkeys, and similar creatures are assumed to have such training.

(SRD 5.1, Mounted Combat — Controlling a Mount, p. 99)

> A controlled mount can move and act even on the turn that you mount it. An independent mount retains its place in the initiative order. Bearing a rider puts no restrictions on the actions the mount can take, and it moves and acts as it wishes. … In either case, if the mount provokes an opportunity attack while you're on it, the attacker can target you or the mount.

(SRD 5.1, Mounted Combat — Controlling a Mount, p. 99)

### 4.31 Underwater combat (brief)

> When making a melee weapon attack, a creature that doesn't have a swimming speed (either natural or granted by magic) has disadvantage on the attack roll unless the weapon is a dagger, javelin, shortsword, spear, or trident. A ranged weapon attack automatically misses a target beyond the weapon's normal range. Even against a target within normal range, the attack roll has disadvantage unless the weapon is a crossbow, a net, or a weapon that is thrown like a javelin (including a spear, trident, or dart). Creatures and objects that are fully immersed in water have resistance to fire damage.

(SRD 5.1, Underwater Combat, p. 99)

---

## 5. Conditions (Appendix PH-A)

Instances of the same condition don't stack. Each keeps its own duration.

> A condition lasts either until it is countered (the prone condition is countered by standing up, for example) or for a duration specified by the effect that imposed the condition. If multiple effects impose the same condition on a creature, each instance of the condition has its own duration, but the condition's effects don't get worse. A creature either has a condition or doesn't.

(SRD 5.1, Appendix PH-A: Conditions, p. 358)

**Blinded** (p. 358)
> A blinded creature can't see and automatically fails any ability check that requires sight. Attack rolls against the creature have advantage, and the creature's attack rolls have disadvantage.

**Charmed** (p. 358)
> A charmed creature can't attack the charmer or target the charmer with harmful abilities or magical effects. The charmer has advantage on any ability check to interact socially with the creature.

**Deafened** (p. 358)
> A deafened creature can't hear and automatically fails any ability check that requires hearing.

**Exhaustion** (p. 358): six cumulative levels. Each long rest with food and drink removes one level.

> Exhaustion is measured in six levels. An effect can give a creature one or more levels of exhaustion, as specified in the effect's description.

| Level | Effect |
| --- | --- |
| 1 | Disadvantage on ability checks |
| 2 | Speed halved |
| 3 | Disadvantage on attack rolls and saving throws |
| 4 | Hit point maximum halved |
| 5 | Speed reduced to 0 |
| 6 | Death |

> If an already exhausted creature suffers another effect that causes exhaustion, its current level of exhaustion increases by the amount specified in the effect's description.

> A creature suffers the effect of its current level of exhaustion as well as all lower levels. … An effect that removes exhaustion reduces its level as specified in the effect's description, with all exhaustion effects ending if a creature's exhaustion level is reduced below 1. Finishing a long rest reduces a creature's exhaustion level by 1, provided that the creature has also ingested some food and drink.

(SRD 5.1, Appendix PH-A — Exhaustion, p. 358)

**Frightened** (p. 358)
> A frightened creature has disadvantage on ability checks and attack rolls while the source of its fear is within line of sight. The creature can't willingly move closer to the source of its fear.

**Grappled** (p. 358)
> A grappled creature's speed becomes 0, and it can't benefit from any bonus to its speed. The condition ends if the grappler is incapacitated (see the condition). The condition also ends if an effect removes the grappled creature from the reach of the grappler or grappling effect

**Incapacitated** (p. 358)
> An incapacitated creature can't take actions or reactions.

**Invisible** (p. 358)
> An invisible creature is impossible to see without the aid of magic or a special sense. For the purpose of hiding, the creature is heavily obscured. The creature's location can be detected by any noise it makes or any tracks it leaves. Attack rolls against the creature have disadvantage, and the creature's attack rolls have advantage.

**Paralyzed** (pp. 358–359)
> A paralyzed creature is incapacitated (see the condition) and can't move or speak. The creature automatically fails Strength and Dexterity saving throws. Attack rolls against the creature have advantage. Any attack that hits the creature is a critical hit if the attacker is within 5 feet of the creature.

**Petrified** (p. 359)
> A petrified creature is transformed, along with any nonmagical object it is wearing or carrying, into a solid inanimate substance (usually stone). … The creature is incapacitated (see the condition), can't move or speak, and is unaware of its surroundings. Attack rolls against the creature have advantage. The creature automatically fails Strength and Dexterity saving throws. The creature has resistance to all damage. The creature is immune to poison and disease, although a poison or disease already in its system is suspended, not neutralized.

**Poisoned** (p. 359)
> A poisoned creature has disadvantage on attack rolls and ability checks.

**Prone** (p. 359)
> A prone creature's only movement option is to crawl, unless it stands up and thereby ends the condition. The creature has disadvantage on attack rolls. An attack roll against the creature has advantage if the attacker is within 5 feet of the creature. Otherwise, the attack roll has disadvantage.

**Restrained** (p. 359)
> A restrained creature's speed becomes 0, and it can't benefit from any bonus to its speed. Attack rolls against the creature have advantage, and the creature's attack rolls have disadvantage. The creature has disadvantage on Dexterity saving throws.

**Stunned** (p. 359)
> A stunned creature is incapacitated (see the condition), can't move, and can speak only falteringly. The creature automatically fails Strength and Dexterity saving throws. Attack rolls against the creature have advantage.

**Unconscious** (p. 359)
> An unconscious creature is incapacitated (see the condition), can't move or speak, and is unaware of its surroundings. The creature drops whatever it's holding and falls prone. The creature automatically fails Strength and Dexterity saving throws. Attack rolls against the creature have advantage. Any attack that hits the creature is a critical hit if the attacker is within 5 feet of the creature.

(All: SRD 5.1, Appendix PH-A: Conditions, pp. 358–359. JSON `5e-SRD-Conditions.json` lists the same 15 conditions with matching text.)

---

## 6. Resting and Hit Dice

### 6.1 Short rest

A short rest lasts at least 1 hour. At its end you can spend Hit Dice one at a time: roll each die + Con modifier and regain that many HP. The pool is at most your level.

> A short rest is a period of downtime, at least 1 hour long, during which a character does nothing more strenuous than eating, drinking, reading, and tending to wounds.

(SRD 5.1, Resting — Short Rest, p. 87)

> A character can spend one or more Hit Dice at the end of a short rest, up to the character's maximum number of Hit Dice, which is equal to the character's level. For each Hit Die spent in this way, the player rolls the die and adds the character's Constitution modifier to it. The character regains hit points equal to the total. The player can decide to spend an additional Hit Die after each roll.

(SRD 5.1, Resting — Short Rest, p. 87)

### 6.2 Long rest

A long rest lasts at least 8 hours, with no more than 2 hours of light activity. An hour or more of strenuous activity restarts it. At its end you regain all HP and half your total Hit Dice (minimum 1). You get at most one per 24 hours, and you need at least 1 HP at the start.

> A long rest is a period of extended downtime, at least 8 hours long, during which a character sleeps or performs light activity: reading, talking, eating, or standing watch for no more than 2 hours. If the rest is interrupted by a period of strenuous activity—at least 1 hour of walking, fighting, casting spells, or similar adventuring activity—the characters must begin the rest again to gain any benefit from it.

(SRD 5.1, Resting — Long Rest, p. 87)

> At the end of a long rest, a character regains all lost hit points. The character also regains spent Hit Dice, up to a number of dice equal to half of the character's total number of them (minimum of one die). For example, if a character has eight Hit Dice, he or she can regain four spent Hit Dice upon finishing a long rest.

(SRD 5.1, Resting — Long Rest, p. 87)

> A character can't benefit from more than one long rest in a 24-hour period, and a character must have at least 1 hit point at the start of the rest to gain its benefits.

(SRD 5.1, Resting — Long Rest, p. 87)

A long rest also removes one exhaustion level, if the creature ate and drank (Section 5), and ends temporary HP (4.24).

### 6.3 Hit Dice per level

You gain one Hit Die each level. See 8.2.

---

## 7. Adventuring rules (short)

### 7.1 Time and travel

> In combat and other fast-paced situations, the game relies on rounds, a 6-second span of time.

(SRD 5.1, Time, p. 84)

> Every character and monster has a speed, which is the distance in feet that the character or monster can walk in 1 round.

(SRD 5.1, Movement — Speed, p. 84)

**Travel Pace** (SRD 5.1, Movement — Travel Pace, p. 84)

| Pace | Per minute | Per hour | Per day | Effect |
| --- | --- | --- | --- | --- |
| Fast | 400 feet | 4 miles | 30 miles | −5 penalty to passive Wisdom (Perception) scores |
| Normal | 300 feet | 3 miles | 24 miles | — |
| Slow | 200 feet | 2 miles | 18 miles | Able to use stealth |

Forced march: each hour past 8 requires a Con save (DC 10 + 1 per extra hour); a failure gives 1 exhaustion level.

> For each additional hour of travel beyond 8 hours, the characters cover the distance shown in the Hour column for their pace, and each character must make a Constitution saving throw at the end of the hour. The DC is 10 + 1 for each hour past 8 hours. On a failed saving throw, a character suffers one level of exhaustion

(SRD 5.1, Movement — Travel Pace: Forced March, p. 84)

Mounts can gallop for about an hour at twice the fast-pace distance. A ship's crew suffers no fast-pace penalty and gains no slow-pace benefit.

> A mounted character can ride at a gallop for about an hour, covering twice the usual distance for a fast pace. If fresh mounts are available every 8 to 10 miles, characters can cover larger distances at this pace, but this is very rare except in densely populated areas.

(SRD 5.1, Movement — Travel Pace: Mounts and Vehicles, p. 84)

> Characters in wagons, carriages, or other land vehicles choose a pace as normal. Characters in a waterborne vessel are limited to the speed of the vessel, and they don't suffer penalties for a fast pace or gain benefits from a slow pace.

(SRD 5.1, Movement — Travel Pace: Mounts and Vehicles, p. 84)

Difficult terrain halves travel distance.

> You move at half speed in difficult terrain—moving 1 foot in difficult terrain costs 2 feet of speed—so you can cover only half the normal distance in a minute, an hour, or a day.

(SRD 5.1, Movement — Difficult Terrain, p. 85)

### 7.2 Climbing, swimming, jumping

> While climbing or swimming, each foot of movement costs 1 extra foot (2 extra feet in difficult terrain), unless a creature has a climbing or swimming speed.

(SRD 5.1, Special Types of Movement — Climbing, Swimming, and Crawling, p. 85)

> At the GM's option, climbing a slippery vertical surface or one with few handholds requires a successful Strength (Athletics) check. Similarly, gaining any distance in rough water might require a successful Strength (Athletics) check.

(SRD 5.1, Special Types of Movement — Climbing, Swimming, and Crawling, p. 85)

> Long Jump. When you make a long jump, you cover a number of feet up to your Strength score if you move at least 10 feet on foot immediately before the jump. When you make a standing long jump, you can leap only half that distance.

(SRD 5.1, Special Types of Movement — Jumping, p. 85)

> High Jump. When you make a high jump, you leap into the air a number of feet equal to 3 + your Strength modifier if you move at least 10 feet on foot immediately before the jump. When you make a standing high jump, you can jump only half that distance.

(SRD 5.1, Special Types of Movement — Jumping, p. 85)

Each foot jumped costs a foot of movement. Low obstacles and landing in difficult terrain can need DC 10 checks.

> Either way, each foot you clear on the jump costs a foot of movement. This rule assumes that the height of your jump doesn't matter, such as a jump across a stream or chasm. At your GM's option, you must succeed on a DC 10 Strength (Athletics) check to clear a low obstacle (no taller than a quarter of the jump's distance), such as a hedge or low wall. Otherwise, you hit it. When you land in difficult terrain, you must succeed on a DC 10 Dexterity (Acrobatics) check to land on your feet. Otherwise, you land prone.

(SRD 5.1, Special Types of Movement — Jumping: Long Jump, p. 85)

> In some circumstances, your GM might allow you to make a Strength (Athletics) check to jump higher than you normally can. You can extend your arms half your height above yourself during the jump. Thus, you can reach above you a distance equal to the height of the jump plus 1½ times your height.

(SRD 5.1, Special Types of Movement — Jumping: High Jump, p. 85)

### 7.3 Falling

A fall deals 1d6 bludgeoning per 10 ft., up to 20d6. The creature lands prone unless it took no damage.

> At the end of a fall, a creature takes 1d6 bludgeoning damage for every 10 feet it fell, to a maximum of 20d6. The creature lands prone, unless it avoids taking damage from the fall.

(SRD 5.1, The Environment — Falling, p. 86)

### 7.4 Suffocating

You can hold your breath for 1 + Con modifier minutes (minimum 30 seconds). After that you survive Con modifier rounds (minimum 1), then drop to 0 HP.

> A creature can hold its breath for a number of minutes equal to 1 + its Constitution modifier (minimum of 30 seconds). When a creature runs out of breath or is choking, it can survive for a number of rounds equal to its Constitution modifier (minimum of 1 round). At the start of its next turn, it drops to 0 hit points and is dying, and it can't regain hit points or be stabilized until it can breathe again.

(SRD 5.1, The Environment — Suffocating, p. 86)

### 7.5 Vision and light

Lightly obscured areas (dim light) give disadvantage on sight-based Perception. Heavily obscured areas (darkness) leave a creature effectively blinded.

> In a lightly obscured area, such as dim light, patchy fog, or moderate foliage, creatures have disadvantage on Wisdom (Perception) checks that rely on sight. A heavily obscured area—such as darkness, opaque fog, or dense foliage—blocks vision entirely. A creature effectively suffers from the blinded condition (see appendix PH-A) when trying to see something in that area.

(SRD 5.1, The Environment — Vision and Light, p. 86)

> Dim light, also called shadows, creates a lightly obscured area. … Darkness creates a heavily obscured area.

(SRD 5.1, The Environment — Vision and Light, p. 86)

Darkvision: within its range, darkness counts as dim light, seen without colour.

> Within a specified range, a creature with darkvision can see in darkness as if the darkness were dim light, so areas of darkness are only lightly obscured as far as that creature is concerned. However, the creature can't discern color in darkness, only shades of gray.

(SRD 5.1, The Environment — Darkvision, p. 86)

> Bright light lets most creatures see normally. Even gloomy days provide bright light, as do torches, lanterns, fires, and other sources of illumination within a specific radius.

(SRD 5.1, The Environment — Vision and Light, p. 86)

> A creature with blindsight can perceive its surroundings without relying on sight, within a specific radius.

(SRD 5.1, The Environment — Blindsight, p. 86)

> A creature with truesight can, out to a specific range, see in normal and magical darkness, see invisible creatures and objects, automatically detect visual illusions and succeed on saving throws against them, and perceives the original form of a shapechanger or a creature that is transformed by magic. Furthermore, the creature can see into the Ethereal Plane.

(SRD 5.1, The Environment — Truesight, p. 86)

Monster senses, including tremorsense, are in 13.1.

Light sources (radius bright / extra dim): candle 5/5 ft., torch 20/20 ft. (1 hour), lamp 15/30 ft., hooded lantern 30/30 ft., bullseye lantern 60/60 ft. cone (lamps and lanterns burn 6 hours per flask of oil).

> Torch. A torch burns for 1 hour, providing bright light in a 20-foot radius and dim light for an additional 20 feet. If you make a melee attack with a burning torch and hit, it deals 1 fire damage.

(SRD 5.1, Adventuring Gear, p. 68; candle p. 67; lamp and lanterns p. 68)

### 7.6 Food and water

> A character needs one pound of food per day … A character can go without food for a number of days equal to 3 + his or her Constitution modifier (minimum 1). At the end of each day beyond that limit, a character automatically suffers one level of exhaustion. A normal day of eating resets the count of days without food to zero.

(SRD 5.1, The Environment — Food, pp. 86–87)

> A character needs one pound of food per day and can make food last longer by subsisting on half rations. Eating half a pound of food in a day counts as half a day without food.

(SRD 5.1, The Environment — Food, pp. 86–87)

> A character needs one gallon of water per day, or two gallons per day if the weather is hot. A character who drinks only half that much water must succeed on a DC 15 Constitution saving throw or suffer one level of exhaustion at the end of the day. A character with access to even less water automatically suffers one level of exhaustion at the end of the day. If the character already has one or more levels of exhaustion, the character takes two levels in either case.

(SRD 5.1, The Environment — Water, p. 87)

> Exhaustion caused by lack of food or water can't be removed until the character eats and drinks the full required amount.

(SRD 5.1, The Environment — Food and Water, p. 86)

### 7.7 Objects

> Objects are immune to poison and psychic damage … Objects always fail Strength and Dexterity saving throws, and they are immune to effects that require other saves. When an object drops to 0 hit points, it breaks.

(SRD 5.1, The Environment — Interacting with Objects, p. 87)

The GM sets an object's AC, hit points and any resistances, and the DC of checks to force or break it.

> The GM determines an object's Armor Class and hit points, and might decide that certain objects have resistance or immunity to certain kinds of attacks.

(SRD 5.1, The Environment — Interacting with Objects, p. 87)

> A character can also attempt a Strength check to break an object. The GM sets the DC for any such check.

(SRD 5.1, The Environment — Interacting with Objects, p. 87)

### 7.8 Between adventures (downtime)

Downtime activities need at least 8 hours a day; the days need not be consecutive.

> Periods of downtime can vary in duration, but each downtime activity requires a certain number of days to complete before you gain any benefit, and at least 8 hours of each day must be spent on the downtime activity for the day to count. The days do not need to be consecutive.

(SRD 5.1, Between Adventures — Downtime Activities, p. 88)

- **Lifestyle expenses**: "At the start of each week or month (your choice), choose a lifestyle from the Expenses table and pay the price to sustain that lifestyle." (p. 72). Prices per day: Wretched —, Squalid 1 sp, Poor 2 sp, Modest 1 gp, Comfortable 2 gp, Wealthy 4 gp, Aristocratic 10 gp minimum (Lifestyle Expenses table, pp. 72–73).
- **Crafting**: "For every day of downtime you spend crafting, you can craft one or more items with a total market value not exceeding 5 gp, and you must expend raw materials worth half the total market value." You must be proficient with the related tools. (p. 88)
- **Practicing a profession**: "You can work between adventures, allowing you to maintain a modest lifestyle without having to pay 1 gp per day." (p. 88)
- **Recuperating**: "After three days of downtime spent recuperating, you can make a DC 15 Constitution saving throw. On a successful save, you can choose one of the following results: End one effect on you that prevents you from regaining hit points. For the next 24 hours, gain advantage on saving throws against one disease or poison currently affecting you." (p. 88)
- **Researching**: "For each day of research, you must spend 1 gp to cover your expenses. This cost is in addition to your normal lifestyle expenses." (p. 89)
- **Training** (a language or a tool): "The training lasts for 250 days and costs 1 gp per day." (p. 89)

---

## 8. Character advancement

### 8.1 XP thresholds

**Character Advancement** (SRD 5.1, Beyond 1st Level, p. 56)

| Level | XP | Proficiency bonus |
| --- | --- | --- |
| 1 | 0 | +2 |
| 2 | 300 | +2 |
| 3 | 900 | +2 |
| 4 | 2,700 | +2 |
| 5 | 6,500 | +3 |
| 6 | 14,000 | +3 |
| 7 | 23,000 | +3 |
| 8 | 34,000 | +3 |
| 9 | 48,000 | +4 |
| 10 | 64,000 | +4 |
| 11 | 85,000 | +4 |
| 12 | 100,000 | +4 |
| 13 | 120,000 | +5 |
| 14 | 140,000 | +5 |
| 15 | 165,000 | +5 |
| 16 | 195,000 | +5 |
| 17 | 225,000 | +6 |
| 18 | 265,000 | +6 |
| 19 | 305,000 | +6 |
| 20 | 355,000 | +6 |

> A character who reaches a specified experience point total advances in capability. This advancement is called gaining a level.

(SRD 5.1, Beyond 1st Level, p. 56)

(The JSON files used have no XP-threshold table, so this table was checked against the PDF only. The proficiency bonus column matches `prof_bonus` in `5e-SRD-Levels.json`.)

### 8.2 Hit points per level (fixed average option)

Each level gives one Hit Die. Add either a roll or the class's fixed value (the average, rounded up), plus the Con modifier.

> Each time you gain a level, you gain 1 additional Hit Die. Roll that Hit Die, add your Constitution modifier to the roll, and add the total to your hit point maximum. Alternatively, you can use the fixed value shown in your class entry, which is the average result of the die roll (rounded up).

(SRD 5.1, Beyond 1st Level, p. 56)

A change to the Con modifier is applied backwards to every level.

> When your Constitution modifier increases by 1, your hit point maximum increases by 1 for each level you have attained.

(SRD 5.1, Beyond 1st Level, p. 56)

> If your Constitution modifier changes, your hit point maximum changes as well, as though you had the new modifier from 1st level.

(SRD 5.1, Using Ability Scores — Constitution: Hit Points, p. 81)

Fixed values: Barbarian 7 (d12), Fighter 6 (d10), Rogue 5 (d8). See Section 9.

### 8.3 Ability Score Improvement

At the ASI levels: +2 to one score, or +1 to two scores. No score can go above 20 this way.

> you can increase one ability score of your choice by 2, or you can increase two ability scores of your choice by 1. As normal, you can't increase an ability score above 20 using this feature.

(SRD 5.1, Barbarian/Fighter/Rogue — Ability Score Improvement, pp. 9, 25, 40)

ASI levels: Barbarian 4, 8, 12, 16, 19. Fighter 4, 6, 8, 12, 14, 16, 19. Rogue 4, 8, 10, 12, 16, 19. Each class states its own levels:

> When you reach 4th level, and again at 8th, 12th, 16th, and 19th level, you can increase one ability score of your choice by 2, or you can increase two ability scores of your choice by 1.

(SRD 5.1, Barbarian — Ability Score Improvement, p. 9)

> When you reach 4th level, and again at 6th, 8th, 12th, 14th, 16th, and 19th level, you can increase one ability score of your choice by 2, or you can increase two ability scores of your choice by 1.

(SRD 5.1, Fighter — Ability Score Improvement, p. 25)

> When you reach 4th level, and again at 8th, 10th, 12th, 16th, and 19th level, you can increase one ability score of your choice by 2, or you can increase two ability scores of your choice by 1.

(SRD 5.1, Rogue — Ability Score Improvement, p. 40)

Optional feats: a feat replaces an ASI, can be taken only once unless it says otherwise, and stops working while its prerequisite isn't met. Grappler is the only SRD feat (4.15).

> You can take each feat only once, unless the feat's description says otherwise. You must meet any prerequisite specified in a feat to take that feat. If you ever lose a feat's prerequisite, you can't use that feat until you regain the prerequisite.

(SRD 5.1, Feats, p. 75)

### 8.4 Multiclassing (out of scope)

The SRD includes multiclassing (prerequisites: Barbarian Str 13; Fighter Str 13 or Dex 13; Rogue Dex 13). v1 does not support it.

> Multiclassing allows you to gain levels in multiple classes.

(SRD 5.1, Multiclassing, p. 56)

---

## 9. Classes

### 9.1 Barbarian (SRD 5.1, pp. 8–10)

**Hit points and proficiencies**

> Hit Dice: 1d12 per barbarian level. Hit Points at 1st Level: 12 + your Constitution modifier. Hit Points at Higher Levels: 1d12 (or 7) + your Constitution modifier per barbarian level after 1st

> Armor: Light armor, medium armor, shields. Weapons: Simple weapons, martial weapons. Tools: None. Saving Throws: Strength, Constitution. Skills: Choose two from Animal Handling, Athletics, Intimidation, Nature, Perception, and Survival

**Starting equipment** (plus background equipment)

> (a) a greataxe or (b) any martial melee weapon; (a) two handaxes or (b) any simple weapon; An explorer's pack and four javelins

(SRD 5.1, Barbarian — Class Features, p. 8)

**The Barbarian** (SRD 5.1, p. 8)

| Level | PB | Features | Rages | Rage Damage |
| --- | --- | --- | --- | --- |
| 1st | +2 | Rage, Unarmored Defense | 2 | +2 |
| 2nd | +2 | Reckless Attack, Danger Sense | 2 | +2 |
| 3rd | +2 | Primal Path | 3 | +2 |
| 4th | +2 | Ability Score Improvement | 3 | +2 |
| 5th | +3 | Extra Attack, Fast Movement | 3 | +2 |
| 6th | +3 | Path feature | 4 | +2 |
| 7th | +3 | Feral Instinct | 4 | +2 |
| 8th | +3 | Ability Score Improvement | 4 | +2 |
| 9th | +4 | Brutal Critical (1 die) | 4 | +3 |
| 10th | +4 | Path feature | 4 | +3 |
| 11th | +4 | Relentless Rage | 4 | +3 |
| 12th | +4 | Ability Score Improvement | 5 | +3 |
| 13th | +5 | Brutal Critical (2 dice) | 5 | +3 |
| 14th | +5 | Path feature | 5 | +3 |
| 15th | +5 | Persistent Rage | 5 | +3 |
| 16th | +5 | Ability Score Improvement | 5 | +4 |
| 17th | +6 | Brutal Critical (3 dice) | 6 | +4 |
| 18th | +6 | Indomitable Might | 6 | +4 |
| 19th | +6 | Ability Score Improvement | 6 | +4 |
| 20th | +6 | Primal Champion | Unlimited | +4 |

(Matches `5e-SRD-Levels.json`; that file stores "Unlimited" as `rage_count: 9999`.)

**Rage (1st).** A bonus action, with no heavy armor. Gives advantage on Str checks and saves, + Rage Damage on Str melee weapon damage, and resistance to bludgeoning, piercing and slashing. Lasts 1 minute. Ends early if you are knocked unconscious, or if your turn ends without you attacking a hostile creature or taking damage since your last turn. Uses per long rest come from the table.

> On your turn, you can enter a rage as a bonus action. While raging, you gain the following benefits if you aren't wearing heavy armor: You have advantage on Strength checks and Strength saving throws. When you make a melee weapon attack using Strength, you gain a bonus to the damage roll that increases as you gain levels as a barbarian, as shown in the Rage Damage column of the Barbarian table. You have resistance to bludgeoning, piercing, and slashing damage.

> If you are able to cast spells, you can't cast them or concentrate on them while raging.

> Your rage lasts for 1 minute. It ends early if you are knocked unconscious or if your turn ends and you haven't attacked a hostile creature since your last turn or taken damage since then. You can also end your rage on your turn as a bonus action. Once you have raged the number of times shown for your barbarian level in the Rages column of the Barbarian table, you must finish a long rest before you can rage again.

(SRD 5.1, Barbarian — Rage, p. 8)

**Unarmored Defense (1st).** With no armor, AC = 10 + Dex + Con. A shield is allowed.

> While you are not wearing any armor, your Armor Class equals 10 + your Dexterity modifier + your Constitution modifier. You can use a shield and still gain this benefit.

(SRD 5.1, Barbarian — Unarmored Defense, p. 8)

**Reckless Attack (2nd).** Choose it on your first attack of the turn. You get advantage on Str melee weapon attacks this turn, and attacks against you have advantage until your next turn.

> When you make your first attack on your turn, you can decide to attack recklessly. Doing so gives you advantage on melee weapon attack rolls using Strength during this turn, but attack rolls against you have advantage until your next turn.

(SRD 5.1, Barbarian — Reckless Attack, p. 9)

**Danger Sense (2nd).** Advantage on Dex saves against effects you can see, unless you are blinded, deafened or incapacitated.

> You have advantage on Dexterity saving throws against effects that you can see, such as traps and spells. To gain this benefit, you can't be blinded, deafened, or incapacitated.

(SRD 5.1, Barbarian — Danger Sense, p. 9)

**Primal Path (3rd).** The path grants features at 3rd, 6th, 10th and 14th level. SRD 5.1 names the Totem Warrior but gives the text of the Path of the Berserker only.

> Choose the Path of the Berserker or the Path of the Totem Warrior, both detailed at the end of the class description. Your choice grants you features at 3rd level and again at 6th, 10th, and 14th levels.

(SRD 5.1, Barbarian — Primal Path, p. 9)

**Ability Score Improvement (4th).** See 8.3. (p. 9)

**Extra Attack (5th).**

> Beginning at 5th level, you can attack twice, instead of once, whenever you take the Attack action on your turn.

(SRD 5.1, Barbarian — Extra Attack, p. 9)

**Fast Movement (5th).** +10 ft. speed without heavy armor.

> Starting at 5th level, your speed increases by 10 feet while you aren't wearing heavy armor.

(SRD 5.1, Barbarian — Fast Movement, p. 9)

Beyond 5th (names only): Feral Instinct (7), Brutal Critical (9, 13, 17), Relentless Rage (11), Persistent Rage (15), Indomitable Might (18), Primal Champion (20). (pp. 9–10)

**Path of the Berserker**

**Frenzy (3rd).** When you rage you can choose to frenzy. While the rage lasts, you can make one melee weapon attack as a bonus action on each of your later turns. When the rage ends, you gain 1 exhaustion level.

> Starting when you choose this path at 3rd level, you can go into a frenzy when you rage. If you do so, for the duration of your rage you can make a single melee weapon attack as a bonus action on each of your turns after this one. When your rage ends, you suffer one level of exhaustion (as described in appendix PH-A).

(SRD 5.1, Barbarian — Path of the Berserker: Frenzy, p. 9)

Beyond 5th (names only): Mindless Rage (6), Intimidating Presence (10), Retaliation (14). (p. 10)

### 9.2 Fighter (SRD 5.1, pp. 24–25)

**Hit points and proficiencies**

> Hit Dice: 1d10 per fighter level. Hit Points at 1st Level: 10 + your Constitution modifier. Hit Points at Higher Levels: 1d10 (or 6) + your Constitution modifier per fighter level after 1st

> Armor: All armor, shields. Weapons: Simple weapons, martial weapons. Tools: None. Saving Throws: Strength, Constitution. Skills: Choose two skills from Acrobatics, Animal Handling, Athletics, History, Insight, Intimidation, Perception, and Survival

**Starting equipment**

> (a) chain mail or (b) leather armor, longbow, and 20 arrows; (a) a martial weapon and a shield or (b) two martial weapons; (a) a light crossbow and 20 bolts or (b) two handaxes; (a) a dungeoneer's pack or (b) an explorer's pack

(SRD 5.1, Fighter — Class Features, p. 24)

**The Fighter** (SRD 5.1, p. 24)

| Level | PB | Features |
| --- | --- | --- |
| 1st | +2 | Fighting Style, Second Wind |
| 2nd | +2 | Action Surge (one use) |
| 3rd | +2 | Martial Archetype |
| 4th | +2 | Ability Score Improvement |
| 5th | +3 | Extra Attack |
| 6th | +3 | Ability Score Improvement |
| 7th | +3 | Martial Archetype feature |
| 8th | +3 | Ability Score Improvement |
| 9th | +4 | Indomitable (one use) |
| 10th | +4 | Martial Archetype feature |
| 11th | +4 | Extra Attack (2) |
| 12th | +4 | Ability Score Improvement |
| 13th | +5 | Indomitable (two uses) |
| 14th | +5 | Ability Score Improvement |
| 15th | +5 | Martial Archetype feature |
| 16th | +5 | Ability Score Improvement |
| 17th | +6 | Action Surge (two uses), Indomitable (three uses) |
| 18th | +6 | Martial Archetype feature |
| 19th | +6 | Ability Score Improvement |
| 20th | +6 | Extra Attack (3) |

**Fighting Style (1st).** Choose one. No option can be taken twice.

> You adopt a particular style of fighting as your specialty. Choose one of the following options. You can't take a Fighting Style option more than once, even if you later get to choose again.

- **Archery**: "You gain a +2 bonus to attack rolls you make with ranged weapons."
- **Defense**: "While you are wearing armor, you gain a +1 bonus to AC."
- **Dueling**: "When you are wielding a melee weapon in one hand and no other weapons, you gain a +2 bonus to damage rolls with that weapon."
- **Great Weapon Fighting**: "When you roll a 1 or 2 on a damage die for an attack you make with a melee weapon that you are wielding with two hands, you can reroll the die and must use the new roll, even if the new roll is a 1 or a 2. The weapon must have the two-handed or versatile property for you to gain this benefit."
- **Protection**: "When a creature you can see attacks a target other than you that is within 5 feet of you, you can use your reaction to impose disadvantage on the attack roll. You must be wielding a shield."
- **Two-Weapon Fighting**: "When you engage in two-weapon fighting, you can add your ability modifier to the damage of the second attack."

(SRD 5.1, Fighter — Fighting Style, p. 24)

**Second Wind (1st).** A bonus action: regain 1d10 + fighter level HP. Once per short or long rest.

> On your turn, you can use a bonus action to regain hit points equal to 1d10 + your fighter level. Once you use this feature, you must finish a short or long rest before you can use it again.

(SRD 5.1, Fighter — Second Wind, p. 24)

**Action Surge (2nd).** One extra action on your turn. Once per short or long rest (twice from 17th level, but only once per turn).

> On your turn, you can take one additional action on top of your regular action and a possible bonus action. Once you use this feature, you must finish a short or long rest before you can use it again. Starting at 17th level, you can use it twice before a rest, but only once on the same turn.

(SRD 5.1, Fighter — Action Surge, p. 25)

**Martial Archetype (3rd).** The archetype grants features at 3rd, 7th, 10th, 15th and 18th level.

> The archetype you choose grants you features at 3rd level and again at 7th, 10th, 15th, and 18th level.

(SRD 5.1, Fighter — Martial Archetype, p. 25)

**Ability Score Improvement (4th).** See 8.3. (p. 25)

**Extra Attack (5th).** Two attacks per Attack action (three at 11th level, four at 20th).

> Beginning at 5th level, you can attack twice, instead of once, whenever you take the Attack action on your turn. The number of attacks increases to three when you reach 11th level in this class and to four when you reach 20th level in this class.

(SRD 5.1, Fighter — Extra Attack, p. 25)

Beyond 5th (names only): Indomitable (9, 13, 17), Extra Attack (2) at 11, Extra Attack (3) at 20. (p. 25)

**Champion**

**Improved Critical (3rd).** Weapon attacks crit on 19–20.

> Beginning when you choose this archetype at 3rd level, your weapon attacks score a critical hit on a roll of 19 or 20.

(SRD 5.1, Fighter — Champion: Improved Critical, p. 25)

Beyond 5th (names only): Remarkable Athlete (7), Additional Fighting Style (10), Superior Critical (15), Survivor (18). (p. 25)

### 9.3 Rogue (SRD 5.1, pp. 39–41)

**Hit points and proficiencies**

> Hit Dice: 1d8 per rogue level. Hit Points at 1st Level: 8 + your Constitution modifier. Hit Points at Higher Levels: 1d8 (or 5) + your Constitution modifier per rogue level after 1st

> Armor: Light armor. Weapons: Simple weapons, hand crossbows, longswords, rapiers, shortswords. Tools: Thieves' tools. Saving Throws: Dexterity, Intelligence. Skills: Choose four from Acrobatics, Athletics, Deception, Insight, Intimidation, Investigation, Perception, Performance, Persuasion, Sleight of Hand, and Stealth

**Starting equipment**

> (a) a rapier or (b) a shortsword; (a) a shortbow and quiver of 20 arrows or (b) a shortsword; (a) a burglar's pack, (b) a dungeoneer's pack, or (c) an explorer's pack; (a) Leather armor, two daggers, and thieves' tools

(SRD 5.1, Rogue — Class Features, p. 39)

**The Rogue** (SRD 5.1, p. 39)

| Level | PB | Sneak Attack | Features |
| --- | --- | --- | --- |
| 1st | +2 | 1d6 | Expertise, Sneak Attack, Thieves' Cant |
| 2nd | +2 | 1d6 | Cunning Action |
| 3rd | +2 | 2d6 | Roguish Archetype |
| 4th | +2 | 2d6 | Ability Score Improvement |
| 5th | +3 | 3d6 | Uncanny Dodge |
| 6th | +3 | 3d6 | Expertise |
| 7th | +3 | 4d6 | Evasion |
| 8th | +3 | 4d6 | Ability Score Improvement |
| 9th | +4 | 5d6 | Roguish Archetype feature |
| 10th | +4 | 5d6 | Ability Score Improvement |
| 11th | +4 | 6d6 | Reliable Talent |
| 12th | +4 | 6d6 | Ability Score Improvement |
| 13th | +5 | 7d6 | Roguish Archetype feature |
| 14th | +5 | 7d6 | Blindsense |
| 15th | +5 | 8d6 | Slippery Mind |
| 16th | +5 | 8d6 | Ability Score Improvement |
| 17th | +6 | 9d6 | Roguish Archetype feature |
| 18th | +6 | 9d6 | Elusive |
| 19th | +6 | 10d6 | Ability Score Improvement |
| 20th | +6 | 10d6 | Stroke of Luck |

**Expertise (1st).** Double the proficiency bonus for two skill proficiencies, or one skill and thieves' tools. Two more at 6th level.

> At 1st level, choose two of your skill proficiencies, or one of your skill proficiencies and your proficiency with thieves' tools. Your proficiency bonus is doubled for any ability check you make that uses either of the chosen proficiencies. At 6th level, you can choose two more of your proficiencies (in skills or with thieves' tools) to gain this benefit.

(SRD 5.1, Rogue — Expertise, p. 39)

**Sneak Attack (1st).** Once per turn, add the table's dice to one hit made with a finesse or ranged weapon. It needs either advantage, or an enemy of the target within 5 ft. of it that isn't incapacitated while you don't have disadvantage.

> Once per turn, you can deal an extra 1d6 damage to one creature you hit with an attack if you have advantage on the attack roll. The attack must use a finesse or a ranged weapon. You don't need advantage on the attack roll if another enemy of the target is within 5 feet of it, that enemy isn't incapacitated, and you don't have disadvantage on the attack roll.

(SRD 5.1, Rogue — Sneak Attack, p. 39)

> The amount of the extra damage increases as you gain levels in this class, as shown in the Sneak Attack column of the Rogue table.

(SRD 5.1, Rogue — Sneak Attack, p. 39)

**Thieves' Cant (1st).** A secret language of jargon and signs. It has no rules effect beyond communication; a message takes four times as long as plain speech.

> During your rogue training you learned thieves' cant, a secret mix of dialect, jargon, and code that allows you to hide messages in seemingly normal conversation. Only another creature that knows thieves' cant understands such messages. It takes four times longer to convey such a message than it does to speak the same idea plainly. In addition, you understand a set of secret signs and symbols used to convey short, simple messages, such as whether an area is dangerous or the territory of a thieves' guild, whether loot is nearby, or whether the people in an area are easy marks or will provide a safe house for thieves on the run.

(SRD 5.1, Rogue — Thieves' Cant, pp. 39–40)

**Cunning Action (2nd).** A bonus action each turn, used only for Dash, Disengage or Hide.

> You can take a bonus action on each of your turns in combat. This action can be used only to take the Dash, Disengage, or Hide action.

(SRD 5.1, Rogue — Cunning Action, p. 40)

**Roguish Archetype (3rd).** The archetype grants features at 3rd, 9th, 13th and 17th level.

> Your archetype choice grants you features at 3rd level and then again at 9th, 13th, and 17th level.

(SRD 5.1, Rogue — Roguish Archetype, p. 40)

**Ability Score Improvement (4th).** See 8.3. (p. 40)

**Uncanny Dodge (5th).** Use your reaction to halve the damage of an attack that hits you, from an attacker you can see.

> Starting at 5th level, when an attacker that you can see hits you with an attack, you can use your reaction to halve the attack's damage against you.

(SRD 5.1, Rogue — Uncanny Dodge, p. 40)

Beyond 5th (names only): Expertise (6), Evasion (7), Reliable Talent (11), Blindsense (14), Slippery Mind (15), Elusive (18), Stroke of Luck (20). (p. 40)

**Thief**

**Fast Hands (3rd).** The Cunning Action bonus action can also make a Sleight of Hand check, use thieves' tools, or take the Use an Object action.

> Starting at 3rd level, you can use the bonus action granted by your Cunning Action to make a Dexterity (Sleight of Hand) check, use your thieves' tools to disarm a trap or open a lock, or take the Use an Object action.

(SRD 5.1, Rogue — Thief: Fast Hands, pp. 40–41)

**Second-Story Work (3rd).** Climbing costs no extra movement. Running jumps go farther by your Dex modifier in feet.

> When you choose this archetype at 3rd level, you gain the ability to climb faster than normal; climbing no longer costs you extra movement. In addition, when you make a running jump, the distance you cover increases by a number of feet equal to your Dexterity modifier.

(SRD 5.1, Rogue — Thief: Second-Story Work, p. 41)

Beyond 5th (names only): Supreme Sneak (9), Use Magic Device (13), Thief's Reflexes (17). (p. 41)

---

## 10. Races (short)

SRD 5.1 has nine races, each with one subrace at most: Dwarf (Hill Dwarf), Elf (High Elf), Halfling (Lightfoot), Human, Dragonborn, Gnome (Rock Gnome), Half-Elf, Half-Orc, Tiefling. (SRD 5.1, Races, pp. 3–7)

> Members of a subrace have the traits of the parent race in addition to the traits specified for their subrace.

(SRD 5.1, Races — Subraces, p. 3)

| Race (subrace) | Ability Score Increase | Size | Speed | Mechanical traits | Page |
| --- | --- | --- | --- | --- | --- |
| Dwarf | Con +2 | Medium | 25 ft. (not reduced by heavy armor) | Darkvision 60 ft.; Dwarven Resilience; Dwarven Combat Training (battleaxe, handaxe, light hammer, warhammer); Tool Proficiency; Stonecunning | 3 |
| Hill Dwarf | Wis +1 | | | Dwarven Toughness | 4 |
| Elf | Dex +2 | Medium | 30 ft. | Darkvision 60 ft.; Keen Senses (Perception); Fey Ancestry; Trance | 4 |
| High Elf | Int +1 | | | Elf Weapon Training (longsword, shortsword, shortbow, longbow); Cantrip; Extra Language | 4 |
| Halfling | Dex +2 | Small | 25 ft. | Lucky; Brave; Halfling Nimbleness | 4–5 |
| Lightfoot | Cha +1 | | | Naturally Stealthy | 5 |
| Human | +1 to all six | Medium | 30 ft. | Extra language | 5 |
| Dragonborn | Str +2, Cha +1 | Medium | 30 ft. | Draconic Ancestry; Breath Weapon; Damage Resistance | 5–6 |
| Gnome | Int +2 | Small | 25 ft. | Darkvision 60 ft.; Gnome Cunning | 6 |
| Rock Gnome | Con +1 | | | Artificer's Lore; Tinker | 6 |
| Half-Elf | Cha +2, two others +1 | Medium | 30 ft. | Darkvision 60 ft.; Fey Ancestry; Skill Versatility (two skills) | 6–7 |
| Half-Orc | Str +2, Con +1 | Medium | 30 ft. | Darkvision 60 ft.; Menacing (Intimidation); Relentless Endurance; Savage Attacks | 7 |
| Tiefling | Int +1, Cha +2 | Medium | 30 ft. | Darkvision 60 ft.; Hellish Resistance (fire); Infernal Legacy (spells) | 7 |

Traits the engine resolves:

> Dwarven Resilience. You have advantage on saving throws against poison, and you have resistance against poison damage. (p. 3)

> Dwarven Toughness. Your hit point maximum increases by 1, and it increases by 1 every time you gain a level. (p. 4)

> Fey Ancestry. You have advantage on saving throws against being charmed, and magic can't put you to sleep. (Elf p. 4; Half-Elf p. 7)

> Lucky. When you roll a 1 on the d20 for an attack roll, ability check, or saving throw, you can reroll the die and must use the new roll. (p. 4)

> Brave. You have advantage on saving throws against being frightened. (p. 4)

> Breath Weapon. You can use your action to exhale destructive energy. … The DC for this saving throw equals 8 + your Constitution modifier + your proficiency bonus. A creature takes 2d6 damage on a failed save, and half as much damage on a successful one. The damage increases to 3d6 at 6th level, 4d6 at 11th level, and 5d6 at 16th level. After you use your breath weapon, you can't use it again until you complete a short or long rest. (pp. 5–6)

Draconic Ancestry (p. 5): Black (acid, 5 by 30 ft. line, Dex save), Blue (lightning, line, Dex), Brass (fire, line, Dex), Bronze (lightning, line, Dex), Copper (acid, line, Dex), Gold (fire, 15 ft. cone, Dex), Green (poison, cone, Con), Red (fire, cone, Dex), Silver (cold, cone, Con), White (cold, cone, Con).

> Gnome Cunning. You have advantage on all Intelligence, Wisdom, and Charisma saving throws against magic. (p. 6)

> Relentless Endurance. When you are reduced to 0 hit points but not killed outright, you can drop to 1 hit point instead. You can't use this feature again until you finish a long rest. (p. 7)

> Savage Attacks. When you score a critical hit with a melee weapon attack, you can roll one of the weapon's damage dice one additional time and add it to the extra damage of the critical hit. (p. 7)

> Hellish Resistance. You have resistance to fire damage. (p. 7)

> Darkvision. … You can see in dim light within 60 feet of you as if it were bright light, and in darkness as if it were dim light. You can't discern color in darkness, only shades of gray. (Dwarf p. 3 and others)

Other traits (SRD 5.1, Races, pp. 3–7):

> Speed. Your base walking speed is 25 feet. Your speed is not reduced by wearing heavy armor. (Dwarf, p. 3)

> Dwarven Combat Training. You have proficiency with the battleaxe, handaxe, light hammer, and warhammer. (p. 3)

> Tool Proficiency. You gain proficiency with the artisan's tools of your choice: smith's tools, brewer's supplies, or mason's tools. (p. 3)

> Stonecunning. Whenever you make an Intelligence (History) check related to the origin of stonework, you are considered proficient in the History skill and add double your proficiency bonus to the check, instead of your normal proficiency bonus. (p. 3)

> Keen Senses. You have proficiency in the Perception skill. (p. 4)

> Trance. Elves don't need to sleep. Instead, they meditate deeply, remaining semiconscious, for 4 hours a day. … After resting in this way, you gain the same benefit that a human does from 8 hours of sleep. (p. 4)

> Elf Weapon Training. You have proficiency with the longsword, shortsword, shortbow, and longbow. (p. 4)

> Cantrip. You know one cantrip of your choice from the wizard spell list. Intelligence is your spellcasting ability for it. (p. 4)

> Extra Language. You can speak, read, and write one extra language of your choice. (High Elf, p. 4)

> Halfling Nimbleness. You can move through the space of any creature that is of a size larger than yours. (p. 5)

> Naturally Stealthy. You can attempt to hide even when you are obscured only by a creature that is at least one size larger than you. (p. 5)

> Draconic Ancestry. You have draconic ancestry. Choose one type of dragon from the Draconic Ancestry table. Your breath weapon and damage resistance are determined by the dragon type, as shown in the table. (p. 5)

> Damage Resistance. You have resistance to the damage type associated with your draconic ancestry. (p. 6)

> Artificer's Lore. Whenever you make an Intelligence (History) check related to magic items, alchemical objects, or technological devices, you can add twice your proficiency bonus, instead of any proficiency bonus you normally apply. (p. 6)

> Tinker. You have proficiency with artisan's tools (tinker's tools). Using those tools, you can spend 1 hour and 10 gp worth of materials to construct a Tiny clockwork device (AC 5, 1 hp). The device ceases to function after 24 hours (unless you spend 1 hour repairing it to keep the device functioning), or when you use your action to dismantle it; at that time, you can reclaim the materials used to create it. You can have up to three such devices active at a time. (p. 6; device options Clockwork Toy, Fire Starter, Music Box)

> Skill Versatility. You gain proficiency in two skills of your choice. (p. 7)

> Menacing. You gain proficiency in the Intimidation skill. (p. 7)

> Infernal Legacy. You know the thaumaturgy cantrip. When you reach 3rd level, you can cast the hellish rebuke spell as a 2nd-level spell once with this trait and regain the ability to do so when you finish a long rest. When you reach 5th level, you can cast the darkness spell once with this trait and regain the ability to do so when you finish a long rest. Charisma is your spellcasting ability for these spells. (p. 7)

Languages (read, speak and write): Dwarf Common and Dwarvish; Elf Common and Elvish (High Elf +1 of choice); Halfling Common and Halfling; Human Common and one of choice; Dragonborn Common and Draconic; Gnome Common and Gnomish; Half-Elf Common, Elvish and one of choice; Half-Orc Common and Orc; Tiefling Common and Infernal. (pp. 3–7)

Small creatures have disadvantage with heavy weapons (12.4).

> Members of a few races are Small (between 2 and 4 feet tall), which means that certain rules of the game affect them differently. The most important of these rules is that Small characters have trouble wielding heavy weapons, as explained in "Equipment."

(SRD 5.1, Races — Racial Traits: Size, p. 3)

---

## 11. Background

SRD 5.1 has one background: **Acolyte**. A background gives two skills, plus tools or languages, equipment, a feature and suggested characteristics.

> Each background gives a character proficiency in two skills … If a character would gain the same proficiency from two different sources, he or she can choose a different proficiency of the same kind (skill or tool) instead.

(SRD 5.1, Backgrounds — Proficiencies, p. 60)

> Skill Proficiencies: Insight, Religion. Languages: Two of your choice. Equipment: A holy symbol (a gift to you when you entered the priesthood), a prayer book or prayer wheel, 5 sticks of incense, vestments, a set of common clothes, and a pouch containing 15 gp

(SRD 5.1, Backgrounds — Acolyte, p. 61)

Feature: Shelter of the Faithful gives free healing and care at temples of your faith and support at a modest lifestyle. It has no dice mechanic.

> You and your adventuring companions can expect to receive free healing and care at a temple, shrine, or other established presence of your faith, though you must provide any material components needed for spells. Those who share your religion will support you (but only you) at a modest lifestyle.

(SRD 5.1, Backgrounds — Acolyte: Feature: Shelter of the Faithful, p. 61)

A background can be customised: replace the feature, choose any two skills, and choose two tools or languages in total.

> To customize a background, you can replace one feature with any other one, choose any two skills, and choose a total of two tool proficiencies or languages from the sample backgrounds.

(SRD 5.1, Backgrounds — Customizing a Background, p. 60)

---

## 12. Equipment

### 12.1 Coinage

> One gold piece is worth ten silver pieces … One silver piece is worth ten copper pieces … An electrum piece is worth five silver pieces, and a platinum piece is worth ten gold pieces. A standard coin weighs about a third of an ounce, so fifty coins weigh a pound.

(SRD 5.1, Equipment — Coins, p. 62)

**Standard Exchange Rates** (SRD 5.1, p. 62). Read across: 1 of the row coin equals this many of the column coin.

| Coin | CP | SP | EP | GP | PP |
| --- | --- | --- | --- | --- | --- |
| Copper (cp) | 1 | 1/10 | 1/50 | 1/100 | 1/1,000 |
| Silver (sp) | 10 | 1 | 1/5 | 1/10 | 1/100 |
| Electrum (ep) | 50 | 5 | 1 | 1/2 | 1/20 |
| Gold (gp) | 100 | 10 | 2 | 1 | 1/10 |
| Platinum (pp) | 1,000 | 100 | 20 | 10 | 1 |

Selling: undamaged equipment fetches half its cost. Gems, art and trade goods keep full value.

> As a general rule, undamaged weapons, armor, and other equipment fetch half their cost when sold in a market. Weapons and armor used by monsters are rarely in good enough condition to sell.

(SRD 5.1, Equipment — Selling Treasure, p. 62)

> Gems, Jewelry, and Art Objects. These items retain their full value in the marketplace, and you can either trade them in for coin or use them as currency for other transactions.

(SRD 5.1, Equipment — Selling Treasure, p. 62)

> Like gems and art objects, trade goods—bars of iron, bags of salt, livestock, and so on—retain their full value in the market and can be used as currency.

(SRD 5.1, Equipment — Selling Treasure: Trade Goods, p. 62)

### 12.2 Armor

Wearing armor without proficiency gives disadvantage on Str and Dex checks, saves and attacks.

> If you wear armor that you lack proficiency with, you have disadvantage on any ability check, saving throw, or attack roll that involves Strength or Dexterity, and you can't cast spells.

(SRD 5.1, Equipment — Armor: Armor Proficiency, p. 62)

AC rules by category: light adds full Dex, medium adds Dex up to +2, and heavy adds no Dex (a negative Dex has no effect). A shield gives +2, and only one shield counts.

> If you wear light armor, you add your Dexterity modifier to the base number from your armor type to determine your Armor Class.

(SRD 5.1, Equipment — Light Armor, p. 63)

> If you wear medium armor, you add your Dexterity modifier, to a maximum of +2, to the base number from your armor type to determine your Armor Class.

(SRD 5.1, Equipment — Medium Armor, p. 63)

> Heavy armor doesn't let you add your Dexterity modifier to your Armor Class, but it also doesn't penalize you if your Dexterity modifier is negative.

(SRD 5.1, Equipment — Heavy Armor, p. 63)

> Wielding a shield increases your Armor Class by 2. You can benefit from only one shield at a time.

(SRD 5.1, Equipment — Armor: Shields, p. 63)

Strength requirement: heavy armor with a "Str" value cuts speed by 10 ft. if your Strength is lower. "Disadvantage" in the Stealth column gives disadvantage on Dexterity (Stealth).

> If the Armor table shows "Str 13" or "Str 15" in the Strength column for an armor type, the armor reduces the wearer's speed by 10 feet unless the wearer has a Strength score equal to or higher than the listed score. Stealth. If the Armor table shows "Disadvantage" in the Stealth column, the wearer has disadvantage on Dexterity (Stealth) checks.

(SRD 5.1, Equipment — Armor: Heavy Armor / Stealth, p. 63)

**Armor** (SRD 5.1, pp. 63–64. Matches `5e-SRD-Equipment.json`.)

| Armor | Cost | Armor Class (AC) | Strength | Stealth | Weight |
| --- | --- | --- | --- | --- | --- |
| *Light Armor* | | | | | |
| Padded | 5 gp | 11 + Dex modifier | — | Disadvantage | 8 lb. |
| Leather | 10 gp | 11 + Dex modifier | — | — | 10 lb. |
| Studded leather | 45 gp | 12 + Dex modifier | — | — | 13 lb. |
| *Medium Armor* | | | | | |
| Hide | 10 gp | 12 + Dex modifier (max 2) | — | — | 12 lb. |
| Chain shirt | 50 gp | 13 + Dex modifier (max 2) | — | — | 20 lb. |
| Scale mail | 50 gp | 14 + Dex modifier (max 2) | — | Disadvantage | 45 lb. |
| Breastplate | 400 gp | 14 + Dex modifier (max 2) | — | — | 20 lb. |
| Half plate | 750 gp | 15 + Dex modifier (max 2) | — | Disadvantage | 40 lb. |
| *Heavy Armor* | | | | | |
| Ring mail | 30 gp | 14 | — | Disadvantage | 40 lb. |
| Chain mail | 75 gp | 16 | Str 13 | Disadvantage | 55 lb. |
| Splint | 200 gp | 17 | Str 15 | Disadvantage | 60 lb. |
| Plate | 1,500 gp | 18 | Str 15 | Disadvantage | 65 lb. |
| *Shield* | | | | | |
| Shield | 10 gp | +2 | — | — | 6 lb. |

**Donning and Doffing Armor** (SRD 5.1, p. 64)

| Category | Don | Doff |
| --- | --- | --- |
| Light Armor | 1 minute | 1 minute |
| Medium Armor | 5 minutes | 1 minute |
| Heavy Armor | 10 minutes | 5 minutes |
| Shield | 1 action | 1 action |

> Don. This is the time it takes to put on armor. You benefit from the armor's AC only if you take the full time to don the suit of armor. Doff. This is the time it takes to take off armor. If you have help, reduce this time by half.

(SRD 5.1, Equipment — Getting Into and Out of Armor, p. 64)

### 12.3 Unarmored defense

There is no general "unarmored AC" rule anywhere in SRD 5.1. A search of the full text for "10 + your Dexterity modifier" finds only Barbarian Unarmored Defense (p. 8), Monk Unarmored Defense (p. 26) and the mirror image spell's duplicates (p. 165). The Dexterity section says only "Depending on the armor you wear, you might add some or all of your Dexterity modifier to your Armor Class" (p. 80). The Barbarian's Unarmored Defense (9.1) is 10 + Dex + Con, and a shield is allowed. (The Monk's version, 10 + Dex + Wis, p. 26, is not used in v1.) Monster AC without armor comes from Dex and natural armor (13.1).

### 12.4 Weapons

Proficiency adds the proficiency bonus to the attack roll. There is no other penalty for lacking proficiency.

> Proficiency with a weapon allows you to add your proficiency bonus to the attack roll for any attack you make with that weapon. If you make an attack roll using a weapon with which you lack proficiency, you do not add your proficiency bonus to the attack roll.

(SRD 5.1, Equipment — Weapon Proficiency, p. 64)

> A melee weapon is used to attack a target within 5 feet of you, whereas a ranged weapon is used to attack a target at a distance.

(SRD 5.1, Equipment — Weapons, p. 64)

**Weapon properties** (SRD 5.1, Equipment — Weapon Properties, pp. 64–65)

- **Ammunition**: "You can use a weapon that has the ammunition property to make a ranged attack only if you have ammunition to fire from the weapon. Each time you attack with the weapon, you expend one piece of ammunition. Drawing the ammunition from a quiver, case, or other container is part of the attack (you need a free hand to load a one-handed weapon). At the end of the battle, you can recover half your expended ammunition by taking a minute to search the battlefield. If you use a weapon that has the ammunition property to make a melee attack, you treat the weapon as an improvised weapon" (p. 64)
- **Finesse**: "When making an attack with a finesse weapon, you use your choice of your Strength or Dexterity modifier for the attack and damage rolls. You must use the same modifier for both rolls." (p. 64)
- **Heavy**: "Small creatures have disadvantage on attack rolls with heavy weapons." (p. 65)
- **Light**: "A light weapon is small and easy to handle, making it ideal for use when fighting with two weapons." (p. 65)
- **Loading**: "Because of the time required to load this weapon, you can fire only one piece of ammunition from it when you use an action, bonus action, or reaction to fire it, regardless of the number of attacks you can normally make." (p. 65)
- **Range**: "The first is the weapon's normal range in feet, and the second indicates the weapon's long range. When attacking a target beyond normal range, you have disadvantage on the attack roll. You can't attack a target beyond the weapon's long range." (p. 65)
- **Reach**: "This weapon adds 5 feet to your reach when you attack with it, as well as when determining your reach for opportunity attacks with it." (p. 65)
- **Special**: "A weapon with the special property has unusual rules governing its use, explained in the weapon's description" (p. 65)
- **Thrown**: "If the weapon is a melee weapon, you use the same ability modifier for that attack roll and damage roll that you would use for a melee attack with the weapon." (p. 65)
- **Two-Handed**: "This weapon requires two hands when you attack with it." (p. 65)
- **Versatile**: "This weapon can be used with one or two hands. A damage value in parentheses appears with the property—the damage when the weapon is used with two hands to make a melee attack." (p. 65)

**Improvised weapons**: 1d4 damage. Thrown range 20/60.

> An object that bears no resemblance to a weapon deals 1d4 damage … If a character uses a ranged weapon to make a melee attack, or throws a melee weapon that does not have the thrown property, it also deals 1d4 damage. An improvised thrown weapon has a normal range of 20 feet and a long range of 60 feet.

(SRD 5.1, Equipment — Improvised Weapons, p. 65)

**Special weapons**

> Lance. You have disadvantage when you use a lance to attack a target within 5 feet of you. Also, a lance requires two hands to wield when you aren't mounted. Net. A Large or smaller creature hit by a net is restrained until it is freed. … A creature can use its action to make a DC 10 Strength check, freeing itself or another creature within its reach on a success. Dealing 5 slashing damage to the net (AC 10) also frees the creature … When you use an action, bonus action, or reaction to attack with a net, you can make only one attack regardless of the number of attacks you can normally make.

(SRD 5.1, Equipment — Special Weapons, p. 65)

Silvering costs 100 gp per weapon or per 10 pieces of ammunition. (p. 65)

**Weapons** (SRD 5.1, pp. 65–66. Every value matches `5e-SRD-Equipment.json`; see the disagreements list for differences in tags only.)

| Name | Cost | Damage | Weight | Properties |
| --- | --- | --- | --- | --- |
| ***Simple Melee Weapons*** | | | | |
| Club | 1 sp | 1d4 bludgeoning | 2 lb. | Light |
| Dagger | 2 gp | 1d4 piercing | 1 lb. | Finesse, light, thrown (range 20/60) |
| Greatclub | 2 sp | 1d8 bludgeoning | 10 lb. | Two-handed |
| Handaxe | 5 gp | 1d6 slashing | 2 lb. | Light, thrown (range 20/60) |
| Javelin | 5 sp | 1d6 piercing | 2 lb. | Thrown (range 30/120) |
| Light hammer | 2 gp | 1d4 bludgeoning | 2 lb. | Light, thrown (range 20/60) |
| Mace | 5 gp | 1d6 bludgeoning | 4 lb. | — |
| Quarterstaff | 2 sp | 1d6 bludgeoning | 4 lb. | Versatile (1d8) |
| Sickle | 1 gp | 1d4 slashing | 2 lb. | Light |
| Spear | 1 gp | 1d6 piercing | 3 lb. | Thrown (range 20/60), versatile (1d8) |
| ***Simple Ranged Weapons*** | | | | |
| Crossbow, light | 25 gp | 1d8 piercing | 5 lb. | Ammunition (range 80/320), loading, two-handed |
| Dart | 5 cp | 1d4 piercing | 1/4 lb. | Finesse, thrown (range 20/60) |
| Shortbow | 25 gp | 1d6 piercing | 2 lb. | Ammunition (range 80/320), two-handed |
| Sling | 1 sp | 1d4 bludgeoning | — | Ammunition (range 30/120) |
| ***Martial Melee Weapons*** | | | | |
| Battleaxe | 10 gp | 1d8 slashing | 4 lb. | Versatile (1d10) |
| Flail | 10 gp | 1d8 bludgeoning | 2 lb. | — |
| Glaive | 20 gp | 1d10 slashing | 6 lb. | Heavy, reach, two-handed |
| Greataxe | 30 gp | 1d12 slashing | 7 lb. | Heavy, two-handed |
| Greatsword | 50 gp | 2d6 slashing | 6 lb. | Heavy, two-handed |
| Halberd | 20 gp | 1d10 slashing | 6 lb. | Heavy, reach, two-handed |
| Lance | 10 gp | 1d12 piercing | 6 lb. | Reach, special |
| Longsword | 15 gp | 1d8 slashing | 3 lb. | Versatile (1d10) |
| Maul | 10 gp | 2d6 bludgeoning | 10 lb. | Heavy, two-handed |
| Morningstar | 15 gp | 1d8 piercing | 4 lb. | — |
| Pike | 5 gp | 1d10 piercing | 18 lb. | Heavy, reach, two-handed |
| Rapier | 25 gp | 1d8 piercing | 2 lb. | Finesse |
| Scimitar | 25 gp | 1d6 slashing | 3 lb. | Finesse, light |
| Shortsword | 10 gp | 1d6 piercing | 2 lb. | Finesse, light |
| Trident | 5 gp | 1d6 piercing | 4 lb. | Thrown (range 20/60), versatile (1d8) |
| War pick | 5 gp | 1d8 piercing | 2 lb. | — |
| Warhammer | 15 gp | 1d8 bludgeoning | 2 lb. | Versatile (1d10) |
| Whip | 2 gp | 1d4 slashing | 3 lb. | Finesse, reach |
| ***Martial Ranged Weapons*** | | | | |
| Blowgun | 10 gp | 1 piercing | 1 lb. | Ammunition (range 25/100), loading |
| Crossbow, hand | 75 gp | 1d6 piercing | 3 lb. | Ammunition (range 30/120), light, loading |
| Crossbow, heavy | 50 gp | 1d10 piercing | 18 lb. | Ammunition (range 100/400), heavy, loading, two-handed |
| Longbow | 50 gp | 1d8 piercing | 2 lb. | Ammunition (range 150/600), heavy, two-handed |
| Net | 1 gp | — | 3 lb. | Special, thrown (range 5/15) |

### 12.5 Adventuring gear relevant to play (short)

All from SRD 5.1, Adventuring Gear, pp. 66–68, unless noted.

- **Acid (vial)**: "make a ranged attack against a creature or object, treating the acid as an improvised weapon. On a hit, the target takes 2d6 acid damage." (p. 66)
- **Alchemist's fire**: "On a hit, the target takes 1d4 fire damage at the start of each of its turns. A creature can end this damage by using its action to make a DC 10 Dexterity check to extinguish the flames." (p. 66)
- **Antitoxin**: "gains advantage on saving throws against poison for 1 hour." (p. 66)
- **Ball bearings**: "A creature moving across the covered area must succeed on a DC 10 Dexterity saving throw or fall prone." (p. 67)
- **Caltrops**: "Any creature that enters the area must succeed on a DC 15 Dexterity saving throw or stop moving this turn and take 1 piercing damage." (p. 67)
- **Crowbar**: "Using a crowbar grants advantage to Strength checks where the crowbar's leverage can be applied." (p. 67)
- **Healer's kit**: ten uses; stabilizes with no check (4.27). (p. 67)
- **Holy water**: "If the target is a fiend or undead, it takes 2d6 radiant damage." (p. 67)
- **Hunting trap**: "must succeed on a DC 13 Dexterity saving throw or take 1d4 piercing damage and stop moving." (p. 67)
- **Lock**: "a creature proficient with thieves' tools can pick this lock with a successful DC 15 Dexterity check." (p. 68)
- **Manacles**: "Escaping the manacles requires a successful DC 20 Dexterity check. Breaking them requires a successful DC 20 Strength check." (p. 68)
- **Oil (flask)**: "If the target takes any fire damage before the oil dries (after 1 minute), the target takes an additional 5 fire damage from the burning oil." (p. 68)
- **Poison, basic**: "A creature hit by the poisoned weapon or ammunition must make a DC 10 Constitution saving throw or take 1d4 poison damage." (p. 68)
- **Potion of healing**: "regains 2d4 + 2 hit points. Drinking or administering a potion takes an action." (p. 68)
- **Ram, portable**: "you gain a +4 bonus on the Strength check. One other character can help you use the ram, giving you advantage on this check." (p. 68)
- **Rope**: "has 2 hit points and can be burst with a DC 17 Strength check." (p. 68)
- **Chain**: "has 10 hit points. It can be burst with a successful DC 20 Strength check." (p. 67)
- **Tinderbox**: "Using it to light a torch—or anything else with abundant, exposed fuel—takes an action. Lighting any other fire takes 1 minute." (p. 68)
- **Quiver**: "A quiver can hold up to 20 arrows." (p. 68)

**Equipment packs** (SRD 5.1, Equipment Packs, p. 70)

> Burglar's Pack (16 gp). Includes a backpack, a bag of 1,000 ball bearings, 10 feet of string, a bell, 5 candles, a crowbar, a hammer, 10 pitons, a hooded lantern, 2 flasks of oil, 5 days rations, a tinderbox, and a waterskin. The pack also has 50 feet of hempen rope strapped to the side of it.

> Dungeoneer's Pack (12 gp). Includes a backpack, a crowbar, a hammer, 10 pitons, 10 torches, a tinderbox, 10 days of rations, and a waterskin. The pack also has 50 feet of hempen rope strapped to the side of it.

> Explorer's Pack (10 gp). Includes a backpack, a bedroll, a mess kit, a tinderbox, 10 torches, 10 days of rations, and a waterskin. The pack also has 50 feet of hempen rope strapped to the side of it.

### 12.6 Carrying capacity

Carrying capacity = Str × 15 lb. You can push, drag or lift up to Str × 30 lb. Over capacity, speed is 5 ft.

> Carrying Capacity. Your carrying capacity is your Strength score multiplied by 15. This is the weight (in pounds) that you can carry

(SRD 5.1, Using Ability Scores — Lifting and Carrying, p. 79)

> Push, Drag, or Lift. You can push, drag, or lift a weight in pounds up to twice your carrying capacity (or 30 times your Strength score). While pushing or dragging weight in excess of your carrying capacity, your speed drops to 5 feet.

(SRD 5.1, Using Ability Scores — Lifting and Carrying, p. 80)

> For each size category above Medium, double the creature's carrying capacity and the amount it can push, drag, or lift. For a Tiny creature, halve these weights.

(SRD 5.1, Using Ability Scores — Size and Strength, p. 80)

Variant encumbrance (optional): more than 5 × Str is encumbered (−10 ft.). More than 10 × Str is heavily encumbered (−20 ft., and disadvantage on Str/Dex/Con checks, attacks and saves). Under this variant the armor Strength requirement (12.2) is ignored.

> When you use this variant, ignore the Strength column of the Armor table. If you carry weight in excess of 5 times your Strength score, you are encumbered, which means your speed drops by 10 feet. If you carry weight in excess of 10 times your Strength score, up to your maximum carrying capacity, you are instead heavily encumbered, which means your speed drops by 20 feet and you have disadvantage on ability checks, attack rolls, and saving throws that use Strength, Dexterity, or Constitution.

(SRD 5.1, Using Ability Scores — Variant: Encumbrance, p. 80)

---

## 13. Monsters

### 13.1 Stat block anatomy

A stat block lists: size, type (with tags), alignment, Armor Class, Hit Points, Speed, the six ability scores, Saving Throws, Skills, Vulnerabilities/Resistances/Immunities, Senses (including passive Perception), Languages, Challenge, Special Traits, Actions, Reactions, and Legendary Actions where present. (SRD 5.1, Monsters, pp. 254–260)

> A monster that wears armor or carries a shield has an Armor Class (AC) that takes its armor, shield, and Dexterity into account. Otherwise, a monster's AC is based on its Dexterity modifier and natural armor, if any.

(SRD 5.1, Monsters — Armor Class, p. 255)

Monster HP = size-based Hit Dice + (Con modifier × number of Hit Dice).

**Hit Dice by Size** (SRD 5.1, p. 256)

| Monster size | Hit Die | Average HP per die |
| --- | --- | --- |
| Tiny | d4 | 2½ |
| Small | d6 | 3½ |
| Medium | d8 | 4½ |
| Large | d10 | 5½ |
| Huge | d12 | 6½ |
| Gargantuan | d20 | 10½ |

> Its Constitution modifier is multiplied by the number of Hit Dice it possesses, and the result is added to its hit points. For example, if a monster has a Constitution of 12 (+1 modifier) and 2d8 Hit Dice, it has 2d8 + 2 hit points (average 11).

(SRD 5.1, Monsters — Hit Points, p. 256)

Skills: ability modifier + CR proficiency, sometimes doubled.

> A skill bonus is the sum of a monster's relevant ability modifier and its proficiency bonus, which is determined by the monster's challenge rating

(SRD 5.1, Monsters — Skills, p. 256)

Senses list passive Perception.

> The Senses entry notes a monster's passive Wisdom (Perception) score, as well as any special senses the monster might have.

(SRD 5.1, Monsters — Senses, p. 257)

A monster is assumed proficient with its own armor, weapons and tools.

> Assume that a creature is proficient with its armor, weapons, and tools. If you swap them out, you decide whether the creature is proficient with its new equipment.

(SRD 5.1, Monsters — Armor, Weapon, and Tool Proficiencies, p. 257)

Type and tags: there are 14 types (aberrations, beasts, celestials, constructs, dragons, elementals, fey, fiends, giants, humanoids, monstrosities, oozes, plants, undead). Neither types nor tags have rules of their own. (pp. 254–255)

> The game includes the following monster types, which have no rules of their own.

(SRD 5.1, Monsters — Type, p. 254)

> The tags have no rules of their own, but something in the game, such as a magic item, might refer to them.

(SRD 5.1, Monsters — Tags, p. 255)

Speed: every monster has a walking speed (0 if it has no ground movement), and may have burrow, climb, fly or swim speeds.

> All creatures have a walking speed, simply called the monster's speed. Creatures that have no form of ground-based locomotion have a walking speed of 0 feet.

(SRD 5.1, Monsters — Speed, p. 256)

> A monster that has a burrowing speed can use that speed to move through sand, earth, mud, or ice. A monster can't burrow through solid rock unless it has a special trait that allows it to do so.

(SRD 5.1, Monsters — Speed: Burrow, p. 256)

> A monster that has a climbing speed can use all or part of its movement to move on vertical surfaces. The monster doesn't need to spend extra movement to climb.

(SRD 5.1, Monsters — Speed: Climb, p. 256)

> A monster that has a flying speed can use all or part of its movement to fly. Some monsters have the ability to hover, which makes them hard to knock out of the air (as explained in the rules on flying in the Player's Handbook). Such a monster stops hovering when it dies.

(SRD 5.1, Monsters — Speed: Fly, p. 256)

> A monster that has a swimming speed doesn't need to spend extra movement to swim.

(SRD 5.1, Monsters — Speed: Swim, p. 256)

Special senses (darkvision and truesight match 7.5):

> If a monster is naturally blind, it has a parenthetical note to this effect, indicating that the radius of its blindsight defines the maximum range of its perception.

(SRD 5.1, Monsters — Senses: Blindsight, p. 257)

> A monster with tremorsense can detect and pinpoint the origin of vibrations within a specific radius, provided that the monster and the source of the vibrations are in contact with the same ground or substance. Tremorsense can't be used to detect flying or incorporeal creatures.

(SRD 5.1, Monsters — Senses: Tremorsense, p. 257)

Languages and telepathy: "A "—" indicates that a creature neither speaks nor understands any language." (p. 257). Telepathy lets a monster talk mentally within a range to a creature that understands at least one language; it can't be started while the monster is incapacitated (p. 257).

Attack entries: a "target" can be a creature or an object. Damage is shown as an average and as dice, and the GM may use either.

> Hit. Any damage dealt or other effects that occur as a result of an attack hitting a target are described after the "Hit" notation. You have the option of taking average damage or rolling the damage; for this reason, both the average damage and the die expression are presented.

(SRD 5.1, Monsters — Melee and Ranged Attacks, p. 259)

> Creature vs. Target. The target of a melee or ranged attack is usually either one creature or one target, the difference being that a "target" can be a creature or an object.

(SRD 5.1, Monsters — Melee and Ranged Attacks, p. 259)

> Miss. If an attack has an effect that occurs on a miss, that information is presented after the "Miss:" notation.

(SRD 5.1, Monsters — Melee and Ranged Attacks, p. 259)

> If a monster can do something special with its reaction, that information is contained here. If a creature has no special reaction, this section is absent.

(SRD 5.1, Monsters — Reactions, p. 259)

A monster's action can be one from its stat block, or a common action such as Dash or Hide.

> When a monster takes its action, it can choose from the options in the Actions section of its stat block or use one of the actions available to all creatures, such as the Dash or Hide action

(SRD 5.1, Monsters — Actions, p. 259)

Limited use: X/Day uses come back on a long rest. "Recharge X–Y" means roll a d6 at the start of each of the monster's turns; a short or long rest also recharges it.

> At the start of each of the monster's turns, roll a d6. If the roll is one of the numbers in the recharge notation, the monster regains the use of the special ability. The ability also recharges when the monster finishes a short or long rest.

(SRD 5.1, Monsters — Limited Usage, p. 259)

> X/Day. The notation "X/Day" means a special ability can be used X number of times and that a monster must finish a long rest to regain expended uses.

(SRD 5.1, Monsters — Limited Usage, p. 259)

> Recharge after a Short or Long Rest. This notation means that a monster can use a special ability once and then must finish a short or long rest to use it again.

(SRD 5.1, Monsters — Limited Usage, p. 259)

Monster ammunition: assume 2d4 thrown and 2d10 projectiles.

> You can assume that a monster has 2d4 pieces of ammunition for a thrown weapon attack, and 2d10 pieces of ammunition for a projectile weapon such as a bow or crossbow.

(SRD 5.1, Monsters — Ammunition, p. 259)

### 13.2 Multiattack

Multiattack can't be used for an opportunity attack.

> A creature that can make multiple attacks on its turn has the Multiattack action. A creature can't use Multiattack when making an opportunity attack, which must be a single melee attack.

(SRD 5.1, Monsters — Multiattack, p. 259)

### 13.3 Proficiency bonus by challenge rating

**Proficiency Bonus by Challenge Rating** (SRD 5.1, p. 256)

| CR | Proficiency bonus |
| --- | --- |
| 0–4 (incl. 1/8, 1/4, 1/2) | +2 |
| 5–8 | +3 |
| 9–12 | +4 |
| 13–16 | +5 |
| 17–20 | +6 |
| 21–24 | +7 |
| 25–28 | +8 |
| 29–30 | +9 |

### 13.4 Challenge rating and XP

> An appropriately equipped and well-rested party of four adventurers should be able to defeat a monster that has a challenge rating equal to its level without suffering any deaths.

(SRD 5.1, Monsters — Challenge, p. 258)

> Monsters with a challenge rating of 0 are insignificant except in large numbers; those with no effective attacks are worth no experience points, while those that have attacks are worth 10 XP each.

(SRD 5.1, Monsters — Challenge, p. 258)

> Typically, XP is awarded for defeating the monster, although the GM may also award XP for neutralizing the threat posed by the monster in some other manner.

(SRD 5.1, Monsters — Experience Points, p. 258)

> Unless something tells you otherwise, a monster summoned by a spell or other magical ability is worth the XP noted in its stat block.

(SRD 5.1, Monsters — Experience Points, p. 258)

> Monsters that are significantly weaker than 1st-level characters have a challenge rating lower than 1. … Some monsters present a greater challenge than even a typical 20th-level party can handle. These monsters have a challenge rating of 21 or higher and are specifically designed to test player skill.

(SRD 5.1, Monsters — Challenge, p. 258)

**Experience Points by Challenge Rating** (SRD 5.1, p. 258)

| CR | XP | CR | XP |
| --- | --- | --- | --- |
| 0 | 0 or 10 | 14 | 11,500 |
| 1/8 | 25 | 15 | 13,000 |
| 1/4 | 50 | 16 | 15,000 |
| 1/2 | 100 | 17 | 18,000 |
| 1 | 200 | 18 | 20,000 |
| 2 | 450 | 19 | 22,000 |
| 3 | 700 | 20 | 25,000 |
| 4 | 1,100 | 21 | 33,000 |
| 5 | 1,800 | 22 | 41,000 |
| 6 | 2,300 | 23 | 50,000 |
| 7 | 2,900 | 24 | 62,000 |
| 8 | 3,900 | 25 | 75,000 |
| 9 | 5,000 | 26 | 90,000 |
| 10 | 5,900 | 27 | 105,000 |
| 11 | 7,200 | 28 | 120,000 |
| 12 | 8,400 | 29 | 135,000 |
| 13 | 10,000 | 30 | 155,000 |

### 13.5 Legendary and lair actions (brief)

Legendary actions happen one at a time, at the end of another creature's turn, and come back at the start of the creature's own turn. They can't be used while incapacitated, or while surprised before the creature's first turn. Lair actions happen on initiative count 20 and lose ties.

> Only one legendary action option can be used at a time and only at the end of another creature's turn. A creature regains its spent legendary actions at the start of its turn. It can forgo using them, and it can't use them while incapacitated or otherwise unable to take actions. If surprised, it can't use them until after its first turn in the combat.

(SRD 5.1, Monsters — Legendary Actions, p. 260)

> On initiative count 20 (losing all initiative ties), it can use one of its lair action options. It can't do so while incapacitated or otherwise unable to take actions. If surprised, it can't use one until after its first turn in the combat.

(SRD 5.1, Monsters — Lair Actions, p. 260)

---

## 14. Encounter building

**Not in SRD 5.1.** The SRD has no encounter-building rules: no XP thresholds by character level, no encounter multipliers, no difficulty bands (easy/medium/hard/deadly), no adventuring-day budget. Searches of the extracted text for "XP Threshold", "encounter multiplier", "encounter difficulty" and "Creating a Combat Encounter" found nothing. "Adventuring day" occurs once, in the Resting introduction ("Adventurers can take short rests in the midst of an adventuring day and a long rest to end the day", p. 87), with no XP budget. The only guidance is the CR sentence quoted in 13.4 (a party of four of level N against one monster of CR N). Nothing from the DMG is added here.

---

## Not in SRD 5.1

These scope items are not in the SRD 5.1 PDF. Nothing below was filled in from memory.

- **Encounter-building rules** (XP thresholds by level, multipliers, difficulty bands, adventuring-day XP). See Section 14.
- **The Path of the Totem Warrior.** The Barbarian's Primal Path names it (p. 9), but the SRD gives no text for it. Only the Berserker is described.
- **Backgrounds other than Acolyte.**
- **Feats other than Grappler.**
- **An auto-success or auto-fail rule for a natural 20 or 1 on ability checks or saving throws.** It applies only to attack rolls (4.9) and death saves (4.26).
- **A general rounding rule** (for example, when resistance halves an odd number). A search of the full extracted text found none. Individual rules state their own rounding ("round down" for ability modifiers, p. 76; "rounded up" for fixed HP, p. 56; "round up" for the Champion's Remarkable Athlete, p. 25). The PHB's general "round down" rule is not part of SRD 5.1. See D10.
- **A general unarmored AC (10 + Dex) for characters.** Monster AC and class Unarmored Defense are covered; a search of the full extracted text found no plain 10 + Dex baseline for an unarmored character (see 12.3).
- **XP thresholds in the cross-check JSON.** The six JSON files used have no XP table, so the XP table (8.1) was checked against the PDF only.

## PDF/JSON disagreements

The PDF wins in every case. Weapons, armor, skills, conditions, class hit dice, proficiencies, saves, skill lists, starting equipment, the Barbarian Rages and Rage Damage columns, the Rogue Sneak Attack column, the Fighter features, and the proficiency bonus by level all match. The differences:

1. **Rogue `ability_score_bonuses` in `5e-SRD-Levels.json` is wrong at levels 11–20.** The PDF puts Rogue ASIs at 4, 8, 10, 12, 16 and 19 (p. 40), so the running count should be 1, 1, 1, 1, 2, 2, 3 (levels 4–10), then 3 (11), 4 (12–15), 5 (16–18) and 6 (19–20). The JSON has 11: 2, 12: 4, 13: 3, 14: 3, 15: 3, 16: 5, 17: 4, 18: 4, 19: 6, 20: 5. That count goes down at times, so it is not a valid running total. The JSON `features` list (ASI at 4, 8, 10, 12, 16, 19) does match the PDF. Use the PDF and the features list, not this counter.
2. **Weapon "Monk" property.** The JSON tags club, dagger, handaxe, javelin, light hammer, mace, quarterstaff, sickle, spear and shortsword with a "Monk" property. The PDF Weapons table has no such property. Monk weapons are defined in the Monk's Martial Arts feature text instead (p. 26).
3. **Barbarian 20th-level rages.** The PDF says "Unlimited"; the JSON stores `rage_count: 9999`. This is a difference of encoding only.
4. **Small wording and encoding differences, same values.** The PDF says "Action Surge (one use)" and the JSON "Action Surge (1 use)". The JSON gives the sling weight as `0`, where the PDF shows "—". The JSON writes "no Strength requirement" as `str_minimum: 0`, where the PDF shows "—". The JSON names some armor "Padded Armor" and "Half Plate Armor", where the PDF says "Padded" and "Half plate". The JSON gives the net a melee-style `range` of 5/15, where the PDF says "Special, thrown (range 5/15)".

---

## Design deviations to decide

Each item sets a v1 design choice (from `docs/Pi Dungeon Master — Design Document.md`) against the SRD rule it changes or leaves out. The owner decides each one; this file decides none.

### D1. Theater of the mind: no grid, distance or movement

v1 tracks no positions, so every rule keyed to feet, reach or movement needs a ruling.

- **Ranged attacks in melee.** "you have disadvantage on the attack roll if you are within 5 feet of a hostile creature who can see you and who isn't incapacitated." (p. 95). Decide: apply it whenever the attacker is "engaged", never, or let Claude declare it?
- **Range bands.** "Your attack roll has disadvantage when your target is beyond normal range, and you can't attack a target beyond the long range." (p. 95). Decide whether the engine models normal and long range at all.
- **Prone.** "An attack roll against the creature has advantage if the attacker is within 5 feet of the creature. Otherwise, the attack roll has disadvantage." (p. 359). The engine needs a melee/ranged proxy for "within 5 feet". Same for **Paralyzed** and **Unconscious**: "Any attack that hits the creature is a critical hit if the attacker is within 5 feet of the creature." (pp. 358–359).
- **Reach.** "This weapon adds 5 feet to your reach when you attack with it, as well as when determining your reach for opportunity attacks with it." (p. 65). Without distance, reach does nothing.
- **Opportunity attacks.** "You can make an opportunity attack when a hostile creature that you can see moves out of your reach." (p. 95). Decide: drop them, or trigger them on a declared "flee/withdraw" intent?
- **Disengage.** "your movement doesn't provoke opportunity attacks for the rest of the turn." (p. 93). It does nothing unless opportunity attacks exist. This also affects the Rogue's Cunning Action (p. 40).
- **Dash.** "you gain extra movement for the current turn." (p. 93). Decide whether Dash means anything (for example, escape or closing distance as a narrative flag).
- **Cover.** "A target with half cover has a +2 bonus to AC and Dexterity saving throws. … three-quarters cover has a +5 bonus" (p. 96). Decide whether Claude may declare cover through a tool argument, or cover is ignored.
- **Help on an attack.** "you can aid a friendly creature in attacking a creature within 5 feet of you." (p. 93).
- **Grapple and shove.** "must be within your reach" and "push it 5 feet away from you" (pp. 95–96). Pushing has no effect without positions.
- **Speed-based effects.** Fast Movement "+10 feet" (p. 9), exhaustion "Speed halved" (p. 358), heavy armor "reduces the wearer's speed by 10 feet" (p. 63), and grappled/restrained "speed becomes 0" (pp. 358–359). Standing from prone "costs an amount of movement equal to half your speed" (p. 91). Decide which of these the engine still enforces as flags. (Speed 0 still matters: it ends Dodge, and it stops a prone creature standing.)
- **Protection fighting style.** It targets an attack against "a target other than you that is within 5 feet of you" (p. 24). In a solo game with no ally it rarely applies.

### D2. Engine plays monsters with Multiattack-or-best-attack against the Character

- The SRD lets a monster "use one of the actions available to all creatures, such as the Dash or Hide action" (p. 259). Simple tactics drop Dash, Disengage, Dodge, Help, Hide, Ready and grapple/shove.
- **Reactions and special traits.** Stat-block Reactions (p. 259), Recharge abilities ("At the start of each of the monster's turns, roll a d6", p. 259), X/Day abilities, and legendary and lair actions (p. 260) need to be handled or explicitly ignored.
- **Opportunity attacks** by monsters "must be a single melee attack" and can't use Multiattack (p. 259). This only matters if D1 keeps opportunity attacks.
- **Group initiative.** "The GM makes one roll for an entire group of identical creatures, so each member of the group acts at the same time." (p. 90). Decide: one roll per group (SRD) or one per Combatant ("Goblin 1", "Goblin 2").
- **Average versus rolled monster damage.** "You have the option of taking average damage or rolling the damage" (p. 259). The design says the engine rolls; that is allowed.
- **Monsters at 0 HP** "die the instant it drops to 0 hit points" (p. 98), unless they are important NPCs. Decide whether named villains make death saves.
- **Knocking out.** "When an attacker reduces a creature to 0 hit points with a melee attack, the attacker can knock the creature out." (p. 98). Decide whether the player's attack tool takes a non-lethal flag, and whether monsters ever knock the Character out instead of killing.

### D3. Ammunition not tracked

- "You can use a weapon that has the ammunition property to make a ranged attack only if you have ammunition to fire from the weapon. Each time you attack with the weapon, you expend one piece of ammunition. … At the end of the battle, you can recover half your expended ammunition" (p. 64). Not tracking ammunition means the Character never runs out. Starting kits list exact counts ("20 arrows", "20 bolts", "quiver of 20 arrows", pp. 24, 39).
- **Loading is a separate rule from tracking and should still apply.** "you can fire only one piece of ammunition from it when you use an action, bonus action, or reaction to fire it, regardless of the number of attacks you can normally make." (p. 65). A 5th-level Fighter with a crossbow gets one shot per action, not two.
- Monster ammunition: "2d4 pieces of ammunition for a thrown weapon attack, and 2d10 pieces of ammunition for a projectile weapon" (p. 259).
- Thrown weapons (handaxe, javelin, dagger) leave the hand when thrown. Decide whether the item is lost or recovered.

### D4. Level cap 5 with a fixed subclass

- XP keeps building past 6,500 (level 5); level 6 needs 14,000 (p. 56). Decide what happens to XP past the cap (for example, store it but don't level).
- The SRD makes some choices the player's: Fighting Style "Choose one of the following options" (p. 24), Expertise "choose two of your skill proficiencies" (p. 39), and ASI "increase one ability score of your choice by 2, or … two ability scores of your choice by 1" (pp. 9, 25, 40). With fixed templates, these must be set in the template, including the 4th-level ASI.
- The Barbarian's Primal Path offers Berserker or Totem Warrior (p. 9). Only the Berserker is in the SRD, so a fixed Berserker loses nothing from the SRD.
- Optional feats ("you can forgo taking that feature to take a feat", p. 75). Grappler is the only one. Decide whether it is excluded.
- **Frenzy has a built-in cost.** "When your rage ends, you suffer one level of exhaustion" (p. 9). Exhaustion clears only one level per long rest with food and drink (p. 358). A fixed Berserker template forces this trade-off on the player whenever they choose to frenzy; Frenzy is optional ("you can go into a frenzy").

### D5. Average HP per level

Not a deviation: the SRD offers it. "Alternatively, you can use the fixed value shown in your class entry, which is the average result of the die roll (rounded up)." (p. 56). Values: Barbarian 7, Fighter 6, Rogue 5. Two points to implement:

- Raising Con is applied backwards: "your hit point maximum increases by 1 for each level you have attained." (p. 56)
- A Hill Dwarf adds +1 per level: "Your hit point maximum increases by 1, and it increases by 1 every time you gain a level." (p. 4)

### D6. Death saves rolled immediately at 0 HP outside an encounter

- SRD: "Whenever you start your turn with 0 hit points, you must make a special saving throw" (p. 98). Death saves are tied to turns. Rolling them at once outside combat is a deviation. It also raises a question the SRD doesn't answer: how many to roll, and how fast. Three failures need at least two rolls (a natural 1 counts double).
- A stable creature "regains 1 hit point after 1d4 hours" (p. 98). Decide whether out-of-combat dying always resolves to stable or dead in one tool call, followed by the 1d4-hour wake-up.
- A Half-Orc's Relentless Endurance ("you can drop to 1 hit point instead", p. 7) and the instant-death check (p. 98) must run before any death save, in and out of combat.
- Damage at 0 HP adds failures (p. 98). This applies to falling or suffocation damage outside combat too.

### D7. Sneak Attack triggers only via advantage (no allies)

- SRD: "You don't need advantage on the attack roll if another enemy of the target is within 5 feet of it, that enemy isn't incapacitated, and you don't have disadvantage on the attack roll." (p. 39). Dropping this clause is a deviation. It matters if the story ever gives the Character an NPC companion who is fighting the target.
- Advantage that is cancelled by disadvantage gives no Sneak Attack. With both, "you are considered to have neither of them" (p. 76).
- "The attack must use a finesse or a ranged weapon." (p. 39)
- "Once per turn", not once per round (p. 39). A Rogue's reaction attack (an opportunity attack, if D1 keeps them) on a monster's turn could qualify again.
- On a critical hit, Sneak Attack dice are doubled too (p. 97).
- Without allies, the Character's sources of advantage are: an unseen attacker or hidden status (p. 94), a target that is prone (within 5 ft.), restrained, blinded, paralyzed, stunned or unconscious (pp. 358–359), a monster's Reckless-style penalty, or Inspiration (p. 60). Cunning Action Hide (p. 40) is the Rogue's main solo tool, and "if you come out of hiding and approach a creature, it usually sees you" (pp. 80–81). Decide how the engine rules a Hide then attack.

### D8. Engine makes every roll

The SRD gives the roller several choices. Each needs a default, or a tool argument for Claude to pass:

- **Lucky**: "you can reroll the die and must use the new roll" (p. 4), and with advantage or disadvantage "You choose which one" to reroll (p. 76). The best default is to always reroll the 1.
- **Great Weapon Fighting**: "you can reroll the die" on 1 or 2 (p. 24). The best default is always.
- **Reckless Attack**: "you can decide to attack recklessly" (p. 9). This needs a flag on `attack`.
- **Frenzy**: "you can go into a frenzy when you rage" (p. 9). This needs a flag on `use_feature("Rage")`.
- **Finesse**: "you use your choice of your Strength or Dexterity modifier" (p. 64). The default is the higher modifier.
- **Spending Hit Dice**: "The player can decide to spend an additional Hit Die after each roll." (p. 87). `rest(kind)` needs a count or a target HP.
- **Temporary HP**: "you decide whether to keep the ones you have or to gain the new ones" (p. 98). The default is the higher value.
- **Knock out**: "the attacker can make this choice" (p. 98).
- **Grapple and shove defence**: "the target chooses the ability to use" (pp. 95–96). The engine picks the defender's better of Athletics and Acrobatics.
- **Initiative ties**: "the players decide the order among their tied characters" (p. 90). Use the optional d20 roll-off, or let the PC go first.
- **Reactions**: Uncanny Dodge "you can use your reaction to halve the attack's damage" (p. 40), plus Protection, opportunity attacks and Ready (pp. 24, 93, 95). These happen on a monster's turn, inside `resolve_npc_turns()`, when the player can't be asked. Decide auto-use rules (for example, Uncanny Dodge on the first hit each round). Note that the design names attacks and the bonus action as enforced per turn but says nothing about the reaction (one per round, reset at the start of your turn, p. 91).
- **Action Surge**: "you can take one additional action" (p. 25). The engine must allow a second Attack action, with Extra Attack again, on that turn.
- **Inspiration** is awarded by the GM (p. 60). Decide whether v1 has it at all.

### D9. Surprise is missing from the encounter flow

The design's `start_encounter(monsters)` rolls initiative but doesn't mention surprise. SRD: "If you're surprised, you can't move or take an action on your first turn of the combat, and you can't take a reaction until that turn ends." (p. 90). Surprise is decided by Stealth against passive Perception. Decide whether `start_encounter` takes a surprise argument.

### D10. Rounding

SRD 5.1 has no general rounding rule (see Not in SRD 5.1). Halving comes up in resistance, Uncanny Dodge, exhaustion level 4, speed halving and long-rest Hit Dice recovery ("half of the character's total number of them (minimum of one die)", p. 87). Decide the engine's rounding direction. The SRD's stated directions for halving are mixed: "rounded down" on pp. 12, 20, 31, 58, 268, 337 and 339, but "rounded up" or "round up" on pp. 21, 25, 48, 53, 56 and 345. Of the two rules that split damage in half, one rounds down (cloaker, p. 268) and one rounds up (shield guardian, p. 345). The SRD makes neither direction a general rule.

## Rulings (decided 2026-11-17)

The owner's decisions on D1–D10. Where a ruling departs from a quoted rule above, the ruling wins in the engine.

- **R1 (D1, within 5 feet).** Melee attacks count as within 5 feet; ranged attacks do not. This drives prone, paralyzed and unconscious. The "ranged attack in close combat" disadvantage is dropped.
- **R2 (D1, movement).** Opportunity attacks, Disengage, Dash, reach and speed changes have no mechanical effect. Fleeing is narrated by Claude, followed by `end_encounter`. Speed 0 (grappled, restrained) is kept only as "cannot stand from prone".
- **R3 (D1, cover).** `attack` takes an optional `cover` (`half` +2 AC, `three_quarters` +5 AC) for the Character's attacks. Monster attacks on the Character ignore cover in M1.
- **R4 (D2, monsters).** Monsters use only attack actions and Multiattack. Reactions, Recharge, X/Day, legendary and lair actions are ignored. Initiative is rolled per Combatant. Monsters die at 0 HP. The Character's melee `attack` takes `nonlethal`; monsters never knock the Character out.
- **R5 (D3, ammunition).** Tracked: each ranged attack spends one piece from inventory and fails with none; `end_encounter` recovers half, rounded down. Thrown weapons are recovered at `end_encounter`. Loading is enforced.
- **R6 (D4, templates).** Fighter: Fighting Style Defense, +2 Str at level 4. Rogue: Expertise in Stealth and thieves' tools, +2 Dex at level 4. Barbarian: Berserker, +2 Str at level 4. No feats. XP past level 5 is stored; levels stop at 5. Frenzy is opt-in through `use_feature("rage", frenzy=true)`.
- **R7 (D6, dying outside an Encounter).** One engine step: instant-death check, Relentless Endurance, then death saves until stable or dead. If stable, the Character stays unconscious, 1d4 hours are rolled, and HP becomes 1.
- **R8 (D7, Sneak Attack).** The "another enemy within 5 feet" clause is dropped (no companions in v1). A `hide()` tool rolls Stealth against the highest passive Perception among conscious Combatants; success makes the Character hidden, the next attack has advantage, and attacking ends hidden. Hide costs the action, or the bonus action through Cunning Action.
- **R9 (D8, choices).** Lucky and Great Weapon Fighting always reroll. Finesse uses the higher modifier. Temporary HP keeps the higher value. Initiative ties go to the Character. A grapple or shove defender uses its better skill. Reckless Attack is a flag on `attack`. Action Surge grants a full second Attack action, Extra Attack included. The Character has one reaction per Combat round; Uncanny Dodge is used on the first hit each round. No Inspiration in v1.
- **R10 (D9, surprise).** `start_encounter` takes `surprise: none | character | monsters`, set by Claude from a prior Stealth check.
- **R11 (D10, rounding).** Round down unless the specific rule says round up. This is a house ruling (the Player's Handbook convention), not SRD text.
- **R12 (races).** Templates fix the race: Human Fighter, Lightfoot Halfling Rogue, Half-Orc Barbarian. Player-chosen races wait for the v2 character builder.
- **R13 (Dodge).** A `dodge()` tool: until the Character's next turn, attacks against it have disadvantage and its Dex saves have advantage; it ends if the Character is incapacitated.
- **R14 (two-weapon fighting).** `attack` takes `offhand`: both weapons must be light, it costs the bonus action, and no positive ability modifier is added to damage.
- **R15 (grapple and shove).** `contest` takes an optional `effect` (`grapple`, `shove_prone`, `escape`); on a win the engine sets or clears the condition.
- **R16 (M2, imported Stat blocks).** A monster joins an Encounter only if it has an action with both an attack bonus and damage. Damage given as a choice uses its first option. A Multiattack part with no attack bonus or no damage is skipped, and a non-numeric count ("Number of Heads", "1d4") plays as one attack. Proposed during M2 (issue #5); awaiting the owner's confirmation.
- **R17 (M4, equip and unequip).** Only armor, a shield and weapons can be equipped. Equipping armor takes off any other armor worn; a shield and any number of weapons may be equipped together. Hands are not tracked, because `attack` does not require an equipped weapon. Gear can't change during an Encounter. Proposed during M4 (issue #9); awaiting owner confirmation.
- **R18 (M6b, caster Templates and slots).** Proposed (issue #29); awaiting owner confirmation. Level 1 Human Wizard (no subclass until level 2) and Human Life Domain Cleric, each with spells known by SRD slug. `spell_slots` rows hold max and used per spell level from the SRD full-caster table (levels 1-5; `grant_xp` grows the maximums). A long rest restores every slot. A short rest restores none, except the Wizard's Arcane Recovery: once per day, up to half the Wizard's level rounded up in combined slot level, and the engine picks the highest slots that fit rather than asking. Concentration and ritual casting are not modelled.
- **R19 (M6b, `cast_spell`).** Proposed (issue #31); awaiting owner confirmation. The Character casts a cantrip or a prepared spell (a Wizard's spellbook-only spells are not castable). A leveled spell spends a slot of `slot_level` (default the spell's level, never lower; no other upcasting rules). In an Encounter the casting time costs the action, bonus action or reaction (casting times longer than that are refused); outside one it costs nothing. Casting ability is Int (Wizard) or Wis (Cleric): spell attack = proficiency + modifier, save DC = 8 + that. The engine resolves spells with a spell attack (crit on 20 doubles the dice), a saving throw (damage once for every target; half or none on a success per the SRD record) or neither (Magic Missile, one target), plus healing (the SRD dice, "MOD" is the casting modifier; Disciple of Life is not modelled). Cantrip dice scale by Character level, spell dice by slot level. Spell attacks ignore cover and Frightened. Any other effect (including Sleep, conditions and buffs such as Shield and Mage Armor) spends the slot and returns the SRD text plus the DC and attack bonus for Claude to narrate; Claude applies lasting effects with `set_condition` and the other tools. An invalid cast (unknown or unprepared spell, no slot, no action left, bad target) returns an error and changes nothing.
- **R20 (Steady Nerve).** Proposed (issue #42); awaiting owner confirmation. Not an SRD mechanic, and distinct from the Lucky feat (§10, R9). Every Character has it: once per long rest, a failed saving throw is rerolled and the new roll stands even if it is lower. It is automatic, never asked of the player (as Lucky always rerolls, R9): the first failed save after a long rest spends the use, with advantage or disadvantage and the bonus unchanged. A short rest does not restore it; a long rest does. It applies to the Character's saving throws only, never to Combatants, ability checks or attack rolls. A save that is an automatic failure (§5) has no roll and spends nothing. Death saving throws (§4.26) are saving throws, so it applies to them too: a failed death save is rerolled and the new roll stands, a natural 1 included. The sheet lists it as `steady_nerve`, `ready` or `spent`.
