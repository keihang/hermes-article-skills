#!/usr/bin/env python3
"""
微信文章 Shadow DOM 格式提取脚本
用于处理使用 Shadow DOM 渲染的新格式微信文章

用法: python3 extract_shadow_dom.py /tmp/wechat_article.html
输出: Markdown 格式的文章内容
"""

import sys
import re
import html as html_module


def extract_from_shadow_dom(html_content):
    """从 Shadow DOM 格式的 HTML 中提取文章内容"""
    
    # 方法 1: 匹配 content 变量
    pattern = r'content:\s*[\'"](.+?)[\'"]'
    matches = re.findall(pattern, html_content, re.DOTALL)
    
    if matches:
        # 取最长的匹配（通常是正文）
        longest_match = max(matches, key=len)
        return decode_content(longest_match)
    
    # 方法 2: 尝试其他可能的变量名
    alt_patterns = [
        r'article_content:\s*[\'"](.+?)[\'"]',
        r'articleContent:\s*[\'"](.+?)[\'"]',
        r'body:\s*[\'"](.+?)[\'"]',
    ]
    
    for pattern in alt_patterns:
        matches = re.findall(pattern, html_content, re.DOTALL)
        if matches:
            longest_match = max(matches, key=len)
            return decode_content(longest_match)
    
    return None


def decode_content(raw_content):
    """解码转义字符"""
    decoded = raw_content
    
    # 解码十六进制转义
    decoded = decoded.replace('\\x0a', '\n')
    decoded = decoded.replace('\\x09', '\t')
    decoded = decoded.replace('\\x26lt;', '<')
    decoded = decoded.replace('\\x26gt;', '>')
    decoded = decoded.replace('\\x26quot;', '"')
    decoded = decoded.replace('\\x26amp;', '&')
    
    # 解码标准转义
    decoded = decoded.replace('\\n', '\n')
    decoded = decoded.replace('\\t', '\t')
    decoded = decoded.replace('\\"', '"')
    decoded = decoded.replace("\\'", "'")
    
    # 解码 HTML 实体
    decoded = html_module.unescape(decoded)
    
    return decoded


def clean_content(content):
    """清理提取的内容"""
    if not content:
        return content
    
    # 处理内联链接 HTML
    # 将 <a href="...">文字</a> 转换为 [文字](链接)
    link_pattern = r'<a[^>]*href="([^"]*)"[^>]*>([^<]*)</a>'
    content = re.sub(link_pattern, r'[\2](\1)', content)
    
    # 去除剩余的 HTML 标签
    content = re.sub(r'<[^>]+>', '', content)
    
    # 清理空行（合并连续空行为单个）
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    # 去除首尾空白
    content = content.strip()
    
    return content


def extract_metadata(html_content):
    """提取文章元数据"""
    metadata = {}
    
    # 标题
    title_match = re.search(r'og:title" content="([^"]*)"', html_content)
    if title_match:
        metadata['title'] = html_module.unescape(title_match.group(1))
    
    # 作者
    author_match = re.search(r'og:article:author" content="([^"]*)"', html_content)
    if author_match:
        metadata['author'] = html_module.unescape(author_match.group(1))
    
    # 时间戳
    ct_match = re.search(r'var ct = "(\d+)"', html_content)
    if ct_match:
        metadata['timestamp'] = ct_match.group(1)
    
    return metadata


def main():
    if len(sys.argv) < 2:
        print("用法: python3 extract_shadow_dom.py <html_file>", file=sys.stderr)
        sys.exit(1)
    
    html_file = sys.argv[1]
    
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        print(f"错误: 文件不存在 - {html_file}", file=sys.stderr)
        sys.exit(1)
    
    # 提取元数据
    metadata = extract_metadata(html_content)
    
    # 提取内容
    content = extract_from_shadow_dom(html_content)
    
    if not content:
        print("ERROR: 无法提取文章内容（Shadow DOM 格式）", file=sys.stderr)
        sys.exit(1)
    
    # 清理内容
    content = clean_content(content)
    
    # 输出结果
    if metadata.get('title'):
        print(f"# {metadata['title']}")
        print()
    
    if metadata.get('author'):
        print(f"**作者**: {metadata['author']}")
        print()
    
    print(content)


if __name__ == '__main__':
    main()
