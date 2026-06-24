# Hermes Article Skills

两个 Hermes Agent 技能，用于文章抓取和转换。

## 技能列表

| 技能 | 说明 | 适用范围 |
|------|------|----------|
| `wechat-article-to-markdown` | 微信公众号/飞书/网页文章转 Markdown | 微信、飞书、通用网页 |
| `x-article-processor` | X/Twitter 文章一键处理 | X/Twitter |

## 安装

```bash
# 方式一：通过 URL 安装（推荐）
hermes skills install https://raw.githubusercontent.com/keihang/hermes-article-skills/main/wechat-article-to-markdown/SKILL.md
hermes skills install https://raw.githubusercontent.com/keihang/hermes-article-skills/main/x-article-processor/SKILL.md

# 方式二：手动复制到 ~/.hermes/skills/
git clone https://github.com/keihang/hermes-article-skills.git
cp -r hermes-article-skills/wechat-article-to-markdown ~/.hermes/skills/
cp -r hermes-article-skills/x-article-processor ~/.hermes/skills/
```

## 配置

安装后需设置环境变量，指定你的文章保存目录。在 `~/.hermes/.env` 或 shell profile 中添加：

```bash
# wechat-article-to-markdown 使用
export ARTICLE_OUTPUT_DIR="/path/to/your/inbox"       # 文章保存目录
export ARTICLE_ASSETS_DIR="/path/to/your/assets"      # 图片保存目录
export ARTICLE_PUBLISH_DIR="/path/to/your/publish"    # 发布目录（可选）
export ARTICLE_DRAFT_DIR="/path/to/your/drafts"       # 草稿目录（可选）

# x-article-processor 使用
export X_ARTICLE_OUTPUT_DIR="/path/to/your/inbox"     # 文章保存目录
export X_ARTICLE_ASSETS_DIR="/path/to/your/assets"    # 图片保存目录
export X_ARTICLE_PUBLISH_DIR="/path/to/your/publish"  # 发布目录（可选）
export X_ARTICLE_DRAFT_DIR="/path/to/your/drafts"     # 草稿目录（可选）
export X_ARTICLE_EXTRACT_SCRIPT="/path/to/extract_x_article.py"  # 提取脚本路径（可选）
```

不设置环境变量时，默认保存到 `~/articles/inbox/` 和 `~/articles/assets/`。

## 使用

- 发送微信文章链接（`mp.weixin.qq.com/s/...`）→ 自动触发 `wechat-article-to-markdown`
- 发送飞书文档链接（`*.feishu.cn/wiki/...`）→ 自动触发 `wechat-article-to-markdown`
- 发送 X/Twitter 链接（`x.com/.../status/...`）→ 自动触发 `x-article-processor`

## 依赖

- Python 3.8+
- `html2text`（可选，用于通用网页转换）：`pip install html2text`
- `curl`（用于下载）
