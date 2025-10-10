# HTML Documentation Generator

This module generates a static HTML website from the documentation markdown files.

## Features

- Converts markdown to HTML with syntax highlighting
- Generates a responsive left-hand navigation from `hierarchy.md`
- Processes images, tables, videos, and code blocks
- Creates a beautiful, modern documentation website
- No external dependencies (runs locally)

## Installation

First, install the required dependencies:

```bash
pip install markdown pygments
```

Or if you're using the project's dependency groups:

```bash
pip install -e ".[github_readme_sync_tool]"
```

## Usage

### Generate HTML Documentation

To generate the HTML documentation:

```bash
python -m tools.github_readme_sync.cli generate-html docs
```

This will:
1. Read the `docs/hierarchy.md` file
2. Process all markdown files according to the hierarchy
3. Convert markdown to HTML with syntax highlighting
4. Copy assets (images, etc.)
5. Generate navigation
6. Create a complete static website in a temporary directory

### Specify Output Directory

To specify a custom output directory:

```bash
python -m tools.github_readme_sync.cli generate-html docs --output /path/to/output
```

### View the Documentation

After generation, open the `index.html` file in your browser:

```bash
open /path/to/output/index.html
```

## Structure

The generated website has the following structure:

```
output_dir/
├── index.html           # Home page
├── docs/               # All documentation pages
│   ├── page1.html
│   ├── page2.html
│   └── ...
├── assets/             # Images and media
│   └── figures/
│       └── ...
├── css/                # Stylesheets
│   ├── style.css
│   └── highlight.css
└── js/                 # JavaScript
    └── main.js
```

## How It Works

1. **Hierarchy Parsing**: Reads `hierarchy.md` to understand document structure
2. **Markdown Processing**: Converts markdown to HTML with:
   - Syntax highlighting for code blocks
   - Image processing with relative paths
   - Table generation from CSV files
   - Video embedding (YouTube and Cloudinary)
   - Link correction for cross-references
3. **Navigation Generation**: Creates a hierarchical navigation menu
4. **Template Application**: Wraps content in HTML templates with navigation
5. **Asset Copying**: Copies images and other assets to the output directory

## Customization

### CSS Styling

The CSS is generated in `HtmlGenerator.generate_css()`. You can modify this method to customize:
- Colors
- Fonts
- Layout
- Responsive breakpoints

### HTML Templates

The HTML template is in `HtmlGenerator.generate_page_template()`. You can modify:
- Header structure
- Footer content
- Meta tags
- Script includes

### JavaScript

The JavaScript is in `HtmlGenerator.generate_javascript()`. Current features:
- Active navigation highlighting
- Copy buttons for code blocks
- Smooth scrolling (can be added)

## Features

### Markdown Extensions

Supported markdown features:
- Headers (H1-H6)
- Lists (ordered and unordered)
- Code blocks with syntax highlighting
- Tables
- Images with captions
- Links
- Blockquotes
- Note/Tip/Warning callouts

### Code Syntax Highlighting

Uses Pygments for syntax highlighting. Supports all languages supported by Pygments.

Example:
\`\`\`python
def hello():
    print("Hello, world!")
\`\`\`

### Images

Images are automatically processed and copied to the assets directory:

```markdown
![Alt text](../figures/image.png)
```

### Tables

Tables can be defined in markdown or loaded from CSV files:

```markdown
!csv[../path/to/table.csv]
```

### Videos

YouTube videos and Cloudinary videos are automatically embedded:

```markdown
[Video Title](https://www.youtube.com/watch?v=VIDEO_ID)
[Video](https://res.cloudinary.com/CLOUD_ID/video/upload/v123/video.mp4)
```

### Callouts

Special callouts for notes, tips, warnings, etc.:

```markdown
[!NOTE] This is a note
[!TIP] This is a tip
[!WARNING] This is a warning
```

## Testing

Run the tests:

```bash
pytest tools/github_readme_sync/tests/test_html_generator.py
```

## Troubleshooting

### Import Errors

If you get import errors for `markdown` or `pygments`, make sure they're installed:

```bash
pip install markdown pygments
```

### Missing Images

If images are not showing up:
1. Check that the `figures/` directory exists in your docs folder
2. Verify image paths in markdown files
3. Check the console output for asset copying messages

### Broken Links

If links between pages are broken:
1. Verify the `hierarchy.md` file is correct
2. Check that all referenced markdown files exist
3. Look for errors in the console output

## Future Enhancements

Potential improvements:
- Search functionality
- Dark mode toggle
- Print-friendly CSS
- PDF export
- Live reload during development
- Better mobile navigation
- Keyboard shortcuts

