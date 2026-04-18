#!/usr/bin/env python3
"""
Paper Sorting Script - Filter bacteriophage-related papers

This script uses LLM to analyze abstracts and identify bacteriophage-related papers.
Input: /home/ubuntu/jiajunwang/extraction_trial/data/A_html2article/*.json
Output: /home/ubuntu/jiajunwang/extraction_trial/data/B_sorted_paper/*.json (phage-related only)
"""

import json
import os
import shutil
from typing import Dict, List

# Add parent directory to path for imports
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.api_client import DeepSeekClient


# Configuration
INPUT_DIR = "/home/ubuntu/jiajunwang/extraction_trial/data/A_html2article"
OUTPUT_DIR = "/home/ubuntu/jiajunwang/extraction_trial/data/B_sorted_paper"

# LLM Configuration (from llm_config.py)
from llm_config import DEEPSEEK_BASE_URL, get_api_key, MODELS

LLM_BASE_URL = DEEPSEEK_BASE_URL
LLM_API_KEY = get_api_key()
LLM_MODEL = MODELS["deepseek-v3"]


# Prompt for bacteriophage detection
SYSTEM_PROMPT = """You are a scientific paper classifier. Your task is to determine whether a research paper is primarily about bacteriophages (phages)."""

USER_PROMPT_TEMPLATE = """Based on the following abstract, determine if this paper is PRIMARILY about bacteriophages (also known as phages, bacterial viruses, or prokaryotic viruses).

A paper is "primarily about bacteriophages" if:
- The main research focus is on bacteriophage structure, function, infection, replication, or characterization
- The paper studies phage therapy, phage biology, or phage ecology

A paper is NOT primarily about bacteriophages if:
- It only mentions phages in passing or as a comparison
- The main focus is on bacterial genetics, signal transduction, introns, or other non-phage topics
- Phages are just incidental mentions

Abstract:
{abstract}

Respond with EXACTLY one word: YES or NO. No explanation needed."""


def get_abstract(json_path: str) -> str:
    """Extract abstract from article JSON file."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # New JSON format: abstract is directly under 'abstract' key
        if 'abstract' in data:
            return data['abstract']
    except Exception as e:
        print(f"Error reading {json_path}: {e}")
    return ""


def is_phage_related(abstract: str, client: DeepSeekClient) -> bool:
    """
    Use LLM to determine if the paper is related to bacteriophages.

    Args:
        abstract: The abstract text of the paper.
        client: DeepSeekClient instance.

    Returns:
        True if the paper is bacteriophage-related, False otherwise.
    """
    if not abstract:
        return False

    user_prompt = USER_PROMPT_TEMPLATE.format(abstract=abstract)

    try:
        response = client.call(
            system_prompt=SYSTEM_PROMPT,
            user_input=user_prompt,
            temperature=0.1,
            max_tokens=50
        )

        # Debug: print full response
        print(f"  LLM Response: {response}")

        content = response.get("content", "")
        if content is None:
            content = ""
        content_upper = content.strip().upper()

        # 检查是否包含 YES
        result = "YES" in content_upper
        print(f"  => Result: {result}")
        return result

    except Exception as e:
        print(f"  Error calling LLM: {e}")
        return False


def copy_json_to_sorted(json_path: str, output_dir: str) -> str:
    """
    Copy JSON file to sorted output directory.

    Args:
        json_path: Source JSON file path.
        output_dir: Output directory path.

    Returns:
        Destination file path.
    """
    paper_name = os.path.basename(json_path)
    dest_path = os.path.join(output_dir, paper_name)

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Copy the JSON file
    shutil.copy2(json_path, dest_path)

    return dest_path


def process_papers() -> Dict[str, List[str]]:
    """
    Process all papers in input directory and sort bacteriophage-related ones.

    Returns:
        Dictionary with 'phage_related' and 'non_phage_related' paper lists.
    """
    # Initialize LLM client
    client = DeepSeekClient(
        base_url=LLM_BASE_URL,
        api_key=LLM_API_KEY,
        model=LLM_MODEL
    )

    # Get all JSON files (not folders)
    json_files = sorted([
        f for f in os.listdir(INPUT_DIR)
        if f.endswith('.json')
    ])

    results = {
        "phage_related": [],
        "non_phage_related": []
    }

    print(f"Found {len(json_files)} papers to process")
    print("=" * 60)

    for i, json_file in enumerate(json_files, 1):
        paper_name = json_file.replace('.json', '')
        json_path = os.path.join(INPUT_DIR, json_file)

        print(f"\n[{i}/{len(json_files)}] Processing: {paper_name}")

        # Get abstract
        abstract = get_abstract(json_path)

        if not abstract:
            print(f"  No abstract found, skipping...")
            results["non_phage_related"].append(paper_name)
            continue

        # Show abstract preview (first 100 chars)
        print(f"  Abstract preview: {abstract[:100]}...")

        # Check if it's phage-related using LLM
        is_phage = is_phage_related(abstract, client)

        if is_phage:
            print(f"  => Phage-related: YES")
            # Copy to sorted folder
            dest = copy_json_to_sorted(json_path, OUTPUT_DIR)
            print(f"  => Copied to: {dest}")
            results["phage_related"].append(paper_name)
        else:
            print(f"  => Phage-related: NO")
            results["non_phage_related"].append(paper_name)

    return results


def main():
    """Main entry point."""
    print("=" * 60)
    print("Bacteriophage Paper Sorter")
    print("=" * 60)
    print(f"Input:  {INPUT_DIR}")
    print(f"Output: {OUTPUT_DIR}")
    print("=" * 60)

    # Process papers
    results = process_papers()

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Phage-related papers: {len(results['phage_related'])}")
    for paper in results['phage_related']:
        print(f"  + {paper}")

    print(f"\nNon-phage-related papers: {len(results['non_phage_related'])}")
    for paper in results['non_phage_related']:
        print(f"  - {paper}")

    print("\nDone!")


if __name__ == "__main__":
    main()
