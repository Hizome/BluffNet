import asyncio
from dataclasses import dataclass
from threading import Lock
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from engine import Engine
from llm_client import LLMClient
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

@dataclass
class TableRuntime:
    engine: Engine
    lock: asyncio.Lock


tables: Dict[str, TableRuntime] = {}
tables_lock = Lock()


def get_table_runtime(table_id: str) -> TableRuntime:
    with tables_lock:
        runtime = tables.get(table_id)
        if runtime is None:
            engine = Engine(n_players=8)
            engine.start_new_hand()
            runtime = TableRuntime(engine=engine, lock=asyncio.Lock())
            tables[table_id] = runtime
        return runtime


get_table_runtime("default")

class PersonaConfig(BaseModel):
    player_id: int
    persona: str


class AgentConfig(BaseModel):
    player_id: int
    agent_type: str  # llm | random | call_station
    profile: Optional[str] = None


class LLMLineupConfig(BaseModel):
    profiles: Optional[List[Optional[str]]] = None


def build_agent_runtime_details(engine: Engine) -> List[Dict[str, object]]:
    details: List[Dict[str, object]] = []
    for cfg in engine.get_agent_configs():
        entry: Dict[str, object] = dict(cfg)
        is_llm = entry.get("agent_type") == "llm"
        if is_llm:
            entry["llm"] = LLMClient.resolve_profile(profile=entry.get("profile"))
        details.append(entry)
    return details

@app.get("/")
def read_root():
    return {"message": "Welcome to BluffNet AI Backend", "default_table_id": "default"}

@app.get("/status")
async def get_status(table_id: str = "default"):
    runtime = get_table_runtime(table_id)
    async with runtime.lock:
        return {
            "server_status": "online",
            "table_id": table_id,
            "pot_size": runtime.engine.pot
        }

@app.get("/state", response_model=GameState)
async def get_state(table_id: str = "default"):
    runtime = get_table_runtime(table_id)
    async with runtime.lock:
        return runtime.engine.get_state()

@app.post("/start_game")
async def start_game(table_id: str = "default"):
    runtime = get_table_runtime(table_id)
    async with runtime.lock:
        return runtime.engine.start_new_hand()


@app.post("/reset_cycle")
async def reset_cycle(table_id: str = "default"):
    runtime = get_table_runtime(table_id)
    async with runtime.lock:
        return runtime.engine.reset_cycle()

@app.post("/next_step")
async def next_step(table_id: str = "default"):
    runtime = get_table_runtime(table_id)
    async with runtime.lock:
        # Advance single step (Action or Stage change)
        return await runtime.engine.step()

@app.post("/config/persona")
async def update_persona(config: PersonaConfig, table_id: str = "default"):
    runtime = get_table_runtime(table_id)
    async with runtime.lock:
        engine = runtime.engine
        if 0 <= config.player_id < len(engine.players):
            engine.players[config.player_id].persona = config.persona
            return {
                "status": "ok",
                "table_id": table_id,
                "player_id": config.player_id,
                "new_persona": config.persona,
            }
        raise HTTPException(status_code=404, detail="Player not found")


@app.get("/config/agents")
async def get_agents_config(table_id: str = "default"):
    runtime = get_table_runtime(table_id)
    async with runtime.lock:
        return {"table_id": table_id, "agents": build_agent_runtime_details(runtime.engine)}


@app.get("/config/llm_profiles")
async def get_llm_profiles():
    return {"profiles": LLMClient.list_profiles()}


@app.post("/config/agent")
async def update_agent(config: AgentConfig, table_id: str = "default"):
    runtime = get_table_runtime(table_id)
    async with runtime.lock:
        engine = runtime.engine
        try:
            engine.set_agent_config(
                player_id=config.player_id,
                agent_type=config.agent_type,
                profile=config.profile,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {
            "status": "ok",
            "table_id": table_id,
            "player_id": config.player_id,
            "agent_type": engine.agent_types[config.player_id],
            "profile": engine.agent_profiles[config.player_id],
            "llm": LLMClient.resolve_profile(profile=engine.agent_profiles[config.player_id])
            if engine.agent_types[config.player_id] == "llm"
            else None,
        }


@app.post("/config/agents/llm_all")
async def set_all_agents_llm(config: LLMLineupConfig, table_id: str = "default"):
    runtime = get_table_runtime(table_id)
    async with runtime.lock:
        runtime.engine.set_all_agents_llm(config.profiles)
        return {"status": "ok", "table_id": table_id, "agents": build_agent_runtime_details(runtime.engine)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
