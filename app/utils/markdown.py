"""
Simple markdown to HTML converter for feedback formatting.
Handles the basic markdown patterns used in AI-generated feedback.
"""

import re


def markdown_to_html(text: str) -> str:
    """
    Convert simple markdown to HTML.

    Supports:
    - **bold** -> <strong>bold</strong>
    - * bullet lists
    - Blank lines for paragraphs

    Args:
        text: Markdown text

    Returns:
        HTML text
    """
    if not text:
        return ""

    # Convert **bold** to <strong>bold</strong>
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)

    # Convert bullet lists (* item)
    lines = text.split('\n')
    html_lines = []
    in_list = False

    for line in lines:
        stripped = line.strip()

        # Check if line is a bullet point
        if stripped.startswith('* ') or stripped.startswith('- '):
            if not in_list:
                html_lines.append('<ul>')
                in_list = True
            # Remove the bullet and wrap in <li>
            item_text = stripped[2:]  # Remove '* ' or '- '
            html_lines.append(f'<li>{item_text}</li>')
        else:
            # Close list if we were in one
            if in_list:
                html_lines.append('</ul>')
                in_list = False

            # Add the line (preserve blank lines for spacing)
            if stripped:
                html_lines.append(line)
            else:
                html_lines.append('<br>')

    # Close list if still open
    if in_list:
        html_lines.append('</ul>')

    return '\n'.join(html_lines)
