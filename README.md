# D-and-Deez
Computah, generate me a D&amp;D that doesn't use all my credits & turn my pi into smth that's not a smart mirror

## Build, run and test

The app runs as one Docker image, built locally on each machine (PC: linux/amd64, Raspberry Pi 5: linux/arm64, 64-bit OS).

First time on a machine:

```sh
cp .env.example .env        # then fill in ANTHROPIC_API_KEY
mkdir -p data backups       # create before the first `up`, or Docker creates them owned by root
```

Run, and after every code change or `git pull`:

```sh
docker compose up -d --build
curl -i http://localhost:8000/health   # expect 200
```

Tests run on the host, not in the image (the image has no test dependencies):

```sh
python -m venv .venv
.venv/bin/pip install -e ".[dev]"      # Windows: .venv\Scripts\pip
.venv/bin/pytest
```
