#!/usr/bin/env bash
# Serve a small Qwen model with vLLM (OpenAI-compatible API) for intent parsing / explanations.
# A1000 8GB: Qwen2.5-1.5B-Instruct fits with headroom. Override with VLLM_MODEL / VLLM_PORT.
set -euo pipefail
MODEL="${VLLM_MODEL:-Qwen/Qwen2.5-1.5B-Instruct}"
PORT="${VLLM_PORT:-8001}"
exec vllm serve "$MODEL" \
  --port "$PORT" \
  --max-model-len 4096 \
  --gpu-memory-utilization "${VLLM_GPU_UTIL:-0.85}"
