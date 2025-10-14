# Copyright 2025 Thousand Brains Project
# Copyright 2024 Numenta Inc.
#
# Copyright may exist in Contributors' modifications
# and/or contributions to the work.
#
# Use of this source code is governed by the MIT
# license that can be found in the LICENSE file or at
# https://opensource.org/licenses/MIT.

import csv
import html as html_module
import os
from typing import Callable, Optional

import nh3
import yaml

from tools.github_readme_sync.constants import (
    IGNORE_TABLES,
    REGEX_CSV_TABLE,
    REGEX_MARKDOWN_SNIPPET,
)


def process_markdown(body: str, slug: str) -> dict:
    doc = {"title": "", "body": "", "hidden": False, "slug": slug}
    frontmatter = parse_frontmatter(body)
    if not frontmatter:
        raise ValueError("No frontmatter found in the document")
    doc["title"] = frontmatter.get("title", "")
    doc["hidden"] = frontmatter.get("hidden", False)
    if "description" in frontmatter:
        doc["description"] = frontmatter.get("description", "")

    body = body.split("---\n", maxsplit=2)
    if len(body) > 2:
        doc["body"] = body[2]
    else:
        doc["body"] = body[0]

    return doc


def parse_frontmatter(file_content):
    if file_content.startswith("---"):
        _, frontmatter, _ = file_content.split("---", 2)
        return yaml.safe_load(frontmatter)
    return {}


def parse_csv_table(
    csv_path: str,
    file_path: str,
    align_validator: Optional[Callable[[str], None]] = None,
) -> str:
    table_name = os.path.basename(csv_path)
    if table_name in IGNORE_TABLES:
        return None

    csv_path = os.path.join(file_path, csv_path)
    csv_path = os.path.normpath(csv_path)

    with open(csv_path, "r") as f:
        reader = csv.reader(f)
        headers = next(reader)
        rows = list(reader)

        unsafe_html = "<div class='data-table'><table>\n<thead>\n<tr>"

        alignments = {}
        for i, unparsed_header in enumerate(headers):
            title_attr = ""
            parts = [p.strip() for p in unparsed_header.split("|")]
            header = parts[0]

            for part in parts[1:]:
                if part.startswith("hover "):
                    hover_text = html_module.escape(part[6:])
                    title_attr = f" title='{hover_text}'"
                elif part.startswith("align "):
                    align_value = part[6:]
                    if align_validator:
                        align_validator(align_value)
                    if align_value in ["left", "right"]:
                        escaped_align = html_module.escape(align_value)
                        alignments[i] = f" style='text-align:{escaped_align}'"
            unsafe_html += f"<th{title_attr}>{header}</th>"
        unsafe_html += "</tr>\n</thead>\n<tbody>\n"

        for row in rows:
            unsafe_html += "<tr>"
            for i, cell in enumerate(row):
                align_style = alignments.get(i, "")
                unsafe_html += f"<td{align_style}>{cell}</td>"
            unsafe_html += "</tr>\n"

        unsafe_html += "</tbody>\n</table></div>"

        return nh3.clean(
            unsafe_html,
            attributes={
                "div": {"class"},
                "th": {"title", "style"},
                "td": {"style"},
            },
        )


def convert_csv_to_html_table(
    body: str,
    file_path: str,
    align_validator: Optional[Callable[[str], None]] = None,
) -> str:
    def replace_match(match):
        csv_path = match.group(1)
        try:
            result = parse_csv_table(csv_path, file_path, align_validator)
            if result is None:
                return match.group(0)
            return result
        except Exception as e:
            return f"[Failed to load table from {csv_path} - {e}]"

    return REGEX_CSV_TABLE.sub(replace_match, body)


def insert_markdown_snippet(
    body: str,
    file_path: str,
    sanitizer: Optional[Callable[[str], str]] = None,
) -> str:
    def replace_match(match):
        snippet_path = os.path.join(file_path, match.group(1))
        snippet_path = os.path.normpath(snippet_path)

        try:
            with open(snippet_path, "r") as f:
                content = f.read()
                if sanitizer:
                    return sanitizer(content)
                return content
        except Exception:
            return f"[File not found or could not be read: {snippet_path}]"

    return REGEX_MARKDOWN_SNIPPET.sub(replace_match, body)
