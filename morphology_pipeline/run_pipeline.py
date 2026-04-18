#!/usr/bin/env python3
"""
Main Pipeline Runner
Runs the complete extraction pipeline: A -> B -> C -> D

Usage:
    python run_pipeline.py                    # Run all stages
    python run_pipeline.py --stage A          # Run specific stage
    python run_pipeline.py --skip-stage B    # Skip specific stage
    python run_pipeline.py --help            # Show help
"""

import os
import sys
import argparse
import subprocess
import json
from typing import List, Optional

# Configuration
BASE_DIR = "/home/ubuntu/jiajunwang/extraction_trial/morphology_pipeline"

# Data directories
DIR_RAW_HTML = f"{BASE_DIR}/data/ten_examples"           # Raw HTML input
DIR_A_HTML2ARTICLE = f"{BASE_DIR}/data/A_html2article"  # Stage A output
DIR_B_SORTED = f"{BASE_DIR}/data/B_sorted_paper"        # Stage B output
DIR_C_EXTRACTED = f"{BASE_DIR}/data/C_extracted_paragraphs"  # Stage C output
DIR_D_FINAL = f"{BASE_DIR}/data/D_final"                # Stage D output


def ensure_dir(path: str):
    """Ensure directory exists."""
    os.makedirs(path, exist_ok=True)


def run_stage_a(input_dir: str = None, output_dir: str = None) -> bool:
    """Stage A: Extract article content from HTML."""
    if input_dir is None:
        input_dir = DIR_RAW_HTML
    if output_dir is None:
        output_dir = DIR_A_HTML2ARTICLE

    print("\n" + "=" * 60)
    print("STAGE A: HTML Article Extraction")
    print("=" * 60)
    print(f"Input:  {input_dir}")
    print(f"Output: {output_dir}")

    ensure_dir(output_dir)

    # Import and use the batch processor
    from core.A_html_extractor import process_all_articles

    processed = process_all_articles(input_dir, output_dir)

    print(f"\nStage A completed: {len(processed)} files processed")
    return True


def run_stage_b(input_dir: str = None, output_dir: str = None) -> bool:
    """Stage B: Filter bacteriophage-related papers."""
    if input_dir is None:
        input_dir = DIR_A_HTML2ARTICLE
    if output_dir is None:
        output_dir = DIR_B_SORTED

    print("\n" + "=" * 60)
    print("STAGE B: Bacteriophage Paper Sorting")
    print("=" * 60)
    print(f"Input:  {input_dir}")
    print(f"Output: {output_dir}")

    # Import and run B_paper_sort
    sys.path.insert(0, BASE_DIR)
    from core.B_paper_sort import process_papers

    results = process_papers()

    print(f"\nStage B completed")
    print(f"  Phage-related: {len(results.get('phage_related', []))}")
    print(f"  Non-phage-related: {len(results.get('non_phage_related', []))}")

    return True


def run_stage_c(input_dir: str = None, output_dir: str = None) -> bool:
    """Stage C: Extract paragraphs from articles."""
    if input_dir is None:
        input_dir = DIR_B_SORTED
    if output_dir is None:
        output_dir = DIR_C_EXTRACTED

    print("\n" + "=" * 60)
    print("STAGE C: Paragraph Extraction")
    print("=" * 60)
    print(f"Input:  {input_dir}")
    print(f"Output: {output_dir}")

    # Import and run C_para_extract
    sys.path.insert(0, BASE_DIR)
    from core.C_para_extract import main as c_main

    c_main()

    print("\nStage C completed")
    return True


def run_stage_d(input_dir: str = None, output_dir: str = None, model: str = "deepseek-v3") -> bool:
    """Stage D: LLM processing (Stage 2 & 3)."""
    if input_dir is None:
        input_dir = DIR_C_EXTRACTED
    if output_dir is None:
        output_dir = DIR_D_FINAL

    print("\n" + "=" * 60)
    print("STAGE D: LLM Processing (Stage 2 & 3)")
    print("=" * 60)
    print(f"Input:  {input_dir}")
    print(f"Output: {output_dir}")
    print(f"Model:  {model}")

    # Import and run D_llm_process
    sys.path.insert(0, BASE_DIR)

    # Temporarily override DEFAULT_MODEL
    import core.D_llm_process as d_module
    original_model = d_module.DEFAULT_MODEL
    d_module.DEFAULT_MODEL = model

    from core.D_llm_process import main as d_main
    d_main()

    d_module.DEFAULT_MODEL = original_model

    print("\nStage D completed")
    return True


def run_full_pipeline(model: str = "deepseek-v3", start_stage: str = "A", skip_stages: List[str] = None):
    """Run the full pipeline."""
    if skip_stages is None:
        skip_stages = []

    print("=" * 60)
    print("EXTRACTION PIPELINE - FULL RUN")
    print("=" * 60)
    print(f"Start Stage: {start_stage}")
    print(f"Skip Stages: {skip_stages if skip_stages else 'None'}")
    print(f"LLM Model:   {model}")
    print("=" * 60)

    # Check API key
    from llm_config import get_api_key
    try:
        api_key = get_api_key()
        print(f"API Key: Loaded (length: {len(api_key)})")
    except ValueError as e:
        print(f"ERROR: {e}")
        print("Please set DEEPSEEK_API_KEY environment variable or configure in llm_config.py")
        sys.exit(1)

    stages = ['A', 'B', 'C', 'D']
    stage_functions = {
        'A': run_stage_a,
        'B': run_stage_b,
        'C': run_stage_c,
        'D': run_stage_d
    }

    start_idx = stages.index(start_stage.upper()) if start_stage.upper() in stages else 0

    for stage in stages[start_idx:]:
        if stage in skip_stages:
            print(f"\n[SKIP] Stage {stage}")
            continue

        print(f"\n>>> Running Stage {stage}...")

        try:
            if stage == 'A':
                run_stage_a()
            elif stage == 'B':
                run_stage_b()
            elif stage == 'C':
                run_stage_c()
            elif stage == 'D':
                run_stage_d(model=model)
        except Exception as e:
            print(f"ERROR in Stage {stage}: {e}")
            import traceback
            traceback.print_exc()
            response = input(f"Stage {stage} failed. Continue? (y/n): ")
            if response.lower() != 'y':
                print("Pipeline stopped by user")
                return False

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETED")
    print("=" * 60)

    # Show output summary
    if os.path.exists(DIR_D_FINAL):
        output_files = [f for f in os.listdir(DIR_D_FINAL) if f.endswith('.json')]
        print(f"\nFinal output: {len(output_files)} files in {DIR_D_FINAL}")

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Main Pipeline Runner for Phage Extraction",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_pipeline.py                      # Run all stages
  python run_pipeline.py --stage B            # Start from stage B
  python run_pipeline.py --skip-stage B       # Skip stage B
  python run_pipeline.py --model deepseek-r1   # Reasoning model
  python run_pipeline.py --help               # Show this help
        """
    )

    parser.add_argument(
        "--stage", "-s",
        default="A",
        choices=["A", "B", "C", "D", "a", "b", "c", "d"],
        help="Starting stage (default: A)"
    )

    parser.add_argument(
        "--skip", "-k",
        nargs="*",
        default=[],
        help="Stages to skip (e.g., --skip B D)"
    )

    parser.add_argument(
        "--model", "-m",
        default="deepseek-v3",
        choices=["deepseek-v3", "deepseek-chat", "deepseek-r1", "deepseek-reasoner"],
        help="LLM model to use for Stage D (DeepSeek official; default: deepseek-v3 -> deepseek-chat)"
    )

    parser.add_argument(
        "--show-config",
        action="store_true",
        help="Show pipeline configuration and exit"
    )

    args = parser.parse_args()

    if args.show_config:
        print("=" * 60)
        print("PIPELINE CONFIGURATION")
        print("=" * 60)
        print(f"Stage A Input:  {DIR_RAW_HTML}")
        print(f"Stage A Output: {DIR_A_HTML2ARTICLE}")
        print(f"Stage B Output: {DIR_B_SORTED}")
        print(f"Stage C Output: {DIR_C_EXTRACTED}")
        print(f"Stage D Output: {DIR_D_FINAL}")
        print(f"Default Model: {args.model}")
        print("=" * 60)
        return

    # Run pipeline
    run_full_pipeline(
        model=args.model,
        start_stage=args.stage.upper(),
        skip_stages=[s.upper() for s in args.skip]
    )


if __name__ == "__main__":
    main()