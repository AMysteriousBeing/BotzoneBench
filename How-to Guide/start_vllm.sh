python -m vllm.entrypoints.openai.api_server \
  --model your-vllm-model-save-path/models/Eslzzyl/Qwen3-4B-Instruct-2507-AWQ \
  --tensor-parallel-size 1 \
  --port 8000 \
  --host 0.0.0.0 \
  --gpu-memory-utilization 0.8 \
  --max-model-len 15360 \
  --max-num-seqs 8