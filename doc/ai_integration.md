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
LLM_API_KEY=sk-your-default-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-3.5-turbo

# Gemini Profile
LLM_GEMINI_API_KEY=your-gemini-key
LLM_GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
LLM_GEMINI_MODEL=gemini-1.5-flash

# Claude Profile (via a proxy)
LLM_CLAUDE_API_KEY=your-claude-key
LLM_CLAUDE_BASE_URL=https://api.anthropic-proxy.com/v1
LLM_CLAUDE_MODEL=claude-3-5-sonnet
```

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
