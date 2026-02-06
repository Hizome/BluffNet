import os
import httpx
import json
from dotenv import load_dotenv

load_dotenv()

class LLMClient:
    def __init__(self):
        self.api_key = os.getenv("LLM_API_KEY")
        self.base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
        self.model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")

    async def call(self, prompt: str, system_prompt: str = "", profile: str = None) -> str:
        # Determine which variables to use
        prefix = f"LLM_{profile.upper()}_" if profile else "LLM_"
        
        api_key = os.getenv(f"{prefix}API_KEY") or os.getenv("LLM_API_KEY")
        base_url = os.getenv(f"{prefix}BASE_URL") or os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
        model = os.getenv(f"{prefix}MODEL") or os.getenv("LLM_MODEL", "gpt-3.5-turbo")

        if not api_key:
            return f'{{"action": "CHECK", "thought": "No API Key found for profile: {profile or 'default'}"}}'
        
        url = f"{base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "response_format": { "type": "json_object" },
            "temperature": 0.7
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, headers=headers, json=payload, timeout=30.0)
                response.raise_for_status()
                data = response.json()
                return data['choices'][0]['message']['content']
            except Exception as e:
                print(f"LLM API Error: {e}")
                return '{"action": "CHECK", "thought": "LLM API Error occurred."}'
