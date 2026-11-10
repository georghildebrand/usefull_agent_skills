import pytest

from local_llm_guard.config import (
    Config,
    NotLocal,
    check_local,
    config_from_env,
    update_config,
)

INSTALLED = ["qwen2.5:14b", "gemma3:4b", "gpt-oss:120b-cloud"]


def test_defaults():
    assert config_from_env({}) == Config()
    assert Config().num_ctx == 16384 and Config().timeout_s == 300


def test_env_overrides():
    cfg = config_from_env(
        {
            "LOCAL_LLM_GUARD_NUM_CTX": "8192",
            "LOCAL_LLM_GUARD_MODEL": "gemma3:4b",
            "LOCAL_LLM_GUARD_TIMEOUT": "60",
            "OLLAMA_HOST": "localhost:11500",
        }
    )
    assert (cfg.num_ctx, cfg.model, cfg.timeout_s) == (8192, "gemma3:4b", 60)
    assert cfg.base_url == "http://localhost:11500"


def test_check_local_refuses_remote_host():
    with pytest.raises(NotLocal, match="http://10.0.0.5:11434 is not a loopback address"):
        check_local(Config(base_url="http://10.0.0.5:11434"), INSTALLED)


def test_check_local_refuses_cloud_and_missing_model():
    with pytest.raises(NotLocal, match="model gpt-oss:120b-cloud is not a local model"):
        check_local(Config(model="gpt-oss:120b-cloud"), INSTALLED)
    with pytest.raises(NotLocal, match="model nope:1b is not a local model"):
        check_local(Config(model="nope:1b"), INSTALLED)


@pytest.mark.parametrize("url", ["http://localhost:11434", "http://[::1]:11434"])
def test_check_local_accepts_loopback(url):
    check_local(Config(base_url=url), INSTALLED)


def _upd(cfg=None, **kw):
    args = {
        "num_ctx": None,
        "model": None,
        "timeout_s": None,
        "model_max_ctx": 32768,
        "installed": INSTALLED,
    }
    args.update(kw)
    return update_config(cfg or Config(), **args)


def test_update_config_range():
    with pytest.raises(ValueError, match="1024"):
        _upd(num_ctx=1024)
    with pytest.raises(ValueError, match="32769"):
        _upd(num_ctx=32769)
    assert _upd(num_ctx=32768).num_ctx == 32768


def test_update_config_model():
    with pytest.raises(ValueError, match="model nope:1b is not a local model"):
        _upd(model="nope:1b")
    with pytest.raises(ValueError, match="is not a local model"):
        _upd(model="gpt-oss:120b-cloud")
    assert _upd(model="gemma3:4b", timeout_s=10).model == "gemma3:4b"
