# Copyright 2025 Thousand Brains Project
# Copyright 2024 Numenta Inc.
#
# Copyright may exist in Contributors' modifications
# and/or contributions to the work.
#
# Use of this source code is governed by the MIT
# license that can be found in the LICENSE file or at
# https://opensource.org/licenses/MIT.

import logging
import shutil
from pathlib import Path

from tools.github_readme_sync.colors import BLUE, CYAN, GREEN, RESET, WHITE
from tools.github_readme_sync.hierarchy import check_hierarchy_file
from tools.github_readme_sync.html_generator import HtmlGenerator


def generate_html_docs(source_dir: str, output_dir: str = None):
    logging.info(f"{BLUE}Starting HTML documentation generation...{RESET}")
    logging.info(f"{WHITE}Source directory: {source_dir}{RESET}")

    generator = HtmlGenerator(output_dir)

    hierarchy = check_hierarchy_file(source_dir)

    logging.info(f"{CYAN}Processing hierarchy...{RESET}")

    html_assets_dir = Path(__file__).parent / "html_assets"
    shutil.copytree(html_assets_dir, generator.output_dir, dirs_exist_ok=True)

    highlight_css_path = Path(generator.css_dir) / "highlight.css"
    with open(highlight_css_path, "w") as f:
        f.write(generator.generate_highlight_css())

    generator.copy_assets(source_dir)

    for category in hierarchy:
        logging.info(f"\n{BLUE}Processing category: {category['title']}{RESET}")

        process_category_children(
            generator=generator,
            parent=category,
            file_path=source_dir,
            hierarchy=hierarchy,
            breadcrumbs=[
                ("Home", "index.html"),
                (category["title"], None),
            ],
        )

    generator.generate_index_from_first_doc(hierarchy, source_dir)

    logging.info(
        f"\n{GREEN}HTML documentation generated successfully!{RESET}"
    )
    logging.info(f"{GREEN}Output directory: {generator.output_dir}{RESET}")
    index_path = f"{generator.output_dir}/index.html"
    logging.info(f"{WHITE}Open {index_path} in your browser{RESET}")

    return generator.output_dir


def process_category_children(
    generator: HtmlGenerator,
    parent: dict,
    file_path: str,
    hierarchy: list,
    breadcrumbs: list = None,
    path_prefix: str = "",
):
    for child in parent.get("children", []):
        current_breadcrumbs = breadcrumbs + [
            (child["slug"], f"{child['slug']}.html")
        ]

        generator.generate_document(
            doc=child,
            hierarchy=hierarchy,
            file_path=file_path,
            category_slug=f"{path_prefix}{parent['slug']}",
            breadcrumbs=current_breadcrumbs,
        )

        if child.get("children"):
            process_category_children(
                generator=generator,
                parent=child,
                file_path=file_path,
                hierarchy=hierarchy,
                breadcrumbs=current_breadcrumbs,
                path_prefix=f"{path_prefix}{parent['slug']}/",
            )

