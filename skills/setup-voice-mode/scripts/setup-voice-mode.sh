#!/usr/bin/env bash
# VoiceMode, speak-only: local mlx-audio service + MCP server from a reviewed checkout.
# No STT service, no OpenAI fallback, no Claude Code plugin hooks.
#
# Read it first, set REPO, then run it yourself.
# Optional: MODEL and VOICE (see SKILL.md, "Speech language and model").
set -euo pipefail

REPO="${REPO:?set REPO to the reviewed voicemode checkout, for example \$HOME/src/voicemode}"
MODEL="${MODEL:-}"   # empty = mlx-audio default (Kokoro-82M)
VOICE="${VOICE:-}"   # empty = voicemode default (af_sky)

echo "== 1/4 Show the checkout state (should be the commit you reviewed)"
git -C "$REPO" log --oneline -1
git -C "$REPO" status --short | head -5

echo "== 2/4 Install mlx-audio as a local TTS service (127.0.0.1:8890)"
# Creates $REPO/.venv, runs 'uv tool install mlx-audio', writes a launchd plist.
uv run --directory "$REPO" voicemode service install mlx-audio

echo "== 3/4 Wait for the TTS service"
for _ in $(seq 1 30); do
  if curl -s -m 2 -o /dev/null http://127.0.0.1:8890/v1/models; then
    echo "mlx-audio answers on 127.0.0.1:8890"
    break
  fi
  sleep 2
done
uv run --directory "$REPO" voicemode service status mlx-audio || true

echo "== 4/4 Register the MCP server (user scope), local URLs only"
EXTRA_ENV=()
[ -n "$MODEL" ] && EXTRA_ENV+=(-e "VOICEMODE_TTS_MODELS_MLX_AUDIO=$MODEL")
[ -n "$VOICE" ] && EXTRA_ENV+=(-e "VOICEMODE_VOICES=$VOICE")

claude mcp remove --scope user voicemode >/dev/null 2>&1 || true
claude mcp add --scope user voicemode \
  -e VOICEMODE_TTS_BASE_URLS=http://127.0.0.1:8890/v1 \
  -e VOICEMODE_STT_BASE_URLS=http://127.0.0.1:2022/v1 \
  -e VOICEMODE_CONTROL_CHANNEL_ENABLED=true \
  ${EXTRA_ENV[@]+"${EXTRA_ENV[@]}"} \
  -- uv run --directory "$REPO" voicemode
claude mcp get voicemode

echo
echo "Done. Restart Claude Code so the MCP server loads."
echo "First spoken answer downloads the model and may fail once; call again."
