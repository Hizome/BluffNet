import asyncio
import json
import os
from typing import Dict, Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

class LLMClient:
    def __init__(self):
        self.api_key = os.getenv("LLM_API_KEY")
        self.base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
        self.model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
        self.timeout = float(os.getenv("LLM_TIMEOUT_SEC", "30"))
        self.max_retries = int(os.getenv("LLM_MAX_RETRIES", "2"))
        self.retry_backoff_sec = float(os.getenv("LLM_RETRY_BACKOFF_SEC", "0.8"))

    @staticmethod
    def _fallback_response(message: str) -> str:
        return json.dumps({"action": "CHECK", "amount": 0, "thought": message}, ensure_ascii=False)

    @staticmethod
    def _env_first(*keys: str) -> Optional[str]:
        for key in keys:
            value = os.getenv(key)
            if value is not None and str(value).strip() != "":
                return str(value).strip()
        return None

    @staticmethod
    def _safe_float(value: Optional[str], default: float) -> float:
        try:
            return float(value) if value is not None else default
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_int(value: Optional[str], default: int) -> int:
        try:
            return int(value) if value is not None else default
        except (TypeError, ValueError):
            return default

    @classmethod
    def _resolve_runtime_config(cls, profile: str = None) -> Dict[str, object]:
        prefix = f"LLM_{profile.upper()}_" if profile else "LLM_"
        provider = (
            cls._env_first(f"{prefix}PROVIDER", "LLM_PROVIDER", "openai") or "openai"
        ).strip().lower()

        if provider == "anthropic":
            api_key = cls._env_first(
                f"{prefix}ANTHROPIC_API_KEY",
                f"{prefix}API_KEY",
                "ANTHROPIC_API_KEY",
                "LLM_API_KEY",
            )
            base_url = cls._env_first(
                f"{prefix}ANTHROPIC_BASE_URL",
                f"{prefix}BASE_URL",
                "ANTHROPIC_BASE_URL",
                "LLM_BASE_URL",
                "https://api.anthropic.com",
            )
            model = cls._env_first(
                f"{prefix}ANTHROPIC_MODEL",
                f"{prefix}MODEL",
                "ANTHROPIC_MODEL",
                "LLM_MODEL",
                "claude-3-5-sonnet",
            )
        else:
            provider = "openai"
            api_key = cls._env_first(f"{prefix}API_KEY", "LLM_API_KEY")
            base_url = cls._env_first(
                f"{prefix}BASE_URL",
                "LLM_BASE_URL",
                "https://api.openai.com/v1",
            )
            model = cls._env_first(
                f"{prefix}MODEL",
                "LLM_MODEL",
                "gpt-3.5-turbo",
            )

        temperature = cls._safe_float(
            cls._env_first(f"{prefix}TEMPERATURE", "LLM_TEMPERATURE"),
            0.7,
        )
        max_tokens = cls._safe_int(
            cls._env_first(f"{prefix}MAX_TOKENS", "LLM_MAX_TOKENS"),
            512,
        )

        return {
            "profile": profile or "default",
            "provider": provider,
            "api_key": api_key,
            "base_url": base_url,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

    @classmethod
    def resolve_profile(cls, profile: str = None) -> dict:
        config = cls._resolve_runtime_config(profile=profile)
        return {
            "profile": config["profile"],
            "provider": config["provider"],
            "model": config["model"],
            "base_url": config["base_url"],
            "has_api_key": bool(config["api_key"]),
        }

    @staticmethod
    def list_profiles() -> list:
        discovered = {"default"}
        reserved_second_tokens = {
            "API",
            "BASE",
            "MODEL",
            "TIMEOUT",
            "MAX",
            "RETRY",
            "PROVIDER",
            "TEMPERATURE",
            "ANTHROPIC",
        }
        profile_key_suffixes = {
            "API",
            "KEY",
            "BASE",
            "URL",
            "MODEL",
            "PROVIDER",
            "TEMPERATURE",
            "TOKENS",
            "MAX",
        }
        for key in os.environ.keys():
            if not key.startswith("LLM_"):
                continue
            parts = key.split("_")
            if len(parts) >= 3 and parts[1] and parts[1] not in reserved_second_tokens:
                suffix = parts[-1]
                if suffix in profile_key_suffixes:
                    discovered.add(parts[1].upper())

        profiles = []
        for name in sorted(discovered):
            profile_name = None if name == "default" else name
            profiles.append(LLMClient.resolve_profile(profile=profile_name))
        return profiles

    async def _call_openai(
        self,
        client: httpx.AsyncClient,
        config: Dict[str, object],
        prompt: str,
        system_prompt: str,
    ) -> str:
        url = f"{str(config['base_url']).rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": config["model"],
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": config["temperature"],
        }
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def _call_anthropic(
        self,
        client: httpx.AsyncClient,
        config: Dict[str, object],
        prompt: str,
        system_prompt: str,
    ) -> str:
        url = f"{str(config['base_url']).rstrip('/')}/v1/messages"
        headers = {
            "x-api-key": str(config["api_key"]),
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        temperature = float(config["temperature"])
        temperature = max(0.01, min(1.0, temperature))

        payload = {
            "model": config["model"],
            "max_tokens": max(1, int(config["max_tokens"])),
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}],
                }
            ],
            "temperature": temperature,
        }
        if system_prompt:
            payload["system"] = system_prompt

        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        text_parts = []
        for block in data.get("content", []):
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(block.get("text", ""))
        text_content = "".join(text_parts).strip()
        if text_content:
            return text_content
        output_text = data.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text
        raise ValueError("Anthropic response did not contain text content.")

    async def call(self, prompt: str, system_prompt: str = "", profile: str = None) -> str:
        config = self._resolve_runtime_config(profile=profile)

        if not config["api_key"]:
            return self._fallback_response(
                f"No API key found for profile: {config['profile']} ({config['provider']})"
            )

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            last_error = "unknown error"
            for attempt in range(self.max_retries + 1):
                try:
                    provider = str(config["provider"])
                    if provider == "anthropic":
                        return await self._call_anthropic(client, config, prompt, system_prompt)
                    return await self._call_openai(client, config, prompt, system_prompt)
                except httpx.HTTPStatusError as e:
                    status_code = e.response.status_code if e.response else "N/A"
                    body = (e.response.text or "")[:300] if e.response else ""
                    print(
                        f"LLM API HTTP error (attempt {attempt + 1}/{self.max_retries + 1}) "
                        f"profile={config['profile']} provider={config['provider']} "
                        f"status={status_code}: {body}"
                    )
                    last_error = f"http {status_code}"
                except (httpx.TimeoutException, httpx.NetworkError) as e:
                    print(
                        f"LLM API network error (attempt {attempt + 1}/{self.max_retries + 1}) "
                        f"profile={config['profile']} provider={config['provider']}: {e}"
                    )
                    last_error = "network timeout/error"
                except Exception as e:
                    print(
                        f"LLM API unexpected error (attempt {attempt + 1}/{self.max_retries + 1}) "
                        f"profile={config['profile']} provider={config['provider']}: {e}"
                    )
                    last_error = "unexpected exception"

                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_backoff_sec * (2 ** attempt))

        return self._fallback_response(
            f"LLM API error, fallback to CHECK ({config['provider']}: {last_error})"
        )
