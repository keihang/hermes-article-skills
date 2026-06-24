# WeChat Article HTML Structure Patterns

WeChat (微信公众号) articles at `mp.weixin.qq.com` have specific HTML patterns.

## Metadata Extraction

```python
import re, datetime

# Title — in an h1 with class rich_media_title
title_match = re.search(r'rich_media_title[^>]*>(.*?)</h1>', html, re.DOTALL)
title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()

# Author / 公众号名称 — in JS var
author_match = re.search(r'nickname\s*=\s*["\'](.+?)["\']', html)
author = author_match.group(1)

# Publish timestamp — Unix epoch in JS var
time_match = re.search(r'var ct = "(\d+)"', html)
pub_time = datetime.datetime.fromtimestamp(int(time_match.group(1))).strftime('%Y-%m-%d %H:%M:%S')
```

## Content Extraction

```python
# Main content div
content_match = re.search(r'id="js_content"[^>]*>(.*)', html, re.DOTALL)
content_html = content_match.group(1)

# Cut at the tools/footer section
end_match = re.search(r'<div[^>]*class="rich_media_tool"', content_html)
if end_match:
    content_html = content_html[:end_match.start()]
```

## Key Characteristics

- **Lazy images**: Use `data-src` attribute, not `src`. The `src` is often a placeholder.
- **Rich formatting**: Articles often use `<section>` with inline styles rather than semantic HTML.
- **Content markers**: `id="js_content"` is the standard content container.
- **Footer marker**: `class="rich_media_tool"` marks end of article content.
- **User-Agent required**: Bare curl without browser UA gets 403 or empty response.
- **Page size**: Typical articles are 100KB–3MB of HTML due to inline styles.
