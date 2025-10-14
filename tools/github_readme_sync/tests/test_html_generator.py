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

    def test_generate_css(self):
        gen = HtmlGenerator()
        css = gen.generate_css()
        assert ".sidebar" in css
        assert ".content" in css
        assert "nav-list" in css

    def test_generate_javascript(self):
        gen = HtmlGenerator()
        js = gen.generate_javascript()
        assert "addEventListener" in js
        assert "DOMContentLoaded" in js

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

