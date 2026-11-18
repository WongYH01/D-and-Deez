# D-and-Deez

Computah, generate me a D&amp;D that doesn't use all my credits & turn my pi into smth that's not a smart mirror

D and Deez is a single-player, text-based D&D 5e game that runs as a web app. Claude narrates; the app's own code is the referee and story planner.

## Features

- Play in the browser: type an action, read streamed narration, watch the character sheet update.
- Code, not the model, rolls the dice and tracks HP, conditions, XP, inventory and spell slots (SRD 5.1 rules, fantasy only).
- Pick a setting, tone and length (one-shot or short campaign), and a pre-made class to play.
- Each campaign gets a hidden plot with clues, clocks and defined endings, so the story can't dead-end. Fights are sized for one character.
- Or import a published adventure from a PDF or text file.
- Continuity across sessions: recaps, remembered NPCs and places, and recall of similar past scenes.
- One Docker image that runs on any 64-bit Linux, Windows or macOS host with Docker, such as a PC or a Raspberry Pi 5. No local LLM; Claude is called through the Anthropic API.

## What you need

- A 64-bit Linux, Windows or macOS host with Docker and Compose.
- An [Anthropic API key](https://console.anthropic.com/).

## Run it

First time on a machine:

```sh
cp .env.example .env        # then set ANTHROPIC_API_KEY in .env
mkdir -p data backups       # create before the first `up`, or Docker creates them owned by root
```

Start it, and again after every `git pull`:

```sh
docker compose up -d --build
```

Open <http://localhost:8000> (from another device, `http://<host-address>:8000`; for a Pi, its address). `curl -i http://localhost:8000/health` returns 200 when it is up.

Your campaigns are saved in `data/`, and a backup is written to `backups/` when a session ends. Optional settings (models, token budget) are in `.env.example`.
