from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from dotenv import load_dotenv
from openai import OpenAI

DEFAULT_NVIDIA_BASE_URL: Final = "https://integrate.api.nvidia.com/v1"
_PROJECT_ROOT: Final = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class NvidiaNimSettings:
    api_key: str
    base_url: str
    model: str | None


def load_nvidia_nim_settings() -> NvidiaNimSettings:
    load_dotenv(_PROJECT_ROOT / ".env", override=False)

    api_key = os.getenv("NVIDIA_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "NVIDIA_API_KEY is not configured. Set NVIDIA_API_KEY in the repository "
            "root .env before creating the NVIDIA NIM client."
        )

    base_url = os.getenv("NVIDIA_BASE_URL", DEFAULT_NVIDIA_BASE_URL).strip()
    model = os.getenv("NVIDIA_MODEL", "").strip() or None

    return NvidiaNimSettings(api_key=api_key, base_url=base_url, model=model)


def create_nvidia_nim_client(settings: NvidiaNimSettings | None = None) -> OpenAI:
    resolved_settings = settings or load_nvidia_nim_settings()
    return OpenAI(
        api_key=resolved_settings.api_key,
        base_url=resolved_settings.base_url,
    )
