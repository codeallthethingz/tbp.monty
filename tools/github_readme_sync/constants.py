# Copyright 2025 Thousand Brains Project
# Copyright 2024 Numenta Inc.
#
# Copyright may exist in Contributors' modifications
# and/or contributions to the work.
#
# Use of this source code is governed by the MIT
# license that can be found in the LICENSE file or at
# https://opensource.org/licenses/MIT.

import re

IGNORE_DOCS = ["placeholder-example-doc", "some-existing-doc"]
IGNORE_IMAGES = ["docs-only-example.png"]
IGNORE_TABLES = ["example-table-for-docs.csv"]

IGNORE_EXTERNAL_URLS = [
    "openai.com",
    "science.org",
    "annualreviews.org",
    "sciencedirect.com",
]

ALLOWED_CSS_PROPERTIES = {"width", "height"}

REGEX_CSV_TABLE = re.compile(r"!table\[(.+?)\]")
REGEX_IMAGES = re.compile(r"!\[(.*?)\]\((.*?)\)")
REGEX_IMAGE_PATH = re.compile(
    r"(\.\./){1,5}figures/((.+)\.(png|jpg|jpeg|gif|svg|webp))"
)
REGEX_MARKDOWN_PATH = re.compile(r"\(([\./]*)([\w\-/]+)\.md(#.*?)?\)")
REGEX_CLOUDINARY_VIDEO = re.compile(
    r"\[(.*?)\]\((https://res\.cloudinary\.com/([^/]+)/video/upload/v(\d+)/([^/]+\.mp4))\)",
    re.IGNORECASE,
)
REGEX_YOUTUBE_LINK = re.compile(
    r"\[(.*?)\]\((https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})(?:[&?][^\)]*)?)\)",
    re.IGNORECASE,
)
REGEX_MARKDOWN_SNIPPET = re.compile(r"!snippet\[(.*?)\]")
REGEX_CODE_BLOCK = re.compile(r"```([^\n]*)?\n(.*?)```", re.DOTALL)
