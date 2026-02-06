from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from engine import Engine
from models import GameState

app = FastAPI(title="BluffNet AI Backend")

# Allow CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Game Engine (default 8 players)
engine = Engine(n_players=8)
engine.start_new_hand()

class PersonaConfig(BaseModel):
    player_id: int
    persona: str

@app.get("/")
def read_root():
    return {"message": "Welcome to BluffNet AI Backend"}

@app.get("/status")
def get_status():
    return {
        "server_status": "online",
        "pot_size": engine.pot
    }

@app.get("/state", response_model=GameState)
def get_state():
    return engine.get_state()

@app.post("/start_game")
def start_game():
    return engine.start_new_hand()

@app.post("/next_step")
async def next_step():
    # Advance single step (Action or Stage change)
    return await engine.step()

@app.post("/config/persona")
def update_persona(config: PersonaConfig):
    if 0 <= config.player_id < len(engine.players):
        engine.players[config.player_id].persona = config.persona
        return {"status": "ok", "player_id": config.player_id, "new_persona": config.persona}
    raise HTTPException(status_code=404, detail="Player not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
