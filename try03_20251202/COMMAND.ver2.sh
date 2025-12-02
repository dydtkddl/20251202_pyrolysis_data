CUDA_VISIBLE_DEVICES=1  python csv_ollama_runner.ver2.py \
    --csv YES_RESULT.with_meta.csv \
    --title_col title_clean \
    --abstract_col abstract_clean \
    --sf_col source_file \
    --prompt prompt.txt \
    --model qwen3:30b-a3b-instruct-2507-q4_K_M \
    --outdir qwen_results_v2
