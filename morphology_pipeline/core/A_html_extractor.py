#!/usr/bin/env python3
"""
HTML Article Section Extractor

Extracts academic paper sections from HTML using <section> tags.
Outputs: title, abstract, body sections with global paragraph numbering.
Excludes: references, acknowledgments.

Output structure:
{
    "title": "...",
    "abstract": "...",
    "MATERIALS AND METHODS": [
        {"para_id": 1, "content": "段落内容"},
        {"para_id": 2, "content": "段落内容"},
        ...
    ],
    "RESULTS": [...],
    "DISCUSSION": [...]
}
"""

import json
import re
import os
from typing import Dict, List, Optional
from bs4 import BeautifulSoup


def extract_article_from_html(html_path: str) -> Dict:
    """
    Extract article content from HTML file using <section> tags.
    """
    with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, 'html.parser')

    result = {}
    global_para_id = 0

    # 1. Extract title
    title_tag = soup.find('title')
    if title_tag:
        title = title_tag.get_text().strip()
        title = re.sub(r'\s*\|\s*Journal.*$', '', title)
        result['title'] = title

    # 2. Extract abstract
    all_sections = {s.get('id'): s for s in soup.find_all('section', id=True)}
    if 'abstract' in all_sections:
        abstract_sec = all_sections['abstract']
        abstract_text = abstract_sec.get_text(separator=' ', strip=True)
        abstract_text = re.sub(r'^ABSTRACT\s*', '', abstract_text)
        abstract_text = re.sub(r'\s+', ' ', abstract_text).strip()
        result['abstract'] = abstract_text

    # 3. Extract supplementary materials
    if 'supplementary-materials' in all_sections:
        supp_sec = all_sections['supplementary-materials']
        supp_paragraphs = extract_paragraphs_from_section(supp_sec, global_para_id)
        if supp_paragraphs:
            result['supplementary materials'] = supp_paragraphs
            global_para_id = supp_paragraphs[-1]['para_id']

    # 4. Extract body sections
    bodymatter = soup.find('section', id='bodymatter')
    if bodymatter:
        # 获取顶级章节 (sec-1, sec-2, etc.)
        all_body_sections = bodymatter.find_all('section', id=True)
        top_level_map = {}

        for sec in all_body_sections:
            sid = sec.get('id')
            if sid.startswith('sec-') and len(sid.split('-')) == 2:
                if sid not in top_level_map:
                    top_level_map[sid] = sec

        # 按顺序处理每个顶级章节
        for sid in sorted(top_level_map.keys(), key=lambda x: int(x.split('-')[1])):
            sec_elem = top_level_map[sid]

            # 获取章节标题
            title_elem = sec_elem.find(['h1', 'h2', 'h3', 'h4'])
            section_title = title_elem.get_text().strip() if title_elem else sid

            # 提取该章节下的所有段落
            paragraphs = extract_paragraphs_from_section(sec_elem, global_para_id)

            if paragraphs:
                result[section_title] = paragraphs
                global_para_id = paragraphs[-1]['para_id']

    return result


def extract_paragraphs_from_section(section_elem, start_para_id: int) -> List[Dict]:
    """
    Extract all paragraphs from a section element.

    优先提取HTML中的<div>作为独立段落，如果没有<div>则提取子章节。

    Args:
        section_elem: BeautifulSoup section element
        start_para_id: 起始段落编号

    Returns:
        List of paragraph dicts with para_id and content
    """
    paragraphs = []
    para_id = start_para_id

    # 1. 首先检查是否有直接的<div>子元素（这代表真正的段落）
    direct_divs = []
    for child in section_elem.children:
        if hasattr(child, 'name') and child.name == 'div':
            # 检查这个div是否是段落（不是空标签）
            text = child.get_text(strip=True)
            if text and len(text) > 20:
                direct_divs.append(text)

    if direct_divs:
        # 有直接<div>，提取每个div作为独立段落
        for div_text in direct_divs:
            # 清理文本
            div_text = re.sub(r'\s+', ' ', div_text).strip()
            if div_text and len(div_text) > 20:
                para_id += 1
                paragraphs.append({
                    "para_id": para_id,
                    "content": div_text
                })
        return paragraphs

    # 2. 没有<div>，检查是否有子章节
    child_sections = section_elem.find_all('section', id=True)

    if child_sections:
        # 有子章节 - 提取每个子章节的内容
        for subsec in child_sections:
            sub_id = subsec.get('id')

            # 获取子章节标题
            title_elem = subsec.find(['h1', 'h2', 'h3', 'h4'])
            sub_title = title_elem.get_text().strip() if title_elem else ""

            # 获取内容
            content = subsec.get_text(separator=' ', strip=True)
            # 清理：去掉标题
            if sub_title:
                content = re.sub(r'^' + re.escape(sub_title) + r'\s*', '', content)
            content = re.sub(r'\s+', ' ', content).strip()

            if content and len(content) > 20:
                para_id += 1
                paragraphs.append({
                    "para_id": para_id,
                    "content": content
                })
    else:
        # 3. 既没有<div>也没有子章节，把整个section作为一段
        title_elem = section_elem.find(['h1', 'h2', 'h3', 'h4'])
        section_title = title_elem.get_text().strip() if title_elem else ""

        content = section_elem.get_text(separator=' ', strip=True)
        if section_title:
            content = re.sub(r'^' + re.escape(section_title) + r'\s*', '', content)
        content = re.sub(r'\s+', ' ', content).strip()

        if content and len(content) > 20:
            para_id += 1
            paragraphs.append({
                "para_id": para_id,
                "content": content
            })

    return paragraphs


def save_sections_to_json(html_path: str, output_path: str) -> Dict:
    """Extract sections and save to JSON file."""
    data = extract_article_from_html(html_path)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return data


def process_all_articles(input_dir: str, output_dir: str):
    """Process all HTML files in input directory."""
    os.makedirs(output_dir, exist_ok=True)
    processed = []
    folders = sorted([f for f in os.listdir(input_dir) if os.path.isdir(os.path.join(input_dir, f))])

    for folder in folders:
        folder_path = os.path.join(input_dir, folder)
        html_path = os.path.join(folder_path, "article.html")

        if not os.path.exists(html_path):
            continue

        output_path = os.path.join(output_dir, f"{folder}.json")
        print(f"  Processing: {folder}")
        try:
            save_sections_to_json(html_path, output_path)
            processed.append(folder)
            print(f"    -> Saved")
        except Exception as e:
            print(f"    -> Error: {e}")

    return processed


# ============================================================================
# Main
# ============================================================================

def main():
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="Extract academic paper sections from HTML")
    parser.add_argument("html_file", help="Path to HTML file (or input directory for batch)")
    parser.add_argument("--output", "-o", help="Output JSON file path (or output directory)")
    parser.add_argument("--batch", action="store_true", help="Batch process all articles")

    args = parser.parse_args()

    if args.batch:
        input_dir = args.html_file
        output_dir = args.output if args.output else input_dir.replace('ten_examples', 'A_html2article')
        print("=" * 60)
        print("Batch Processing")
        print("=" * 60)
        processed = process_all_articles(input_dir, output_dir)
        print(f"\nProcessed {len(processed)} articles")
    else:
        if not args.output:
            print("Error: --output is required")
            sys.exit(1)
        result = save_sections_to_json(args.html_file, args.output)
        print(f"Saved to: {args.output}")


if __name__ == "__main__":
    main()
