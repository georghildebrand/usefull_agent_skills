"""Measure Ollama time and memory at two context sizes. Needs a running Ollama."""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import httpx2 as httpx  # noqa: E402

from local_llm_guard.config import Config  # noqa: E402
from local_llm_guard.ollama import OllamaClient, OllamaError  # noqa: E402

FILLER = "The quick brown fox jumps over the lazy dog. "
CTX_SIZES = (16384, 32768)


def used_memory_gb(base_url: str, model: str) -> tuple[float, float]:
    data = httpx.get(base_url + "/api/ps", timeout=30).json()
    for m in data.get("models", []):
        if model in (m.get("name"), m.get("model")):
            return m.get("size", 0) / 1e9, m.get("size_vram", 0) / 1e9
    return 0.0, 0.0


def main() -> None:
    for num_ctx in CTX_SIZES:
        cfg = Config(num_ctx=num_ctx, timeout_s=1800)
        tokens = int(0.8 * num_ctx)
        chars = tokens * 3
        prompt = (FILLER * (chars // len(FILLER) + 1))[:chars]
        started = time.monotonic()
        try:
            OllamaClient(cfg).chat("Answer with one word.", prompt + "\nSay OK.")
        except OllamaError as exc:
            print(f"model={cfg.model} num_ctx={num_ctx} error: {exc}")
            continue
        elapsed = time.monotonic() - started
        size, vram = used_memory_gb(cfg.base_url, cfg.model)
        print(
            f"model={cfg.model} num_ctx={num_ctx} prompt_chars={chars} "
            f"time={elapsed:.1f}s size={size:.1f}GB size_vram={vram:.1f}GB"
        )


if __name__ == "__main__":
    main()
