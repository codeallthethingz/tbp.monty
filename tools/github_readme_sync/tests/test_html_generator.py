# Copyright 2025 Thousand Brains Project
# Copyright 2024 Numenta Inc.
#
# Copyright may exist in Contributors' modifications
# and/or contributions to the work.
#
# Use of this source code is governed by the MIT
# license that can be found in the LICENSE file or at
# https://opensource.org/licenses/MIT.

import os
import tempfile

import pytest

from tools.github_readme_sync.html_generator import HtmlGenerator


class TestHtmlGenerator:
    def test_init_creates_directories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = HtmlGenerator(tmpdir)
            assert os.path.exists(gen.output_dir)
            assert os.path.exists(gen.assets_dir)
            assert os.path.exists(gen.css_dir)

    def test_correct_file_locations(self):
        gen = HtmlGenerator()
        body = "Check out [this link](./subfolder/some-doc.md) for more."
        result = gen.correct_file_locations(body)
        assert "some-doc.html" in result
        assert ".md" not in result

    def test_correct_image_locations(self):
        gen = HtmlGenerator()
        body = "![alt text](../figures/overview/image.png)"
        result = gen.correct_image_locations(body)
        assert "assets/overview/image.png" in result

    def test_convert_note_tags(self):
        gen = HtmlGenerator()
        body = "[!NOTE] This is important"
        result = gen.convert_note_tags(body)
        assert '<div class="note">' in result

    def test_generate_navigation_html(self):
        gen = HtmlGenerator()
        hierarchy = [
            {
                "title": "Overview",
                "slug": "overview",
                "children": [
                    {"slug": "intro", "children": []},
                ],
            }
        ]
        nav = gen.generate_navigation_html(hierarchy, "intro")
        assert "Overview" in nav
        assert "intro" in nav
        assert 'class="active"' in nav

    def test_generate_page_template(self):
        gen = HtmlGenerator()
        title = "Test Page"
        content = "<p>Test content</p>"
        nav = "<nav>Test nav</nav>"
        breadcrumbs = [("Home", "index.html"), ("Test", None)]
        result = gen.generate_page_template(title, content, nav, breadcrumbs)
        assert "<!DOCTYPE html>" in result
        assert title in result
        assert content in result
        assert nav in result
        assert "breadcrumbs" in result

    def test_process_latex_blocks_with_latex_language(self):
        gen = HtmlGenerator()
        body = "```latex\n\\[\nE = mc^2\n\\]\n```"
        result = gen.process_latex_blocks(body)
        assert '<div class="latex-block">' in result
        assert "E = mc^2" in result

    def test_process_latex_blocks_with_tex_language(self):
        gen = HtmlGenerator()
        body = "```tex\n\\[\nF = ma\n\\]\n```"
        result = gen.process_latex_blocks(body)
        assert '<div class="latex-block">' in result
        assert "F = ma" in result

    def test_process_latex_blocks_with_math_language(self):
        gen = HtmlGenerator()
        body = "```math\n\\[\na^2 + b^2 = c^2\n\\]\n```"
        result = gen.process_latex_blocks(body)
        assert '<div class="latex-block">' in result
        assert "a^2 + b^2 = c^2" in result

    def test_process_latex_blocks_ignores_other_languages(self):
        gen = HtmlGenerator()
        body = "```python\nprint('hello')\n```"
        result = gen.process_latex_blocks(body)
        assert '<div class="latex-block">' not in result
        assert "```python" in result

    def test_process_latex_blocks_multiple_blocks(self):
        gen = HtmlGenerator()
        body = "```latex\n\\[x = 1\\]\n```\n\nSome text\n\n```latex\n\\[y = 2\\]\n```"
        result = gen.process_latex_blocks(body)
        assert result.count('<div class="latex-block">') == 2
        assert "x = 1" in result
        assert "y = 2" in result

    def test_page_template_includes_mathjax(self):
        gen = HtmlGenerator()
        result = gen.generate_page_template("Test", "<p>Test</p>", "<nav></nav>")
        assert "MathJax" in result
        assert "tex-mml-chtml.js" in result
        assert "inlineMath" in result
        assert "displayMath" in result
