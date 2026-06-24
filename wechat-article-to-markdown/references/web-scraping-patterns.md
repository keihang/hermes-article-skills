# 通用网页抓取模式

## Next.js 图片优化

Next.js 站点使用 `/_next/image?url=...` 格式的图片 URL。

**提取方法**：
```python
from urllib.parse import unquote
import re

img_urls = re.findall(r'(/_next/image\?url=[^"&]+)', html)
for url in img_urls:
    decoded = unquote(url)  # → /blog/slug/image.webp
```

**下载**：拼接站点域名 + decoded 路径即可。

## html2text 使用要点

```python
import html2text
h = html2text.HTML2Text()
h.ignore_links = False   # 保留链接
h.ignore_images = False  # 保留图片
h.body_width = 0         # 不自动换行
```

**清理噪音**：html2text 会保留 header/footer/nav 内容，需手动清理：
- 网站导航栏
- 页脚版权信息
- 侧边栏
- 广告/推广内容
- CTA 按钮

## 常见站点结构

| 站点类型 | 正文位置 | 图片格式 |
|----------|----------|----------|
| 微信公众号 | `#js_content` div | `data-src` 懒加载 |
| X/Twitter | fxtwitter API JSON | `pbs.twimg.com` |
| Next.js 博客 | `<article>` 或 `<main>` | `/_next/image?url=` |
| WordPress | `.entry-content` 或 `#content` | 直接 URL |
| 飞书 | Open API | 需 auth token |

## 图片下载注意事项

- `pbs.twimg.com`：curl SSL 失败（exit 35），用 Python urllib 替代
- Next.js 图片：需解码 URL 参数，拼接站点域名
- 微信图片：从 `data-src` 提取，跳过 `data:image/svg+xml` 占位符
- 懒加载图片：检查 `data-src`、`data-original`、`loading="lazy"` 等属性
