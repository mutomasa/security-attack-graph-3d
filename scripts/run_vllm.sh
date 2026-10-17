#!/usr/bin/env bash
# Serve a small Qwen model with vLLM (OpenAI-compatible API) for intent parsing / explanations.
# A1000 8GB: Qwen3-1.7B fits (~6.5GB incl. KV cache); see scripts/eval_llm.py for the comparison. Override with VLLM_MODEL / VLLM_PORT.
set -euo pipefail
MODEL="${VLLM_MODEL:-Qwen/Qwen3-1.7B}"
PORT="${VLLM_PORT:-8001}"
# FlashInfer's sampler JIT-compiles with nvcc; fall back to the PyTorch sampler when no CUDA toolkit is installed.
if ! command -v nvcc >/dev/null 2>&1; then
  export VLLM_USE_FLASHINFER_SAMPLER="${VLLM_USE_FLASHINFER_SAMPLER:-0}"
fi
# Larger models (e.g. Qwen2.5-7B-Instruct-AWQ on 8GB) need:
#   VLLM_MAX_LEN=2048 VLLM_GPU_UTIL=0.95 VLLM_EXTRA_ARGS=--enforce-eager
# shellcheck disable=SC2086
exec vllm serve "$MODEL" \
  --port "$PORT" \
  --max-model-len "${VLLM_MAX_LEN:-4096}" \
  --gpu-memory-utilization "${VLLM_GPU_UTIL:-0.85}" \
  ${VLLM_EXTRA_ARGS:-}
