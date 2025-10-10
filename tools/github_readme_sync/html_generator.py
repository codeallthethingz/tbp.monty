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
import logging
import os
import re
import shutil
import tempfile
from urllib.parse import parse_qs

import markdown
import nh3
import yaml
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound

from tools.github_readme_sync.colors import CYAN, GREEN, RESET, WHITE
from tools.github_readme_sync.constants import (
    IGNORE_IMAGES,
    IGNORE_TABLES,
    REGEX_CSV_TABLE,
)

regex_images = re.compile(r"!\[(.*?)\]\((.*?)\)")
regex_image_path = re.compile(
    r"(\.\./){1,5}figures/((.+)\.(png|jpg|jpeg|gif|svg|webp))"
)
regex_markdown_path = re.compile(r"\(([\./]*)([\w\-/]+)\.md(#.*?)?\)")
regex_cloudinary_video = re.compile(
    r"\[(.*?)\]\((https://res\.cloudinary\.com/([^/]+)/video/upload/v(\d+)/([^/]+\.mp4))\)",
    re.IGNORECASE,
)
regex_youtube_link = re.compile(
    r"\[(.*?)\]\((https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})(?:[&?][^\)]*)?)\)",
    re.IGNORECASE,
)
regex_markdown_snippet = re.compile(r"!snippet\[(.*?)\]")
regex_code_block = re.compile(r"```(\w+)?\n(.*?)```", re.DOTALL)

ALLOWED_CSS_PROPERTIES = {"width", "height"}


class HtmlGenerator:
    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or tempfile.mkdtemp(prefix="docs_")
        self.docs_dir = os.path.join(self.output_dir, "docs")
        self.assets_dir = os.path.join(self.output_dir, "assets")
        self.css_dir = os.path.join(self.output_dir, "css")
        os.makedirs(self.docs_dir, exist_ok=True)
        os.makedirs(self.assets_dir, exist_ok=True)
        os.makedirs(self.css_dir, exist_ok=True)
        logging.info(f"{GREEN}Output directory: {self.output_dir}{RESET}")

    def process_markdown(self, body: str, file_path: str, slug: str) -> str:
        body = self.insert_markdown_snippet(body, file_path)
        body = self.convert_csv_to_html_table(body, file_path)
        body = self.correct_image_locations(body)
        body = self.correct_file_locations(body)
        body = self.convert_note_tags(body)
        body = self.parse_images(body)
        body = self.convert_cloudinary_videos(body)
        body = self.convert_youtube_videos(body)
        body = self.highlight_code_blocks(body)
        body = self.markdown_to_html(body)
        return body

    def markdown_to_html(self, markdown_text: str) -> str:
        md = markdown.Markdown(
            extensions=[
                "extra",
                "codehilite",
                "fenced_code",
                "tables",
                "nl2br",
                "sane_lists",
            ],
            extension_configs={
                "codehilite": {
                    "css_class": "highlight",
                    "linenums": False,
                }
            },
        )
        return md.convert(markdown_text)

    def highlight_code_blocks(self, markdown_text: str) -> str:
        def replace_code(match):
            language = match.group(1) or "text"
            code = match.group(2)

            lexer = None
            try:
                lexer = get_lexer_by_name(language, stripall=True)
            except ClassNotFound:
                pass

            if lexer:
                formatter = HtmlFormatter(
                    cssclass="highlight", noclasses=False
                )
                highlighted = highlight(code, lexer, formatter)
                return highlighted

            escaped_code = html_module.escape(code)
            return (
                f'<pre><code class="language-{language}">'
                f"{escaped_code}</code></pre>"
            )

        return regex_code_block.sub(replace_code, markdown_text)

    def convert_csv_to_html_table(self, body: str, file_path: str) -> str:
        def replace_match(match):
            csv_path = match.group(1)
            table_name = os.path.basename(csv_path)
            if table_name in IGNORE_TABLES:
                return match.group(0)

            csv_path = os.path.join(file_path, csv_path)
            csv_path = os.path.normpath(csv_path)

            try:
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
                                if align_value in ["left", "right"]:
                                    escaped_align = html_module.escape(
                                        align_value
                                    )
                                    alignments[i] = (
                                        f" style='text-align:{escaped_align}'"
                                    )
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

            except Exception as e:  # noqa: BLE001
                return f"[Failed to load table from {csv_path} - {e}]"

        return REGEX_CSV_TABLE.sub(replace_match, body)

    def correct_image_locations(self, body: str) -> str:
        new_body = body

        def replace_image_path(match):
            image_filename = match.group(2)
            if image_filename in IGNORE_IMAGES:
                return match.group(0)
            return f"../assets/{image_filename}"

        img_tags = re.finditer(r'<img\s+[^>]*src="([^"]*)"[^>]*>', new_body)
        for match in img_tags:
            img_tag = match.group(0)
            src = match.group(1)
            if "../figures/" in src:
                image_path = re.search(regex_image_path, src)
                if image_path:
                    image_filename = image_path.group(2)
                    if image_filename not in IGNORE_IMAGES:
                        new_src = f"../assets/{image_filename}"
                        new_img_tag = img_tag.replace(src, new_src)
                        new_body = new_body.replace(img_tag, new_img_tag)

        new_body = re.sub(regex_image_path, replace_image_path, new_body)
        return new_body

    def correct_file_locations(self, body: str) -> str:
        def replace_path(match):
            matched_text = match.group(0)
            slug = match.group(2).split("/")[-1]
            fragment = match.group(3) or ""
            return f"({slug}.html{fragment})"

        return re.sub(regex_markdown_path, replace_path, body)

    def convert_note_tags(self, body: str) -> str:
        conversions = {
            r"\[!NOTE\]": '<div class="note">📘 <strong>Note:</strong>',
            r"\[!TIP\]": '<div class="tip">👍 <strong>Tip:</strong>',
            r"\[!IMPORTANT\]": '<div class="important">📘 <strong>Important:</strong>',
            r"\[!WARNING\]": '<div class="warning">🚧 <strong>Warning:</strong>',
            r"\[!CAUTION\]": '<div class="caution">❗️ <strong>Caution:</strong>',
        }

        for old, new in conversions.items():
            body = re.sub(old, new, body)
            body = re.sub(r"(</div>.*?)(\n\n|$)", r"\1</div>\2", body)

        return body

    def parse_images(self, markdown_text: str) -> str:
        def replace_image(match):
            if any(ignore_image in match.groups()[1] for ignore_image in IGNORE_IMAGES):
                return match.group(0)
            alt_text, image_src = match.groups()

            src_parts = image_src.split("#")
            clean_src = nh3.clean(src_parts[0])
            style = "border-radius: 8px; max-width: 100%;"

            if len(src_parts) > 1:
                try:
                    params = parse_qs(src_parts[1])
                    allowed_styles = []
                    for key, values in params.items():
                        if key in ALLOWED_CSS_PROPERTIES:
                            safe_key = nh3.clean(key)
                            safe_value = nh3.clean(values[0])
                            allowed_styles.append(f"{safe_key}: {safe_value}")
                    if allowed_styles:
                        style = f"{style} " + "; ".join(allowed_styles)
                except (ValueError, ImportError):
                    pass

            if alt_text:
                clean_alt = nh3.clean(alt_text)
                unsafe_html = (
                    f'<figure><img src="{clean_src}" alt="{clean_alt}" '
                    f'style="{style}" />'
                    f"<figcaption>{clean_alt}</figcaption></figure>"
                )
            else:
                unsafe_html = (
                    f'<figure><img src="{clean_src}" style="{style}" />'
                    f"</figure>"
                )

            return nh3.clean(
                unsafe_html,
                attributes={
                    "img": {"src", "alt", "style"},
                    "figure": set(),
                    "figcaption": set(),
                },
            )

        return regex_images.sub(replace_image, markdown_text)

    def convert_cloudinary_videos(self, markdown_text: str) -> str:
        def replace_video(match):
            title, full_url, cloud_id, version, filename = match.groups()
            base_url = "https://res.cloudinary.com"
            new_url = f"{base_url}/{cloud_id}/video/upload/v{version}/{filename}"
            poster_url = new_url.replace(".mp4", ".jpg")
            return (
                f'<div class="video-container">'
                f'<video width="640" height="360" controls '
                f'poster="{poster_url}">'
                f'<source src="{new_url}" type="video/mp4">'
                f"Your browser does not support the video tag.</video></div>"
            )

        return regex_cloudinary_video.sub(replace_video, markdown_text)

    def convert_youtube_videos(self, markdown_text: str) -> str:
        def replace_youtube(match):
            title, full_url, video_id = match.groups()
            embed_url = f"https://www.youtube.com/embed/{video_id}"
            escaped_title = html_module.escape(title)
            allow_attr = (
                "accelerometer; autoplay; clipboard-write; "
                "encrypted-media; gyroscope; picture-in-picture"
            )
            return (
                f'<div class="video-container">'
                f'<iframe width="854" height="480" '
                f'src="{embed_url}" '
                f'title="{escaped_title}" '
                f'frameborder="0" '
                f'allow="{allow_attr}" '
                f'allowfullscreen></iframe></div>'
            )

        return regex_youtube_link.sub(replace_youtube, markdown_text)

    def insert_markdown_snippet(self, body: str, file_path: str) -> str:
        def replace_match(match):
            snippet_path = os.path.join(file_path, match.group(1))
            snippet_path = os.path.normpath(snippet_path)

            try:
                with open(snippet_path, "r") as f:
                    return f.read()
            except Exception:  # noqa: BLE001
                snippet_error = (
                    f"[File not found or could not be read: {snippet_path}]"
                )
                return snippet_error

        return regex_markdown_snippet.sub(replace_match, body)

    def generate_navigation_html(
        self, hierarchy: list, current_slug: str = ""
    ) -> str:
        nav_html = (
            '<nav class="sidebar"><div class="nav-header">Documentation'
            '</div><ul class="nav-list">'
        )

        for category in hierarchy:
            nav_html += '<li class="nav-category">'
            escaped_title = html_module.escape(category["title"])
            nav_html += f'<div class="category-title">{escaped_title}</div>'
            nav_html += '<ul class="nav-sublist">'

            for doc in category.get("children", []):
                nav_html += self._generate_nav_item(doc, current_slug, 0)

            nav_html += "</ul></li>"

        nav_html += "</ul></nav>"
        return nav_html

    def _generate_nav_item(
        self, doc: dict, current_slug: str, level: int
    ) -> str:
        slug = doc["slug"]
        is_active = slug == current_slug
        active_class = ' class="active"' if is_active else ""
        indent_class = f"indent-{level}" if level > 0 else ""

        html_content = f'<li class="{indent_class}">'
        title_text = slug.replace("-", " ").title()
        escaped_title = html_module.escape(title_text)
        html_content += (
            f'<a href="{slug}.html"{active_class}>{escaped_title}</a>'
        )

        if doc.get("children"):
            html_content += '<ul class="nav-sublist">'
            for child in doc["children"]:
                child_item = self._generate_nav_item(
                    child, current_slug, level + 1
                )
                html_content += child_item
            html_content += "</ul>"

        html_content += "</li>"
        return html_content

    def generate_page_template(
        self, title: str, content: str, navigation: str, breadcrumbs: list = None
    ) -> str:
        breadcrumb_html = ""
        if breadcrumbs:
            breadcrumb_html = '<div class="breadcrumbs">'
            for i, (name, link) in enumerate(breadcrumbs):
                if i > 0:
                    breadcrumb_html += " > "
                if link:
                    escaped_name = html_module.escape(name)
                    breadcrumb_html += f'<a href="{link}">{escaped_name}</a>'
                else:
                    breadcrumb_html += html_module.escape(name)
            breadcrumb_html += "</div>"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html_module.escape(title)} - Documentation</title>
    <link rel="stylesheet" href="../css/style.css">
    <link rel="stylesheet" href="../css/highlight.css">
</head>
<body>
    {navigation}
    <main class="content">
        {breadcrumb_html}
        <article>
            <h1>{html_module.escape(title)}</h1>
            {content}
        </article>
        <footer>
            <p>Thousand Brains Project Documentation</p>
        </footer>
    </main>
    <script src="../js/main.js"></script>
</body>
</html>"""

    def generate_css(self) -> str:
        return """* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, \
Oxygen, Ubuntu, Cantarell, sans-serif;
    line-height: 1.6;
    color: #333;
    background-color: #f5f5f5;
}

.sidebar {
    position: fixed;
    left: 0;
    top: 0;
    width: 280px;
    height: 100vh;
    background-color: #2c3e50;
    color: #ecf0f1;
    overflow-y: auto;
    padding: 20px 0;
    z-index: 1000;
}

.nav-header {
    font-size: 1.5rem;
    font-weight: bold;
    padding: 0 20px 20px;
    border-bottom: 2px solid #34495e;
    margin-bottom: 20px;
}

.nav-list {
    list-style: none;
}

.nav-category {
    margin-bottom: 15px;
}

.category-title {
    font-weight: bold;
    font-size: 0.9rem;
    text-transform: uppercase;
    color: #95a5a6;
    padding: 8px 20px;
    letter-spacing: 0.5px;
}

.nav-sublist {
    list-style: none;
}

.nav-sublist li {
    margin: 2px 0;
}

.nav-sublist a {
    display: block;
    padding: 8px 20px;
    color: #ecf0f1;
    text-decoration: none;
    transition: all 0.2s;
    border-left: 3px solid transparent;
}

.nav-sublist a:hover {
    background-color: #34495e;
    border-left-color: #3498db;
}

.nav-sublist a.active {
    background-color: #34495e;
    border-left-color: #3498db;
    font-weight: bold;
}

.nav-sublist .indent-1 a {
    padding-left: 35px;
    font-size: 0.9rem;
}

.nav-sublist .indent-2 a {
    padding-left: 50px;
    font-size: 0.85rem;
}

.content {
    margin-left: 280px;
    padding: 40px 60px;
    max-width: 1200px;
}

.breadcrumbs {
    font-size: 0.9rem;
    color: #7f8c8d;
    margin-bottom: 20px;
}

.breadcrumbs a {
    color: #3498db;
    text-decoration: none;
}

.breadcrumbs a:hover {
    text-decoration: underline;
}

article {
    background-color: white;
    padding: 40px;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    margin-bottom: 40px;
}

article h1 {
    font-size: 2.5rem;
    margin-bottom: 1.5rem;
    color: #2c3e50;
    border-bottom: 2px solid #ecf0f1;
    padding-bottom: 0.5rem;
}

article h2 {
    font-size: 2rem;
    margin-top: 2rem;
    margin-bottom: 1rem;
    color: #34495e;
}

article h3 {
    font-size: 1.5rem;
    margin-top: 1.5rem;
    margin-bottom: 0.75rem;
    color: #34495e;
}

article h4 {
    font-size: 1.25rem;
    margin-top: 1rem;
    margin-bottom: 0.5rem;
    color: #34495e;
}

article p {
    margin-bottom: 1rem;
}

article a {
    color: #3498db;
    text-decoration: none;
}

article a:hover {
    text-decoration: underline;
}

article ul, article ol {
    margin-left: 2rem;
    margin-bottom: 1rem;
}

article li {
    margin-bottom: 0.5rem;
}

article code {
    background-color: #f8f9fa;
    padding: 2px 6px;
    border-radius: 3px;
    font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
    font-size: 0.9em;
    color: #e74c3c;
}

article pre {
    background-color: #f8f9fa;
    padding: 1rem;
    border-radius: 5px;
    overflow-x: auto;
    margin-bottom: 1rem;
    border-left: 4px solid #3498db;
}

article pre code {
    background-color: transparent;
    padding: 0;
    color: inherit;
}

article table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 1rem;
}

article th, article td {
    padding: 12px;
    text-align: left;
    border-bottom: 1px solid #ecf0f1;
}

article th {
    background-color: #34495e;
    color: white;
    font-weight: bold;
}

article tr:hover {
    background-color: #f8f9fa;
}

article figure {
    margin: 2rem 0;
    text-align: center;
}

article figure img {
    max-width: 100%;
    height: auto;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

article figcaption {
    margin-top: 0.5rem;
    font-size: 0.9rem;
    color: #7f8c8d;
    font-style: italic;
}

.data-table {
    overflow-x: auto;
    margin: 1.5rem 0;
}

.video-container {
    position: relative;
    padding-bottom: 56.25%;
    height: 0;
    overflow: hidden;
    max-width: 100%;
    margin: 2rem 0;
}

.video-container iframe,
.video-container video {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    border-radius: 8px;
}

.note, .tip, .important, .warning, .caution {
    padding: 1rem;
    margin: 1.5rem 0;
    border-radius: 5px;
    border-left: 4px solid;
}

.note {
    background-color: #e3f2fd;
    border-left-color: #2196f3;
}

.tip {
    background-color: #f1f8e9;
    border-left-color: #8bc34a;
}

.important {
    background-color: #fff3e0;
    border-left-color: #ff9800;
}

.warning {
    background-color: #fff9c4;
    border-left-color: #ffc107;
}

.caution {
    background-color: #ffebee;
    border-left-color: #f44336;
}

footer {
    text-align: center;
    padding: 2rem 0;
    color: #7f8c8d;
    font-size: 0.9rem;
}

@media (max-width: 768px) {
    .sidebar {
        width: 100%;
        height: auto;
        position: relative;
    }
    
    .content {
        margin-left: 0;
        padding: 20px;
    }
    
    article {
        padding: 20px;
    }
}

blockquote {
    border-left: 4px solid #3498db;
    padding-left: 1rem;
    margin: 1.5rem 0;
    color: #7f8c8d;
    font-style: italic;
}
"""

    def generate_highlight_css(self) -> str:
        formatter = HtmlFormatter(style="colorful")
        return formatter.get_style_defs(".highlight")

    def generate_javascript(self) -> str:
        return """document.addEventListener('DOMContentLoaded', function() {
    const links = document.querySelectorAll('.nav-sublist a');
    links.forEach(link => {
        link.addEventListener('click', function(e) {
            links.forEach(l => l.classList.remove('active'));
            this.classList.add('active');
        });
    });

    document.querySelectorAll('pre code').forEach((block) => {
        const button = document.createElement('button');
        button.className = 'copy-button';
        button.textContent = 'Copy';
        button.addEventListener('click', () => {
            navigator.clipboard.writeText(block.textContent);
            button.textContent = 'Copied!';
            setTimeout(() => {
                button.textContent = 'Copy';
            }, 2000);
        });
        block.parentElement.style.position = 'relative';
        block.parentElement.appendChild(button);
    });
});
"""

    def copy_assets(self, source_docs_dir: str):
        figures_dir = os.path.join(source_docs_dir, "figures")
        if os.path.exists(figures_dir):
            logging.info(
                f"{CYAN}Copying assets from {figures_dir}...{RESET}"
            )
            for root, _dirs, files in os.walk(figures_dir):
                for file in files:
                    if file.lower().endswith(
                        (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")
                    ):
                        src_path = os.path.join(root, file)
                        rel_path = os.path.relpath(root, figures_dir)
                        dest_dir = os.path.join(self.assets_dir, rel_path)
                        os.makedirs(dest_dir, exist_ok=True)
                        dest_path = os.path.join(dest_dir, file)
                        shutil.copy2(src_path, dest_path)
            logging.info(f"{GREEN}Assets copied successfully{RESET}")

    def write_static_files(self):
        css_path = os.path.join(self.css_dir, "style.css")
        with open(css_path, "w") as f:
            f.write(self.generate_css())

        highlight_css_path = os.path.join(self.css_dir, "highlight.css")
        with open(highlight_css_path, "w") as f:
            f.write(self.generate_highlight_css())

        js_dir = os.path.join(self.output_dir, "js")
        os.makedirs(js_dir, exist_ok=True)
        js_path = os.path.join(js_dir, "main.js")
        with open(js_path, "w") as f:
            f.write(self.generate_javascript())

        logging.info(f"{GREEN}Static files written{RESET}")

    def generate_document(
        self,
        doc: dict,
        hierarchy: list,
        file_path: str,
        category_slug: str,
        breadcrumbs: list = None,
    ) -> str:
        doc_file_path = os.path.join(
            file_path, category_slug, f"{doc['slug']}.md"
        )

        if not os.path.exists(doc_file_path):
            logging.error(f"File not found: {doc_file_path}")
            return None

        with open(doc_file_path, "r", encoding="utf-8") as f:
            raw_content = f.read()

        if raw_content.startswith("---"):
            _, frontmatter_str, body = raw_content.split("---", 2)
            frontmatter = yaml.safe_load(frontmatter_str)
            title = frontmatter.get(
                "title", doc["slug"].replace("-", " ").title()
            )
        else:
            body = raw_content
            title = doc["slug"].replace("-", " ").title()

        content = self.process_markdown(
            body, os.path.join(file_path, category_slug), doc["slug"]
        )

        navigation = self.generate_navigation_html(hierarchy, doc["slug"])

        html_content = self.generate_page_template(
            title, content, navigation, breadcrumbs
        )

        output_file = os.path.join(self.docs_dir, f"{doc['slug']}.html")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        logging.info(f"{WHITE}Generated: {doc['slug']}.html{RESET}")
        return output_file

    def generate_index(self, hierarchy: list):
        content = """
        <div style="text-align: center; padding: 40px 0;">
            <h2>Welcome to the Documentation</h2>
            <p>Select a topic from the navigation to get started.</p>
        </div>
        """

        navigation = self.generate_navigation_html(hierarchy, "")
        html_content = self.generate_page_template("Home", content, navigation)

        output_file = os.path.join(self.output_dir, "index.html")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        logging.info(f"{GREEN}Index page generated{RESET}")

