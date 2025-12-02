python csv_ollama_runner.py \
    --csv articles_V10_QWEN_input_head.test.csv \
    --text_col QWEN_INPUT \
    --prompt prompt.txt \
    --model qwen3:30b-a3b-instruct-2507-q4_K_M \
    --outdir qwen_results_test \
    --limit 5

