#!/usr/bin/env python3
"""
Stage E: Quality Scorer for extraction results.

What this script does:
1. Loads evaluator prompt from words.txt (Stage 4 prompt).
2. By default, scores only papers listed under B_sorted_paper (phage-related cohort; same
   full-article JSON as A, copied at stage B). ORIGINAL_TEXT is the flattened full article
   (title, abstract, all sections) unless --original-max-chars caps it; paired with
   EXTRACTED_JSON from D_final (empty fallback if missing).
3. To score the full A corpus again, pass --input-dir path/to/A_html2article and optional
   --max-papers.
4. Saves per-paper scores, ranking, and score distribution plot.

Outputs (default under data/E_quality_results):
- E_scores_all.json
- E_scores_ranking.csv
- E_scores_summary.json
- E_score_distribution.png
"""

import argparse
import csv
import json
import os
import re
import statistics
import time
from datetime import datetime
from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt

# Add parent directory to path for imports
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.api_client import DeepSeekClient
from llm_config import DEEPSEEK_BASE_URL, get_api_key, MODELS


BASE_DIR = "/home/ubuntu/jiajunwang/extraction_trial/morphology_pipeline"
DIR_A = f"{BASE_DIR}/data/A_html2article"
DIR_B_SORTED = f"{BASE_DIR}/data/B_sorted_paper"
DIR_D = f"{BASE_DIR}/data/D_final"
PROMPT_PATH = f"{BASE_DIR}/words.txt"
DEFAULT_OUTPUT_DIR = f"{BASE_DIR}/data/E_quality_results_morphology"

DEFAULT_MODEL = "deepseek-chat"

# Morphology Stage 4 evaluator (ref_words.txt §Stage 4)
SCORE_DIMENSIONS = [
    "morphology_coverage_completeness",
    "value_fidelity_verbatim",
    "attribution_correctness",
    "schema_compliance",
    "hallucination_and_noise_control",
]


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def load_system_prompt(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def list_paper_ids(dir_a: str) -> List[str]:
    paper_ids = []
    for name in sorted(os.listdir(dir_a)):
        if name.endswith(".json"):
            paper_ids.append(name[:-5])
    return paper_ids


def flatten_article_json(article: Dict[str, Any], max_chars: int = 0) -> str:
    """
    Build ORIGINAL_TEXT for evaluator from article JSON (same structure as A/B).

    max_chars: if > 0, truncate flattened text to this length (suffix marker appended).
               if 0, keep the entire flattened article.
    """
    chunks: List[str] = []

    title = article.get("title", "")
    if isinstance(title, str) and title.strip():
        chunks.append(f"TITLE: {title.strip()}")

    abstract = article.get("abstract", "")
    if isinstance(abstract, str) and abstract.strip():
        chunks.append(f"ABSTRACT: {abstract.strip()}")

    for k, v in article.items():
        if k in ("title", "abstract"):
            continue
        if isinstance(v, list):
            chunks.append(f"SECTION: {k}")
            for item in v:
                if isinstance(item, dict):
                    content = item.get("content", "")
                    if isinstance(content, str) and content.strip():
                        chunks.append(content.strip())
                elif isinstance(item, str) and item.strip():
                    chunks.append(item.strip())
        elif isinstance(v, str) and v.strip():
            chunks.append(f"{k}: {v.strip()}")

    text = "\n\n".join(chunks)
    if max_chars > 0 and len(text) > max_chars:
        return text[:max_chars] + "\n\n[TRUNCATED_FOR_EVALUATION]"
    return text


def load_original_text(paper_id: str, max_chars: int = 0) -> str:
    path = os.path.join(DIR_A, f"{paper_id}.json")
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return flatten_article_json(data, max_chars=max_chars)


def load_extracted_json(paper_id: str) -> Tuple[Dict[str, Any], bool]:
    """
    Returns extracted_json and whether D_final result exists.
    """
    path = os.path.join(DIR_D, f"{paper_id}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f), True

    # Fallback for papers without extraction result
    return {"summary": "", "phages": {}}, False


def parse_eval_json(raw: str) -> Dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)

    start_idx = text.find("{")
    end_idx = text.rfind("}")
    if start_idx == -1 or end_idx == -1 or end_idx <= start_idx:
        raise ValueError("No valid JSON object found in model response")
    return json.loads(text[start_idx:end_idx + 1])


def scores_to_map(scores: List[Dict[str, Any]]) -> Dict[str, float]:
    score_map: Dict[str, float] = {}
    for item in scores:
        dim = item.get("dimension")
        score = item.get("score")
        if isinstance(dim, str) and isinstance(score, (int, float)):
            score_map[dim] = float(score)
    return score_map


def compute_overall_score(score_map: Dict[str, float]) -> float:
    values: List[float] = []
    for dim in SCORE_DIMENSIONS:
        if dim in score_map:
            values.append(score_map[dim])
    if not values:
        return 0.0
    return round(sum(values) / len(values), 4)


def evaluate_paper(
    paper_id: str,
    original_text: str,
    extracted_json: Dict[str, Any],
    system_prompt: str,
    client: DeepSeekClient,
    max_retries: int = 3,
    score_samples: int = 3,
    temperature: float = 0.0,
) -> Dict[str, Any]:
    extracted_json_str = json.dumps(extracted_json, ensure_ascii=False, indent=2)
    user_input = (
        "ORIGINAL_TEXT:\n"
        f"{original_text}\n\n"
        "EXTRACTED_JSON:\n"
        f"{extracted_json_str}"
    )

    run_count = max(1, score_samples)
    success_runs: List[Dict[str, Any]] = []
    errors: List[str] = []

    for _ in range(run_count):
        run_result = None
        for attempt in range(1, max_retries + 1):
            try:
                response = client.call(
                    system_prompt=system_prompt,
                    user_input=user_input,
                    temperature=temperature,
                    max_tokens=1800,
                )
                content = response.get("content", "")
                parsed = parse_eval_json(content)
                score_map = scores_to_map(parsed.get("scores", []))
                run_result = {
                    "raw_eval": parsed,
                    "score_map": score_map,
                    "overall": compute_overall_score(score_map),
                    "raw_response_preview": content[:600],
                }
                break
            except Exception as e:
                errors.append(str(e))
                if attempt < max_retries:
                    time.sleep(2)

        if run_result is not None:
            success_runs.append(run_result)

    if not success_runs:
        return {
            "ok": False,
            "paper_id": paper_id,
            "overall_score": 0.0,
            "dimension_scores": {},
            "raw_eval": {},
            "error": errors[-1] if errors else "unknown error",
            "successful_samples": 0,
            "requested_samples": run_count,
        }

    aggregated_scores: Dict[str, float] = {}
    for dim in SCORE_DIMENSIONS:
        vals = [
            float(r["score_map"][dim])
            for r in success_runs
            if dim in r["score_map"]
        ]
        if vals:
            aggregated_scores[dim] = round(float(statistics.median(vals)), 4)

    overall = compute_overall_score(aggregated_scores)
    run_overalls = [float(r["overall"]) for r in success_runs]

    return {
        "ok": True,
        "paper_id": paper_id,
        "overall_score": overall,
        "dimension_scores": aggregated_scores,
        "raw_eval": success_runs[0]["raw_eval"],
        "raw_response_preview": success_runs[0]["raw_response_preview"],
        "successful_samples": len(success_runs),
        "requested_samples": run_count,
        "sample_overall_scores": run_overalls,
        "sample_overall_std": round(statistics.pstdev(run_overalls), 4) if len(run_overalls) > 1 else 0.0,
    }


def save_json(path: str, obj: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def save_ranking_csv(path: str, records: List[Dict[str, Any]]) -> None:
    headers = [
        "rank",
        "paper_id",
        "overall_score",
        "has_d_final_output",
        "status",
    ] + SCORE_DIMENSIONS

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for i, rec in enumerate(records, start=1):
            row = {
                "rank": i,
                "paper_id": rec.get("paper_id", ""),
                "overall_score": rec.get("overall_score", 0.0),
                "has_d_final_output": rec.get("has_d_final_output", False),
                "status": "ok" if rec.get("ok") else "error",
            }
            dims = rec.get("dimension_scores", {})
            for dim in SCORE_DIMENSIONS:
                row[dim] = dims.get(dim, "")
            writer.writerow(row)


def plot_distribution(path: str, scores: List[float], title: str) -> None:
    plt.figure(figsize=(10, 6))
    bins = [x / 2 for x in range(0, 21)]  # 0.0 ~ 10.0 by 0.5
    plt.hist(scores, bins=bins, edgecolor="black", alpha=0.8)
    plt.title(title)
    plt.xlabel("Overall Score (0-10)")
    plt.ylabel("Paper Count")
    plt.grid(axis="y", linestyle="--", alpha=0.4)
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def summarize(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    ok_records = [r for r in records if r.get("ok")]
    scores = [r.get("overall_score", 0.0) for r in records]
    ok_scores = [r.get("overall_score", 0.0) for r in ok_records]

    dim_avgs: Dict[str, float] = {}
    for dim in SCORE_DIMENSIONS:
        dim_values = []
        for rec in ok_records:
            val = rec.get("dimension_scores", {}).get(dim)
            if isinstance(val, (int, float)):
                dim_values.append(float(val))
        dim_avgs[dim] = round(sum(dim_values) / len(dim_values), 4) if dim_values else 0.0

    return {
        "total_papers": len(records),
        "successful_evals": len(ok_records),
        "failed_evals": len(records) - len(ok_records),
        "overall_avg_all": round(sum(scores) / len(scores), 4) if scores else 0.0,
        "overall_avg_success_only": round(sum(ok_scores) / len(ok_scores), 4) if ok_scores else 0.0,
        "overall_median_success_only": round(statistics.median(ok_scores), 4) if ok_scores else 0.0,
        "dimension_averages_success_only": dim_avgs,
    }


def run(args: argparse.Namespace) -> None:
    ensure_dir(args.output_dir)

    system_prompt = load_system_prompt(args.prompt_file)
    paper_ids = list_paper_ids(args.input_dir)

    if args.max_papers > 0:
        paper_ids = paper_ids[:args.max_papers]

    if not paper_ids:
        print("No input papers found.")
        return

    model_name = MODELS.get(args.model, args.model)
    base_url = args.base_url.strip() if args.base_url else DEEPSEEK_BASE_URL
    api_key = args.api_key.strip() if args.api_key else get_api_key()
    client = DeepSeekClient(
        base_url=base_url,
        api_key=api_key,
        model=model_name,
        max_retries=1,
    )

    print("=" * 70)
    print("Stage E - Quality Scoring", flush=True)
    print("=" * 70)
    print(f"Prompt file: {args.prompt_file}", flush=True)
    print(f"Input dir:   {args.input_dir}", flush=True)
    print(f"D final dir: {args.d_final_dir}", flush=True)
    print(f"Model:       {model_name}", flush=True)
    print(f"Base URL:    {base_url}", flush=True)
    print(f"Papers:      {len(paper_ids)}", flush=True)
    print(f"Score samples/paper: {args.score_samples}", flush=True)
    print(f"Temperature: {args.temperature}", flush=True)
    cap = args.original_max_chars
    print(
        f"ORIGINAL_TEXT: {'full flattened article' if cap <= 0 else f'cap {cap} chars'}",
        flush=True,
    )
    print(f"Output dir:  {args.output_dir}", flush=True)
    print("=" * 70, flush=True)

    all_records: List[Dict[str, Any]] = []

    for idx, paper_id in enumerate(paper_ids, start=1):
        print(f"[{idx}/{len(paper_ids)}] {paper_id}", flush=True)

        original_text = load_original_text(
            paper_id, max_chars=args.original_max_chars
        )
        extracted_json, has_d_final_output = load_extracted_json(paper_id)

        if not original_text.strip():
            rec = {
                "ok": False,
                "paper_id": paper_id,
                "overall_score": 0.0,
                "dimension_scores": {},
                "raw_eval": {},
                "error": "No original text available",
                "has_d_final_output": has_d_final_output,
            }
            all_records.append(rec)
            print("  -> Skipped: original text missing", flush=True)
            continue

        result = evaluate_paper(
            paper_id=paper_id,
            original_text=original_text,
            extracted_json=extracted_json,
            system_prompt=system_prompt,
            client=client,
            max_retries=args.eval_retries,
            score_samples=args.score_samples,
            temperature=args.temperature,
        )
        result["has_d_final_output"] = has_d_final_output
        all_records.append(result)

        if result.get("ok"):
            print(f"  -> Score: {result.get('overall_score')}", flush=True)
        else:
            print(f"  -> Error: {result.get('error')}", flush=True)

        time.sleep(args.sleep_seconds)

    ranked_records = sorted(
        all_records,
        key=lambda x: x.get("overall_score", 0.0),
        reverse=True,
    )
    summary = summarize(all_records)

    # Save outputs
    scores_json = os.path.join(args.output_dir, "E_scores_all.json")
    ranking_csv = os.path.join(args.output_dir, "E_scores_ranking.csv")
    summary_json = os.path.join(args.output_dir, "E_scores_summary.json")
    dist_png = os.path.join(args.output_dir, "E_score_distribution.png")

    save_json(scores_json, all_records)
    save_ranking_csv(ranking_csv, ranked_records)
    save_json(summary_json, summary)
    plot_distribution(
        dist_png,
        [x.get("overall_score", 0.0) for x in all_records],
        f"Extraction Quality Distribution ({len(all_records)} Papers)",
    )

    print("\n" + "=" * 70, flush=True)
    print("Done.", flush=True)
    print(f"Saved: {scores_json}", flush=True)
    print(f"Saved: {ranking_csv}", flush=True)
    print(f"Saved: {summary_json}", flush=True)
    print(f"Saved: {dist_png}", flush=True)
    print("=" * 70, flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage E quality scorer")
    parser.add_argument(
        "--prompt-file",
        default=PROMPT_PATH,
        help="Path to evaluator system prompt file (default: words.txt)",
    )
    parser.add_argument(
        "--input-dir",
        default=DIR_B_SORTED,
        help=(
            "Article JSON directory: used to list paper_ids and build ORIGINAL_TEXT "
            "(default: data/B_sorted_paper, phage-related only). Use data/A_html2article "
            "to score the full corpus."
        ),
    )
    parser.add_argument(
        "--d-final-dir",
        default=DIR_D,
        help="Extraction results directory (default: data/D_final)",
    )
    parser.add_argument(
        "--original-max-chars",
        type=int,
        default=0,
        help=(
            "Max characters for flattened ORIGINAL_TEXT sent to the model (0 = no cap, "
            "use full article from input-dir JSON). Use a positive value if the API "
            "context window is exceeded."
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory (default: data/E_quality_results)",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="Model key in llm_config.MODELS, or direct model id from /v1/models",
    )
    parser.add_argument(
        "--base-url",
        default=DEEPSEEK_BASE_URL,
        help="Chat completion endpoint URL",
    )
    parser.add_argument(
        "--api-key",
        default="",
        help="API key override for this run",
    )
    parser.add_argument(
        "--max-papers",
        type=int,
        default=0,
        help="Max papers to score after sorting IDs (0 = no cap; default scores entire input-dir)",
    )
    parser.add_argument(
        "--eval-retries",
        type=int,
        default=1,
        help="Retries per paper on parse/API failure",
    )
    parser.add_argument(
        "--score-samples",
        type=int,
        default=3,
        help="Independent scoring calls per paper; final score uses per-dimension median",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Sampling temperature for evaluator model (default 0.0 for stability)",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=7.0,
        help="Sleep between paper evaluations to reduce burst load",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    # Keep global dirs configurable from args where needed.
    DIR_A = args.input_dir
    DIR_D = args.d_final_dir
    run(args)
