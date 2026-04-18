#!/usr/bin/env python3
"""
LLM Processing Script - Stage 2 & 3
Extract phage names and detailed properties using LLM

Input: /home/ubuntu/jiajunwang/extraction_trial/data/C_extracted_paragraphs
Output: /home/ubuntu/jiajunwang/extraction_trial/data/D_final
"""

import os
import json
import sys
from typing import Dict, List, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.api_client import DeepSeekClient
from prompts.prompts import STRAIN_EXTRACT_SYS_PROMPT, DETAIL_EXTRACT_SYS_PROMPT
from llm_config import DEEPSEEK_BASE_URL, get_api_key, MODELS

# Configuration
INPUT_DIR = "/home/ubuntu/jiajunwang/extraction_trial/data/C_extracted_paragraphs"
OUTPUT_DIR = "/home/ubuntu/jiajunwang/extraction_trial/data/D_final"

# Model selection - can be changed to use different models
# Available keys: see llm_config.MODELS (DeepSeek official: deepseek-v3, deepseek-chat, deepseek-r1, ...)
DEFAULT_MODEL = "deepseek-v3"


def load_extracted_paragraphs(paper_id: str) -> tuple:
    """Load extracted paragraphs from JSON file.

    Returns:
        tuple: (title, combined_text)
    """
    json_path = os.path.join(INPUT_DIR, f"{paper_id}.json")
    if not os.path.exists(json_path):
        return "", ""

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # New format: {"title": "...", "1": "paragraph", "2": "paragraph", ...}
    title = data.get('title', '')

    # Combine all numbered paragraphs into a single text
    paragraphs = []
    for key, value in data.items():
        if key != 'title' and isinstance(value, str) and value.strip():
            paragraphs.append(value)

    combined_text = "\n\n".join(paragraphs)
    return title, combined_text


def extract_phage_names(text: str, client: DeepSeekClient) -> Dict[str, List[str]]:
    """
    Stage 2: Extract phage names from text using LLM.

    Args:
        text: Combined extracted paragraphs
        client: DeepSeekClient instance

    Returns:
        Dictionary with 'paper_phages' and 'comparison_phages'
    """
    response = client.call(
        system_prompt=STRAIN_EXTRACT_SYS_PROMPT,
        user_input=text,
        temperature=0.1,
        max_tokens=2000
    )

    content = response.get("content", "")

    # Parse JSON response
    try:
        # Find JSON in response (in case LLM adds extra text)
        start_idx = content.find('{')
        end_idx = content.rfind('}') + 1
        if start_idx != -1 and end_idx != 0:
            json_str = content[start_idx:end_idx]
            result = json.loads(json_str)
            return {
                "paper_phages": result.get("paper_phages", []),
                "comparison_phages": result.get("comparison_phages", [])
            }
    except json.JSONDecodeError as e:
        print(f"  Failed to parse JSON: {e}")
        print(f"  Raw response: {content[:500]}")

    return {"paper_phages": [], "comparison_phages": []}


def extract_phage_details(text: str, paper_phages: List[str], client: DeepSeekClient) -> Dict[str, Any]:
    """
    Stage 3: Extract detailed properties for each phage using LLM.

    Args:
        text: Combined extracted paragraphs
        paper_phages: List of phage names to extract details for
        client: DeepSeekClient instance

    Returns:
        Dictionary with summary and phages details
    """
    if not paper_phages:
        return {"summary": "", "phages": {}}

    # Create user input with text and phage list
    user_input = f"""ORIGINAL_TEXT:
{text}

PAPER_PHAGES:
{json.dumps(paper_phages, ensure_ascii=False)}"""

    response = client.call(
        system_prompt=DETAIL_EXTRACT_SYS_PROMPT,
        user_input=user_input,
        temperature=0.1,
        max_tokens=4000
    )

    content = response.get("content", "")

    # Parse JSON response
    try:
        start_idx = content.find('{')
        end_idx = content.rfind('}') + 1
        if start_idx != -1 and end_idx != 0:
            json_str = content[start_idx:end_idx]
            result = json.loads(json_str)
            return result
    except json.JSONDecodeError as e:
        print(f"  Failed to parse JSON: {e}")
        print(f"  Raw response: {content[:500]}")

    return {"summary": "", "phages": {}}


def process_paper(paper_id: str, client: DeepSeekClient) -> Dict[str, Any]:
    """
    Process a single paper: extract phage names and details.

    Args:
        paper_id: Paper identifier
        client: DeepSeekClient instance

    Returns:
        Dictionary with extraction results
    """
    print(f"\n[Processing] {paper_id}")

    # Step 1: Load extracted paragraphs
    title, text = load_extracted_paragraphs(paper_id)
    if not text:
        print(f"  No extracted paragraphs found")
        return {"error": "No extracted paragraphs", "title": title}

    print(f"  Title: {title[:60]}..." if title else "  No title")
    print(f"  Text length: {len(text)} characters")

    # Step 2: Stage 2 - Extract phage names
    print(f"  [Stage 2] Extracting phage names...")
    phage_names_result = extract_phage_names(text, client)
    # Combine paper_phages and comparison_phages into a single list
    all_phages = phage_names_result.get("paper_phages", []) + phage_names_result.get("comparison_phages", [])
    print(f"  Extracted {len(all_phages)} phage names: {all_phages}")

    # Step 3: Stage 3 - Extract detailed properties
    print(f"  [Stage 3] Extracting phage details...")
    phage_properties = {}
    summary = ""
    if all_phages:
        details = extract_phage_details(text, all_phages, client)
        phage_properties = details.get("phages", {})
        summary = details.get("summary", "")
        print(f"  Extracted properties for {len(phage_properties)} phages")

    # Structure with title and phage entries
    return {
        "title": title,
        "summary": summary,
        "phages": phage_properties
    }


def save_result(paper_id: str, result: Dict[str, Any]):
    """Save extraction result to output file."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    output_path = os.path.join(OUTPUT_DIR, f"{paper_id}.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"  Saved to: {output_path}")


def main():
    """Main entry point."""
    print("=" * 60)
    print("LLM Processing - Stage 2 & 3")
    print("=" * 60)
    print(f"Input:  {INPUT_DIR}")
    print(f"Output: {OUTPUT_DIR}")
    print(f"Model:  {DEFAULT_MODEL}")
    print("=" * 60)

    # Initialize LLM client
    client = DeepSeekClient(
        base_url=DEEPSEEK_BASE_URL,
        api_key=get_api_key(),
        model=MODELS[DEFAULT_MODEL]
    )

    # Get all JSON files in input directory
    json_files = [f.replace('.json', '') for f in os.listdir(INPUT_DIR) if f.endswith('.json')]

    if not json_files:
        print("No JSON files found in input directory")
        return

    print(f"Found {len(json_files)} papers to process")

    # Process each paper
    results = []
    for i, paper_id in enumerate(sorted(json_files), 1):
        print(f"\n[{i}/{len(json_files)}]")
        try:
            result = process_paper(paper_id, client)
            save_result(paper_id, result)
            results.append({"paper_id": paper_id, "status": "success"})
        except Exception as e:
            print(f"  Error: {e}")
            results.append({"paper_id": paper_id, "status": "error", "message": str(e)})

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    success_count = sum(1 for r in results if r.get("status") == "success")
    print(f"Processed: {len(results)} papers")
    print(f"Success:   {success_count}")
    print(f"Failed:    {len(results) - success_count}")

    print("\nDone!")


if __name__ == "__main__":
    main()