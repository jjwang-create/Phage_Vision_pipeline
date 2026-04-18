#!/usr/bin/env python3
"""
Paragraph Extraction Script - Extract paragraphs containing reference keywords

Input: morphology_pipeline/data/B_sorted_paper/*.json
Output: morphology_pipeline/data/C_extracted_paragraphs/*.json

This script:
1. Reads JSON files from B_sorted_paper
2. Extracts all paragraphs (excluding title) that contain keywords from ref_words.txt
3. Outputs JSON with title and extracted paragraphs (renumbered)
"""

import json
import os
import re
from typing import Dict, List

# Configuration
INPUT_DIR = "/home/ubuntu/jiajunwang/extraction_trial/morphology_pipeline/data/B_sorted_paper"
OUTPUT_DIR = "/home/ubuntu/jiajunwang/extraction_trial/morphology_pipeline/data/C_extracted_paragraphs"
REF_WORDS_FILE = "/home/ubuntu/jiajunwang/extraction_trial/morphology_pipeline/data/ref_words.txt"


def load_reference_words(filepath: str) -> List[str]:
    """Load reference keywords from file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        words = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return words


def contains_keyword(text: str, keywords: List[str]) -> bool:
    """
    Check if text contains any of the keywords.

    Args:
        text: Text to search
        keywords: List of keywords

    Returns:
        True if any keyword is found
    """
    text_lower = text.lower()
    for keyword in keywords:
        # Handle regex patterns like gp[0-9]
        if '[' in keyword or ']' in keyword:
            try:
                pattern = keyword.replace('[0-9]', '\\d')
                if re.search(pattern, text_lower):
                    return True
            except:
                pass
        # Regular word matching
        pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
        if re.search(pattern, text_lower):
            return True
    return False


def extract_paragraphs_with_keywords(json_path: str, keywords: List[str]) -> Dict:
    """
    Extract paragraphs containing keywords from article JSON.

    New JSON format:
    {
        "title": "...",
        "1": "paragraph content",
        "2": "paragraph content",
        ...
    }

    Args:
        json_path: Path to article JSON file
        keywords: List of keywords to match

    Returns:
        Dictionary with title and extracted paragraphs
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    result = {}

    # Extract title
    title = data.get('title', '')
    result['title'] = title

    # Always include abstract (regardless of keywords)
    para_id = 0
    abstract = data.get('abstract', '')
    if abstract:
        para_id += 1
        result[str(para_id)] = abstract

    # Extract all paragraphs (everything except title and abstract)
    for key, value in data.items():
        if key == 'title' or key == 'abstract':
            continue

        if isinstance(value, list):
            # It's a list of paragraphs (e.g., MATERIALS AND METHODS, RESULTS, etc.)
            for para in value:
                if isinstance(para, dict):
                    content = para.get('content', '')
                    if content and contains_keyword(content, keywords):
                        para_id += 1
                        result[str(para_id)] = content
                elif isinstance(para, str):
                    # Some sections might be plain strings
                    if para and contains_keyword(para, keywords):
                        para_id += 1
                        result[str(para_id)] = para
        elif isinstance(value, str):
            # Direct string value (e.g., abstract)
            if value and contains_keyword(value, keywords):
                para_id += 1
                result[str(para_id)] = value

    return result


def process_papers():
    """Process all papers and extract paragraphs with keywords."""
    # Load reference words
    keywords = load_reference_words(REF_WORDS_FILE)
    print(f"Loaded {len(keywords)} reference keywords")

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Output directory: {OUTPUT_DIR}")

    # Get all JSON files (not folders)
    json_files = sorted([
        f for f in os.listdir(INPUT_DIR)
        if f.endswith('.json')
    ])

    print(f"Found {len(json_files)} papers to process")
    print("=" * 60)

    results_summary = {}

    for i, json_file in enumerate(json_files, 1):
        paper_name = json_file.replace('.json', '')
        json_path = os.path.join(INPUT_DIR, json_file)

        print(f"\n[{i}/{len(json_files)}] Processing: {paper_name}")

        try:
            # Extract paragraphs with keywords
            extracted = extract_paragraphs_with_keywords(json_path, keywords)

            # Count extracted paragraphs (excluding title)
            para_count = sum(1 for k in extracted.keys() if k != 'title')
            print(f"  Found {para_count} paragraphs with keywords")

            # Save to output file
            output_path = os.path.join(OUTPUT_DIR, f"{paper_name}.json")
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(extracted, f, indent=2, ensure_ascii=False)

            print(f"  Saved to: {output_path}")
            results_summary[paper_name] = para_count

        except Exception as e:
            print(f"  Error: {e}")

    return results_summary


def main():
    """Main entry point."""
    print("=" * 60)
    print("Paragraph Extractor - Keyword-based Paragraph Extraction")
    print("=" * 60)
    print(f"Input:  {INPUT_DIR}")
    print(f"Output: {OUTPUT_DIR}")
    print(f"Keywords: {REF_WORDS_FILE}")
    print("=" * 60)

    # Process papers
    results = process_papers()

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    total = sum(results.values())
    print(f"Total paragraphs extracted: {total}")
    for paper, count in results.items():
        print(f"  {paper}: {count} paragraphs")

    print("\nDone!")


if __name__ == "__main__":
    main()
