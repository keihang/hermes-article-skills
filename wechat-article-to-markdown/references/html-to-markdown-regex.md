# HTML to Markdown Regex Converter

When `html2text` is unavailable, use this Python regex-based converter as a fallback.

## Full Converter Function

```python
import re

def html_to_markdown(html: str) -> str:
    text = html

    # Remove style/script tags
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)

    # Tables (convert to markdown format)
    def convert_table(match):
        table_html = match.group(0)
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, re.DOTALL)
        if not rows:
            return table_html
        
        md_rows = []
        for i, row in enumerate(rows):
            cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL)
            cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
            if cells:
                md_rows.append('| ' + ' | '.join(cells) + ' |')
                if i == 0:
                    md_rows.append('| ' + ' | '.join(['---'] * len(cells)) + ' |')
        
        return '\n' + '\n'.join(md_rows) + '\n'
    
    text = re.sub(r'<table[^>]*>.*?</table>', convert_table, text, flags=re.DOTALL)

    # Images (prefer data-src for lazy-loaded images like WeChat)
    text = re.sub(r'<img[^>]*data-src="([^"]*)"[^>]*/?>', r'\n![图片](\1)\n', text)
    text = re.sub(r'<img[^>]*src="([^"]*)"[^>]*/?>', r'\n![图片](\1)\n', text)

    # Headers (process from h6 to h1 to avoid conflicts)
    for i in range(6, 0, -1):
        text = re.sub(rf'<h{i}[^>]*>(.*?)</h{i}>', rf'\n{"#" * i} \1\n', text, flags=re.DOTALL)

    # Bold
    text = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', text, flags=re.DOTALL)
    text = re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', text, flags=re.DOTALL)

    # Italic
    text = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', text, flags=re.DOTALL)
    text = re.sub(r'<i[^>]*>(.*?)</i>', r'*\1*', text, flags=re.DOTALL)

    # Code blocks and inline code
    text = re.sub(r'<pre[^>]*><code[^>]*>(.*?)</code></pre>', r'\n```\n\1\n```\n', text, flags=re.DOTALL)
    text = re.sub(r'<code[^>]*>(.*?)</code>', r'`\1`', text, flags=re.DOTALL)

    # Lists
    text = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1', text, flags=re.DOTALL)
    text = re.sub(r'<ul[^>]*>|</ul>', '\n', text)
    text = re.sub(r'<ol[^>]*>|</ol>', '\n', text)

    # Blockquote
    text = re.sub(r'<blockquote[^>]*>(.*?)</blockquote>', lambda m: '\n> ' + m.group(1).strip() + '\n', text, flags=re.DOTALL)

    # Paragraphs and line breaks
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'<p[^>]*>(.*?)</p>', r'\n\1\n', text, flags=re.DOTALL)

    # Links
    text = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r'[\2](\1)', text, flags=re.DOTALL)

    # Remove remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)

    # Decode HTML entities
    entities = {'&nbsp;': ' ', '&amp;': '&', '&lt;': '<', '&gt;': '>', '&quot;': '"'}
    for ent, char in entities.items():
        text = text.replace(ent, char)

    # Clean up whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' +', ' ', text)
    text = text.strip()

    return text
```

## Notes

- Order matters: process headers h6→h1, remove scripts/styles first.
- WeChat uses `data-src` instead of `src` for lazy-loaded images.
- Always decode HTML entities after tag removal.
- Tables are converted to markdown pipe format with header separator.
- **Preserve ALL elements** — tables, images, links, code blocks must never be deleted.
