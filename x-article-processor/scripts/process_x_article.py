#!/usr/bin/env python3
"""
一键处理 X/Twitter 文章：提取、下载图片、翻译、保存

用法：
    python3 process_x_article.py "https://x.com/xxx/status/xxx"
    python3 process_x_article.py "https://x.com/xxx/status/xxx" --tags "AI" "productivity"
    python3 process_x_article.py urls.txt  # 批量处理

环境变量配置：
    X_ARTICLE_ASSETS_DIR: 图片保存目录（默认：~/ai 学习/素材库：阿恒识滴AI/00-inbox/assets）
    X_ARTICLE_OUTPUT_DIR: 文章保存目录（默认：~/ai 学习/素材库：阿恒识滴AI/00-inbox/new）
    X_ARTICLE_EXTRACT_SCRIPT: 提取脚本路径（默认：~/.hermes/skills/wechat-article-to-markdown/scripts/extract_x_article.py）

优化点：
1. 合并所有重复步骤到一个脚本
2. 添加重试机制（3次）
3. 并行下载图片
4. 标准化命名和 frontmatter
5. 添加质量检查
6. 支持环境变量配置
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.request
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ============ 配置 ============

def get_config():
    """从环境变量获取配置，提供默认值"""
    home = os.path.expanduser("~")
    
    # 默认路径
    default_assets = os.path.join(home, "ai 学习", "素材库：阿恒识滴AI", "00-inbox", "assets")
    default_output = os.path.join(home, "ai 学习", "素材库：阿恒识滴AI", "00-inbox", "new")
    default_extract = os.path.join(home, ".hermes", "skills", "wechat-article-to-markdown", "scripts", "extract_x_article.py")
    
    return {
        "assets_dir": os.environ.get("X_ARTICLE_ASSETS_DIR", default_assets),
        "output_dir": os.environ.get("X_ARTICLE_OUTPUT_DIR", default_output),
        "extract_script": os.environ.get("X_ARTICLE_EXTRACT_SCRIPT", default_extract),
        "max_retries": 3,
        "max_workers": 4
    }

CONFIG = get_config()

# ============ 工具函数 ============

def extract_tweet_id(url: str) -> Optional[str]:
    """从 X URL 提取 tweet ID"""
    # 支持多种 URL 格式
    patterns = [
        r'/status/(\d+)',
        r'/statuses/(\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def fetch_with_retry(url: str, output_path: str, retries: int = None) -> bool:
    """带重试的下载（使用curl）"""
    retries = retries or CONFIG["max_retries"]
    for attempt in range(retries):
        try:
            # 使用curl下载，更稳定
            result = subprocess.run(
                ["curl", "-sL", "-o", output_path, url],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                # 检查文件是否下载成功
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    return True
                else:
                    raise Exception("下载的文件为空或不存在")
            else:
                raise Exception(f"curl 返回码: {result.returncode}, 错误: {result.stderr}")
        except Exception as e:
            if attempt == retries - 1:
                print(f"    ✗ 下载失败 (尝试 {retries} 次): {e}")
                return False
            time.sleep(1 * (attempt + 1))  # 指数退避
    return False


def detect_language(text: str) -> str:
    """检测文章语言"""
    # 取前 1000 个字符检测
    sample = text[:1000]
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', sample))
    total_chars = len(sample)
    
    if total_chars == 0:
        return 'en'
    
    # 如果中文字符占比超过 10%，认为是中文
    return 'zh' if chinese_chars / total_chars > 0.1 else 'en'


def generate_slug(title: str, max_length: int = 50) -> str:
    """生成 URL 友好的 slug"""
    # 转小写，替换非字母数字为连字符
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower())
    # 移除首尾连字符
    slug = slug.strip('-')
    # 限制长度
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip('-')
    return slug or 'untitled'


def generate_frontmatter(
    title: str,
    author: str,
    date: str,
    source: str,
    translated: bool,
    cover: str = "",
    tags: List[str] = None
) -> str:
    """生成标准化的 frontmatter"""
    tags = tags or []
    tags_str = "\n".join(f"  - {t}" for t in tags)
    
    # 转义标题中的引号
    escaped_title = title.replace('"', '\\"')
    
    return f"""---
title: "{escaped_title}"
author: "{author}"
date: {date}
source: "{source}"
cover: "{cover}"
translated: {str(translated).lower()}
tags:
{tags_str}
---
"""


# ============ 核心处理函数 ============

def fetch_tweet(tweet_id: str) -> Optional[dict]:
    """获取 tweet JSON 数据"""
    tmp_path = f"/tmp/x_tweet_{tweet_id}.json"
    api_url = f"https://api.fxtwitter.com/status/{tweet_id}"
    
    print(f"  📥 获取 tweet 数据...")
    if fetch_with_retry(api_url, tmp_path):
        try:
            with open(tmp_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"  ✗ JSON 解析失败: {e}")
            return None
    return None


def extract_article_content(tweet_data: dict, tweet_id: str) -> str:
    """提取文章内容为 Markdown"""
    tmp_json = f"/tmp/x_tweet_{tweet_id}.json"
    tmp_md = f"/tmp/x_article_{tweet_id}.md"
    
    # 保存 tweet 数据
    with open(tmp_json, 'w', encoding='utf-8') as f:
        json.dump(tweet_data, f, ensure_ascii=False)
    
    # 调用提取脚本
    print(f"  📄 提取文章内容...")
    extract_script = CONFIG["extract_script"]
    os.system(f"python3 {extract_script} {tmp_json} > {tmp_md}")
    
    # 读取提取的内容
    try:
        with open(tmp_md, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"  ✗ 提取失败")
        return ""


def download_single_image(url: str, filename: str) -> Tuple[str, Optional[str]]:
    """下载单张图片（用于并行下载）"""
    assets_dir = CONFIG["assets_dir"]
    local_path = os.path.join(assets_dir, filename)
    if fetch_with_retry(url, local_path):
        return url, filename
    return url, None


def download_images(tweet_data: dict, slug: str) -> Dict[str, str]:
    """并行下载图片并返回 URL -> 本地路径映射"""
    article = tweet_data.get('tweet', {}).get('article', {})
    media_entities = article.get('media_entities', [])
    
    if not media_entities:
        print(f"  ℹ️  没有图片需要下载")
        return {}
    
    print(f"  🖼️  下载 {len(media_entities)} 张图片...")
    
    # 准备下载任务
    tasks = []
    for i, media in enumerate(media_entities, 1):
        url = media.get('media_info', {}).get('original_img_url', '')
        if not url:
            continue
        
        ext = url.split('.')[-1].split('?')[0]
        filename = f"{slug}-{i:02d}.{ext}"
        tasks.append((url, filename))
    
    # 并行下载
    url_map = {}
    max_workers = CONFIG["max_workers"]
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(download_single_image, url, filename): (url, filename)
            for url, filename in tasks
        }
        
        for future in as_completed(futures):
            url, filename = future.result()
            if filename:
                url_map[url] = filename
                print(f"    ✓ {filename}")
            else:
                print(f"    ✗ {url}")
    
    print(f"  📊 成功下载: {len(url_map)}/{len(tasks)} 张")
    return url_map


def replace_image_urls(content: str, url_map: Dict[str, str]) -> str:
    """替换内容中的图片 URL 为本地路径"""
    for url, filename in url_map.items():
        content = content.replace(url, f"../assets/{filename}")
    return content


def check_remaining_urls(content: str) -> int:
    """检查是否还有未替换的外部图片 URL"""
    return len(re.findall(r'https://pbs\.twimg\.com/', content))


# ============ 主处理流程 ============

def process_single_article(url: str, tags: List[str] = None) -> Optional[str]:
    """处理单篇 X 文章"""
    print(f"\n{'='*60}")
    print(f"🔗 处理文章: {url}")
    print(f"{'='*60}")
    
    # 1. 提取 tweet ID
    tweet_id = extract_tweet_id(url)
    if not tweet_id:
        print(f"✗ 无法从 URL 提取 tweet ID")
        return None
    
    print(f"  🆔 Tweet ID: {tweet_id}")
    
    # 2. 获取 tweet 数据
    tweet_data = fetch_tweet(tweet_id)
    if not tweet_data:
        print(f"✗ 获取 tweet 数据失败")
        return None
    
    # 3. 提取元数据
    tweet = tweet_data.get('tweet', {})
    article = tweet.get('article', {})
    author = tweet.get('author', {}).get('name', 'Unknown')
    title = article.get('title', 'untitled')
    date = datetime.now().strftime('%Y-%m-%d')
    slug = generate_slug(title)
    
    print(f"  📝 标题: {title}")
    print(f"  ✍️  作者: {author}")
    
    # 4. 提取文章内容
    content = extract_article_content(tweet_data, tweet_id)
    if not content:
        print(f"✗ 提取文章内容失败")
        return None
    
    # 5. 检测语言
    lang = detect_language(content)
    need_translate = lang == 'en'
    print(f"  🌐 语言: {'英文 (需要翻译)' if need_translate else '中文'}")
    
    # 6. 下载图片
    url_map = download_images(tweet_data, slug)
    
    # 7. 替换图片 URL
    content = replace_image_urls(content, url_map)
    
    # 8. 检查是否还有未替换的 URL
    remaining = check_remaining_urls(content)
    if remaining > 0:
        print(f"  ⚠️  还有 {remaining} 个未替换的图片 URL")
    
    # 9. 生成 frontmatter
    cover = list(url_map.values())[0] if url_map else ""
    frontmatter = generate_frontmatter(
        title=title,
        author=author,
        date=date,
        source=url,
        translated=need_translate,
        cover=cover,
        tags=tags
    )
    
    # 10. 保存文件
    output_dir = CONFIG["output_dir"]
    filename = f"{date}-{slug}.md"
    filepath = os.path.join(output_dir, filename)
    
    # 确保目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(frontmatter + content)
    
    print(f"\n✅ 处理完成!")
    print(f"   📁 文件: {filename}")
    print(f"   🖼️  图片: {len(url_map)} 张")
    print(f"   🌐 翻译: {'是' if need_translate else '否'}")
    print(f"   📍 路径: {filepath}")
    
    return filepath


def process_batch(urls: List[str], tags: List[str] = None) -> List[str]:
    """批量处理多篇文章"""
    results = []
    total = len(urls)
    
    print(f"\n🚀 开始批量处理 {total} 篇文章")
    print(f"{'='*60}")
    
    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{total}]")
        try:
            filepath = process_single_article(url, tags)
            if filepath:
                results.append(filepath)
        except Exception as e:
            print(f"✗ 处理失败: {e}")
    
    print(f"\n{'='*60}")
    print(f"📊 批量处理完成: {len(results)}/{total} 篇成功")
    
    return results


# ============ 命令行接口 ============

def main():
    parser = argparse.ArgumentParser(
        description="一键处理 X/Twitter 文章",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 处理单篇文章
  python3 process_x_article.py "https://x.com/xxx/status/xxx"
  
  # 处理单篇文章并添加标签
  python3 process_x_article.py "https://x.com/xxx/status/xxx" --tags "AI" "productivity"
  
  # 批量处理（从文件读取 URL）
  python3 process_x_article.py urls.txt
  
  # 批量处理（命令行列出多个 URL）
  python3 process_x_article.py "url1" "url2" "url3"
  
环境变量:
  X_ARTICLE_ASSETS_DIR: 图片保存目录
  X_ARTICLE_OUTPUT_DIR: 文章保存目录
  X_ARTICLE_EXTRACT_SCRIPT: 提取脚本路径
        """
    )
    
    parser.add_argument(
        "urls",
        nargs="+",
        help="X 文章 URL 或包含 URL 的文件路径"
    )
    
    parser.add_argument(
        "--tags",
        nargs="+",
        default=[],
        help="文章标签"
    )
    
    parser.add_argument(
        "--output-dir",
        default=None,
        help=f"输出目录 (默认: {CONFIG['output_dir']})"
    )
    
    parser.add_argument(
        "--assets-dir",
        default=None,
        help=f"图片目录 (默认: {CONFIG['assets_dir']})"
    )
    
    args = parser.parse_args()
    
    # 更新配置
    if args.output_dir:
        CONFIG["output_dir"] = args.output_dir
    if args.assets_dir:
        CONFIG["assets_dir"] = args.assets_dir
    
    # 确保目录存在
    os.makedirs(CONFIG["assets_dir"], exist_ok=True)
    os.makedirs(CONFIG["output_dir"], exist_ok=True)
    
    # 收集所有 URL
    all_urls = []
    for url_or_file in args.urls:
        if os.path.isfile(url_or_file):
            # 从文件读取 URL
            with open(url_or_file, 'r', encoding='utf-8') as f:
                urls_from_file = [
                    line.strip() 
                    for line in f 
                    if line.strip() and not line.startswith('#')
                ]
                all_urls.extend(urls_from_file)
        else:
            # 直接是 URL
            all_urls.append(url_or_file)
    
    if not all_urls:
        print("✗ 没有提供有效的 URL")
        sys.exit(1)
    
    # 处理
    if len(all_urls) == 1:
        # 单篇文章
        process_single_article(all_urls[0], args.tags)
    else:
        # 批量处理
        process_batch(all_urls, args.tags)


if __name__ == "__main__":
    main()