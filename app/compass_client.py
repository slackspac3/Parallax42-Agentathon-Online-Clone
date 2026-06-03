"""Safe Compass/OpenAI-compatible configuration probe."""

from __future__ import annotations

import os
from typing import Any, Dict
from urllib.parse import urlparse

import httpx


def truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


class CompassClient:
    def probe(self) -> Dict[str, Any]:
        base_url = (os.environ.get("OPENAI_BASE_URL") or "https://compass.core42.ai/v1").rstrip("/")
        api_key = os.environ.get("OPENAI_API_KEY") or ""
        live_probe = truthy(os.environ.get("COMPASS_PROBE_LIVE", "0"))
        result: Dict[str, Any] = {
            "ok": True,
            "provider": "openai_compatible_compass",
            "base_url_configured": bool(base_url),
            "base_url_host": urlparse(base_url).netloc or "unconfigured",
            "api_key_configured": bool(api_key),
            "live_call_performed": False,
            "live_llm_enabled": truthy(os.environ.get("CREWAI_ENABLE_LIVE_LLM", "0")),
            "sample_mode": truthy(os.environ.get("SAMPLE_MODE", "false")),
        }
        if not live_probe:
            result["message"] = "Configuration-only probe; set COMPASS_PROBE_LIVE=1 to verify /models."
            return result
        if not api_key:
            result.update({"ok": False, "message": "OPENAI_API_KEY is not configured."})
            return result
        try:
            response = httpx.get(
                f"{base_url}/models",
                headers={"Authorization": "Bearer [redacted]".replace("[redacted]", api_key)},
                timeout=10,
            )
            result["live_call_performed"] = True
            result["status_code"] = response.status_code
            result["ok"] = response.status_code < 500
            result["message"] = "Compass /models probe completed without exposing credentials."
        except Exception as exc:  # pragma: no cover - network optional
            result.update(
                {
                    "ok": False,
                    "live_call_performed": True,
                    "message": f"Compass probe failed: {exc.__class__.__name__}",
                }
            )
        return result
