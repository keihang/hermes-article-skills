#!/usr/bin/env python3
"""从下载的微信公众号 HTML 中提取正文并转为 Markdown。

用法：
    python3 extract_wechat.py < /tmp/wechat_article.html > /tmp/wechat_content.md
    或
    python3 extract_wechat.py /tmp/wechat_article.html > /tmp/wechat_content.md
"""
import re
import html
import sys


def extract_content(html_text: str) -> str:
    # 定位正文区域
    start_marker = 'id="js_content"'
    end_markers = ['class="rich_media_tool"', 'var first_sceen__time']

    start_idx = html_text.find(start_marker)
    if start_idx == -1:
        return "ERROR: Could not find js_content"

    end_idx = len(html_text)
    for marker in end_markers:
        idx = html_text.find(marker, start_idx)
        if idx != -1 and idx < end_idx:
            end_idx = idx

    content = html_text[start_idx:end_idx]

    # 去掉 js_content 的 id/style 属性
    content = re.sub(r'id="js_content"\s*', '', content, count=1)
    content = re.sub(r'style="[^"]*visibility:\s*hidden[^"]*"', '', content, count=1)

    # 图片：从 data-src 提取真实 URL
    def convert_img(match):
        tag = match.group(0)
        data_src = re.search(r'data-src="([^"]*)"', tag)
        alt = re.search(r'alt="([^"]*)"', tag)
        if data_src:
            url = data_src.group(1)
            alt_text = alt.group(1) if alt else "图片"
            return f'\n![{alt_text}]({url})\n'
        return ''

    content = re.sub(r'<img[^>]*>', convert_img, content)

    # 链接
    def convert_link(match):
        tag = match.group(0)
        href = re.search(r'href="([^"]*)"', tag)
        text = re.sub(r'<[^>]+>', '', tag).strip()
        if href and text:
            return f'[{text}]({href.group(1)})'
        return text

    content = re.sub(r'<a[^>]*>.*?</a>', convert_link, content, flags=re.DOTALL)

    # 代码块：<pre><code>...</code></pre> — 先去除内部 <span> 标签
    def convert_pre_code(match):
        code_content = match.group(1)
        code_content = re.sub(r'</?span[^>]*>', '', code_content)
        code_content = code_content.strip()
        return f'\n```\n{code_content}\n```\n'

    content = re.sub(r'<pre[^>]*><code[^>]*>(.*?)</code></pre>', convert_pre_code, content, flags=re.DOTALL)
    content = re.sub(r'<pre[^>]*>(.*?)</pre>', convert_pre_code, content, flags=re.DOTALL)

    # 内联代码（不在 pre 内的 code）
    # 简单处理：把 <code>text</code> 变成 `text`
    content = re.sub(r'<code[^>]*>(.*?)</code>', r'`\1`', content, flags=re.DOTALL)

    # 标题
    for i in range(6, 0, -1):
        content = re.sub(
            f'<h{i}[^>]*>(.*?)</h{i}>',
            lambda m, level=i: f'\n{"#" * level} {m.group(1).strip()}\n',
            content, flags=re.DOTALL
        )

    # 加粗 / 斜体
    content = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', content, flags=re.DOTALL)
    content = re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', content, flags=re.DOTALL)
    content = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', content, flags=re.DOTALL)
    content = re.sub(r'<i[^>]*>(.*?)</i>', r'*\1*', content, flags=re.DOTALL)

    # 列表
    content = re.sub(r'<li[^>]*>(.*?)</li>', r'\n- \1', content, flags=re.DOTALL)
    content = re.sub(r'<ul[^>]*>(.*?)</ul>', r'\1', content, flags=re.DOTALL)
    content = re.sub(r'<ol[^>]*>(.*?)</ol>', r'\1', content, flags=re.DOTALL)

    # 引用
    content = re.sub(r'<blockquote[^>]*>(.*?)</blockquote>', lambda m: f'\n> {m.group(1).strip()}\n', content, flags=re.DOTALL)

    # 段落 / 换行 / div
    content = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', content, flags=re.DOTALL)
    content = re.sub(r'<br\s*/?>', '\n', content)
    content = re.sub(r'<div[^>]*>(.*?)</div>', r'\1\n', content, flags=re.DOTALL)
    content = re.sub(r'<section[^>]*>(.*?)</section>', r'\1\n', content, flags=re.DOTALL)

    # 去除剩余 HTML 标签
    content = re.sub(r'<[^>]+>', '', content)

    # 解码 HTML 实体
    content = html.unescape(content)

    # 清理孤立的 blockquote 标记（微信文章中 section/div 嵌套 blockquote 产生的残留）
    content = re.sub(r'^\s*>\s*\n', '', content)

    # 清理空白
    content = re.sub(r'\n{3,}', '\n\n', content)
    content = content.strip()

    return content


def main():
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            html_text = f.read()
    else:
        html_text = sys.stdin.read()

    print(extract_content(html_text))


if __name__ == '__main__':
    main()
