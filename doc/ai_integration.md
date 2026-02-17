# AI Integration: Multi-Profile "All-Star" Lineup

This document explains how to configure and use multiple AI providers (OpenAI, Gemini, Claude, MiniMax, etc.) simultaneously in Project BluffNet.

## Unified Interface Strategy

We use the **OpenAI Standard** as the common language. Even if you use Gemini or Claude, the code will communicate using the same format. This is achieved by either:
1.  Using an **Aggregator Gateway** (like OneAPI, NewAPI, or OpenRouter).
2.  Using our **Named Profiles** system in the backend.

## How to Configure

To have different AI models playing together, you define "Profiles" in your `.env` file. 

### 1. Define Profiles in `.env`

You can define as many profiles as you like using the prefix `LLM_{NAME}_`.

```env
# Default Profile (used if no specific profile is set)
LLM_PROVIDER=openai
LLM_API_KEY=sk-your-default-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-3.5-turbo

# Gemini Profile (OpenAI-compatible endpoint)
LLM_GEMINI_PROVIDER=openai
LLM_GEMINI_API_KEY=your-gemini-key
LLM_GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
LLM_GEMINI_MODEL=gemini-1.5-flash

# MiniMax Profile (Anthropic-compatible endpoint)
LLM_MINIMAX_PROVIDER=anthropic
LLM_MINIMAX_ANTHROPIC_API_KEY=your-minimax-key
LLM_MINIMAX_ANTHROPIC_BASE_URL=https://api.minimaxi.com/anthropic
LLM_MINIMAX_ANTHROPIC_MODEL=MiniMax-M2.5
```

Supported provider values:
- `openai`: calls `.../chat/completions`
- `anthropic`: calls `.../v1/messages` with Anthropic headers

### 2. Assign Profiles to Players

In the `backend/engine.py`, you can assign different profiles to different agents:

```python
# Player 1 uses Gemini
self.agents[0] = LLMAgent(player_id=0, profile="GEMINI")

# Player 2 uses Claude
self.agents[1] = LLMAgent(player_id=1, profile="CLAUDE")
```

## How the Code Handles It

1.  **`llm_client.py`**: When `call(profile="GEMINI", ...)` is called, it automatically looks up the environment variables with the `LLM_GEMINI_` prefix.
2.  **Standardized Response**: All profiles expect a JSON response containing `action`, `amount`, and `thought`.
3.  **One Key, Multiple Roles**: If you only have one key but want multiple AI personalities, you can use the same profile for multiple agents—the `Engine` will provide the unique `persona` of each player to the LLM during the call.

## Summary: What you need to do
1.  **Obtain Keys**: Get your API keys for the providers you want to use.
2.  **Add to `.env`**: Add them with the `LLM_{NAME}_` prefix.
3.  **Update Engine**: (Or use the upcoming Dashboard) to tell the Engine which player uses which profile name.

## Runtime API (AI vs AI)

You can switch agents without changing code.

### 1) View current lineup

```bash
curl "http://localhost:8000/config/agents?table_id=dev1"
```

### 2) Set one player to a specific model profile

```bash
curl -X POST "http://localhost:8000/config/agent?table_id=dev1" \
  -H "Content-Type: application/json" \
  -d '{"player_id":0,"agent_type":"llm","profile":"AI1"}'
```

Supported `agent_type`:
- `llm`
- `random`
- `call_station`

### 3) Switch the full table to LLM-vs-LLM

```bash
curl -X POST "http://localhost:8000/config/agents/llm_all?table_id=dev1" \
  -H "Content-Type: application/json" \
  -d '{"profiles":["AI1","AI2","AI3","AI4","AI5","AI6","AI7","AI8"]}'
```

### 4) Discover available LLM profiles (sanitized)

```bash
curl "http://localhost:8000/config/llm_profiles"
```

This endpoint returns profile diagnostics without exposing keys:
- `profile`
- `model`
- `base_url`
- `has_api_key`

### 5) Check active agent lineup with LLM diagnostics

```bash
curl "http://localhost:8000/config/agents?table_id=dev1"
```

For LLM seats, each item includes `llm` diagnostics (`model/base_url/has_api_key`).

## Stability Settings

You can tune LLM request reliability from `.env`:

```env
LLM_TIMEOUT_SEC=30
LLM_MAX_RETRIES=2
LLM_RETRY_BACKOFF_SEC=0.8
```

Behavior:
- Timeouts and transient API/network errors will retry with exponential backoff.
- If retries still fail, agent falls back to a safe JSON action (`CHECK`) and keeps the game running.

## Dashboard Workflow (No curl needed)

In `Dashboard`:
1. Set each player's `agent_type` (`llm/random/call_station`)
2. Optionally set `profile` for `llm`
3. Click `Save`

The page also shows whether that player's current LLM profile has a usable API key (`key: yes/no`).
