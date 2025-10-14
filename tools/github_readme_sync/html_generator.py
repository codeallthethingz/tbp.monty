# Copyright 2025 Thousand Brains Project
# Copyright 2024 Numenta Inc.
#
# Copyright may exist in Contributors' modifications
# and/or contributions to the work.
#
# Use of this source code is governed by the MIT
# license that can be found in the LICENSE file or at
# https://opensource.org/licenses/MIT.

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
    ALLOWED_CSS_PROPERTIES,
    IGNORE_IMAGES,
    REGEX_CLOUDINARY_VIDEO,
    REGEX_CODE_BLOCK,
    REGEX_IMAGE_PATH,
    REGEX_IMAGES,
    REGEX_MARKDOWN_PATH,
    REGEX_YOUTUBE_LINK,
)
from tools.github_readme_sync.md import (
    convert_csv_to_html_table as convert_csv_table_util,
)
from tools.github_readme_sync.md import (
    insert_markdown_snippet as insert_snippet_util,
)


class HtmlGenerator:
    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or tempfile.mkdtemp(prefix="docs_")
        self.assets_dir = os.path.join(self.output_dir, "assets")
        self.css_dir = os.path.join(self.output_dir, "css")
        os.makedirs(self.output_dir, exist_ok=True)
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
        body = self.process_latex_blocks(body)
        body = self.highlight_code_blocks(body)
        body = self.markdown_to_html(body)
        body = self.add_heading_anchors(body)
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
                formatter = HtmlFormatter(cssclass="highlight", noclasses=False)
                highlighted = highlight(code, lexer, formatter)
                return highlighted

            escaped_code = html_module.escape(code)
            return f'<pre><code class="language-{language}">{escaped_code}</code></pre>'

        return REGEX_CODE_BLOCK.sub(replace_code, markdown_text)

    def convert_csv_to_html_table(self, body: str, file_path: str) -> str:
        return convert_csv_table_util(body, file_path)

    def correct_image_locations(self, body: str) -> str:
        new_body = body

        def replace_image_path(match):
            image_filename = match.group(2)
            if image_filename in IGNORE_IMAGES:
                return match.group(0)
            return f"assets/{image_filename}"

        img_tags = re.finditer(r'<img\s+[^>]*src="([^"]*)"[^>]*>', new_body)
        for match in img_tags:
            img_tag = match.group(0)
            src = match.group(1)
            if "../figures/" in src:
                image_path = re.search(REGEX_IMAGE_PATH, src)
                if image_path:
                    image_filename = image_path.group(2)
                    if image_filename not in IGNORE_IMAGES:
                        new_src = f"assets/{image_filename}"
                        new_img_tag = img_tag.replace(src, new_src)
                        new_body = new_body.replace(img_tag, new_img_tag)

        new_body = re.sub(REGEX_IMAGE_PATH, replace_image_path, new_body)
        return new_body

    def correct_file_locations(self, body: str) -> str:
        def replace_path(match):
            matched_text = match.group(0)
            slug = match.group(2).split("/")[-1]
            fragment = match.group(3) or ""
            return f"({slug}.html{fragment})"

        return re.sub(REGEX_MARKDOWN_PATH, replace_path, body)

    def convert_note_tags(self, body: str) -> str:
        tag_classes = {
            r"\[!NOTE\]": ("note", "📘 <strong>Note:</strong>"),
            r"\[!TIP\]": ("tip", "👍 <strong>Tip:</strong>"),
            r"\[!IMPORTANT\]": ("important", "📘 <strong>Important:</strong>"),
            r"\[!WARNING\]": ("warning", "🚧 <strong>Warning:</strong>"),
            r"\[!CAUTION\]": ("caution", "❗️ <strong>Caution:</strong>"),
        }

        pattern = r"^((?:>.*\n?)+)"
        blocks = re.split(pattern, body, flags=re.MULTILINE)

        result = []
        for block in blocks:
            if block.startswith(">"):
                lines = block.split("\n")
                first_line = lines[0] if lines else ""

                converted = False
                for tag_pattern, (css_class, header) in tag_classes.items():
                    if re.search(tag_pattern, first_line):
                        content_lines = []
                        for line in lines:
                            clean_line = re.sub(r"^> ?", "", line)
                            clean_line = re.sub(tag_pattern, "", clean_line)
                            content_lines.append(clean_line)

                        if content_lines:
                            content = "\n".join(content_lines).strip()
                            content_html = self.markdown_to_html(content)
                            div_html = (
                                f'<div class="{css_class}">\n'
                                f"{header}\n{content_html}\n</div>"
                            )
                            result.append(div_html)
                            converted = True
                            break

                if not converted:
                    result.append(block)
            else:
                result.append(block)

        return "".join(result)

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
                    f'<figure><img src="{clean_src}" style="{style}" /></figure>'
                )

            return nh3.clean(
                unsafe_html,
                attributes={
                    "img": {"src", "alt", "style"},
                    "figure": set(),
                    "figcaption": set(),
                },
            )

        return REGEX_IMAGES.sub(replace_image, markdown_text)

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

        return REGEX_CLOUDINARY_VIDEO.sub(replace_video, markdown_text)

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
                f"allowfullscreen></iframe></div>"
            )

        return REGEX_YOUTUBE_LINK.sub(replace_youtube, markdown_text)

    def process_latex_blocks(self, markdown_text: str) -> str:
        latex_blocks = []

        def preserve_latex(match):
            language = match.group(1) or ""
            code = match.group(2)

            if language.lower() in ["latex", "tex", "math"]:
                placeholder = f"__LATEX_BLOCK_{len(latex_blocks)}__"
                latex_blocks.append(code)
                return placeholder

            return match.group(0)

        result = REGEX_CODE_BLOCK.sub(preserve_latex, markdown_text)

        for i, latex_code in enumerate(latex_blocks):
            placeholder = f"__LATEX_BLOCK_{i}__"
            latex_html = f'<div class="latex-block">\n{latex_code}\n</div>'
            result = result.replace(placeholder, latex_html)

        return result

    def insert_markdown_snippet(self, body: str, file_path: str) -> str:
        return insert_snippet_util(body, file_path)

    def add_heading_anchors(self, html_content: str) -> str:
        def add_anchor(match):
            tag = match.group(1)
            content = match.group(2)
            anchor_id = re.sub(r"[^\w\s-]", "", content.lower())
            anchor_id = re.sub(r"[\s_]+", "-", anchor_id)
            return (
                f'<{tag} id="{anchor_id}">'
                f'<a href="#{anchor_id}" class="heading-link">{content}</a>'
                f"</{tag}>"
            )

        pattern = r"<(h[1-6])>(.*?)</h[1-6]>"
        return re.sub(pattern, add_anchor, html_content)

    def generate_navigation_html(self, hierarchy: list, current_slug: str = "") -> str:
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

    def _generate_nav_item(self, doc: dict, current_slug: str, level: int) -> str:
        slug = doc["slug"]
        is_active = slug == current_slug
        has_children = bool(doc.get("children"))
        active_class = ' class="active"' if is_active else ""
        indent_class = f"indent-{level}" if level > 0 else ""

        html_content = f'<li class="{indent_class}" data-slug="{slug}">'
        title_text = slug.replace("-", " ").title()
        escaped_title = html_module.escape(title_text)

        if has_children:
            html_content += (
                f'<a href="{slug}.html"{active_class} has-children">'
                f'<span class="has-children-indicator">› </span>'
                f"{escaped_title}"
                f"</a>"
            )
            html_content += '<ul class="nav-sublist collapsed">'
            for child in doc["children"]:
                child_item = self._generate_nav_item(child, current_slug, level + 1)
                html_content += child_item
            html_content += "</ul>"
        else:
            html_content += f'<a href="{slug}.html"{active_class}>{escaped_title}</a>'

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
    <link rel="stylesheet" href="css/style.css">
    <link rel="stylesheet" href="css/highlight.css">
    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
    <script>
    window.MathJax = {{
        tex: {{
            inlineMath: [['\\\\(', '\\\\)']],
            displayMath: [['\\\\[', '\\\\]']],
            processEscapes: true
        }},
        svg: {{
            fontCache: 'global'
        }}
    }};
    </script>
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
    <script src="js/main.js"></script>
</body>
</html>"""

    def generate_highlight_css(self) -> str:
        formatter = HtmlFormatter(style="colorful")
        return formatter.get_style_defs(".highlight")

    def copy_assets(self, source_docs_dir: str):
        figures_dir = os.path.join(source_docs_dir, "figures")
        if os.path.exists(figures_dir):
            logging.info(f"{CYAN}Copying assets from {figures_dir}...{RESET}")
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

    def generate_document(
        self,
        doc: dict,
        hierarchy: list,
        file_path: str,
        category_slug: str,
        breadcrumbs: list = None,
    ) -> str:
        doc_file_path = os.path.join(file_path, category_slug, f"{doc['slug']}.md")

        if not os.path.exists(doc_file_path):
            logging.error(f"File not found: {doc_file_path}")
            return None

        with open(doc_file_path, "r", encoding="utf-8") as f:
            raw_content = f.read()

        if raw_content.startswith("---"):
            _, frontmatter_str, body = raw_content.split("---", 2)
            frontmatter = yaml.safe_load(frontmatter_str)
            title = frontmatter.get("title", doc["slug"].replace("-", " ").title())
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

        output_file = os.path.join(self.output_dir, f"{doc['slug']}.html")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        logging.info(f"{WHITE}Generated: {doc['slug']}.html{RESET}")
        return output_file

    def generate_index_from_first_doc(self, hierarchy: list, file_path: str) -> str:
        if not hierarchy or not hierarchy[0].get("children"):
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
            return output_file

        first_category = hierarchy[0]
        first_doc = first_category["children"][0]

        doc_file_path = os.path.join(
            file_path, first_category["slug"], f"{first_doc['slug']}.md"
        )

        if not os.path.exists(doc_file_path):
            logging.error(f"First doc not found: {doc_file_path}")
            return None

        with open(doc_file_path, "r", encoding="utf-8") as f:
            raw_content = f.read()

        if raw_content.startswith("---"):
            _, frontmatter_str, body = raw_content.split("---", 2)
            frontmatter = yaml.safe_load(frontmatter_str)
            title = frontmatter.get(
                "title", first_doc["slug"].replace("-", " ").title()
            )
        else:
            body = raw_content
            title = first_doc["slug"].replace("-", " ").title()

        content = self.process_markdown(
            body,
            os.path.join(file_path, first_category["slug"]),
            first_doc["slug"],
        )

        navigation = self.generate_navigation_html(hierarchy, first_doc["slug"])

        html_content = self.generate_page_template(
            title, content, navigation, [("Home", "index.html")]
        )

        output_file = os.path.join(self.output_dir, "index.html")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        logging.info(f"{GREEN}Index page generated from first doc{RESET}")
        return output_file
