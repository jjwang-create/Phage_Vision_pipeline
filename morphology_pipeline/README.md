# Morphology pipeline (副本)

独立副本目录：`extraction_trial/morphology_pipeline/`

- **Stage 3 抽取**：`prompts/prompts.py` 中 `DETAIL_EXTRACT_SYS_PROMPT` 与 `data/ref_words.txt` 中 Stage 3（形态/结构）一致。
- **Stage 4 评分**：根目录 `words.txt` 与 `data/ref_words.txt` 中 Stage 4（形态评分维度）一致；`core/E_quality_scorer.py` 中 `SCORE_DIMENSIONS` 为 5 维形态指标。

## 数据布局

- `data/A_html2article`、`B_sorted_paper`、`C_extracted_paragraphs`：指向上级 `extraction_trial/data/...` 的符号链接（复用已有中间结果，不重复占磁盘）。
- `data/D_final/`：本副本 **Stage D** 输出（形态学抽取 JSON）。
- `data/E_quality_results_morphology/`：**Stage E** 评分输出。

## 运行

需设置 `DEEPSEEK_API_KEY`（或按 `llm_config.py` 配置）。

```bash
cd /home/ubuntu/jiajunwang/extraction_trial/morphology_pipeline

# 仅重跑 D（输入为已存在的 C_extracted）与 E
python run_pipeline.py --stage D --skip A B C

python core/E_quality_scorer.py \
  --model deepseek-v3 \
  --output-dir data/E_quality_results_morphology \
  --sleep-seconds 2
```

若要从 A 重新跑全流程，去掉 `--skip`；注意 B/C 输出会写入符号链接目录，即与主项目共享。
