"""Settings from environment variables, plus the local-only checks."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from urllib.parse import urlparse

DEFAULT_BASE_URL = "http://127.0.0.1:11434"
MIN_NUM_CTX = 2048
LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}


@dataclass
class Config:
    model: str = "qwen2.5:14b"
    num_ctx: int = 16384
    timeout_s: int = 300
    base_url: str = DEFAULT_BASE_URL


class NotLocal(Exception):
    """The Ollama endpoint or the model is not local."""


def _int_env(env: Mapping[str, str], name: str, default: int) -> int:
    raw = env.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw.strip())
    except ValueError:
        raise ValueError(f"{name} must be an integer") from None


def config_from_env(env: Mapping[str, str]) -> Config:
    defaults = Config()
    host = env.get("OLLAMA_HOST", "").strip()
    if host and "://" not in host:
        host = "http://" + host
    return Config(
        model=env.get("LOCAL_LLM_GUARD_MODEL", "").strip() or defaults.model,
        num_ctx=_int_env(env, "LOCAL_LLM_GUARD_NUM_CTX", defaults.num_ctx),
        timeout_s=_int_env(env, "LOCAL_LLM_GUARD_TIMEOUT", defaults.timeout_s),
        base_url=host or defaults.base_url,
    )


def _is_cloud(model: str) -> bool:
    return "cloud" in model.lower()


def check_host(cfg: Config) -> None:
    """Loopback check on the URL only. Makes no network call."""
    try:
        host = urlparse(cfg.base_url).hostname
    except ValueError:
        host = None
    if host not in LOOPBACK_HOSTS:
        raise NotLocal(f"Ollama endpoint {cfg.base_url} is not a loopback address")


def check_model(cfg: Config, installed: list[str]) -> None:
    if cfg.model not in installed or _is_cloud(cfg.model):
        raise NotLocal(f"model {cfg.model} is not a local model")


def check_local(cfg: Config, installed: list[str]) -> None:
    check_host(cfg)
    check_model(cfg, installed)


def update_config(
    cfg: Config,
    *,
    num_ctx: int | None,
    model: str | None,
    timeout_s: int | None,
    model_max_ctx: int,
    installed: list[str],
) -> Config:
    new_model = cfg.model if model is None else model
    if model is not None and (model not in installed or _is_cloud(model)):
        raise ValueError(f"model {model} is not a local model")
    if num_ctx is not None and not (MIN_NUM_CTX <= num_ctx <= model_max_ctx):
        raise ValueError(
            f"num_ctx {num_ctx} is out of range: allowed {MIN_NUM_CTX} to {model_max_ctx}"
        )
    if timeout_s is not None and timeout_s < 1:
        raise ValueError("timeout_s must be at least 1")
    return replace(
        cfg,
        model=new_model,
        num_ctx=cfg.num_ctx if num_ctx is None else num_ctx,
        timeout_s=cfg.timeout_s if timeout_s is None else timeout_s,
    )
