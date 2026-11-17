from fastapi import FastAPI

app = FastAPI(title="Pi Dungeon Master")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
